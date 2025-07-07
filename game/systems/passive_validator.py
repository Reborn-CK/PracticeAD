from typing import Dict, Any, List
from ..core.entity import Entity
from ..core.components import (ResistanceComponent, GrievousWoundsComponent, ThornsComponent)

class PassiveValidator:
    """被动能力验证器，负责验证和创建被动能力组件"""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.component_mapping = {
            'resistance': ResistanceComponent,
            'grievous_wounds': GrievousWoundsComponent,
            'thorns': ThornsComponent,
        }
    
    def validate_passive(self, passive_id: str, passive_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证被动能力配置是否正确"""
        passive_config = self.data_manager.get_passive_data(passive_id)
        if not passive_config:
            return False, [f"未找到被动能力配置: {passive_id}"]
        
        errors = []
        
        # 检查必需的属性
        required_properties = passive_config.get('required_properties', [])
        for prop in required_properties:
            if prop not in passive_data:
                errors.append(f"缺少必需属性: {prop}")
        
        # 检查属性类型
        properties_config = passive_config.get('properties', {})
        for prop_name, prop_value in passive_data.items():
            if prop_name in properties_config:
                expected_type = properties_config[prop_name].get('type')
                if expected_type == 'float' and not isinstance(prop_value, (int, float)):
                    errors.append(f"属性 {prop_name} 应该是数值类型")
                elif expected_type == 'dict' and not isinstance(prop_value, dict):
                    errors.append(f"属性 {prop_name} 应该是字典类型")
        
        return len(errors) == 0, errors
    
    def create_passive_component(self, passive_id: str, passive_data: Dict[str, Any]):
        """根据配置创建被动能力组件"""
        if passive_id not in self.component_mapping:
            raise ValueError(f"不支持的被动能力类型: {passive_id}")
        
        component_class = self.component_mapping[passive_id]
        
        if passive_id == 'resistance':
            return component_class(resistances=passive_data['resistances'])
        elif passive_id == 'grievous_wounds':
            return component_class(reduction_percentage=passive_data['reduction_percentage'])
        elif passive_id == 'thorns':
            return component_class(thorns_percentage=passive_data['thorns_percentage'])
        else:
            raise ValueError(f"未实现的被动能力类型: {passive_id}")
    
    def get_passive_info(self, passive_id: str) -> Dict[str, Any]:
        """获取被动能力信息"""
        passive_config = self.data_manager.get_passive_data(passive_id)
        if not passive_config:
            return {}
        
        return {
            'name': passive_config.get('name', passive_id),
            'description': passive_config.get('description', ''),
            'type': passive_config.get('type', passive_id),
            'component': passive_config.get('component', ''),
            'required_properties': passive_config.get('required_properties', []),
            'properties': passive_config.get('properties', {})
        }
    
    def list_available_passives(self) -> List[str]:
        """列出所有可用的被动能力"""
        return list(self.data_manager.passive_data.keys()) 