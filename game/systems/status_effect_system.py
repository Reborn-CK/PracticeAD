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
        target = payload.target
        effect = payload.effect
        container = target.get_component(StatusEffectContainerComponent)

        if not container:
            container = target.add_component(StatusEffectContainerComponent())
        
        existing_effect = next((e for e in container.effects if e.effect_id == effect.effect_id), None)
        if existing_effect:
            if effect.stacking == "refresh_duration":
                existing_effect.duration = max(existing_effect.duration, effect.duration)
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 的 {effect.name} 效果持续时间刷新为 {existing_effect.duration} 回合")))
            elif effect.stacking == "stack_intensity":
                existing_effect.stack_count = min(existing_effect.stack_count + effect.stack_count, effect.max_stacks)
                existing_effect.duration = effect.duration
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 的 {effect.name} 效果叠加为 {existing_effect.stack_count} 层, 持续时间刷新为 {existing_effect.duration} 回合")))
            
        else:
            container.effects.append(effect)
            effect.logic.on_apply(target, effect, self.event_bus)
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 获得了 {effect.name} 效果")))
    
    def on_dispel_effect(self, event: GameEvent):
        payload: DispelRequestPayload = event.payload
        container = payload.target.get_component(StatusEffectContainerComponent)
        if not container: return
        effects_to_dispel = [e for e in container.effects if e.category == payload.category_to_dispel]
        for i in range(min(payload.count, len(effects_to_dispel))):
            effect = effects_to_dispel[i]
            effect.logic.on_remove(payload.target, effect, self.event_bus)
            container.effects.remove(effect)
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {payload.target.name} 的 {effect.name} 效果已移除")))
    
    def on_stat_query(self, event: GameEvent):
        container = event.payload.entity.get_component(StatusEffectContainerComponent)
        if container:
            for effect in container.effects:
                effect.logic.on_stat_query(event.payload, effect)
    
    def on_remove_effect(self, event: GameEvent):
        payload: RemoveStatusEffectRequestPayload = event.payload
        container = payload.target.get_component(StatusEffectContainerComponent)
        if container:
            effect_to_remove = next((e for e in container.effects if e.effect_id == payload.effect_id), None)
            if effect_to_remove:
                effect_to_remove.logic.on_remove(payload.target, effect_to_remove, self.event_bus)
                container.effects.remove(effect_to_remove)
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", f"[{payload.target.name}] 状态效果 {payload.effect_id} 已移除")))
    
    def on_update_effects_duration(self, event: GameEvent):
        payload: UpdateStatusEffectsDurationRequestPayload = event.payload
        container = payload.target.get_component(StatusEffectContainerComponent)
        if container:
            effect = next((e for e in container.effects if e.effect_id == payload.effect_id), None)
            if effect:
                effect.duration += payload.change
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", f"[{payload.target.name}] 状态效果 {payload.effect_id} 的持续时间更新为 {effect.duration} 回合")))

    def on_round_start(self, event: GameEvent):
        """回合开始时，处理所有实体的状态效果"""
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", "---状态效果结算阶段---")))
        for entity in self.world.entities:
            if entity.has_component(DeadComponent):
                continue

            container = entity.get_component(StatusEffectContainerComponent)
            if not container: continue

            for effect in list(container.effects):
                effect.logic.on_tick(entity, effect, self.event_bus)
                effect.duration -= 1

            # 移除已过期的状态效果
            expired_effects = [e for e in container.effects if e.duration <= 0]
            for expired_effect in expired_effects:
                expired_effect.logic.on_remove(entity, expired_effect, self.event_bus)
                container.effects.remove(expired_effect)
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", f"[{entity.name}] 状态效果 {expired_effect.name} 效果已过期")))
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {entity.name} 的 {expired_effect.name} 效果已结束")))
        
        # 状态结算完毕，发出通知
        self.event_bus.dispatch(GameEvent(EventName.STATUS_EFFECTS_RESOLVED))