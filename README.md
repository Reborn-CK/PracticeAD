# PracticeAD - 回合制战斗游戏

这是一个基于事件驱动架构的回合制战斗游戏项目，使用Python开发。

## 项目结构

```
PracticeAD/
├── data/                          # 数据文件
│   ├── spells.yaml               # 法术数据
│   └── status_effects.yaml       # 状态效果数据
├── game/                         # 游戏核心代码
│   ├── core/                     # 核心系统
│   │   ├── components.py         # 组件定义
│   │   ├── entity.py            # 实体类
│   │   ├── enums.py             # 事件枚举
│   │   ├── event_bus.py         # 事件总线
│   │   └── payloads.py          # 事件载荷
│   ├── systems/                  # 游戏系统
│   │   ├── combat/              # 战斗系统
│   │   ├── data_manager.py      # 数据管理
│   │   ├── dead_system.py       # 死亡系统
│   │   ├── enemy_ai_system.py   # 敌人AI
│   │   ├── interaction_system.py # 交互系统
│   │   ├── log_system.py        # 日志系统
│   │   ├── mana_system.py       # 法力系统
│   │   ├── passive_ability_system.py # 被动能力
│   │   ├── player_input_system.py # 玩家输入
│   │   ├── spell_cast_system.py # 法术施放
│   │   ├── status_effect_system.py # 状态效果
│   │   ├── turn_manager_system.py # 回合管理
│   │   └── ui_system.py         # UI系统
│   ├── status_effects/           # 状态效果逻辑
│   │   ├── effect_logic.py      # 效果逻辑
│   │   └── status_effect.py     # 状态效果类
│   ├── world.py                 # 游戏世界
│   └── main.py                  # 主程序
├── practice_0.py                # 完整示例代码
├── run_game.py                  # 游戏运行脚本
├── test_project_structure.py    # 项目结构测试
└── README.md                    # 项目说明
```

## 运行游戏

### 方法1：使用运行脚本
```bash
python run_game.py
```

### 方法2：直接运行主程序
```bash
python -m game.main
```

### 方法3：运行完整示例
```bash
python practice_0.py
```

## 测试项目结构

在运行游戏之前，可以先测试项目结构是否正确：

```bash
python test_project_structure.py
```

## 游戏特性

### 核心系统
- **事件驱动架构**：所有游戏逻辑通过事件系统进行通信
- **组件系统**：实体通过组件组合实现不同功能
- **回合制战斗**：基于速度的回合顺序
- **状态效果系统**：支持buff/debuff的叠加和持续时间管理

### 战斗系统
- **伤害计算**：支持护盾、抗性、反伤等机制
- **治疗系统**：支持溢出治疗转换为护盾
- **生命偷取**：部分法术支持生命偷取
- **被动能力**：如绝地护盾等被动技能

### 法术系统
- **多种效果**：伤害、治疗、状态效果、驱散等
- **目标选择**：支持敌人、友军、任意目标
- **法术交互**：如燃烬技能可以消耗燃烧状态造成额外伤害
- **法力消耗**：每个法术都有相应的法力消耗

### 状态效果
- **持续伤害**：如燃烧、中毒等
- **属性修改**：如加速、减速等
- **溢出治疗转换**：将溢出治疗转换为护盾

## 数据文件

### spells.yaml
定义所有法术的数据，包括：
- 法术名称和描述
- 法力消耗
- 目标类型
- 效果列表（伤害、治疗、状态效果等）
- 交互效果（如燃烬的消耗效果）

### status_effects.yaml
定义所有状态效果的数据，包括：
- 效果名称和描述
- 持续时间
- 叠加规则
- 效果逻辑类型
- 上下文数据

## 开发说明

### 添加新法术
1. 在 `data/spells.yaml` 中添加法术定义
2. 确保相关的状态效果在 `data/status_effects.yaml` 中定义
3. 在 `game/main.py` 中将法术ID添加到玩家的法术列表中

### 添加新状态效果
1. 在 `data/status_effects.yaml` 中添加效果定义
2. 在 `game/status_effects/effect_logic.py` 中实现效果逻辑
3. 在 `EFFECT_LOGIC_MAP` 中注册新的效果逻辑

### 添加新系统
1. 创建新的系统类
2. 在构造函数中订阅相关事件
3. 在 `game/main.py` 中注册系统

## 技术特点

- **模块化设计**：每个系统职责单一，易于维护和扩展
- **事件驱动**：系统间通过事件通信，降低耦合度
- **数据驱动**：游戏内容通过YAML文件配置，易于修改
- **类型提示**：使用Python类型提示提高代码可读性
- **错误处理**：完善的异常处理机制

## 依赖

- Python 3.7+
- PyYAML

安装依赖：
```bash
pip install pyyaml
``` 