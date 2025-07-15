import traceback
from dataclasses import dataclass
from typing import Any, Callable
from .enums import EventName

@dataclass
class GameEvent:
    name: EventName
    payload: Any = None

class EventBus:
    def __init__(self):
        self._listeners: dict[EventName, list[Callable]] = {}

    def subscribe(self, event_name: EventName, listener: Callable):
        if event_name not in self._listeners: self._listeners[event_name] = []
        self._listeners[event_name].append(listener)

    def dispatch(self, event: GameEvent):
        if event.name in self._listeners:
            for callback in self._listeners[event.name]:
                try:
                    callback(event)
                except Exception as e:
                    error_message = f"Error in event listener for {event.name}"
                    print(f"[CRITICAL ERROR] {error_message}")
                    print(traceback.format_exc())