# 被动能力系统说明

## 概述

被动能力系统已经重构为基于YAML配置的模块化设计，passives.yaml和characters.yaml之间形成了真正的关联关系，方便扩展和维护。

## 文件结构

```
data/
├── characters.yaml    # 角色配置（包含被动能力引用）
├── passives.yaml      # 被动能力定义
├── spells.yaml        # 法术配置
└── status_effects.yaml # 状态效果配置
```

## 被动能力配置 (passives.yaml)

### 配置格式

```yaml
passive_id:
  name: "被动能力名称"
  description: "被动能力描述"
  type: "passive_type"
  component: "ComponentClassName"
  required_properties:
    - "property_name"  # 必需属性列表
  properties:
    property_name:
      type: "property_type"
      description: "属性描述"
      example: value
```

### 当前支持的被动能力

1. **resistance** - 元素抗性
   - 减少特定元素伤害
   - 属性：resistances (dict)

2. **grievous_wounds** - 重伤
   - 减少治疗效果
   - 属性：reduction_percentage (float)

3. **thorns** - 反伤
   - 受到攻击时反弹伤害
   - 属性：thorns_percentage (float)

## 角色配置 (characters.yaml)

### 被动能力引用格式

```yaml
character_id:
  # ... 其他属性 ...
  passives:
    - id: "passive_id"  # 引用passives.yaml中的被动能力
      property_name: value  # 具体的属性值
```

### 示例

```yaml
hero:
  name: "勇者"
  type: "player"
  stats:
    hp: 100
    max_hp: 100
    # ... 其他属性
  passives:
    - id: "resistance"
      resistances:
        fire: 0.5
    - id: "grievous_wounds"
      reduction_percentage: 0.5
```

## 系统架构

### 核心组件

1. **PassiveValidator** - 被动能力验证器
   - 验证被动能力配置的正确性
   - 根据配置自动创建对应的组件
   - 提供被动能力信息查询功能

2. **DataManager** - 数据管理器
   - 加载passives.yaml和characters.yaml
   - 提供数据访问接口

3. **CharacterFactory** - 角色工厂
   - 使用PassiveValidator创建被动能力组件
   - 自动验证和错误处理

### 数据关联

- **passives.yaml** 定义被动能力的模板和验证规则
- **characters.yaml** 引用passives.yaml中的被动能力ID，并提供具体的属性值
- **PassiveValidator** 负责验证关联关系的正确性

## 添加新的被动能力

### 步骤1：在passives.yaml中定义

```yaml
new_passive:
  name: "新被动能力"
  description: "新被动能力的描述"
  type: "new_passive"
  component: "NewPassiveComponent"
  required_properties:
    - "new_property"
  properties:
    new_property:
      type: "float"
      description: "新属性描述"
      example: 0.5
```

### 步骤2：在components.py中创建组件

```python
@dataclass
class NewPassiveComponent:
    new_property: float
```

### 步骤3：在passive_validator.py中添加映射

```python
self.component_mapping = {
    'resistance': ResistanceComponent,
    'grievous_wounds': GrievousWoundsComponent,
    'thorns': ThornsComponent,
    'new_passive': NewPassiveComponent,  # 添加新映射
}
```

### 步骤4：在passive_validator.py中添加创建逻辑

```python
elif passive_id == 'new_passive':
    return component_class(new_property=passive_data['new_property'])
```

### 步骤5：在characters.yaml中引用

```yaml
character_id:
  # ... 其他配置 ...
  passives:
    - id: "new_passive"
      new_property: 0.5
```

## 优势

1. **真正的关联**：passives.yaml和characters.yaml之间形成了真正的关联关系
2. **自动验证**：系统自动验证被动能力配置的正确性
3. **类型安全**：通过组件系统确保类型安全
4. **易于扩展**：添加新被动能力只需修改配置文件
5. **文档化**：每个被动能力都有详细的描述和示例
6. **可重用**：同一被动能力可以被多个角色使用
7. **错误处理**：提供详细的错误信息，便于调试

## 使用示例

```python
# 在角色工厂中自动创建被动能力组件
character_factory = CharacterFactory(event_bus, data_manager)
hero = character_factory.create_character("hero", world)

# 检查被动能力是否正确添加
if hero.has_component(ResistanceComponent):
    resistance = hero.get_component(ResistanceComponent)
    print(f"火抗: {resistance.resistances.get('fire', 0)}") 