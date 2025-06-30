from abc import ABC, abstractmethod
from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import StatQueryPayload, HealRequestPayload, UIMessagePayload, DamageRequestPayload, GainShieldPayload
from ..core.entity import Entity
from .status_effect import StatusEffect

class EffectLogic(ABC):
    """buff，debuff的抽象基类"""
    def on_apply(self, target: Entity, effect: StatusEffect, event_bus: EventBus): pass
    def on_tick(self, target: Entity, effect: StatusEffect, event_bus: EventBus): pass
    def on_remove(self, target: Entity, effect: StatusEffect, event_bus: EventBus): pass
    def on_stat_query(self, query: StatQueryPayload, effect: StatusEffect): pass
    def on_heal(self, payload: HealRequestPayload, effect: StatusEffect, event_bus: EventBus): pass

class DamageOverTimeEffect(EffectLogic):
    """持续伤害效果"""
    def on_tick(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        damage_per_round = effect.context.get("damage_per_round", 0)
        stacks = effect.stack_count
        total_damage = damage_per_round * stacks
        if total_damage > 0:
            event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                f"**持续伤害**: {target.name} 因[{effect.name} x{stacks}] 受到了 {total_damage:.1f} 点伤害"
            )))
            event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                caster=effect.caster or target,
                target=target,
                source_spell_id=effect.effect_id,
                source_spell_name=effect.name,
                base_damage=total_damage,
                damage_type=effect.context.get("damage_type", "pure"),
                is_reflection=False
            )))

class StatModificationLogic(EffectLogic):
    """属性修改效果"""
    def on_stat_query(self, query: StatQueryPayload, effect: StatusEffect):
        stat_mods = effect.context.get("stat_mods", {})
        if query.stat_name in stat_mods:
            mods = stat_mods[query.stat_name]
            query.current_value *= mods.get("multiply", 1)
            query.current_value += mods.get("add", 0)
    
    def on_remove(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        pass

class OverhealConversionLogic(EffectLogic):
    """溢疗转换效果"""
    def on_heal(self, payload: HealRequestPayload, effect: StatusEffect, event_bus: EventBus):
        if payload.overheal_conversion_rate is not None:
            rate = effect.context.get("conversion_rate", 0)
            shield_gain = payload.overheal_amount * rate
            if shield_gain > 0:
                event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                    f"**被动**: {payload.target.name}在[{effect.name}]下将 {payload.overheal_amount:.1f}点溢出治疗转化为 {shield_gain:.1f}点护盾"
                )))
                event_bus.dispatch(GameEvent(EventName.GAIN_SHIELD_REQUEST, GainShieldPayload(
                    target=payload.target, source=effect.name, amount=shield_gain
                )))

class PoisonDotEffect(EffectLogic):
    """中毒持续伤害效果 - 基于状态数量，结算后层数减1"""
    def on_tick(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        # 伤害计算：基础伤害 × 1（与层数无关，只与状态数量相关）
        damage_per_round = effect.context.get("damage_per_round", 0)
        total_damage = damage_per_round  # 每个中毒状态造成基础伤害，与层数无关
        if total_damage > 0:
            event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                f"**持续伤害**: {target.name} 因[{effect.name}] 受到了 {total_damage:.1f} 点伤害"
            )))
            event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                caster=effect.caster or target,
                target=target,
                source_spell_id=effect.effect_id,
                source_spell_name=effect.name,
                base_damage=total_damage,
                damage_type=effect.context.get("damage_type", "pure"),
                is_reflection=False
            )))
    
    def on_remove(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        pass