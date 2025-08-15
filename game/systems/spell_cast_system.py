# 导入新的处理器
from .effect_handlers.direct_damage_handler import DirectDamageHandler
from .effect_handlers.heal_handler import HealHandler
from .effect_handlers.apply_status_effect_handler import ApplyStatusEffectHandler
from .effect_handlers.add_shield_handler import AddShieldHandler
from .effect_handlers.dispel_handler import DispelHandler
from .effect_handlers.multi_effect_handler import MultiEffectHandler
from .effect_handlers.amplify_poison_handler import AmplifyPoisonHandler
from .effect_handlers.detonate_poison_handler import DetonatePoisonHandler
from .effect_handlers.reduce_debuffs_handler import ReduceDebuffsHandler

from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import (CastSpellRequestPayload, EffectResolutionPayload, DispelRequestPayload, 
                             UIMessagePayload, LogRequestPayload, ManaCostRequestPayload, EnergyCostRequestPayload, UltimateChargeRequestPayload)
from ..core.components import (ManaComponent, DeadComponent, HealthComponent, ShieldComponent,
                               StatusEffectContainerComponent, SpellListComponent, EnergyComponent, UltimateChargeComponent)
from ..core.entity import Entity
from .data_manager import DataManager
from game.status_effects.status_effect_factory import StatusEffectFactory
from typing import Dict, Any, Optional
from game.world import World
from game.core.payloads import ActionRequestPayload
from game.core.payloads import ActionAfterActPayload
from game.systems.ultimate_charge_system import UltimateChargeSystem

class SpellCastSystem:
    def __init__(self, event_bus: EventBus, data_manager: DataManager, world: World, ultimate_charge_system: 'UltimateChargeSystem' = None):
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.world = world
        self.ultimate_charge_system = ultimate_charge_system
        self.status_effect_factory = StatusEffectFactory(data_manager)
        
        # 注册事件监听
        event_bus.subscribe(EventName.CAST_SPELL_REQUEST, self.on_cast_spell_request)

        # 创建并注册所有的效果处理器
        self.effect_handlers = {
            "damage": DirectDamageHandler(event_bus, data_manager, world),
            "heal": HealHandler(event_bus, data_manager, world),
            "apply_status_effect": ApplyStatusEffectHandler(event_bus, data_manager, world),
            "add_shield": AddShieldHandler(event_bus, data_manager, world),
            "dispel": DispelHandler(event_bus, data_manager, world),
            "multi_effect": MultiEffectHandler(event_bus, data_manager, world),
            "amplify_poison": AmplifyPoisonHandler(event_bus, data_manager, world),
            "detonate_poison": DetonatePoisonHandler(event_bus, data_manager, world),
            "reduce_debuffs": ReduceDebuffsHandler(event_bus, data_manager, world),
        }
        
        # 为 MultiEffectHandler 注入对本系统实例的引用
        multi_handler = self.effect_handlers.get("multi_effect")
        if multi_handler and isinstance(multi_handler, MultiEffectHandler):
            # 类型注解：明确指定spell_effect_system的类型
            multi_handler.spell_effect_system = self  # type: ignore

    def on_cast_spell_request(self, event: GameEvent):
        payload: CastSpellRequestPayload = event.payload
        caster, target, spell_id = payload.caster, payload.target, payload.spell_id

        # 获取法术数据
        spell_data = self.data_manager.get_spell_data(spell_id)
        if not spell_data:
            return

        # 检查是否是全体目标法术
        target_type = self.data_manager.get_spell_target_type(spell_id)
        
        # 只有单体法术才在这里播报，群体法术会在_apply_spell_to_all_targets中播报
        if target_type not in ["all_enemies", "all_allies"]:
            # 记录施法尝试
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                tag="[SPELL]", message=f"{caster.name} 准备施放 {spell_data['name']} (目标: {target.name})"
            )))

        # 检查法力消耗
        mana_cost = self.data_manager.get_spell_cost(spell_id)
        mana_request = ManaCostRequestPayload(entity=caster, cost=mana_cost)
        self.event_bus.dispatch(GameEvent(EventName.MANA_COST_REQUEST, mana_request))
        
        if not mana_request.is_affordable:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[SPELL]", "施法失败: 法力不足")))
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**提示**: [{caster.name}] 法力不足!")))
            # 施法失败，不派发ACTION_AFTER_ACT事件，让玩家重新选择
            return

        # 检查能量点消耗
        energy_cost = self.data_manager.get_spell_energy_cost(spell_id)
        if energy_cost > 0:
            energy_request = EnergyCostRequestPayload(entity=caster, cost=energy_cost)
            self.event_bus.dispatch(GameEvent(EventName.ENERGY_COST_REQUEST, energy_request))
            
            if not energy_request.is_affordable:
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[SPELL]", "施法失败: 能量不足")))
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**提示**: [{caster.name}] 能量不足!")))
                # 施法失败，不派发ACTION_AFTER_ACT事件，让玩家重新选择
                return

        # 检查终极技能消耗
        ultimate_cost = self.data_manager.get_spell_ultimate_cost(spell_id)
        if ultimate_cost > 0:
            ultimate_request = UltimateChargeRequestPayload(entity=caster, cost=ultimate_cost)
            self.event_bus.dispatch(GameEvent(EventName.ULTIMATE_CHARGE_REQUEST, ultimate_request))
            
            if not ultimate_request.is_affordable:
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[SPELL]", "施法失败: 充能不足")))
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**提示**: [{caster.name}] 充能不足!")))
                # 施法失败，不派发ACTION_AFTER_ACT事件，让玩家重新选择
                return

        # 应用法术效果
        self.apply_spell(caster, target, spell_id)

    def apply_spell(self, caster: Entity, target: Entity, spell_id: str):
        # 获取法术数据
        spell_data = self.data_manager.get_spell_data(spell_id)
        if not spell_data:
            return
            
        # 检查是否是全体目标法术
        target_type = self.data_manager.get_spell_target_type(spell_id)
        if target_type in ["all_enemies", "all_allies"]:
            # 全体目标法术 - 对多个目标施法
            self._apply_spell_to_all_targets(caster, target, spell_id, target_type)
        else:
            # 单体目标法术 - 原有逻辑
            self._apply_spell_to_single_target(caster, target, spell_id)
    
    def _apply_spell_to_single_target(self, caster: Entity, target: Entity, spell_id: str):
        """对单个目标施法"""
        # 获取法术效果列表
        effects = self.data_manager.get_spell_effects(spell_id)
        
        # 初始化效果解析的负载对象
        resolution_payload = EffectResolutionPayload(caster=caster, target=target, source_spell=spell_id)
        
        # 遍历法术的所有效果
        for effect in effects:
            self._apply_single_effect(caster, target, effect, resolution_payload)
            
        # 派发最终的效果解析完成事件，UI系统等会监听这个事件来显示结果
        resolution_payload.finalize()
        # 移除"没有产生任何效果"的播报，因为战斗解析系统会正确处理效果判断
        self.event_bus.dispatch(GameEvent(EventName.EFFECT_RESOLUTION_COMPLETE, resolution_payload))
        
        # 新增：从施法中获取终极技能充能值
        if self.ultimate_charge_system:
            self.ultimate_charge_system.add_charge_from_spell(caster, spell_id, self.data_manager)
        
        # 新增：施法成功后，派发 ACTION_AFTER_ACT 事件，结算当前角色的状态效果并结束回合
        self.event_bus.dispatch(GameEvent(EventName.ACTION_AFTER_ACT, ActionAfterActPayload(caster)))
    
    def _apply_spell_to_all_targets(self, caster: Entity, selected_target: Entity, spell_id: str, target_type: str):
        """对全体目标施法"""
        from ..core.components import AIControlledComponent, PlayerControlledComponent, DeadComponent, TeamComponent
        
        # 获取施法者的阵营
        caster_team = None
        if caster.has_component(TeamComponent):
            caster_team = caster.get_component(TeamComponent).team_id
        
        # 根据目标类型和施法者阵营获取所有有效目标
        if target_type == "all_enemies":
            # 攻击敌方全体：根据施法者阵营选择目标
            if caster_team == "player":
                # 玩家攻击敌人
                all_targets = [e for e in self.world.entities 
                              if e.has_component(TeamComponent) and 
                              e.get_component(TeamComponent).team_id == "enemy" and
                              not e.has_component(DeadComponent)]
            else:
                # 敌人攻击玩家
                all_targets = [e for e in self.world.entities 
                              if e.has_component(TeamComponent) and 
                              e.get_component(TeamComponent).team_id == "player" and
                              not e.has_component(DeadComponent)]
        elif target_type == "all_allies":
            # 治疗我方全体：根据施法者阵营选择目标
            if caster_team == "player":
                # 玩家治疗玩家
                all_targets = [e for e in self.world.entities 
                              if e.has_component(TeamComponent) and 
                              e.get_component(TeamComponent).team_id == "player" and
                              not e.has_component(DeadComponent)]
            else:
                # 敌人治疗敌人
                all_targets = [e for e in self.world.entities 
                              if e.has_component(TeamComponent) and 
                              e.get_component(TeamComponent).team_id == "enemy" and
                              not e.has_component(DeadComponent)]
        else:
            # 如果不是全体目标，回退到单体施法
            self._apply_spell_to_single_target(caster, selected_target, spell_id)
            return
        
        # 获取法术数据用于播报
        spell_data = self.data_manager.get_spell_data(spell_id)
        spell_name = spell_data.get('name', '未知法术') if spell_data else '未知法术'
        
        # 构建目标名称列表用于播报
        target_names = [target.name for target in all_targets]
        targets_str = ", ".join(target_names)
        
        # 记录群体施法播报
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            tag="[SPELL]", message=f"{caster.name} 准备施放 {spell_name} (目标: {targets_str})"
        )))
        
        # 获取法术效果列表
        effects = self.data_manager.get_spell_effects(spell_id)
        
        # 对每个目标施法
        for target in all_targets:
            # 初始化效果解析的负载对象
            resolution_payload = EffectResolutionPayload(caster=caster, target=target, source_spell=spell_id)
            
            # 遍历法术的所有效果
            for effect in effects:
                self._apply_single_effect(caster, target, effect, resolution_payload)
                
            # 派发最终的效果解析完成事件
            resolution_payload.finalize()
            # 移除"没有产生任何效果"的播报，因为战斗解析系统会正确处理效果判断
            self.event_bus.dispatch(GameEvent(EventName.EFFECT_RESOLUTION_COMPLETE, resolution_payload))
        
        # 新增：从施法中获取终极技能充能值
        if self.ultimate_charge_system:
            self.ultimate_charge_system.add_charge_from_spell(caster, spell_id, self.data_manager)
        
        # 新增：施法成功后，派发 ACTION_AFTER_ACT 事件，结算当前角色的状态效果并结束回合
        self.event_bus.dispatch(GameEvent(EventName.ACTION_AFTER_ACT, ActionAfterActPayload(caster)))

    def _apply_single_effect(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        """应用单个效果，查询处理器并委托任务"""
        effect_type = effect.get('type')
        if effect_type is None:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload('[Spell System]', f'警告: 效果缺少type字段')))
            return
            
        handler = self.effect_handlers.get(effect_type)

        if handler:
            handler.apply(caster, target, effect, payload)
        else:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload('[Spell System]', f'警告: 未知的法术效果类型: {effect_type}')))