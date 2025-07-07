from ..core.entity import Entity
from ..core.components import (HealthComponent, ManaComponent, SpeedComponent, SpellListComponent,
                              DefenseComponent, StatusEffectContainerComponent, PlayerControlledComponent,
                              AIControlledComponent)
from ..core.event_bus import EventBus
from .passive_validator import PassiveValidator

class CharacterFactory:
    """角色工厂类，负责根据配置创建角色实体"""
    
    def __init__(self, event_bus: EventBus, data_manager):
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.passive_validator = PassiveValidator(data_manager)
    
    def create_character(self, character_id: str, world) -> Entity:
        """根据角色ID创建角色实体"""
        character_data = self.data_manager.get_character_data(character_id)
        if not character_data:
            raise ValueError(f"未找到角色配置: {character_id}")
        
        # 创建实体
        entity = world.add_entity(Entity(character_data['name']))
        
        # 添加基础组件
        stats = character_data['stats']
        entity.add_component(HealthComponent(entity, self.event_bus, stats['hp'], stats['max_hp']))
        entity.add_component(ManaComponent(mana=stats['mana'], max_mana=stats['max_mana']))
        entity.add_component(SpeedComponent(speed=stats['speed']))
        entity.add_component(DefenseComponent(defense_value=stats['defense']))
        entity.add_component(StatusEffectContainerComponent())
        entity.add_component(SpellListComponent(spells=character_data['spells']))
        
        # 根据类型添加控制组件
        if character_data['type'] == 'player':
            entity.add_component(PlayerControlledComponent())
        elif character_data['type'] == 'enemy':
            entity.add_component(AIControlledComponent())
        
        # 添加被动能力组件
        self._add_passive_components(entity, character_data.get('passives', []))
        
        return entity
    
    def _add_passive_components(self, entity: Entity, passives: list):
        """添加被动能力组件"""
        for passive in passives:
            passive_id = passive['id']
            passive_data = {k: v for k, v in passive.items() if k != 'id'}
            
            # 验证被动能力配置
            is_valid, errors = self.passive_validator.validate_passive(passive_id, passive_data)
            if not is_valid:
                print(f"警告: 被动能力 {passive_id} 配置错误:")
                for error in errors:
                    print(f"  - {error}")
                continue
            
            try:
                # 创建被动能力组件
                component = self.passive_validator.create_passive_component(passive_id, passive_data)
                entity.add_component(component)
                
                # 获取被动能力信息用于显示
                passive_info = self.passive_validator.get_passive_info(passive_id)
                print(f"成功添加被动能力: {passive_info['name']} ({passive_id})")
                
            except Exception as e:
                print(f"错误: 创建被动能力 {passive_id} 失败: {e}")
                continue 