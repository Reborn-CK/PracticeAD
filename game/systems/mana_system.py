from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import ManaCostRequestPayload
from ..core.components import ManaComponent

class ManaSystem:
    """ <<< 升级: 适配新的法术消耗格式 >>> """
    def __init__(self, e_bus): 
        self.event_bus = e_bus
        e_bus.subscribe(EventName.MANA_COST_REQUEST, self.on_mana_cost_request)
    
    def on_mana_cost_request(self, event):
        p = event.payload
        mana_comp = p.entity.get_component(ManaComponent)
        if mana_comp and mana_comp.mana >= p.cost: 
            mana_comp.mana -= p.cost
            p.is_affordable = True
        else: 
            p.is_affordable = False