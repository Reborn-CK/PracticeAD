from typing import Optional

# 核心导入
from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import (CastSpellRequestPayload, DamageRequestPayload, RemoveStatusEffectRequestPayload,
                             UpdateStatusEffectsDurationRequestPayload, ApplyStatusEffectRequestPayload, UIMessagePayload)
from ..core.entity import Entity
from ..core.components import StatusEffectContainerComponent

# 依赖
from .data_manager import DataManager
from ..status_effects.status_effect import StatusEffect

# 这个系统也需要创建StatusEffect，所以暂时也需要这个逻辑
from ..status_effects.effect_logic import DamageOverTimeEffect, StatModificationLogic, OverhealConversionLogic, EffectLogic
EFFECT_LOGIC_MAP = {
    "dot": DamageOverTimeEffect, "stat_mod": StatModificationLogic, "overheal": OverhealConversionLogic
}

class InteractionSystem:
    def __init__(self, event_bus: EventBus, data_manager: DataManager):
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.event_bus.subscribe(EventName.CAST_SPELL_REQUEST, self.on_spell_cast)
        self.event_bus.subscribe(EventName.DAMAGE_REQUEST, self.on_damage)

    def _get_target_effect(self, target: Entity, effect_id: str) -> Optional[StatusEffect]:
        container = target.get_component(StatusEffectContainerComponent)
        if container:
            return next((e for e in container.effects if e.effect_id == effect_id), None)
        return None

    def on_spell_cast(self, event: GameEvent):
        payload: CastSpellRequestPayload = event.payload
        interactions = self.data_manager.get_spell_interactions(payload.spell_id)
        for inter in interactions:
            if inter.get("type") == "on_cast":
                if target_effect := self._get_target_effect(payload.target, inter.get("target_has_effect")):
                    self._execute_interaction_action(inter, payload.caster, payload.target, payload.spell_id, target_effect)

    def on_damage(self, event: GameEvent):
        payload: DamageRequestPayload = event.payload
        if payload.is_reflection: return
        interactions = self.data_manager.get_spell_interactions(payload.source_spell_id)
        for inter in interactions:
            if inter.get("type") == "on_damage_deal":
                if target_effect := self._get_target_effect(payload.target, inter.get("target_has_effect")):
                    self._execute_interaction_action(inter, payload.caster, payload.target, payload.source_spell_id, target_effect, damage_payload=payload)

    def _execute_interaction_action(self, inter_data: dict, caster: Entity, target: Entity, spell_id: str,
                                   target_effect: StatusEffect, damage_payload: Optional[DamageRequestPayload] = None):
        action = inter_data.get("action")
        context = inter_data.get("context", {})
        damage = 0

        if action == "consume_and_damage":
            if context.get("damage_source") == "remaining_dot_damage":
                dot_damage = target_effect.context.get("damage_per_round", 0)
                damage = dot_damage * target_effect.duration
            if damage > 0:
                self.event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                    caster=caster, target=target, source_spell_id=spell_id,
                    source_spell_name=self.data_manager.get_spell_data(spell_id).get('name', '燃烬引爆'),
                    base_damage=damage, damage_type=context.get("damage_type", "pure")
                )))
            self.event_bus.dispatch(GameEvent(EventName.REMOVE_STATUS_EFFECT_REQUEST, RemoveStatusEffectRequestPayload(
                target=target, effect_id=target_effect.effect_id)))

        elif action == "extinguish":
            if damage_payload: damage_payload.base_damage *= context.get("damage_multiplier", 1.0)
            if remove_id := context.get("remove_effect_id"):
                self.event_bus.dispatch(GameEvent(EventName.REMOVE_STATUS_EFFECT_REQUEST, RemoveStatusEffectRequestPayload(target, remove_id)))
            if apply_id := context.get("apply_status_effect_id"):
                effect_data = self.data_manager.get_status_effect_data(apply_id)
                if effect_data:
                    logic_class = EFFECT_LOGIC_MAP.get(effect_data.get("logic", ""), EffectLogic)
                    new_effect = StatusEffect(
                        effect_id=apply_id, name=effect_data["name"], duration=effect_data["duration"],
                        caster=caster, context=effect_data.get("context", {}), logic=logic_class()
                    )
                    self.event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, ApplyStatusEffectRequestPayload(target, new_effect)))
        
        elif action == "extend_duration":
            if change := context.get("extend_duration", 0):
                self.event_bus.dispatch(GameEvent(EventName.UPDATE_STATUS_EFFECTS_DURATION_REQUEST,
                    UpdateStatusEffectsDurationRequestPayload(target, target_effect.effect_id, change)))

        if msg_template := context.get("message"):
            spell_name = self.data_manager.get_spell_data(spell_id).get("name")
            formatted_msg = msg_template.format(caster_name=caster.name, target_name=target.name, source_spell_name=spell_name, damage=damage)
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(formatted_msg)))