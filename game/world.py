import time
from typing import List, Any
from .core.event_bus import EventBus
from .core.entity import Entity

FRAME_RATE = 60
TICK_INTERVAL = 1.0 / FRAME_RATE

class World:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.entities = []
        self.systems: List[tuple[int, Any]] = []
        self.is_running = False

    def add_entity(self, e: Entity): self.entities.append(e); return e
    def get_entity_by_name(self, name: str): return next((e for e in self.entities if e.name == name), None)
    def add_system(self, s: Any, priority: int = 100):
        self.systems.append((priority, s))
        self.systems.sort(key=lambda x: x[0])

    def get_system(self, system_type: type):
        for _, system in self.systems:
            if isinstance(system, system_type):
                return system
        return None

    def start(self):
        self.is_running = True
        self.game_loop()

    def game_loop(self):
        while self.is_running:
            loop_start_time = time.time()

            for priority, system in self.systems:
                if hasattr(system, 'update'):
                    system.update()
            if not self.is_running:
                break

            loop_end_time = time.time()
            elapsed_time = loop_end_time - loop_start_time
            sleep_time = TICK_INTERVAL - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)