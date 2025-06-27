from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import ManaCostRequestPayload
from ..core.components import ManaComponent

class ManaSystem:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        event_bus.subscribe(EventName.MANA_COST_REQUEST, self.on_mana_cost_request)
    
    def on_mana_cost_request(self, event: GameEvent):
        payload: ManaCostRequestPayload = event.payload
        mana_comp = payload.entity.get_component(ManaComponent)
        if mana_comp and mana_comp.mana >= payload.cost:
            mana_comp.mana -= payload.cost
            payload.is_affordable = True
        else:
            payload.is_affordable = False