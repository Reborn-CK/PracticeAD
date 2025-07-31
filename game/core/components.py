from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING, Dict, Optional, Any

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
class EnergyComponent:
    """能量点组件 - 管理角色的能量点"""
    energy: float
    max_energy: float
    recovery_per_turn: float = 1.0  # 每回合恢复的能量点数，可通过装备等修改

@dataclass
class UltimateChargeComponent:
    """终极技能充能条组件 - 管理角色的终极技能充能"""
    charge: float = 0.0  # 当前充能值（0-200%）
    max_charge: float = 200.0  # 最大充能值
    charge_per_spell: float = 10.0  # 每次施法获得的充能值

@dataclass
class SpeedComponent:
    speed: int

@dataclass
class SpellListComponent:
    spells: List[str]

@dataclass
class UltimateSpellListComponent:
    ultimate_spells: List[str]

@dataclass
class BattlefieldComponent:
    """战场组件，存储当前战场的信息"""
    battlefield_id: str
    current_round: int
    max_rounds: int
    victory_condition: str
    defeat_condition: str
    is_completed: bool = False

@dataclass
class BattlefieldConfigComponent:
    """战场配置组件，存储战场的基本配置"""
    name: str
    description: str
    max_players: int
    starting_avatars: List[str]
    battlefield_id: str

@dataclass
class EnemyWaveComponent:
    """敌人波次组件，存储当前波次的敌人信息"""
    round_number: int
    enemies: List[str]  # 简化为敌人模板名称列表
    is_spawned: bool = False

@dataclass
class TeamComponent:
    """队伍组件，标识实体属于哪个队伍"""
    team_id: str  # "player" 或 "enemy"
    position: str = "front"  # "front" 或 "back"

@dataclass
class AIComponent:
    """AI组件，控制敌人的智能行为"""
    ai_template: str  # AI模板名称
    behavior_patterns: List[Dict[str, Any]]  # 行为模式配置
    custom_behavior: Dict[str, Any]  # 自定义行为参数
    last_action_time: float = 0.0  # 上次行动时间
    action_cooldown: float = 1.0   # 行动冷却时间

@dataclass
class PositionComponent:
    """位置组件，用于AP值相等时的先手判断"""
    position_id: int

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
class CounterStrikeComponent:
    """反震组件 - 被攻击时造成固定数值的反伤"""
    counter_damage: float = 0.0  # 固定反伤数值

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

@dataclass
class InventoryComponent:
    """物品栏组件，管理角色的物品"""
    items: Dict[str, 'InventoryItem'] = None  # 物品ID -> 物品实例
    
    def __post_init__(self):
        if self.items is None:
            self.items = {}
    
    def add_item(self, item_id: str, quantity: int = 1) -> bool:
        """添加物品到物品栏"""
        if item_id in self.items:
            # 如果物品已存在且可堆叠，增加数量
            # 这里需要从DataManager获取物品数据来判断是否可堆叠
            # 暂时假设所有物品都可堆叠
            self.items[item_id].quantity += quantity
            return True
        else:
            # 创建新物品实例
            self.items[item_id] = InventoryItem(item_id, quantity)
            return True
    
    def remove_item(self, item_id: str, quantity: int = 1) -> bool:
        """从物品栏移除物品"""
        if item_id not in self.items:
            return False
        
        item = self.items[item_id]
        if item.quantity <= quantity:
            # 移除整个物品
            del self.items[item_id]
        else:
            # 减少数量
            item.quantity -= quantity
        
        return True
    
    def get_item(self, item_id: str) -> Optional['InventoryItem']:
        """获取指定物品"""
        return self.items.get(item_id)
    
    def get_all_items(self) -> List['InventoryItem']:
        """获取所有物品"""
        return list(self.items.values())
    
    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """检查是否有指定数量的物品"""
        if item_id not in self.items:
            return False
        return self.items[item_id].quantity >= quantity

@dataclass
class InventoryItem:
    """物品栏中的物品实例"""
    item_id: str
    quantity: int = 1
    
    def __post_init__(self):
        # 物品数据会在使用时从DataManager获取
        pass