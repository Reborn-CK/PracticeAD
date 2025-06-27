from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import UIMessagePayload, LogRequestPayload
from ..core.components import DeadComponent, HealthComponent, PlayerControlledComponent, AIControlledComponent

class DeadSystem:
    def __init__(self, event_bus: EventBus, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.world = world
    
    def check_game_end(self):
        players_alive = any(e.has_component(PlayerControlledComponent) and not e.has_component(DeadComponent) for e in self.world.entities)
        enemies_alive = any(e.has_component(AIControlledComponent) and not e.has_component(DeadComponent) for e in self.world.entities)
        
        if not players_alive:
            self.world.is_running = False
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"战斗结束！你被击败了。")))
            return True
        if not enemies_alive:
            self.world.is_running = False
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"战斗结束！你胜利了！")))
            return True
        return False
    
    def update(self):
        for entity in self.world.entities:
            if not entity.has_component(DeadComponent) and (hc := entity.get_component(HealthComponent)) and hc.hp <= 0:
                entity.add_component(DeadComponent())
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**[{entity.name}] 倒下了！**")))
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("SYSTEM", f"实体 {entity.name} 已死亡")))
                
        self.check_game_end()