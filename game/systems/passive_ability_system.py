from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import HealthChangePayload, LogRequestPayload, GainShieldPayload
from ..core.components import EntageShieldUsedComponent

class PassiveAbilitySystem:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.pending_passive_triggers = []
        event_bus.subscribe(EventName.HEALTH_CHANGED, self.on_health_changed)
    
    def on_health_changed(self, event: GameEvent):
        payload: HealthChangePayload = event.payload
        entity = payload.entity

        # 绝地护盾被动
        if not entity.has_component(EntageShieldUsedComponent):
            if payload.new_hp > 0 and payload.new_hp / payload.max_hp <= 0.5:
                shield_gain = 50
                entity.add_component(EntageShieldUsedComponent())

                passive_info = f"{entity.name} 的 [绝地护盾] 触发，获得 {shield_gain} 点护盾！"
                self.pending_passive_triggers.append(passive_info)
                
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("PASSIVE", passive_info)))
                self.event_bus.dispatch(GameEvent(EventName.GAIN_SHIELD_REQUEST, GainShieldPayload(
                    target=entity, source="绝地护盾", amount=shield_gain
                )))
    
    def get_and_clear_pending_triggers(self):
        triggers = self.pending_passive_triggers.copy()
        self.pending_passive_triggers.clear()
        return triggers