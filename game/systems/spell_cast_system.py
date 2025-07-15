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
                             UIMessagePayload, LogRequestPayload, ManaCostRequestPayload)
from ..core.components import (ManaComponent, DeadComponent, HealthComponent, ShieldComponent,
                               StatusEffectContainerComponent, SpellListComponent)
from ..core.entity import Entity
from .data_manager import DataManager
from game.status_effects.status_effect_factory import StatusEffectFactory
from typing import Dict, Any, Optional
from game.world import World

class SpellCastSystem:
    def __init__(self, event_bus: EventBus, data_manager: DataManager, world: World):
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.world = world
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
            return

        # 应用法术效果
        self.apply_spell(caster, target, spell_id)

    def apply_spell(self, caster: Entity, target: Entity, spell_id: str):
        # 获取法术效果列表
        effects = self.data_manager.get_spell_effects(spell_id)
        
        # 初始化效果解析的负载对象
        resolution_payload = EffectResolutionPayload(caster=caster, target=target, source_spell=spell_id)
        
        # 遍历法术的所有效果
        for effect in effects:
            self._apply_single_effect(caster, target, effect, resolution_payload)
            
        # 派发最终的效果解析完成事件，UI系统等会监听这个事件来显示结果
        resolution_payload.finalize()
        if resolution_payload.effect_produced:
             self.event_bus.dispatch(GameEvent(EventName.EFFECT_RESOLUTION_COMPLETE, resolution_payload))
        else:
            resolution_payload.no_effect_produced = True
            self.event_bus.dispatch(GameEvent(EventName.EFFECT_RESOLUTION_COMPLETE, resolution_payload))
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload('[Spell System]', f'法术{spell_id}没有产生任何效果')))

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