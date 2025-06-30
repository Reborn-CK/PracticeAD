# 中毒层数UI显示修复

## 问题描述
用户反馈UI没有显示中毒的层数，导致玩家无法直观地看到中毒效果的叠加情况。

## 解决方案
修改了 `game/systems/ui_system.py` 中的状态效果显示逻辑，为可以叠加的效果显示层数信息。

## 修改内容

### 修改前
```python
effects_list = [f"{e.name} ({e.duration}回合)" for e in container.effects]
```

### 修改后
```python
effects_list = []
for e in container.effects:
    if e.stacking == "stack_intensity":
        effects_list.append(f"{e.name} x{e.stack_count} ({e.duration}回合)")
    else:
        effects_list.append(f"{e.name} ({e.duration}回合)")
```

## 显示效果

### 中毒效果（可叠加）
- 1层：`中毒 x1 (5回合)` ✅ **现在1层也显示层数**
- 2层：`中毒 x2 (5回合)`
- 5层：`中毒 x5 (5回合)`
- 10层：`中毒 x10 (5回合)`

### 燃烧效果（不可叠加）
- 始终显示：`燃烧 (3回合)`

## 层数叠加逻辑

### YAML配置
```yaml
poison_01:
  name: 中毒
  category: "physical_debuff"
  logic: "poison_dot"  # 新的逻辑类型
  stacking: "stack_intensity"
  stack_intensity: 2
  poison_number: 5  # 一次性添加5个中毒状态
  max_stacks: 10
  # 移除了 duration 字段
  context:
    damage_per_round: 5
    damage_type: "poison"
```

### 初始层数设置
修改了 `game/status_effects/status_effect_factory.py`，让第一次施加时按照YAML配置的`stack_intensity`设置初始层数：

```python
# 修改前
stack_count=1,  # 默认1层

# 修改后
stack_count=effect_data.get("stack_intensity", 1),  # 初始层数等于stack_intensity
```

### 叠加过程
1. **第一次施放毒云术**：获得2层中毒（按YAML配置）
2. **第二次施放毒云术**：2 + 2 = 4层中毒
3. **第三次施放毒云术**：4 + 2 = 6层中毒
4. **继续施放**：直到达到最大10层

### 状态效果系统逻辑
```python
# 在 game/systems/status_effect_system.py 第32行
existing_effect.stack_count = min(existing_effect.stack_count + effect.stack_intensity, effect.max_stacks)
```

## 播报消息改进

### 第一次获得效果
修改了 `game/systems/status_effect_system.py` 的播报逻辑：

```python
# 修改前
self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 获得了 {effect.name} 效果")))

# 修改后
if effect.stacking == "stack_intensity":
    self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 获得了 {effect.name} 效果 x{effect.stack_count} 层")))
else:
    self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 获得了 {effect.name} 效果")))
```

### 效果叠加时
```python
# 修改前
self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 的 {effect.name} 效果叠加为 {existing_effect.stack_count} 层, 持续时间刷新为 {existing_effect.duration} 回合")))

# 修改后
old_stack_count = existing_effect.stack_count
existing_effect.stack_count = min(existing_effect.stack_count + effect.stack_intensity, effect.max_stacks)
added_stacks = existing_effect.stack_count - old_stack_count
self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 的 {effect.name} 效果增加了 {added_stacks} 层，现在总共 {existing_effect.stack_count} 层，持续时间刷新为 {existing_effect.duration} 回合")))
```

### 播报效果示例
- **第一次获得**：`**状态效果**: Boss 获得了 5 个 中毒 效果，每个 x2 层，现在共有 5 个中毒状态`
- **第二次获得**：`**状态效果**: Boss 获得了 5 个 中毒 效果，每个 x2 层，现在共有 10 个中毒状态`
- **达到10个后**：`**状态效果**: Boss 的 中毒 效果增加了 2 层，现在总共 4 层`
- **回合结算**：`**持续伤害**: Boss 因[10个中毒状态] 受到了 50.0 点伤害`
- **状态移除**：`**状态效果**: Boss 的 3 个中毒状态层数归0，已移除`

## 相关系统验证

### 状态效果系统
- ✅ 正确实现层数叠加逻辑
- ✅ 在叠加时更新 `stack_count`
- ✅ 限制最大层数不超过 `max_stacks`
- ✅ 使用YAML配置的 `stack_intensity` 值
- ✅ 第一次施加时按 `stack_intensity` 设置初始层数

### 持续伤害效果
- ✅ 伤害计算：`total_damage = damage_per_round * stacks`
- ✅ UI消息显示层数：`因[中毒 x3] 受到了 15.0 点伤害`

### 数据配置
- ✅ 中毒效果配置为 `stacking: "stack_intensity"`
- ✅ 最大层数：10层
- ✅ 每次叠加：2层（按YAML配置）
- ✅ 初始层数：2层（按YAML配置）

## 测试方法
1. 使用毒云术对敌人施放1次 → 应该显示：`中毒 x5个(2层)(2层)(2层)(2层)(2层)`，播报：`获得了 5 个 中毒 效果，每个 x2 层，现在共有 5 个中毒状态`
2. 再次使用毒云术 → 应该显示：`中毒 x10个(2层)(2层)(2层)(2层)(2层)(2层)(2层)(2层)(2层)(2层)`，播报：`获得了 5 个 中毒 效果，每个 x2 层，现在共有 10 个中毒状态`
3. 继续施放 → 应该播报：`中毒 效果增加了 2 层，现在总共 4 层`
4. 观察持续伤害消息中的层数显示

## 技术细节
- 所有 `stacking == "stack_intensity"` 的效果都显示层数（包括1层）
- 其他效果（如燃烧）保持原有显示格式
- 层数显示格式：`效果名 x层数 (持续时间回合)`
- 叠加逻辑：`新层数 = min(当前层数 + stack_intensity, max_stacks)`
- 初始层数：`stack_count = stack_intensity`
- 播报消息显示获得层数和总层数

---

# 新中毒逻辑设计

## 设计理念
改变中毒效果的设计理念，从基于回合数的持续效果改为基于状态数量的独立效果。

## 核心变化

### 1. 移除回合数限制
- **修改前**：中毒效果有固定的回合数（如5回合）
- **修改后**：中毒效果不再有回合数限制，而是基于层数

### 2. 多个独立的中毒状态
- **修改前**：只能有一个中毒效果，通过层数叠加
- **修改后**：可以同时存在最多10个独立的中毒状态

### 3. 结算机制改变
- **修改前**：回合结束时减少持续时间
- **修改后**：回合结束时每个中毒状态的层数减1，层数归0时移除

## 技术实现

### YAML配置修改
```yaml
poison_01:
  name: 中毒
  category: "physical_debuff"
  logic: "poison_dot"  # 新的逻辑类型
  stacking: "stack_intensity"
  stack_intensity: 2
  poison_number: 5  # 一次性添加5个中毒状态
  max_stacks: 10
  # 移除了 duration 字段
  context:
    damage_per_round: 5
    damage_type: "poison"
```

### 新的逻辑类
创建了 `PoisonDotEffect` 类，继承自 `EffectLogic`：
```python
class PoisonDotEffect(EffectLogic):
    """中毒持续伤害效果 - 基于状态数量，结算后层数减1"""
    def on_tick(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        # 伤害计算：基础伤害 × 1（与层数无关，只与状态数量相关）
        damage_per_round = effect.context.get("damage_per_round", 0)
        total_damage = damage_per_round  # 每个中毒状态造成基础伤害，与层数无关
        # 派发伤害事件...
```

### 中毒伤害计算逻辑
**重要变化**：中毒伤害计算不再与层数相关，只与中毒状态数量相关：

#### 旧逻辑
```python
# 伤害 = 基础伤害 × 层数
total_damage = damage_per_round * effect.stack_count
```

#### 新逻辑
```python
# 伤害 = 基础伤害 × 状态数量（与层数无关）
total_damage = damage_per_round  # 每个中毒状态造成基础伤害
```

#### 伤害计算示例
- **3个1层中毒状态**：3 × 5 = 15点伤害
- **3个10层中毒状态**：3 × 5 = 15点伤害（与旧逻辑的150点不同）
- **1个1层中毒状态**：1 × 5 = 5点伤害
- **1个10层中毒状态**：1 × 5 = 5点伤害（与旧逻辑的50点不同）

### 一次性播报机制
修改了回合结算逻辑，实现一次性播报：

#### 伤害播报
```python
# 计算总伤害：每个中毒状态造成基础伤害，与层数无关
total_damage = 0
for poison_effect in poison_effects:
    damage_per_round = poison_effect.context.get("damage_per_round", 0)
    total_damage += damage_per_round

# 一次性播报所有中毒伤害
if total_damage > 0:
    self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
        f"**持续伤害**: {entity.name} 因[{len(poison_effects)}个中毒状态] 受到了 {total_damage:.1f} 点伤害"
    )))
```

#### 移除播报
```python
# 一次性播报移除信息
if expired_poison_effects:
    self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
        f"**状态效果**: {entity.name} 的 {len(expired_poison_effects)} 个中毒状态层数归0，已移除"
    )))
```

### poison_number 功能
新增了 `poison_number` 字段，决定技能一次性添加多少个中毒状态：

#### StatusEffect 类修改
```python
@dataclass
class StatusEffect:
    # ... 其他字段 ...
    poison_number: int = 1  # 一次性添加的中毒状态数量
```

#### 状态效果工厂修改
```python
return StatusEffect(
    # ... 其他字段 ...
    poison_number=effect_data.get("poison_number", 1),  # 一次性添加的中毒状态数量
)
```

#### 应用效果逻辑
```python
# 添加新的中毒状态，根据poison_number决定添加几个
added_count = 0
for i in range(poison_number):
    if len(existing_poison_effects) + added_count >= 10:
        break  # 达到最大数量限制
    
    # 创建新的中毒状态
    new_poison_effect = StatusEffect(...)
    container.effects.append(new_poison_effect)
    added_count += 1

# 播报消息
self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
    f"**状态效果**: {target.name} 获得了 {added_count} 个 {effect.name} 效果，每个 x{effect.stack_count} 层，现在共有 {total_poison_effects} 个中毒状态"
)))
```

### UI显示修改
```python
# 特殊处理中毒效果 - 显示多个中毒状态
poison_effects = [e for e in container.effects if e.effect_id == "poison_01"]
if poison_effects:
    poison_str = f"中毒 x{len(poison_effects)}个"
    for effect in poison_effects:
        poison_str += f"({effect.stack_count}层)"
    effects_list.append(poison_str)
```

## 效果示例

### UI显示
- **1个中毒状态**：`中毒 x1个(2层)`
- **3个中毒状态**：`中毒 x3个(2层)(3层)(1层)`
- **10个中毒状态**：`中毒 x10个(1层)(2层)(1层)(3层)(1层)(2层)(1层)(1层)(1层)(1层)`

### 播报消息
- **第一次获得**：`**状态效果**: Boss 获得了 5 个 中毒 效果，每个 x2 层，现在共有 5 个中毒状态`
- **第二次获得**：`**状态效果**: Boss 获得了 5 个 中毒 效果，每个 x2 层，现在共有 10 个中毒状态`
- **达到10个后**：`**状态效果**: Boss 的 中毒 效果增加了 2 层，现在总共 4 层`
- **回合结算**：`**持续伤害**: Boss 因[10个中毒状态] 受到了 50.0 点伤害`
- **状态移除**：`**状态效果**: Boss 的 3 个中毒状态层数归0，已移除`

### 回合结算
- **回合1**：每个中毒状态层数减1，移除层数归0的状态，一次性播报总伤害
- **回合2**：继续减1，继续移除，一次性播报总伤害
- **直到所有中毒状态都被移除**

#### 结算示例
```
回合1结算:
  **持续伤害**: Boss 因[10个中毒状态] 受到了 50.0 点伤害
  **状态效果**: Boss 的 2 个中毒状态层数归0，已移除
  [STATUS]: Boss 剩余 8 个中毒状态

回合2结算:
  **持续伤害**: Boss 因[8个中毒状态] 受到了 40.0 点伤害
  **状态效果**: Boss 的 3 个中毒状态层数归0，已移除
  [STATUS]: Boss 剩余 5 个中毒状态
```

## 优势
1. **更灵活的效果管理**：可以同时存在多个不同层数的中毒状态
2. **更直观的UI显示**：清楚显示有多少个中毒状态和各自的层数
3. **更精确的伤害计算**：每个中毒状态独立计算伤害
4. **更好的策略性**：玩家可以管理多个中毒状态的层数

## 限制
1. **最多10个中毒状态**：防止状态过多影响性能
2. **每个状态最多10层**：保持平衡性
3. **层数归0时立即移除**：确保状态管理的清晰性 