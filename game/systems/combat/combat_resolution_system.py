from dataclasses import dataclass
from typing import TYPE_CHECKING
from ...core.event_bus import EventBus, GameEvent
from ...core.enums import EventName
from ...core.payloads import DamageRequestPayload, HealRequestPayload, LogRequestPayload, EffectResolutionPayload, GainShieldPayload
from ...core.components import HealthComponent, DefenseComponent, StatusEffectContainerComponent
from ...core.pipeline import Pipeline, EffectExecutionContext

# --- 导入新的处理器 ---
from .damage_processors import CritHandler, DefenseHandler, ResistanceHandler, LifestealHandler, ThornsHandler, AttackTriggerPassiveHandler
from .heal_processors import GrievousWoundsHandler, OverhealToShieldHandler, SkillOverhealToShieldHandler, StatusEffectOverhealToShieldHandler

if TYPE_CHECKING:
    from ..data_manager import DataManager
    from ..passive_ability_system import PassiveAbilitySystem

class CombatResolutionSystem:
    def __init__(self, event_bus: EventBus, data_manager: 'DataManager' = None, passive_system: 'PassiveAbilitySystem' = None, status_effect_factory=None):
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.passive_system = passive_system
        self.status_effect_factory = status_effect_factory

        # --- 1. 定义伤害处理管线 ---
        # 伤害计算阶段 (顺序很重要：暴击 -> 护盾 -> 抗性)
        damage_calculation_processors = [
            CritHandler(self.event_bus),
            DefenseHandler(self.event_bus),
            ResistanceHandler(self.event_bus),
        ]
        # 造成伤害后阶段 (吸血、反伤、攻击触发被动)
        post_damage_processors = [
            LifestealHandler(self.event_bus),
            ThornsHandler(self.event_bus),
            AttackTriggerPassiveHandler(self.event_bus, self.status_effect_factory),
        ]
        self.damage_pipeline = Pipeline(processors=damage_calculation_processors)
        self.post_damage_pipeline = Pipeline(processors=post_damage_processors)

        # --- 2. 定义治疗处理管线 ---
        heal_calculation_processors = [
            GrievousWoundsHandler(self.event_bus),
        ]

        #新增治疗后管线
        post_heal_processors = [
            StatusEffectOverhealToShieldHandler(self.event_bus),
            SkillOverhealToShieldHandler(self.event_bus),
            OverhealToShieldHandler(self.event_bus)
        ]
        self.heal_pipeline = Pipeline(processors=heal_calculation_processors)
        self.post_heal_pipeline = Pipeline(processors=post_heal_processors)

        # --- 3. 订阅事件 ---
        event_bus.subscribe(EventName.DAMAGE_REQUEST, self.on_damage_request)
        event_bus.subscribe(EventName.HEAL_REQUEST, self.on_heal_request)
        event_bus.subscribe(EventName.GAIN_SHIELD_REQUEST, self.on_gain_shield_request)

    def on_damage_request(self, event: GameEvent):
        payload: DamageRequestPayload = event.payload
        
        # 记录攻击前的状态，用于判断是否有实际效果
        target_health_before = payload.target.get_component(HealthComponent).hp if payload.target.get_component(HealthComponent) else 0
        target_shield_before = payload.target.get_component(DefenseComponent).defense_value if payload.target.get_component(DefenseComponent) else 0
        target_status_effects_before = len(payload.target.get_component(StatusEffectContainerComponent).effects) if payload.target.get_component(StatusEffectContainerComponent) else 0
        
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "[COMBAT]", f"--- 开始伤害结算: {payload.source_spell_name} from {payload.caster.name} to {payload.target.name} ---"
        )))
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "[COMBAT]", f"基础伤害: {payload.base_damage:.1f}"
        )))
        
        # 创建伤害执行上下文，将 payload 所有属性作为 metadata 传入. copy()是为了不改变payload的值
        payload_dict = vars(payload).copy()
        # 移除已经在构造函数中明确指定的参数
        payload_dict.pop('caster', None)
        payload_dict.pop('target', None)
        
        context = EffectExecutionContext(
            source=payload.caster,
            target=payload.target,
            effect_type='damage',
            initial_value=payload.base_damage,
            **payload_dict
        )
        
        # 执行伤害计算管线
        resolved_context = self.damage_pipeline.execute(context)
        final_damage = int(resolved_context.current_value)
        
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "[COMBAT]", f"最终伤害: {final_damage:.1f}"
        )))

        # 施加伤害
        if final_damage > 0:
            if (health_comp := payload.target.get_component(HealthComponent)):
                health_comp.hp -= final_damage
        
        # 执行造成伤害后的管线 (吸血、反伤、攻击触发被动)
        self.post_damage_pipeline.execute(resolved_context)
        
        # 记录攻击后的状态
        target_health_after = payload.target.get_component(HealthComponent).hp if payload.target.get_component(HealthComponent) else 0
        target_shield_after = payload.target.get_component(DefenseComponent).defense_value if payload.target.get_component(DefenseComponent) else 0
        target_status_effects_after = len(payload.target.get_component(StatusEffectContainerComponent).effects) if payload.target.get_component(StatusEffectContainerComponent) else 0
        
        # 检查是否有实际效果产生
        health_changed = target_health_before != target_health_after
        shield_changed = target_shield_before != target_shield_after
        shield_change_amount = target_shield_after - target_shield_before  # 计算护盾变化数值
        new_status_effects = target_status_effects_after > target_status_effects_before
        
        # 检查是否有实际效果产生
        has_effect = health_changed or shield_changed or new_status_effects
        
        # 构建资源变化列表
        resource_changes = []
        
        # 添加生命值变化
        if health_changed:
            health_change_amount = target_health_after - target_health_before
            resource_changes.append({
                'resource_name': 'health',
                'change_amount': health_change_amount,
                'current_value': target_health_after,
                'max_value': payload.target.get_component(HealthComponent).max_hp if payload.target.get_component(HealthComponent) else None
            })
        
        # 添加护盾变化
        if shield_changed:
            resource_changes.append({
                'resource_name': 'shield',
                'change_amount': shield_change_amount,
                'current_value': target_shield_after,
                'max_value': None
            })
        
        # 只有非被动伤害才触发UI播报
        if not payload.is_passive_damage:
            # 派发结算完成事件
            self.event_bus.dispatch(GameEvent(EventName.EFFECT_RESOLUTION_COMPLETE, EffectResolutionPayload(
                caster=payload.caster, 
                target=payload.target,
                source_spell=payload.source_spell_id,
                resource_changes=resource_changes,
                health_changed=health_changed,
                shield_changed=shield_changed,
                shield_change_amount=shield_change_amount,
                shield_before=target_shield_before,
                new_status_effects=new_status_effects,
                no_effect_produced=not has_effect,
                is_dot_damage=getattr(payload, 'is_dot_damage', False)  # 新增
            )))
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[COMBAT]", "--- 伤害结算完毕 ---")))


    def on_heal_request(self, event: GameEvent):
        payload: HealRequestPayload = event.payload
        
        # 记录治疗前的状态，用于判断是否有实际效果
        target_health_before = payload.target.get_component(HealthComponent).hp if payload.target.get_component(HealthComponent) else 0
        target_shield_before = payload.target.get_component(DefenseComponent).defense_value if payload.target.get_component(DefenseComponent) else 0
        target_status_effects_before = len(payload.target.get_component(StatusEffectContainerComponent).effects) if payload.target.get_component(StatusEffectContainerComponent) else 0
        
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "[HEAL]", f"--- 开始治疗结算: {payload.source_spell_name} on {payload.target.name} ---"
        )))
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
             "[HEAL]", f"基础治疗: {payload.base_heal:.1f}"
        )))

        # 创建治疗执行上下文
        payload_dict = vars(payload).copy()
        # 移除已经在构造函数中明确指定的参数
        payload_dict.pop('caster', None)
        payload_dict.pop('target', None)
        
        context = EffectExecutionContext(
            source=payload.caster,
            target=payload.target,
            effect_type='heal',
            initial_value=payload.base_heal,
            **payload_dict
        )
        # 如果治疗不可被修改（如吸血），直接跳过管线
        if not payload.can_be_modified:
            final_heal = payload.base_heal
        else:
            # 执行治疗计算管线
            resolved_context = self.heal_pipeline.execute(context)
            final_heal = resolved_context.current_value
        
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "[HEAL]", f"最终治疗: {int(final_heal):.1f}"
        )))

        # 计算实际治疗量和溢出治疗量
        actual_heal = 0
        overheal_amount = 0

        if final_heal > 0:
            if (health_comp := payload.target.get_component(HealthComponent)):
                missing_health = health_comp.max_hp - health_comp.hp
                actual_heal = min(final_heal, missing_health)
                overheal_amount = final_heal - actual_heal

                context.current_value = actual_heal
                context.overheal_amount = overheal_amount

        # 施加治疗
        if final_heal > 0:
            health_comp.hp += actual_heal
        if overheal_amount > 0:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[HEAL]", f"实际治疗: {actual_heal:.1f}, 溢出治疗: {overheal_amount:.1f}"
             )))
        
        # 执行治疗后管线
        self.post_heal_pipeline.execute(context)
        
        # 记录治疗后的状态
        target_health_after = payload.target.get_component(HealthComponent).hp if payload.target.get_component(HealthComponent) else 0
        target_shield_after = payload.target.get_component(DefenseComponent).defense_value if payload.target.get_component(DefenseComponent) else 0
        target_status_effects_after = len(payload.target.get_component(StatusEffectContainerComponent).effects) if payload.target.get_component(StatusEffectContainerComponent) else 0
        
        # 检查是否有实际效果产生
        health_changed = target_health_before != target_health_after
        shield_changed = target_shield_before != target_shield_after
        shield_change_amount = target_shield_after - target_shield_before  # 计算护盾变化数值
        new_status_effects = target_status_effects_after > target_status_effects_before
        
        # 检查是否有实际效果产生
        has_effect = health_changed or shield_changed or new_status_effects
        
        # 构建资源变化列表
        resource_changes = []
        
        # 添加生命值变化
        if health_changed:
            health_change_amount = target_health_after - target_health_before
            resource_changes.append({
                'resource_name': 'health',
                'change_amount': health_change_amount,
                'current_value': target_health_after,
                'max_value': payload.target.get_component(HealthComponent).max_hp if payload.target.get_component(HealthComponent) else None
            })
        
        # 添加护盾变化
        if shield_changed:
            resource_changes.append({
                'resource_name': 'shield',
                'change_amount': shield_change_amount,
                'current_value': target_shield_after,
                'max_value': None
            })
        
        # 派发结算完成事件
        self.event_bus.dispatch(GameEvent(EventName.EFFECT_RESOLUTION_COMPLETE, EffectResolutionPayload(
            caster=payload.caster,
            target=payload.target,
            source_spell=payload.source_spell_name,  # 使用法术名称而不是ID
            resource_changes=resource_changes,
            health_changed=health_changed,
            shield_changed=shield_changed,
            shield_change_amount=shield_change_amount,
            shield_before=target_shield_before,
            new_status_effects=new_status_effects,
            no_effect_produced=not has_effect,
            is_dot_damage=False  # 治疗不是持续伤害
        )))
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[HEAL]", "--- 治疗结算完毕 ---")))
    def on_gain_shield_request(self, event: GameEvent):
        payload: GainShieldPayload = event.payload
        if (defense_comp := payload.target.get_component(DefenseComponent)):
            defense_comp.defense_value += payload.amount
        else:
            defense_comp = payload.target.add_component(DefenseComponent(defense_value=payload.amount))
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[COMBAT]", f"来源[{payload.source}] 获得了 {payload.amount:.1f} 点护盾")))