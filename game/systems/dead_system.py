from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import UIMessagePayload, LogRequestPayload
from ..core.components import DeadComponent, HealthComponent

class DeadSystem:
    def __init__(self, event_bus, world):
        self.event_bus = event_bus
        self.world = world
    
    def check_game_end(self):
        living_entities = [e for e in self.world.entities if not e.has_component(DeadComponent)]
        if len(living_entities) < 2:
            self.world.is_running = False
            winner = living_entities[0] if living_entities else None
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"战斗结束！胜利者是: {winner.name if winner else '无'}")))
            return True
        return False
    
    def update(self):
        for entity in self.world.entities:
            if not entity.has_component(DeadComponent) and (hc := entity.get_component(HealthComponent)) and hc.hp <= 0:
                entity.add_component(DeadComponent())
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**[{entity.name}] 倒下了！**")))
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[SYSTEM]", f"实体 {entity.name} 已死亡")))
                # 立即检查游戏是否应该结束
                if self.check_game_end():
                    return