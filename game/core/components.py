from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING, Dict, Optional

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

@dataclass
class EquipmentComponent:
    """装备组件，管理角色的装备"""
    equipment_slots: Dict[str, Optional[str]] = None  # 装备槽位 -> 装备ID
    equipped_items: Dict[str, 'EquipmentItem'] = None  # 装备ID -> 装备实例
    
    def __post_init__(self):
        if self.equipment_slots is None:
            self.equipment_slots = {
                'main_hand': None,
                'off_hand': None,
                'chest': None,
                'head': None,
                'legs': None,
                'feet': None,
                'ring': None,
                'necklace': None,
                'belt': None,
                'cloak': None
            }
        if self.equipped_items is None:
            self.equipped_items = {}
    
    def equip_item(self, slot: str, equipment_id: str, equipment_item: 'EquipmentItem'):
        """装备物品到指定槽位"""
        self.equipment_slots[slot] = equipment_id
        self.equipped_items[equipment_id] = equipment_item
    
    def unequip_item(self, slot: str) -> Optional['EquipmentItem']:
        """从指定槽位卸下装备"""
        equipment_id = self.equipment_slots.get(slot)
        if equipment_id:
            equipment_item = self.equipped_items.pop(equipment_id, None)
            self.equipment_slots[slot] = None
            return equipment_item
        return None
    
    def get_equipped_item(self, slot: str) -> Optional['EquipmentItem']:
        """获取指定槽位的装备"""
        equipment_id = self.equipment_slots.get(slot)
        if equipment_id:
            return self.equipped_items.get(equipment_id)
        return None
    
    def get_all_equipped_items(self) -> List['EquipmentItem']:
        """获取所有已装备的物品"""
        return list(self.equipped_items.values())

@dataclass
class EquipmentItem:
    """装备物品类"""
    equipment_id: str
    name: str
    description: str
    equipment_type: str  # weapon, armor, accessory
    slot: str
    rarity: str
    max_durability: int
    current_durability: int
    base_stats: Dict[str, float]
    durability_scaling: Dict[int, float]  # 耐久度百分比 -> 属性倍率
    durability_loss: Dict[str, int]  # 耐久损耗配置
    
    def get_current_stats(self) -> Dict[str, float]:
        """获取当前耐久度下的实际属性值"""
        durability_percentage = (self.current_durability / self.max_durability) * 100
        
        # 找到最接近的耐久度百分比对应的倍率
        scaling_factor = 1.0
        for threshold, factor in sorted(self.durability_scaling.items(), reverse=True):
            if durability_percentage >= threshold:
                scaling_factor = factor
                break
        
        # 计算实际属性值
        actual_stats = {}
        for stat_name, base_value in self.base_stats.items():
            actual_stats[stat_name] = base_value * scaling_factor
        
        return actual_stats
    
    def lose_durability(self, loss_type: str, amount: int = None) -> bool:
        """损耗耐久度，返回是否装备被摧毁"""
        if amount is None:
            amount = self.durability_loss.get(loss_type, 0)
        
        self.current_durability = max(0, self.current_durability - amount)
        
        # 如果耐久度为0，装备被摧毁
        return self.current_durability <= 0
    
    def get_durability_percentage(self) -> float:
        """获取当前耐久度百分比"""
        return (self.current_durability / self.max_durability) * 100