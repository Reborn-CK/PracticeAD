from ..core.entity import Entity
from ..core.components import (HealthComponent, ManaComponent, SpeedComponent, SpellListComponent,
                              ShieldComponent, StatusEffectContainerComponent, PlayerControlledComponent,
                              AIControlledComponent, CritComponent, OverhealToShieldComponent)
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
        entity = world.add_entity(Entity(character_data['name']))
        
        # 添加基础组件
        stats = character_data['stats']
        entity.add_component(HealthComponent(entity, self.event_bus, stats['hp'], stats['max_hp']))
        entity.add_component(ManaComponent(mana=stats['mana'], max_mana=stats['max_mana']))
        entity.add_component(SpeedComponent(speed=stats['speed']))
        entity.add_component(ShieldComponent(shield_value=stats['shield']))
        entity.add_component(StatusEffectContainerComponent())
        entity.add_component(SpellListComponent(spells=character_data['spells']))
        entity.add_component(CritComponent(crit_chance=stats['crit_chance'], crit_damage_multiplier=stats['crit_damage_multiplier']))
        
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
