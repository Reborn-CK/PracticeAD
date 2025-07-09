# 燃烧效果多版本堆叠逻辑实现

## 需求说明

用户希望燃烧效果有多个版本（如 `burning_01`、`burning_02`），当应用相同版本时只刷新该版本的时间，不同版本时创建新的效果。

## 实现方案

### 1. 数据结构设计

在 `status_effects.yaml` 中为燃烧效果添加多个版本：

```yaml
# 燃烧
burning:
  name: "燃烧"
  description: "持续造成火焰伤害的燃烧效果。"
  category: "elemental_debuff"
  logic: "dot"
  stacking: "refresh_duration"
  versions:
    - version_id: "burning_01"
      name: "燃烧1"
      description: "基础燃烧效果，每回合造成火焰伤害。"
      duration: 3
      context:
        damage_per_round: 5
        damage_type: "fire"
    - version_id: "burning_02"
      name: "燃烧2"
      description: "中级燃烧效果，每回合造成火焰伤害。"
      duration: 3
      context:
        damage_per_round: 10
        damage_type: "fire"
```

### 2. 堆叠逻辑实现

#### 2.1 效果堆叠判断

在 `EffectLogic` 类中，`can_stack_with` 方法确保只有完全相同的效果ID才能堆叠：

```python
def can_stack_with(self, existing_effect: StatusEffect, new_effect: StatusEffect) -> bool:
    """检查新效果是否可以与现有效果堆叠"""
    # 只有完全相同的效果ID才能堆叠（包括版本号）
    return existing_effect.effect_id == new_effect.effect_id
```

#### 2.2 效果应用逻辑

在 `StatusEffectSystem` 的 `_apply_normal_effect` 方法中：

```python
def _apply_normal_effect(self, target, effect, container):
    """应用普通效果的标准逻辑"""
    existing_effect = next((e for e in container.effects if e.effect_id == effect.effect_id), None)
    
    if existing_effect:
        # 尝试堆叠
        if effect.logic.handle_stacking(target, existing_effect, effect, self.event_bus):
            return  # 堆叠成功，不需要创建新效果
    
    # 创建新效果
    container.effects.append(effect)
    effect.logic.on_apply(target, effect, self.event_bus)
```

### 3. 堆叠行为说明

#### 3.1 相同版本堆叠

- **场景**: 应用 `burning_01` 后再次应用 `burning_01`
- **行为**: 刷新现有效果的持续时间，不创建新效果
- **结果**: 只有一个 `burning_01` 效果，持续时间重置为3回合

#### 3.2 不同版本共存

- **场景**: 应用 `burning_01` 后应用 `burning_02`
- **行为**: 创建新的效果，与现有效果共存
- **结果**: 同时存在 `burning_01` 和 `burning_02` 两个效果

#### 3.3 不同版本独立堆叠

- **场景**: 已有 `burning_01` 和 `burning_02`，再次应用 `burning_01`
- **行为**: 只刷新 `burning_01` 的持续时间，不影响 `burning_02`
- **结果**: `burning_01` 持续时间重置，`burning_02` 保持不变

### 4. 效果结算

#### 4.1 独立结算

每个燃烧效果独立进行回合结算：

```python
def _tick_normal_effects(self, entity, effects, container):
    """结算普通效果"""
    for effect in list(effects):
        effect.logic.on_tick(entity, effect, self.event_bus)
        effect.duration -= 1

    # 移除已过期的状态效果
    expired_effects = [e for e in effects if e.duration <= 0]
    for expired_effect in expired_effects:
        expired_effect.logic.on_remove(entity, expired_effect, self.event_bus)
        container.effects.remove(expired_effect)
```

#### 4.2 伤害计算

每个燃烧效果独立计算伤害：

```python
def on_tick(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
    damage_per_round = effect.context.get("damage_per_round", 0)
    if effect.stack_count is None:
        total_damage = damage_per_round
    else:
        stacks = effect.stack_count
        total_damage = damage_per_round * stacks
    
    if total_damage > 0:
        # 派发伤害事件
        event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(...)))
```

### 5. 测试用例

#### 5.1 测试场景

1. **应用 burning_01**
   - 期望: 创建 burning_01 效果，持续时间3回合

2. **再次应用 burning_01**
   - 期望: 刷新 burning_01 的持续时间，不创建新效果

3. **应用 burning_02**
   - 期望: 创建 burning_02 效果，与 burning_01 共存

4. **再次应用 burning_02**
   - 期望: 刷新 burning_02 的持续时间，不影响 burning_01

5. **回合结算**
   - 期望: 两个效果独立结算，分别造成伤害

#### 5.2 预期结果

- `burning_01`: 每回合造成5点火焰伤害
- `burning_02`: 每回合造成10点火焰伤害
- 总伤害: 每回合15点火焰伤害
- 持续时间: 各自独立计算

### 6. 扩展性

#### 6.1 添加新版本

可以轻松添加新的燃烧版本：

```yaml
- version_id: "burning_03"
  name: "燃烧3"
  description: "高级燃烧效果，每回合造成火焰伤害。"
  duration: 5
  context:
    damage_per_round: 15
    damage_type: "fire"
```

#### 6.2 其他效果类型

相同的逻辑可以应用到其他效果类型：

- 中毒效果: `poison_01`, `poison_02`
- 加速效果: `speedup_01`, `speedup_02`
- 等等

### 7. 优势

1. **版本独立性**: 每个版本独立存在和结算
2. **堆叠精确性**: 只有相同版本才能堆叠
3. **扩展性**: 可以轻松添加新版本
4. **兼容性**: 保持与现有系统的兼容性
5. **清晰性**: 逻辑清晰，易于理解和维护

## 结论

燃烧效果的多版本堆叠逻辑已经成功实现，能够满足用户的需求：

- ✅ 相同版本只刷新时间
- ✅ 不同版本独立存在
- ✅ 独立结算和伤害计算
- ✅ 支持扩展新版本
- ✅ 保持系统稳定性 