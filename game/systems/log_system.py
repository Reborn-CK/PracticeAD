from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import LogRequestPayload

class LogSystem:
    def __init__(self, event_bus: EventBus, enabled: bool = True, hidden_tags: set = None):
        self.event_bus = event_bus
        self.enabled = enabled
        self.hidden_tags = hidden_tags or set()
        self.event_bus.subscribe(EventName.LOG_REQUEST, self.on_log_request)

    def set_enabled(self, enabled: bool): self.enabled = enabled
    def hide_tag(self, tag: str): self.hidden_tags.add(tag)
    def show_tag(self, tag: str): self.hidden_tags.discard(tag)
    def on_log_request(self, event: GameEvent):
        payload: LogRequestPayload = event.payload
        if not self.enabled or payload.tag in self.hidden_tags:
            return
        print(f"[{payload.tag}] {payload.message}")