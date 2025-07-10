from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import (CastSpellRequestPayload, ManaCostRequestPayload, DamageRequestPayload,
                             HealRequestPayload, ApplyStatusEffectRequestPayload, DispelRequestPayload,
                             LogRequestPayload, UIMessagePayload, AmplifyPoisonRequestPayload,
                             DetonatePoisonRequestPayload, ReduceDebuffsRequestPayload)
from .data_manager import DataManager
from ..status_effects.status_effect_factory import StatusEffectFactory
from ..status_effects.status_effect import StatusEffect
from ..status_effects.effect_logic import DamageOverTimeEffect, StatModificationLogic, OverhealConversionLogic, EffectLogic
from ..core.components import CritComponent

EFFECT_LOGIC_MAP = {
    "dot": DamageOverTimeEffect,
    "stat_mod": StatModificationLogic,
    "overheal": OverhealConversionLogic
}

class SpellCastSystem:
    """ <<< 职责变更: 现在施法时会派发LOG事件 >>> """
    def __init__(self, event_bus: EventBus, data_manager: DataManager, status_effect_factory: StatusEffectFactory):
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.status_effect_factory = status_effect_factory
        event_bus.subscribe(EventName.CAST_SPELL_REQUEST, self.on_spell_cast_request)

    def on_spell_cast_request(self, event: GameEvent):
        payload: CastSpellRequestPayload = event.payload
        spell_data = self.data_manager.get_spell_data(payload.spell_id)
        if not spell_data: 
            return

        # Log the cast attempt
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            tag="[SPELL]", message=f"{payload.caster.name} 准备施放 {spell_data['name']} (目标: {payload.target.name})"
        )))

        # 检查法力消耗
        mana_cost = self.data_manager.get_spell_cost(payload.spell_id)
        mana_request = ManaCostRequestPayload(entity=payload.caster, cost=mana_cost)
        self.event_bus.dispatch(GameEvent(EventName.MANA_COST_REQUEST, mana_request))
        
        if not mana_request.is_affordable:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[SPELL]", "施法失败: 法力不足")))
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**提示**: [{payload.caster.name}] 法力不足!")))
            return
        
        # 处理所有法术效果
        effects = self.data_manager.get_spell_effects(payload.spell_id)
        
        for effect in effects:
            effect_type = effect.get('type')
            
            if effect_type == "damage":
                crit_comp = payload.caster.get_component(CritComponent)
                crit_chance = crit_comp.crit_chance
                crit_damage_multiplier = crit_comp.crit_damage_multiplier

                damage_payload = DamageRequestPayload(
                    caster=payload.caster, 
                    target=payload.target, 
                    source_spell_id=payload.spell_id,
                    source_spell_name=spell_data["name"],
                    base_damage=effect["amount"], 
                    original_base_damage=effect["amount"],
                    damage_type=effect["damage_type"],
                    lifesteal_ratio=effect.get("lifesteal_ratio", 0),
                    is_reflection=effect.get("is_reflection", False),
                    can_be_reflected=spell_data.get("can_be_reflected", False),

                    # 暴击配置优先级：versions.can_crit > versions.can_be_crit > spell.can_crit > spell.can_be_crit
                    can_crit=spell_data.get("can_crit", False),
                    crit_chance=crit_chance,
                    crit_damage_multiplier=crit_damage_multiplier
                )
                self.event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, damage_payload))

            elif effect_type == "heal":
                heal_payload = HealRequestPayload(
                    caster=payload.caster, target=payload.target, 
                    source_spell_id=payload.spell_id,
                    source_spell_name=spell_data["name"],
                    base_heal=effect["amount"], 
                    heal_type=effect["heal_type"],

                    overheal_to_shield_config=effect.get("overheal_to_shield")
                )
                self.event_bus.dispatch(GameEvent(EventName.HEAL_REQUEST, heal_payload))

            elif effect_type == "apply_status_effect":
                status_effect_id = effect.get("status_effect_id")
                if not status_effect_id: continue

                new_effect = self.status_effect_factory.create_effect(status_effect_id, payload.caster)

                if new_effect:
                    self.event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, ApplyStatusEffectRequestPayload(
                        target=payload.target,
                        effect=new_effect
                    )))
            elif effect_type == "dispel":
                self.event_bus.dispatch(GameEvent(EventName.DISPEL_REQUEST, DispelRequestPayload(
                    target=payload.target,
                    category_to_dispel=effect.get("category", "uncategorized"),
                    count=effect.get("count")
                )))
            elif effect_type == "amplify_poison":
                amplify_amount = effect.get("amplify_amount", 2)
                self.event_bus.dispatch(GameEvent(EventName.AMPLIFY_POISON_REQUEST, AmplifyPoisonRequestPayload(
                    target=payload.target,
                    amplify_amount=amplify_amount,
                    caster=payload.caster,
                    source_spell_id=payload.spell_id,
                    source_spell_name=spell_data["name"]
                )))
            elif effect_type == "detonate_poison":
                damage_multiplier = effect.get("damage_multiplier", 1.0)
                self.event_bus.dispatch(GameEvent(EventName.DETONATE_POISON_REQUEST, DetonatePoisonRequestPayload(
                    target=payload.target,
                    damage_multiplier=damage_multiplier,
                    caster=payload.caster,
                    source_spell_id=payload.spell_id,
                    source_spell_name=spell_data["name"]
                )))
            elif effect_type == "reduce_debuffs":
                reduce_stack_count = effect.get("reduce_stack_count", 0)
                reduce_duration_count = effect.get("reduce_duration_count", 0)
                self.event_bus.dispatch(GameEvent(EventName.REDUCE_DEBUFFS_REQUEST, ReduceDebuffsRequestPayload(
                    target=payload.target,
                    reduce_stack_count=reduce_stack_count,
                    reduce_duration_count=reduce_duration_count
                )))
            # 可以在这里添加更多效果类型的处理