from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.entity import Entity
    from .effect_logic import EffectLogic

@dataclass
class StatusEffect:
    """代表一个具体的Buff或Debuff实例"""
    effect_id: str
    name: str
    duration: int
    category: str = "uncategorized"
    stacking: str = "refresh_duration"
    max_stacks: int = 1
    stack_count: int = 1
    caster: Optional['Entity'] = None # type: ignore
    context: dict = field(default_factory=dict)
    logic: Optional['EffectLogic'] = None # type: ignore