from typing import Dict, Optional
from ..core.entity import Entity
from ..core.components import EquipmentComponent, EquipmentItem, StatsComponent
from ..core.event_bus import EventBus
from ..core.enums import EventName
from ..core.payloads import LogRequestPayload
from ..core.event_bus import GameEvent
from .data_manager import DataManager

class EquipmentSystem:
    """装备系统，管理装备的装备、卸下、耐久损耗等功能"""
    
    def __init__(self, event_bus: EventBus, data_manager: DataManager):
        self.event_bus = event_bus
        self.data_manager = data_manager
        
        # 订阅相关事件
        self.event_bus.subscribe(EventName.DAMAGE_REQUEST, self._on_damage_request)
        self.event_bus.subscribe(EventName.TURN_START, self._on_turn_start)
    
    def equip_item(self, entity: Entity, equipment_id: str, slot: str) -> bool:
        """装备物品到指定槽位"""
        equipment_comp = entity.get_component(EquipmentComponent)
        if not equipment_comp:
            return False
        
        # 检查槽位是否已被占用
        if equipment_comp.equipment_slots.get(slot):
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[EQUIPMENT]", f"❌ {entity.name} 的 {slot} 槽位已被占用"
            )))
            return False
        
        # 获取装备数据
        equipment_data = self.data_manager.get_equipment_data(equipment_id)
        if not equipment_data:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[EQUIPMENT]", f"❌ 未找到装备数据: {equipment_id}"
            )))
            return False
        
        # 检查槽位是否匹配
        if equipment_data.get('slot') != slot:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[EQUIPMENT]", f"❌ {equipment_data['name']} 不能装备到 {slot} 槽位"
            )))
            return False
        
        # 创建装备实例
        equipment_item = EquipmentItem(
            equipment_id=equipment_id,
            name=equipment_data['name'],
            description=equipment_data['description'],
            equipment_type=equipment_data['type'],
            slot=equipment_data['slot'],
            rarity=equipment_data['rarity'],
            max_durability=equipment_data['max_durability'],
            current_durability=equipment_data['max_durability'],  # 初始满耐久
            base_stats=equipment_data['base_stats'],
            durability_scaling=equipment_data['durability_scaling'],
            durability_loss=equipment_data['durability_loss']
        )
        
        # 装备物品
        equipment_comp.equip_item(slot, equipment_id, equipment_item)
        
        # 更新角色属性
        self._update_entity_stats(entity)
        
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "[EQUIPMENT]", f"✅ {entity.name} 装备了 {equipment_item.name}"
        )))
        
        return True
    
    def unequip_item(self, entity: Entity, slot: str) -> Optional[EquipmentItem]:
        """从指定槽位卸下装备"""
        equipment_comp = entity.get_component(EquipmentComponent)
        if not equipment_comp:
            return None
        
        equipment_item = equipment_comp.unequip_item(slot)
        if equipment_item:
            # 更新角色属性
            self._update_entity_stats(entity)
            
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[EQUIPMENT]", f"🔧 {entity.name} 卸下了 {equipment_item.name}"
            )))
        
        return equipment_item
    
    def _on_damage_request(self, event):
        """处理伤害请求事件，损耗装备耐久"""
        payload = event.payload
        source = payload.caster
        target = payload.target
        source_spell_id = payload.source_spell_id
        
        # 物品伤害不损耗装备耐久
        if source_spell_id == "item":
            return
        
        # 损耗攻击者装备耐久
        if source:
            self._lose_equipment_durability(source, "on_attack")
        
        # 损耗防御者装备耐久
        if target:
            self._lose_equipment_durability(target, "on_block")
    
    def _on_turn_start(self, event):
        """处理回合开始事件，损耗装备耐久"""
        payload = event.payload
        entity = payload.entity
        
        if entity:
            self._lose_equipment_durability(entity, "per_turn")
    
    def _lose_equipment_durability(self, entity: Entity, loss_type: str):
        """损耗装备耐久度"""
        equipment_comp = entity.get_component(EquipmentComponent)
        if not equipment_comp:
            return
        
        destroyed_items = []
        
        for equipment_item in equipment_comp.get_all_equipped_items():
            # 损耗耐久度
            is_destroyed = equipment_item.lose_durability(loss_type)
            
            if is_destroyed:
                destroyed_items.append(equipment_item)
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[EQUIPMENT]", f"💥 {entity.name} 的 {equipment_item.name} 耐久度耗尽，装备被摧毁！"
                )))
            else:
                # 记录耐久度变化
                durability_percentage = equipment_item.get_durability_percentage()
                if durability_percentage <= 20:  # 耐久度低于20%时提醒
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[EQUIPMENT]", f"⚠️ {entity.name} 的 {equipment_item.name} 耐久度仅剩 {durability_percentage:.1f}%"
                    )))
        
        # 移除被摧毁的装备
        for destroyed_item in destroyed_items:
            for slot, equipment_id in equipment_comp.equipment_slots.items():
                if equipment_id == destroyed_item.equipment_id:
                    equipment_comp.unequip_item(slot)
                    break
        
        # 更新角色属性
        if destroyed_items:
            self._update_entity_stats(entity)
    
    def _update_entity_stats(self, entity: Entity):
        """更新角色属性，计算装备加成"""
        equipment_comp = entity.get_component(EquipmentComponent)
        stats_comp = entity.get_component(StatsComponent)
        
        if not equipment_comp or not stats_comp:
            return
        
        # 获取角色基础属性 - 从StatsComponent中获取，而不是每次都重新计算
        # 如果StatsComponent中没有基础属性信息，则从角色数据中获取并保存
        if not hasattr(stats_comp, '_base_attack') or not hasattr(stats_comp, '_base_defense'):
            # 首次初始化基础属性
            base_attack = 0
            base_defense = 0
            
            # 尝试从角色数据中获取基础属性
            # 注意：这里需要根据角色名称反向查找角色ID
            character_data = None
            for char_id, char_info in self.data_manager.character_data.items():
                if char_info.get('name') == entity.name:
                    character_data = char_info
                    break
            
            if character_data and 'stats' in character_data:
                base_attack = character_data['stats'].get('attack', 0)
                base_defense = character_data['stats'].get('defense', 0)
            
            # 保存基础属性到StatsComponent
            stats_comp._base_attack = base_attack
            stats_comp._base_defense = base_defense
        
        # 使用保存的基础属性
        base_attack = stats_comp._base_attack
        base_defense = stats_comp._base_defense
        
        # 计算装备加成
        total_attack = base_attack
        total_defense = base_defense
        
        for equipment_item in equipment_comp.get_all_equipped_items():
            current_stats = equipment_item.get_current_stats()
            total_attack += current_stats.get('attack', 0)
            total_defense += current_stats.get('defense', 0)
        
        # 更新StatsComponent
        stats_comp.attack = total_attack
        stats_comp.defense = total_defense
        
        # 记录装备属性变化
        if equipment_comp.get_all_equipped_items():
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[EQUIPMENT]", f"📊 {entity.name} 装备属性: 攻击力 {total_attack:.1f}, 防御力 {total_defense:.1f}"
            )))
        else:
            # 当没有装备时，显示基础属性
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[EQUIPMENT]", f"📊 {entity.name} 基础属性: 攻击力 {base_attack:.1f}, 防御力 {base_defense:.1f}"
            )))
    
    def get_equipment_info(self, entity: Entity) -> Dict:
        """获取角色的装备信息"""
        equipment_comp = entity.get_component(EquipmentComponent)
        if not equipment_comp:
            return {}
        
        info = {
            'equipped_items': {},
            'total_stats': {'attack': 0, 'defense': 0}
        }
        
        for slot, equipment_id in equipment_comp.equipment_slots.items():
            if equipment_id:
                equipment_item = equipment_comp.get_equipped_item(slot)
                if equipment_item:
                    current_stats = equipment_item.get_current_stats()
                    info['equipped_items'][slot] = {
                        'name': equipment_item.name,
                        'durability': f"{equipment_item.current_durability}/{equipment_item.max_durability}",
                        'durability_percentage': equipment_item.get_durability_percentage(),
                        'stats': current_stats
                    }
                    
                    # 累计总属性
                    info['total_stats']['attack'] += current_stats.get('attack', 0)
                    info['total_stats']['defense'] += current_stats.get('defense', 0)
        
        return info 