from abc import ABC, abstractmethod
from typing import List, Optional
from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import StatQueryPayload, HealRequestPayload, UIMessagePayload, DamageRequestPayload, GainShieldPayload
from ..core.entity import Entity
from ..core.pipeline import EffectExecutionContext
from .status_effect import StatusEffect

class EffectLogic(ABC):
    """buff，debuff的抽象基类"""
    def on_apply(self, target: Entity, effect: StatusEffect, event_bus: EventBus): pass
    def on_tick(self, target: Entity, effect: StatusEffect, event_bus: EventBus): pass
    def on_remove(self, target: Entity, effect: StatusEffect, event_bus: EventBus): pass
    def on_stat_query(self, query: StatQueryPayload, effect: StatusEffect): pass
    def on_heal(self, payload: HealRequestPayload, effect: StatusEffect, event_bus: EventBus): pass
    
    def can_stack_with(self, existing_effect: StatusEffect, new_effect: StatusEffect) -> bool:
        """检查新效果是否可以与现有效果堆叠"""
        # 只有完全相同的效果ID才能堆叠（包括版本号）
        return existing_effect.effect_id == new_effect.effect_id
    
    def handle_stacking(self, target: Entity, existing_effect: StatusEffect, new_effect: StatusEffect, event_bus: EventBus) -> bool:
        """
        处理效果堆叠逻辑
        返回True表示堆叠成功，False表示需要创建新效果
        """
        if not self.can_stack_with(existing_effect, new_effect):
            return False
            
        if existing_effect.stacking == "refresh_duration":
            old_duration = existing_effect.duration
            existing_effect.duration = max(existing_effect.duration, new_effect.duration)
            event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                f"**状态效果**: {target.name} 的 {existing_effect.name} 效果持续时间刷新为 {existing_effect.duration} 回合"
            )))
            return True
        elif existing_effect.stacking == "stack_intensity":
            old_stack_count = existing_effect.stack_count
            existing_effect.stack_count = min(existing_effect.stack_count + new_effect.stack_intensity, existing_effect.max_stacks)
            existing_effect.duration = new_effect.duration
            added_stacks = existing_effect.stack_count - old_stack_count
            event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                f"**状态效果**: {target.name} 的 {existing_effect.name} 效果增加了 {added_stacks} 层，现在总共 {existing_effect.stack_count} 层，持续时间刷新为 {existing_effect.duration} 回合"
            )))
            return True
        
        return False

class DamageOverTimeEffect(EffectLogic):
    """持续伤害效果"""
    def on_tick(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        damage_per_round = effect.context.get("damage_per_round", 0)
        if effect.stack_count is None:
            total_damage = damage_per_round
        else:
            stacks = effect.stack_count
            total_damage = damage_per_round * stacks

        if total_damage > 0:
            # 获取施法者名称，如果没有则显示"未知"
            caster_name = effect.caster.name if effect.caster else "未知"
            
            if effect.stack_count:
                event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                    f"**持续伤害**: {target.name} 因为 {caster_name} 施加的持续伤害 [{effect.name} x{stacks}] 受到 {total_damage:.1f} 点伤害"
                )))
            else:
                event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                    f"**持续伤害**: {target.name} 因为 {caster_name} 施加的持续伤害 [{effect.name}] 受到 {total_damage:.1f} 点伤害"
                )))
            event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                caster=effect.caster or target,
                target=target,
                source_spell_id=effect.effect_id,
                source_spell_name=effect.name,
                base_damage=total_damage,
                damage_type=effect.context.get("damage_type", "pure"),
                can_be_reflected=effect.context.get("can_be_reflected", False),
                is_reflection=effect.context.get("is_reflection", False),
                is_dot_damage=True  # 标记为持续伤害
            )))

class StatModificationLogic(EffectLogic):
    """属性修改效果"""
    def on_stat_query(self, query: StatQueryPayload, effect: StatusEffect):
        stat_mods = effect.context.get("stat_mods", {})
        if query.stat_name in stat_mods:
            mods = stat_mods[query.stat_name]
            query.current_value *= mods.get("multiply", 1)
            query.current_value += mods.get("add", 0)
    
    def on_remove(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        pass

class OverhealConversionLogic(EffectLogic):
    """溢疗转换效果"""
    def on_heal(self,payload: 'EffectExecutionContext', effect: StatusEffect, event_bus: EventBus):
        if rate := effect.context.get("conversion_rate", 0):
            shield_gain = payload.overheal_amount * rate
            if shield_gain > 0:
                event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                    f"**被动**: {payload.target.name}在[{effect.name}]下将 {payload.overheal_amount:.1f}点溢出治疗转化为 {shield_gain:.1f}点护盾"
                )))
                event_bus.dispatch(GameEvent(EventName.GAIN_SHIELD_REQUEST, GainShieldPayload(
                    target=payload.target, source=effect.name, amount=shield_gain
                )))

class PoisonDotEffect(EffectLogic):
    """中毒持续伤害效果 - 基于状态数量，结算后层数减1"""
    
    def can_stack_with(self, existing_effect: StatusEffect, new_effect: StatusEffect) -> bool:
        """中毒效果可以存在多个独立的状态"""
        return False  # 中毒效果不堆叠，而是创建新的独立状态
    
    def handle_stacking(self, target: Entity, existing_effect: StatusEffect, new_effect: StatusEffect, event_bus: EventBus) -> bool:
        """中毒效果不堆叠，总是创建新状态"""
        return False
    
    def on_tick(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        # 伤害计算：基础伤害 × 1（与层数无关，只与状态数量相关）
        damage_per_round = effect.context.get("damage_per_round", 0)
        total_damage = damage_per_round  # 每个中毒状态造成基础伤害，与层数无关
        if total_damage > 0:
            # 获取施法者名称，如果没有则显示"未知"
            caster_name = effect.caster.name if effect.caster else "未知"
            
            event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                f"**持续伤害**: {target.name} 因为 {caster_name} 施加的持续伤害 [{effect.name}] 受到 {total_damage:.1f} 点伤害"
            )))
            event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                caster=effect.caster or target,
                target=target,
                source_spell_id=effect.effect_id,
                source_spell_name=effect.name,
                base_damage=total_damage,
                damage_type=effect.context.get("damage_type", "pure"),
                can_be_reflected=effect.context.get("can_be_reflected", False),
                is_reflection=effect.context.get("is_reflection", False),
                is_dot_damage=True  # 标记为持续伤害
            )))

    def on_remove(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        pass

class PoisonEffectLogic(EffectLogic):
    """专门处理中毒效果的应用、堆叠和结算逻辑"""
    
    def can_stack_with(self, existing_effect: StatusEffect, new_effect: StatusEffect) -> bool:
        """中毒效果可以存在多个独立的状态"""
        return False  # 中毒效果不堆叠，而是创建新的独立状态
    
    def handle_stacking(self, target: Entity, current_effect: StatusEffect, stack_num: int, event_bus: EventBus) -> bool:
        """中毒效果堆叠，所有中毒效果层数叠加"""
        current_effect.stack_count = min(current_effect.stack_count + stack_num, current_effect.max_stacks)
        return True 
    def apply_poison_effects(self, target: Entity, new_effect: StatusEffect, existing_poison_effects: List[StatusEffect], event_bus: EventBus) -> int:
        """
        应用中毒效果的特殊逻辑
        返回实际添加的中毒状态数量
        """
        poison_number = new_effect.poison_number  # 一次性添加的中毒状态数量
        max_poison_effects = 10  # 最大中毒状态数量
        
        if len(existing_poison_effects) >= max_poison_effects:
            # 如果已经有10个中毒状态，找到层数最低的一个进行叠加
            min_stack_effect = min(existing_poison_effects, key=lambda e: e.stack_count)
            old_stack_count = min_stack_effect.stack_count
            min_stack_effect.stack_count = min(min_stack_effect.stack_count + new_effect.stack_intensity, new_effect.max_stacks)
            added_stacks = min_stack_effect.stack_count - old_stack_count
            event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                f"**状态效果**: {target.name} 的 {new_effect.name} 效果增加了 {added_stacks} 层，现在总共 {min_stack_effect.stack_count} 层"
            )))
            return 0  # 没有添加新状态，只是叠加了层数
        else:
            # 添加新的中毒状态，根据poison_number决定添加几个
            added_count = 0
            for i in range(poison_number):
                if len(existing_poison_effects) + added_count >= max_poison_effects:
                    break  # 达到最大数量限制
                
                # 这里只是计算数量，实际创建在外部处理
                added_count += 1
            
            total_poison_effects = len(existing_poison_effects) + added_count
            event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                f"**状态效果**: {target.name} 获得了 {added_count} 个 {new_effect.name} 效果，每个 x{new_effect.stack_count} 层，现在共有 {total_poison_effects} 个中毒状态"
            )))
            return added_count
    
    def tick_poison_effects(self, target: Entity, poison_effects: List[StatusEffect], event_bus: EventBus) -> List[StatusEffect]:
        """
        结算中毒效果的特殊逻辑
        返回需要移除的中毒效果列表
        """
        # 计算总伤害：每个中毒状态造成基础伤害，与层数无关
        total_damage = 0
        for poison_effect in poison_effects:
            damage_per_round = poison_effect.context.get("damage_per_round", 0)
            total_damage += damage_per_round
        
        # 一次性播报所有中毒伤害
        if total_damage > 0:
            # 获取施法者名称，如果没有则显示"未知"
            caster_name = poison_effects[0].caster.name if poison_effects[0].caster else "未知"
            
            event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                f"**持续伤害**: {target.name} 因为 {caster_name} 施加的持续伤害 [{len(poison_effects)}个中毒状态] 受到 {total_damage:.1f} 点伤害"
            )))
            event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                caster=poison_effects[0].caster or target,
                target=target,
                source_spell_id="poison_01",
                source_spell_name="中毒",
                base_damage=total_damage,
                damage_type="poison",
                can_be_reflected=poison_effects[0].context.get("can_be_reflected", False),
                is_reflection=poison_effects[0].context.get("is_reflection", False)
            )))
        
        # 中毒层数减1
        for poison_effect in poison_effects:
            poison_effect.stack_count -= 1
        
        # 返回层数归0的中毒效果
        expired_poison_effects = [e for e in poison_effects if e.stack_count <= 0]
        return expired_poison_effects
    
    def on_apply(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        """中毒效果的应用逻辑"""
        pass  # 具体逻辑在apply_poison_effects中处理
    
    def on_tick(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        """中毒效果的结算逻辑"""
        pass  # 具体逻辑在tick_poison_effects中处理
    
    def on_remove(self, target: Entity, effect: StatusEffect, event_bus: EventBus):
        pass