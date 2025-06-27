# 核心导入
from ...core.event_bus import EventBus, GameEvent
from ...core.enums import EventName
from ...core.payloads import (DamageRequestPayload, HealRequestPayload, GainShieldPayload,
                             LogRequestPayload, EffectResolutionPayload, ResourceChangeEntry)
from ...core.components import HealthComponent, DefenseComponent, ThornsComponent
from ...core.entity import Entity

# 依赖的系统和数据管理器
from ..data_manager import DataManager
from ..passive_ability_system import PassiveAbilitySystem

# 导入计算流水线
from .damage_modifiers import (DamageResolutionContext, DefenseHandler, ResistanceHandler,
                             HealResolutionContext, GrievousWoundsHandler)

class CombatResolutionSystem:
    def __init__(self, event_bus: EventBus, data_manager: DataManager, passive_system: PassiveAbilitySystem):
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.passive_system = passive_system
        self.damage_pipeline = [DefenseHandler(), ResistanceHandler()]
        self.heal_pipeline = [GrievousWoundsHandler()]
        event_bus.subscribe(EventName.DAMAGE_REQUEST, self.on_damage_request)
        event_bus.subscribe(EventName.HEAL_REQUEST, self.on_heal_request)
        event_bus.subscribe(EventName.GAIN_SHIELD_REQUEST, self.on_gain_shield_request)

    def on_damage_request(self, event):
        payload: DamageRequestPayload = event.payload
        health_comp = payload.target.get_component(HealthComponent)
        if not health_comp: return

        # 处理反射伤害（通常是最终伤害，不进入计算流水线）
        if payload.is_reflection:
            health_comp.hp -= payload.base_damage
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "COMBAT", f"反射伤害: {payload.target.name} 对 {payload.caster.name} 造成了 {payload.base_damage:.1f} 点伤害")))
            return

        context = DamageResolutionContext(
            caster=payload.caster, target=payload.target, source_spell_id=payload.source_spell_id,
            damage_type=payload.damage_type, current_damage=payload.base_damage)
        
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "COMBAT", f"基础伤害: {context.current_damage:.1f}")))
        
        pre_defense_value = payload.target.get_component(DefenseComponent).defense_value if payload.target.get_component(DefenseComponent) else 0
        for modifier in self.damage_pipeline:
            modifier.process(context, self.event_bus)
        post_defense_value = payload.target.get_component(DefenseComponent).defense_value if payload.target.get_component(DefenseComponent) else 0
        shield_blocked = pre_defense_value - post_defense_value

        final_damage = context.current_damage
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("COMBAT", f"最终伤害: {final_damage:.1f}")))
        
        if final_damage > 0:
            health_comp.hp -= final_damage
            # 处理反伤
            if thorns_comp := payload.target.get_component(ThornsComponent):
                reflection_damage = final_damage * thorns_comp.thorns_percentage
                # ... 派发新的反射伤害事件 ...
            # 处理吸血
            if payload.lifesteal_ratio and payload.lifesteal_ratio > 0:
                lifesteal_amount = final_damage * payload.lifesteal_ratio
                # ... 派发新的治疗事件 ...
        
        resource_changes = [ResourceChangeEntry("health", -final_damage, health_comp.hp, health_comp.max_hp)]
        self.event_bus.dispatch(GameEvent(EventName.EFFECT_RESOLUTION_COMPLETE, EffectResolutionPayload(
            caster=payload.caster, target=payload.target, source_spell=payload.source_spell_id,
            resource_changes=resource_changes, shield_blocked=shield_blocked,
            passive_triggers=self.passive_system.get_and_clear_pending_triggers()
        )))

    def on_heal_request(self, event):
        payload: HealRequestPayload = event.payload
        health_comp = payload.target.get_component(HealthComponent)
        if not health_comp: return

        context = HealResolutionContext(
            caster=payload.caster, target=payload.target, source_spell_id=payload.source_spell_id,
            source_spell_name=payload.source_spell_name, current_heal=payload.base_heal)
        
        for modifier in self.heal_pipeline:
            modifier.process(context, self.event_bus)
        
        final_heal = context.current_heal
        old_hp = health_comp.hp
        health_comp.hp += final_heal
        actual_heal = health_comp.hp - old_hp
        overheal = final_heal - actual_heal
        payload.overheal_amount = overheal

        # 处理溢出治疗
        if overheal > 0:
            # 检查法术本身的溢疗转换
            if payload.overheal_conversion_rate is not None:
                shield_gain = overheal * payload.overheal_conversion_rate
                # ... 派发护盾事件 ...
            
            # 检查是否有buff/debuff需要对治疗事件做出反应
            if container := payload.target.get_component('StatusEffectContainerComponent'): # type: ignore
                for effect in container.effects:
                    effect.logic.on_heal(payload, effect, self.event_bus)
        
        # ... 派发 EFFECT_RESOLUTION_COMPLETE 事件 ...
        
    def on_gain_shield_request(self, event):
        payload: GainShieldPayload = event.payload
        defense_comp = payload.target.get_component(DefenseComponent)
        if defense_comp:
            defense_comp.defense_value += payload.amount
        else:
            payload.target.add_component(DefenseComponent(defense_value=payload.amount))
        # ... 派发 LOG_REQUEST 事件 ...