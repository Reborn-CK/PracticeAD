from ..core.entity import Entity
from ..core.components import (HealthComponent, ManaComponent, SpeedComponent, SpellListComponent,
                              ShieldComponent, StatusEffectContainerComponent, PlayerControlledComponent,
                              AIControlledComponent, CritComponent, OverhealToShieldComponent, StatsComponent,
                              EquipmentComponent)
from ..core.event_bus import EventBus
from ..core.enums import EventName
from ..core.payloads import LogRequestPayload
from ..core.event_bus import GameEvent
from .passive_factory import PassiveFactory

class CharacterFactory:
    """角色工厂类，负责根据配置创建角色实体"""
    
    def __init__(self, event_bus: EventBus, data_manager):
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.passive_factory = PassiveFactory(data_manager)
    
    def create_character(self, character_id: str, world) -> Entity:
        """根据角色ID创建角色实体"""
        character_data = self.data_manager.get_character_data(character_id)
        if not character_data:
            raise ValueError(f"未找到角色配置: {character_id}")
        
        # 创建实体
        entity = world.add_entity(Entity(character_data['name'], self.event_bus))
        
        # 添加基础组件
        stats = character_data['stats']
        entity.add_component(HealthComponent(entity, self.event_bus, stats['hp'], stats['max_hp']))
        entity.add_component(ManaComponent(mana=stats['mana'], max_mana=stats['max_mana']))
        entity.add_component(SpeedComponent(speed=stats['speed']))
        entity.add_component(ShieldComponent(shield_value=stats['shield']))
        entity.add_component(StatusEffectContainerComponent())
        entity.add_component(SpellListComponent(spells=character_data['spells']))
        entity.add_component(CritComponent(crit_chance=stats['crit_chance'], crit_damage_multiplier=stats['crit_damage_multiplier']))
        
        # 添加StatsComponent - 使用角色数据中的基础属性
        attack = stats.get('attack', 0)
        defense = stats.get('defense', 0)
        entity.add_component(StatsComponent(attack=attack, defense=defense))
        
        # 添加EquipmentComponent
        equipment_slots = character_data.get('equipment_slots', {})
        entity.add_component(EquipmentComponent(equipment_slots=equipment_slots))
        
        # 装备预设的装备
        self._equip_preset_equipment(entity, equipment_slots, character_id)
        
        # 更新装备属性
        self._update_equipment_stats(entity, character_id)
        
        # 根据类型添加控制组件
        if character_data['type'] == 'player':
            entity.add_component(PlayerControlledComponent())
        elif character_data['type'] == 'enemy':
            entity.add_component(AIControlledComponent())
        
        # 添加被动能力组件
        passive_versions = character_data.get('passives', [])
        self._add_passive_components(entity, passive_versions)
        
        return entity
    
    def _add_passive_components(self, entity: Entity, passives_versions: list):
        """添加被动能力组件"""
        for version_id in passives_versions:
            try:
                # 创建被动能力组件
                component = self.passive_factory.create_passive_component(version_id)
                if component:
                    entity.add_component(component)
                    passive_info = self.data_manager.get_passive_version_data(version_id)
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[PASSIVE Load]", f"成功添加被动能力: {passive_info['name']} ({version_id})")))
                    
            except Exception as e:
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[PASSIVE Load]", f"创建被动能力组件失败: {e}")))
                continue
    
    def _equip_preset_equipment(self, entity: Entity, equipment_slots: dict, character_id: str):
        """装备预设的装备"""
        equipment_comp = entity.get_component(EquipmentComponent)
        if not equipment_comp:
            return
        
        for slot, equipment_id in equipment_slots.items():
            if equipment_id and equipment_id != "null":
                try:
                    # 获取装备数据
                    equipment_data = self.data_manager.get_equipment_data(equipment_id)
                    if equipment_data:
                        # 创建装备实例
                        from ..core.components import EquipmentItem
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
                        
                        # 记录日志
                        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                            "[EQUIPMENT]", f"✅ {entity.name} 自动装备了 {equipment_item.name}"
                        )))
                        
                except Exception as e:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[EQUIPMENT]", f"❌ {entity.name} 装备 {equipment_id} 失败: {e}"
                    )))
    
    def _update_equipment_stats(self, entity: Entity, character_id: str):
        """更新角色装备属性"""
        equipment_comp = entity.get_component(EquipmentComponent)
        stats_comp = entity.get_component(StatsComponent)
        
        if not equipment_comp or not stats_comp:
            return
        
        # 获取角色基础属性
        base_attack = 0
        base_defense = 0
        
        # 从角色数据中获取基础属性
        character_data = self.data_manager.get_character_data(character_id)
        if character_data and 'stats' in character_data:
            base_attack = character_data['stats'].get('attack', 0)
            base_defense = character_data['stats'].get('defense', 0)
        
        # 保存基础属性到StatsComponent
        stats_comp._base_attack = base_attack
        stats_comp._base_defense = base_defense
        
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
