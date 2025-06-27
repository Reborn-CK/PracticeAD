from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import (CastSpellRequestPayload, LogRequestPayload, ManaCostRequestPayload, 
                             UIMessagePayload, DamageRequestPayload, HealRequestPayload, 
                             ApplyStatusEffectRequestPayload, DispelRequestPayload)
from .data_manager import DataManager
# 在阶段二，我们会注入工厂。目前暂时保持原样
from ..status_effects.status_effect import StatusEffect
from ..status_effects.effect_logic import DamageOverTimeEffect, StatModificationLogic, OverhealConversionLogic, EffectLogic

EFFECT_LOGIC_MAP = {
    "dot": DamageOverTimeEffect,
    "stat_mod": StatModificationLogic,
    "overheal": OverhealConversionLogic
}

class SpellCastSystem:
    def __init__(self, event_bus: EventBus, data_manager: DataManager):
        self.event_bus = event_bus
        self.data_manager = data_manager
        event_bus.subscribe(EventName.CAST_SPELL_REQUEST, self.on_spell_cast_request)

    def on_spell_cast_request(self, event: GameEvent):
        payload: CastSpellRequestPayload = event.payload
        spell_data = self.data_manager.get_spell_data(payload.spell_id)
        if not spell_data: return

        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "SPELL", f"{payload.caster.name} 准备施放 {spell_data['name']} (目标: {payload.target.name})")))

        mana_cost = self.data_manager.get_spell_cost(payload.spell_id)
        mana_request = ManaCostRequestPayload(entity=payload.caster, cost=mana_cost)
        self.event_bus.dispatch(GameEvent(EventName.MANA_COST_REQUEST, mana_request))
        
        if not mana_request.is_affordable:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("SPELL", "施法失败: 法力不足")))
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**提示**: [{payload.caster.name}] 法力不足!")))
            return
        
        effects = self.data_manager.get_spell_effects(payload.spell_id)
        for effect in effects:
            effect_type = effect.get('type')
            
            if effect_type == "damage":
                self.event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                    caster=payload.caster, target=payload.target, source_spell_id=payload.spell_id,
                    source_spell_name=spell_data["name"], base_damage=effect["amount"], 
                    damage_type=effect["damage_type"], lifesteal_ratio=effect.get("lifesteal_ratio")
                )))
            elif effect_type == "heal":
                self.event_bus.dispatch(GameEvent(EventName.HEAL_REQUEST, HealRequestPayload(
                    caster=payload.caster, target=payload.target, source_spell_id=payload.spell_id,
                    source_spell_name=spell_data["name"], base_heal=effect["amount"], heal_type=effect["heal_type"],
                    overheal_conversion_rate=next((e.get("conversion_rate") for e in effects if e.get('type') == 'overheal'), None)
                )))
            elif effect_type == "apply_status_effect":
                status_effect_id = effect.get("status_effect_id")
                if not status_effect_id: continue
                effect_data = self.data_manager.get_status_effect_data(status_effect_id)
                if not effect_data: continue
                logic_class = EFFECT_LOGIC_MAP.get(effect_data.get("logic", ""), EffectLogic)
                new_effect = StatusEffect(
                    effect_id=status_effect_id, name=effect_data['name'], duration=effect_data['duration'],
                    category=effect_data.get("category", "uncategorized"), stacking=effect_data.get("stacking", "refresh_duration"),
                    max_stacks=effect_data.get("max_stacks", 1), caster=payload.caster,
                    context=effect_data.get("context", {}), logic=logic_class()
                )
                self.event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, ApplyStatusEffectRequestPayload(
                    target=payload.target, effect=new_effect)))
            elif effect_type == "dispel":
                # ...
                pass