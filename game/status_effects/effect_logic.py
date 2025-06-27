from abc import ABC, abstractmethod
from ..core.event_bus import GameEvent, EventBus
from ..core.enums import EventName
from ..core.payloads import HealRequestPayload, StatQueryPayload, DamageRequestPayload, UIMessagePayload, GainShieldPayload
from ..core.entity import Entity

class EffectLogic(ABC):
    """buff，debuff的抽象基类"""
    def on_apply(self, target: Entity, effect: 'StatusEffect', event_bus: EventBus): pass # type: ignore
    def on_tick(self, target: Entity, effect: 'StatusEffect', event_bus: EventBus): pass # type: ignore
    def on_remove(self, target: Entity, effect: 'StatusEffect', event_bus: EventBus): pass # type: ignore
    def on_stat_query(self, query: StatQueryPayload, effect: 'StatusEffect'): pass # type: ignore
    def on_heal(self, payload: HealRequestPayload, effect: 'StatusEffect', event_bus: EventBus): pass # type: ignore

class DamageOverTimeEffect(EffectLogic):
    """持续伤害效果"""
    def on_tick(self, target: Entity, effect: 'StatusEffect', event_bus: EventBus): # type: ignore
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
    def on_stat_query(self, query: StatQueryPayload, effect: 'StatusEffect'): # type: ignore
        stat_mods = effect.context.get("stat_mods", {})
        if query.stat_name in stat_mods:
            mods = stat_mods[query.stat_name]
            query.current_value *= mods.get("multiply", 1)
            query.current_value += mods.get("add", 0)

class OverhealConversionLogic(EffectLogic):
    """溢疗转换效果"""
    def on_heal(self, payload: HealRequestPayload, effect: 'StatusEffect', event_bus: EventBus): # type: ignore
        if payload.overheal_amount > 0:
            rate = effect.context.get("conversion_rate", 0)
            shield_gain = payload.overheal_amount * rate
            if shield_gain > 0:
                event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                    f"**被动**: {payload.target.name}在[{effect.name}]下将 {payload.overheal_amount:.1f}点溢出治疗转化为 {shield_gain:.1f}点护盾"
                )))
                event_bus.dispatch(GameEvent(EventName.GAIN_SHIELD_REQUEST, GainShieldPayload(
                    target=payload.target, source=effect.name, amount=shield_gain
                )))