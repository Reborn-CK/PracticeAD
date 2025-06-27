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
from ..status_effects.status_effect_factory import StatusEffectFactory


class InteractionSystem:
    def __init__(self, event_bus: EventBus, data_manager: DataManager, status_effect_factory: StatusEffectFactory):
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.status_effect_factory = status_effect_factory

        self.event_bus.subscribe(EventName.CAST_SPELL_REQUEST, self.on_spell_cast)
        self.event_bus.subscribe(EventName.DAMAGE_REQUEST, self.on_damage)

    def _get_target_effect(self, target: Entity, effect_id: str) -> Optional[StatusEffect]:
        """辅助函数：检查目标身上是否有指定ID效果"""
        container = target.get_component(StatusEffectContainerComponent)
        if container:
            return next((e for e in container.effects if e.effect_id == effect_id), None)
        return None

    def on_spell_cast(self, event: GameEvent):
        """处理施法时的直接互动，如'燃烬'."""
        payload: CastSpellRequestPayload = event.payload
        interactions = self.data_manager.get_spell_interactions(payload.spell_id)

        for inter in interactions:
            if inter.get("type") == "on_cast":
                target_effect_id = inter.get("target_has_effect")
                target_effect_instance = self._get_target_effect(payload.target, target_effect_id)
                if target_effect_instance:
                    self._execute_interaction_action(
                        inter, 
                        payload.caster, 
                        payload.target, 
                        payload.spell_id,
                        target_effect_instance
                    )

    def on_damage(self, event: GameEvent):
        payload: DamageRequestPayload = event.payload
        if payload.is_reflection: return

        interactions = self.data_manager.get_spell_interactions(payload.source_spell_id)

        for inter in interactions:
            if inter.get("type") == "on_damage_deal":
                target_effect_id = inter.get("target_has_effect")
                target_effect_instance = self._get_target_effect(payload.target, target_effect_id)
                if target_effect_instance:
                    self._execute_interaction_action(
                        inter, 
                        payload.caster, 
                        payload.target, 
                        payload.source_spell_id, 
                        target_effect_instance, 
                        damage_payload=payload
                    )
    
    def _execute_interaction_action(self, interaction_data: dict, caster: Entity, target: Entity, source_spell_id: str, target_effect: StatusEffect, damage_payload: Optional[DamageRequestPayload] = None):
        """根据action类型执行不同的交互逻辑"""
        action = interaction_data.get("action")
        context = interaction_data.get("context", {})

        if action == "consume_and_damage":
            damage=0
            if context.get("damage_source") == "remaining_dot_damage":
                dot_damage = target_effect.context.get("damage_per_round", 0)
                remaining_duration = target_effect.duration
                damage = dot_damage * remaining_duration
            
            if damage > 0:
                #派发伤害
                self.event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                    caster=caster, 
                    target=target, 
                    source_spell_id=source_spell_id, 
                    source_spell_name=self.data_manager.get_spell_data(source_spell_id).get('name', '燃烬引爆'),
                    base_damage=damage, 
                    damage_type=context.get("damage_type", "pure")
                )))
                # 移除被消耗的效果
                self.event_bus.dispatch(GameEvent(EventName.REMOVE_STATUS_EFFECT_REQUEST,RemoveStatusEffectRequestPayload(
                    target=target, 
                    effect_id=target_effect.effect_id)))

        elif action == "extinguish":
            if damage_payload:
                damage_payload.base_damage *= context.get("damage_multiplier", 1)
            
            if (remove_id := context.get("remove_effect_id")):
                self.event_bus.dispatch(GameEvent(EventName.REMOVE_STATUS_EFFECT_REQUEST,RemoveStatusEffectRequestPayload(
                    target=target, 
                    effect_id=remove_id
                )))
            if (apply_id := context.get("apply_status_effect_id")):
                new_effect = self.status_effect_factory.create_effect(apply_id, caster)
                #effect_data = self.data_manager.get_status_effect_data(apply_id)
                # if effect_data:
                #     logic_class =  EFFECT_LOGIC_MAP.get(effect_data.get("logic", ""), EffectLogic)
                #     new_effect = StatusEffect(
                #         effect_id=apply_id,
                #         name= effect_data["name"],
                #         duration=effect_data["duration"],
                #         caster=caster,
                #         context=effect_data.get("context", {}),
                #         logic=logic_class()
                #     )
                if new_effect:
                    self.event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, ApplyStatusEffectRequestPayload(
                        target=target,
                        effect=new_effect
                    )))
        elif action == "extend_duration":
            change = context.get("extend_duration", 0)
            if change != 0:
                self.event_bus.dispatch(GameEvent(EventName.UPDATE_STATUS_EFFECTS_DURATION_REQUEST,UpdateStatusEffectsDurationRequestPayload(
                    target=target, 
                    effect_id=target_effect.effect_id, 
                    change=change
                )))
        
        if (message_template := context.get("message")):
            spell_name = self.data_manager.get_spell_data(source_spell_id).get("name") if source_spell_id else "法术联动"
            formatted_message = message_template.format(
                caster_name=caster.name,
                target_name=target.name,
                spell_name=spell_name,
                damage= damage if 'damage' in locals() else 0
            )
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(formatted_message)))