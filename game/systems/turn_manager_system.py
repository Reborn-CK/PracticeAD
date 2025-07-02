from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import RoundStartPayload, ActionRequestPayload, StatQueryPayload
from ..core.components import DeadComponent, SpeedComponent
from ..core.entity import Entity

class TurnManagerSystem:
    def __init__(self, event_bus: EventBus, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.world = world
        self.round_number = 0
        self.turn_queue = []

    def get_final_stat(self, entity: 'Entity', stat_name: str, base_value: float) -> float: # type: ignore
        query = StatQueryPayload(entity, stat_name, base_value, base_value)
        self.event_bus.dispatch(GameEvent(EventName.STAT_QUERY, query))
        return query.current_value

    def update(self):
        if not self.turn_queue:
            self.round_number += 1
            living_entities = [e for e in self.world.entities if not e.has_component(DeadComponent)]
            if len(living_entities) < 2:
                self.world.is_running = False
                return

            living_entities.sort(key=lambda e: self.get_final_stat(e, "speed", e.get_component(SpeedComponent).speed), reverse=True)
            self.turn_queue = living_entities
            
            # 先触发状态效果结算事件
            self.event_bus.dispatch(GameEvent(EventName.ROUND_START, RoundStartPayload(self.round_number)))
            
            # 等待状态效果结算完成后再刷新UI
            # 状态效果系统会在结算完成后触发 STATUS_EFFECTS_RESOLVED 事件

        if self.turn_queue:
            acting_entity = self.turn_queue.pop(0)
            self.event_bus.dispatch(GameEvent(EventName.ACTION_REQUEST, ActionRequestPayload(acting_entity)))