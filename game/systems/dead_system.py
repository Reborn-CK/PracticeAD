from ..core.event_bus import GameEvent
from ..core.enums import EventName
from ..core.payloads import UIMessagePayload, LogRequestPayload
from ..core.components import DeadComponent, HealthComponent

class DeadSystem:
    def __init__(self, event_bus, world):
        self.event_bus = event_bus
        self.world = world
    
    def update(self):
        for entity in self.world.entities:
            if not entity.has_component(DeadComponent) and (hc := entity.get_component(HealthComponent)) and hc.hp <= 0:
                entity.add_component(DeadComponent())
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**[{entity.name}] 倒下了！**")))
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[SYSTEM]", f"实体 {entity.name} 已死亡")))
                
                # 发送实体死亡事件，让战场系统处理胜利条件检测
                self.event_bus.dispatch(GameEvent(EventName.ENTITY_DEATH, {
                    "entity": entity
                }))