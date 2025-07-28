from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

from game.core.entity import Entity
from game.core.event_bus import EventBus, GameEvent
from game.status_effects.status_effect import StatusEffect

# --- 核心组件 ---
@dataclass
class HealthComponent:
    def __init__(self, owner: 'Entity', event_bus: 'EventBus', hp: float, max_hp: float):
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
class ShieldComponent:
    shield_value: float

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

@dataclass
class CritComponent:
    crit_chance: float = 0.0
    crit_damage_multiplier: float = 2.0

@dataclass
class OverhealToShieldComponent:
    conversion_ratio: float = 1.0

@dataclass
class AttackTriggerPassiveComponent:
    """攻击触发被动效果组件"""
    passive_id: str
    trigger_chance: float = 1.0  # 触发概率，1.0表示100%触发
    effect_type: str = "damage"  # 效果类型：damage, heal, status_effect等
    effect_value: float = 0.0    # 效果数值
    effect_target: str = "self"  # 效果目标：self, target, random
    effect_name: str = ""        # 效果名称，用于显示
    damage_type: str = "pure"    # 伤害类型（当effect_type为damage时）
    status_effect_id: str = ""   # 状态效果ID（当effect_type为status_effect时）
    use_damage_ratio: bool = False  # 是否使用伤害比例模式
    damage_ratio: float = 0.0    # 伤害比例（当use_damage_ratio为True时）
    trigger_condition: str = "always"  # 触发条件：always, on_damage, on_hit

# --- 状态标记组件 ---
@dataclass
class PlayerControlledComponent: pass
@dataclass
class AIControlledComponent: pass
@dataclass
class DeadComponent: pass
@dataclass
class EntageShieldUsedComponent: pass

@dataclass
class StatsComponent:
    """统一管理角色属性的组件"""
    attack: float = 0.0  # 攻击力
    defense: float = 0.0  # 防御力