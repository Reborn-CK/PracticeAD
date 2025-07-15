from typing import Any, TYPE_CHECKING
from game.core.payloads import StatQueryPayload
from game.core.event_bus import EventName, GameEvent
from game.core.event_bus import EventBus

if TYPE_CHECKING:
    from .components import ResistanceComponent

class Entity:
    def __init__(self, name: str, event_bus: 'EventBus'): 
        self.name = name
        self.event_bus = event_bus
        self._components = {}  # 存储单个组件
        self._component_lists = {}  # 存储多个同类型组件
    
    def get_final_stat(self, stat_name: str, base_value: float) -> float:
        """通过事件总线查询考虑所有效果后的最终属性值"""
        query = StatQueryPayload(self, stat_name, base_value,current_value=base_value)
        self.event_bus.dispatch(GameEvent(EventName.STAT_QUERY, query))
        return query.current_value
        
    def add_component(self, c: Any): 
        # 对于某些组件类型，允许多个实例
        component_type = type(c)
        component_name = component_type.__name__
        
        # 可以添加多个同类型组件的组件列表
        multi_component_types = ['ResistanceComponent', 'AttackTriggerPassiveComponent']
        
        if component_name in multi_component_types:  # 可以添加多个抗性组件
            if component_type not in self._component_lists:
                self._component_lists[component_type] = []
            self._component_lists[component_type].append(c)
            return c
        else:
            # 其他组件类型只允许一个实例
            self._components[component_type] = c
            return c
    
    def get_component(self, ct: type): 
        # 优先从单个组件中获取
        if ct in self._components:
            return self._components[ct]
        # 如果单个组件中没有，从组件列表中获取第一个
        if ct in self._component_lists and self._component_lists[ct]:
            return self._component_lists[ct][0]
        return None
    
    def has_component(self, ct: type): 
        return ct in self._components or (ct in self._component_lists and self._component_lists[ct])
    
    def get_components(self, ct: type): 
        """获取指定类型的所有组件（用于支持多个同类型组件）"""
        if ct in self._component_lists:
            return self._component_lists[ct]
        elif ct in self._components:
            return [self._components[ct]]
        return []