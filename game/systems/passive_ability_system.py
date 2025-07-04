from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import HealthChangePayload, GainShieldPayload, LogRequestPayload
from ..core.components import EntageShieldUsedComponent

class PassiveAbilitySystem:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.pending_passive_triggers = []  # 存储待处理的被动触发信息
        event_bus.subscribe(EventName.HEALTH_CHANGED, self.on_health_changed)
    
    def on_health_changed(self, event: GameEvent):
        payload: HealthChangePayload = event.payload
        entity = payload.entity

        if entity.has_component(EntageShieldUsedComponent):
            return
        
        if payload.new_hp / payload.max_hp <= 0.5:
            shield_gain = 50

            entity.add_component(EntageShieldUsedComponent())

            # 记录被动触发信息
            passive_info = f"[{entity.name}][绝地护盾]生命过半，护盾值增加 {shield_gain} 点"
            self.pending_passive_triggers.append(passive_info)
            
            # 仍然发送日志信息供调试使用
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[PASSIVE]", passive_info)))

            self.event_bus.dispatch(GameEvent(EventName.GAIN_SHIELD_REQUEST, GainShieldPayload(
                target=entity, source="绝地护盾", amount=shield_gain
            )))
    
    def get_and_clear_pending_triggers(self):
        """获取并清空待处理的被动触发信息"""
        triggers = self.pending_passive_triggers.copy()
        self.pending_passive_triggers.clear()
        return triggers