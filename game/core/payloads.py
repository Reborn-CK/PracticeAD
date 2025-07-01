from dataclasses import dataclass, field
from typing import Optional, Any, List
from .entity import Entity
from .enums import EventName

# --- Event Payloads ---
@dataclass
class ApplyStatusEffectRequestPayload:
    target: Entity
    effect: 'StatusEffect' # type: ignore
@dataclass
class RemoveStatusEffectRequestPayload:
    target: Entity
    effect_id: str
@dataclass
class UpdateStatusEffectsDurationRequestPayload:
    target: Entity
    effect_id: str
    change: int

@dataclass
class RoundStartPayload:
    round_number: int

@dataclass
class LogRequestPayload:
    tag: str
    message: str

@dataclass
class ActionRequestPayload:
    acting_entity: Entity

@dataclass
class CastSpellRequestPayload:
    caster: Entity
    target: Entity
    spell_id: str

@dataclass
class ManaCostRequestPayload:
    entity: Entity
    cost: float
    is_affordable: bool = True

@dataclass
class DamageRequestPayload:
    caster: Entity
    target: Entity
    source_spell_id: str
    source_spell_name: str
    base_damage: float
    damage_type: str
    original_base_damage: Optional[float] = None
    lifesteal_ratio: Optional[float] = None
    is_reflection: bool = False

@dataclass
class HealRequestPayload:
    caster: Entity
    target: Entity
    source_spell_id: str
    source_spell_name: str
    base_heal: float
    heal_type: str
    overheal_amount: float = 0.0
    overheal_conversion_rate: Optional[float] = None

@dataclass
class GainShieldPayload:
    target: Entity
    source: str
    amount: float

@dataclass
class HealthChangePayload:
    entity: Entity
    old_hp: float
    new_hp: float
    max_hp: float

@dataclass
class OverhealRequestPayload:
    caster: Entity
    target: Entity
    source_spell: str
    conversion_rate: float

@dataclass
class ResourceChangeEntry:
    resource_name: str
    change_amount: float
    current_value: float
    max_value: Optional[float] = None

@dataclass
class EffectResolutionPayload:
    caster: Entity
    target: Entity
    source_spell: str
    resource_changes: list = field(default_factory=list)
    shield_blocked: float = 0.0
    passive_triggers: list = field(default_factory=list)

@dataclass
class UIMessagePayload:
    message: str

@dataclass
class UIDisplayOptionsPayload:
    prompt: str
    options: List[str]
    response_event_name: EventName
    context: dict

@dataclass
class StatQueryPayload:
    entity: Entity
    stat_name: str
    base_value: float
    current_value: float

@dataclass
class DispelRequestPayload:
    target: Entity
    category_to_dispel: str
    count: int

@dataclass
class AmplifyPoisonRequestPayload:
    target: Entity
    stacks_to_add: int
    caster: Entity
    source_spell_id: str
    source_spell_name: str

@dataclass
class DetonatePoisonRequestPayload:
    target: Entity
    damage_multiplier: float
    caster: Entity
    source_spell_id: str
    source_spell_name: str