from typing import Dict, Any, List
from ..core.components import (ResistanceComponent, GrievousWoundsComponent, ThornsComponent, OverhealToShieldComponent, AttackTriggerPassiveComponent)

# 组件映射表，Key是YAML中的component名，Value是组件类
COMPONENT_MAPPING = {
    'ResistanceComponent': ResistanceComponent,
    'GrievousWoundsComponent': GrievousWoundsComponent,
    'ThornsComponent': ThornsComponent,
    'OverhealToShieldComponent': OverhealToShieldComponent,
    'AttackTriggerPassiveComponent': AttackTriggerPassiveComponent,
    # 未来新增的被动组件在这里注册
}

class PassiveFactory:
    """被动能力工厂，负责根据配置创建被动能力组件"""

    def __init__(self, data_manager):
        self.data_manager = data_manager

    def create_passive_component(self, version_id: str):
        """根据 version_id 创建被动能力组件"""
        passive_data = self.data_manager.get_passive_version_data(version_id)
        if not passive_data:
            raise ValueError(f"未找到被动能力版本: {version_id}")

        component_name = passive_data.get("component")
        if not component_name or component_name not in COMPONENT_MAPPING:
            raise ValueError(f"被动 {version_id} 指定的组件 {component_name} 无效或未注册")

        component_class = COMPONENT_MAPPING[component_name]

        # 从 passive_data 中提取组件构造函数需要的参数
        # 这里利用了Python的动态参数传递
        # dataclass 的字段名需要和 YAML 中的 values key 一致
        # 例如 ResistanceComponent(element="fire", percentage=0.5)
        # 这就要求你的 Component 的 __init__ 参数名和 YAML 中的 key 一致
        # dataclass 完美地满足了这个需求
        
        # 为了更通用，我们不再硬编码 if/elif
        # 而是动态地从 passive_data 中提取 component_class 所需的参数
        import inspect
        
        constructor_args = inspect.signature(component_class).parameters
        args_to_pass = {}
        for arg_name in constructor_args:
            if arg_name in passive_data:
                args_to_pass[arg_name] = passive_data[arg_name]
        
        try:
            return component_class(**args_to_pass)
        except TypeError as e:
            print(f"创建组件 {component_name} 失败: {e}。请检查 passive.yaml 中的 values 和组件的构造函数参数是否匹配。")
            return None




# from typing import Dict, Any, List
# from ..core.entity import Entity
# from ..core.components import (ResistanceComponent, GrievousWoundsComponent, ThornsComponent)

# class PassiveValidator:
#     """被动能力验证器，负责验证和创建被动能力组件"""
    
#     def __init__(self, data_manager):
#         self.data_manager = data_manager
#         self.component_mapping = {
#             'resistance': ResistanceComponent,
#             'grievous_wounds': GrievousWoundsComponent,
#             'thorns': ThornsComponent,
#         }
    
#     def validate_passive(self, passive_id: str, passive_data: Dict[str, Any]) -> tuple[bool, List[str]]:
#         """验证被动能力配置是否正确"""
#         passive_config = self.data_manager.get_passive_data(passive_id)
#         if not passive_config:
#             return False, [f"未找到被动能力配置: {passive_id}"]
        
#         errors = []
        
#         # 检查必需的属性
#         required_properties = passive_config.get('required_properties', [])
#         for prop in required_properties:
#             if prop not in passive_data:
#                 errors.append(f"缺少必需属性: {prop}")
        
#         # 检查属性类型
#         properties_config = passive_config.get('properties', {})
#         for prop_name, prop_value in passive_data.items():
#             if prop_name in properties_config:
#                 expected_type = properties_config[prop_name].get('type')
#                 if expected_type == 'float' and not isinstance(prop_value, (int, float)):
#                     errors.append(f"属性 {prop_name} 应该是数值类型")
#                 elif expected_type == 'dict' and not isinstance(prop_value, dict):
#                     errors.append(f"属性 {prop_name} 应该是字典类型")
        
#         return len(errors) == 0, errors
    
#     def create_passive_component(self, passive_id: str, passive_data: Dict[str, Any]):
#         """根据配置创建被动能力组件"""
#         if passive_id not in self.component_mapping:
#             raise ValueError(f"不支持的被动能力类型: {passive_id}")
        
#         component_class = self.component_mapping[passive_id]
        
#         if passive_id == 'resistance':
#             return component_class(resistances=passive_data['resistances'])
#         elif passive_id == 'grievous_wounds':
#             return component_class(reduction_percentage=passive_data['reduction_percentage'])
#         elif passive_id == 'thorns':
#             return component_class(thorns_percentage=passive_data['thorns_percentage'])
#         else:
#             raise ValueError(f"未实现的被动能力类型: {passive_id}")
    
#     def get_passive_info(self, passive_id: str) -> Dict[str, Any]:
#         """获取被动能力信息"""
#         passive_config = self.data_manager.get_passive_data(passive_id)
#         if not passive_config:
#             return {}
        
#         return {
#             'name': passive_config.get('name', passive_id),
#             'description': passive_config.get('description', ''),
#             'type': passive_config.get('type', passive_id),
#             'component': passive_config.get('component', ''),
#             'required_properties': passive_config.get('required_properties', []),
#             'properties': passive_config.get('properties', {})
#         }
    
#     def list_available_passives(self) -> List[str]:
#         """列出所有可用的被动能力"""
#         return list(self.data_manager.passive_data.keys()) 