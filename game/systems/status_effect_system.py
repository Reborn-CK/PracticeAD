from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import (ApplyStatusEffectRequestPayload, RemoveStatusEffectRequestPayload,
                             UpdateStatusEffectsDurationRequestPayload, DispelRequestPayload,
                             StatQueryPayload, LogRequestPayload, UIMessagePayload)
from ..core.components import StatusEffectContainerComponent, DeadComponent
from ..status_effects.status_effect import StatusEffect

class StatusEffectSystem:
    def __init__(self, event_bus: EventBus, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.world = world
        self.event_bus.subscribe(EventName.ROUND_START, self.on_round_start)
        self.event_bus.subscribe(EventName.APPLY_STATUS_EFFECT_REQUEST, self.on_apply_effect)
        self.event_bus.subscribe(EventName.REMOVE_STATUS_EFFECT_REQUEST, self.on_remove_effect)
        self.event_bus.subscribe(EventName.UPDATE_STATUS_EFFECTS_DURATION_REQUEST, self.on_update_effects_duration)
        self.event_bus.subscribe(EventName.DISPEL_REQUEST, self.on_dispel_effect)
        self.event_bus.subscribe(EventName.STAT_QUERY, self.on_stat_query)
    
    def on_apply_effect(self, event: GameEvent):
        payload: ApplyStatusEffectRequestPayload = event.payload
        container = payload.target.get_component(StatusEffectContainerComponent)
        if not container:
            container = payload.target.add_component(StatusEffectContainerComponent())
        
        effect = payload.effect
        existing_effect = next((e for e in container.effects if e.effect_id == effect.effect_id), None)
        
        if existing_effect:
            if effect.stacking == "refresh_duration":
                existing_effect.duration = max(existing_effect.duration, effect.duration)
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态**: {payload.target.name} 的 [{effect.name}] 持续时间刷新了")))
            elif effect.stacking == "stack_intensity":
                existing_effect.stack_count = min(existing_effect.stack_count + effect.stack_count, effect.max_stacks)
                existing_effect.duration = effect.duration
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态**: {payload.target.name} 的 [{effect.name}] 叠加至 {existing_effect.stack_count} 层")))
        else:
            container.effects.append(effect)
            effect.logic.on_apply(payload.target, effect, self.event_bus)
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态**: {payload.target.name} 获得了 [{effect.name}]")))

    def on_dispel_effect(self, event: GameEvent):
        # ... (与原文件逻辑相同) ...
        pass

    def on_stat_query(self, event: GameEvent):
        container = event.payload.entity.get_component(StatusEffectContainerComponent)
        if container:
            for effect in container.effects:
                effect.logic.on_stat_query(event.payload, effect)
    
    def on_remove_effect(self, event: GameEvent):
        # ... (与原文件逻辑相同) ...
        pass

    def on_update_effects_duration(self, event: GameEvent):
        # ... (与原文件逻辑相同) ...
        pass

    def on_round_start(self, event: GameEvent):
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("STATUS", "---状态效果结算阶段---")))
        for entity in self.world.entities:
            if entity.has_component(DeadComponent): continue

            container = entity.get_component(StatusEffectContainerComponent)
            if not container: continue

            # Tick and decrement duration
            for effect in list(container.effects):
                effect.logic.on_tick(entity, effect, self.event_bus)
                if effect.duration > 0: # -1 for permanent effects
                    effect.duration -= 1
            
            # Remove expired
            expired_effects = [e for e in container.effects if e.duration == 0]
            for expired in expired_effects:
                expired.logic.on_remove(entity, expired, self.event_bus)
                container.effects.remove(expired)
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态**: {entity.name} 的 [{expired.name}] 效果结束了")))

        self.event_bus.dispatch(GameEvent(EventName.STATUS_EFFECTS_RESOLVED))