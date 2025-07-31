from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING
from game.core.enums import EventName

if TYPE_CHECKING:
    from game.core.entity import Entity

# --- Event Payloads ---
@dataclass
class ApplyStatusEffectRequestPayload:
    target: 'Entity'
    effect: 'StatusEffect' # type: ignore
@dataclass
class RemoveStatusEffectRequestPayload:
    target: 'Entity'
    effect_id: str
@dataclass
class UpdateStatusEffectsDurationRequestPayload:
    target: 'Entity'
    effect_id: str
    change: int

@dataclass
class RoundStartPayload:
    round_number: int

@dataclass
class TurnStartPayload:
    entity: 'Entity'

@dataclass
class LogRequestPayload:
    tag: str
    message: str

@dataclass
class ActionRequestPayload:
    acting_entity: 'Entity'

@dataclass
class ActionAfterActPayload:
    acting_entity: 'Entity'

@dataclass
class PostActionSettlementPayload:
    acting_entity: 'Entity'

@dataclass
class CastSpellRequestPayload:
    caster: 'Entity'
    target: 'Entity'
    spell_id: str

@dataclass
class ManaCostRequestPayload:
    entity: 'Entity'
    cost: float
    is_affordable: bool = True

@dataclass
class DamageRequestPayload:
    caster: 'Entity'
    target: 'Entity'
    source_spell_id: str
    source_spell_name: str
    base_damage: float
    damage_type: str
    original_base_damage: Optional[float] = None
    lifesteal_ratio: Optional[float] = 0.0
    can_be_reflected: bool = False
    is_reflection: bool = False
    is_passive_damage: bool = False  # 标记是否为被动伤害，防止无限循环
    is_dot_damage: bool = False  # 标记是否为持续伤害

    can_crit: bool = False
    crit_chance: float = 0.0
    crit_damage_multiplier: float = 2.0
    # 新增：是否触发攻击被动
    trigger_on_attack: bool = True

@dataclass
class HealRequestPayload:
    caster: 'Entity'
    target: 'Entity'
    source_spell_id: str
    source_spell_name: str
    base_heal: float
    heal_type: str
    can_be_modified: bool = True

    overheal_to_shield_config: Optional[dict] = None

@dataclass
class GainShieldPayload:
    target: 'Entity'
    source: str
    amount: float

@dataclass
class HealthChangePayload:
    entity: 'Entity'
    old_hp: float
    new_hp: float
    max_hp: float

@dataclass
class OverhealRequestPayload:
    caster: 'Entity'
    target: 'Entity'
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
    caster: 'Entity'
    target: 'Entity'
    source_spell: str
    resource_changes: list = field(default_factory=list)
    shield_blocked: float = 0.0
    passive_triggers: list = field(default_factory=list)
    log_reflection: Optional[bool] = None
    health_changed: bool = False
    shield_changed: bool = False
    shield_change_amount: float = 0.0  # 护盾变化的具体数值
    shield_before: float = 0.0  # 护盾变化前的值
    new_status_effects: list = field(default_factory=list)  # 修改为list类型
    no_effect_produced: bool = False
    is_dot_damage: bool = False  # 新增：是否为持续伤害
    effect_produced: bool = False  # 新增：是否有效果产生

    def add_resource_change(self, resource_name: str, change_amount: float, current_value: float, max_value: Optional[float] = None):
        """添加资源变化记录"""
        self.resource_changes.append({
            'resource_name': resource_name,
            'change_amount': change_amount,
            'current_value': current_value,
            'max_value': max_value
        })

    def finalize(self):
        """完成效果解析，计算是否有实际效果产生"""
        self.effect_produced = (
            self.health_changed or 
            self.shield_changed or 
            len(self.new_status_effects) > 0 or
            any(abs(change['change_amount']) > 0 for change in self.resource_changes)
        )

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
    entity: 'Entity'
    stat_name: str
    base_value: float
    current_value: float

@dataclass
class DispelRequestPayload:
    target: 'Entity'
    category_to_dispel: str
    count: int

@dataclass
class AmplifyPoisonRequestPayload:
    target: 'Entity'
    amplify_amount: int
    caster: 'Entity'
    source_spell_id: str
    source_spell_name: str

@dataclass
class DetonatePoisonRequestPayload:
    target: 'Entity'
    damage_multiplier: float
    caster: 'Entity'
    source_spell_id: str
    source_spell_name: str

@dataclass
class StatusEffectsResolvedPayload:
    """状态效果结算完成事件的payload"""
    pass

@dataclass
class ReduceDebuffsRequestPayload:
    target: 'Entity'
    reduce_stack_count: int
    reduce_duration_count: int

# 物品系统相关payload
@dataclass
class UseItemRequestPayload:
    user: 'Entity'
    item_id: str
    target: Optional['Entity'] = None

@dataclass
class ManaChangeRequestPayload:
    target: 'Entity'
    amount: float
    change_type: str  # "restore" or "consume"

@dataclass
class EnergyCostRequestPayload:
    entity: 'Entity'
    cost: float
    is_affordable: bool = True

@dataclass
class EnergyChangeRequestPayload:
    target: 'Entity'
    amount: float
    change_type: str  # "restore" or "consume"

@dataclass
class UltimateChargeRequestPayload:
    entity: 'Entity'
    cost: float
    is_affordable: bool = True

@dataclass
class UltimateChargeChangeRequestPayload:
    target: 'Entity'
    amount: float
    change_type: str  # "add" or "consume"

@dataclass
class PlayerSpellChoicePayload:
    """玩家技能选择事件payload"""
    caster: 'Entity'
    spell_id: str

@dataclass
class PlayerTargetChoicePayload:
    """玩家目标选择事件payload"""
    caster: 'Entity'
    spell_id: str
    target: 'Entity'