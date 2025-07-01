from abc import ABC, abstractmethod
from ...core.event_bus import EventBus, GameEvent
from ...core.enums import EventName
from ...core.payloads import LogRequestPayload
from ...core.components import GrievousWoundsComponent
from .damage_modifiers import HealResolutionContext

class HealModifier(ABC):
    @abstractmethod
    def process(self, context: 'HealResolutionContext', event_bus: EventBus): pass

class GrievousWoundsHandler(HealModifier):
    def process(self, context: 'HealResolutionContext', event_bus: EventBus):
        if grievous_comp := context.target.get_component(GrievousWoundsComponent):
            event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[COMBAT]", f"受到了 {grievous_comp.reduction_percentage:.1f} 治疗减益")))
            context.current_heal *= (1 - grievous_comp.reduction_percentage) 