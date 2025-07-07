from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING
from .entity import Entity
from .event_bus import EventBus, GameEvent

if TYPE_CHECKING:
    from ..status_effects.status_effect import StatusEffect

# --- 核心组件 ---
@dataclass
class HealthComponent:
    def __init__(self, owner: Entity, event_bus: EventBus, hp: float, max_hp: float):
        self._owner = owner
        self._event_bus = event_bus
        self._hp = hp
        self._max_hp = max_hp

    @property
    def hp(self) -> float: return self._hp

    @hp.setter
    def hp(self, value: float):
        from .enums import EventName
        from .payloads import HealthChangePayload
        old_hp = self._hp
        self._hp = max(0, min(value, self.max_hp))
        if self._hp != old_hp:
            self._event_bus.dispatch(GameEvent(EventName.HEALTH_CHANGED, HealthChangePayload(self._owner, old_hp, self._hp, self.max_hp)))
    
    @property
    def max_hp(self) -> float: return self._max_hp

@dataclass
class ManaComponent:
    mana: float
    max_mana: float

@dataclass
class SpeedComponent:
    speed: int

@dataclass
class SpellListComponent:
    spells: List[str]

@dataclass
class DefenseComponent:
    defense_value: float

@dataclass
class StatusEffectContainerComponent:
    effects: List['StatusEffect'] = field(default_factory=list) # type: ignore

@dataclass
class GrievousWoundsComponent:
    reduction: float = 0.5

@dataclass
class ResistanceComponent:
    element: str
    percentage: float

@dataclass
class ThornsComponent:
    thorns_percentage: float

# --- 状态标记组件 ---
@dataclass
class PlayerControlledComponent: pass
@dataclass
class AIControlledComponent: pass
@dataclass
class DeadComponent: pass
@dataclass
class EntageShieldUsedComponent: pass