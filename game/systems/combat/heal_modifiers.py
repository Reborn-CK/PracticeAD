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
            original_heal = context.current_heal
            context.current_heal *= (1 - grievous_comp.reduction)
            heal_reduced = original_heal - context.current_heal
            event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[COMBAT]", 
                f"{context.target.name} 的重伤效果使治疗降低了 {grievous_comp.reduction*100:.0f}%，治疗从 {original_heal:.1f} 降低到 {context.current_heal:.1f}，减少了 {heal_reduced:.1f} 点治疗"
            ))) 