from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import (ApplyStatusEffectRequestPayload, RemoveStatusEffectRequestPayload,
                             UpdateStatusEffectsDurationRequestPayload, DispelRequestPayload,
                             StatQueryPayload, LogRequestPayload, UIMessagePayload, DamageRequestPayload)
from ..core.components import StatusEffectContainerComponent, DeadComponent
from ..status_effects.status_effect import StatusEffect

class StatusEffectSystem:
    def __init__(self, event_bus: EventBus, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.world = world

        self.event_bus.subscribe(EventName.ROUND_START, self.on_round_start)
        self.event_bus.subscribe(EventName.APPLY_STATUS_EFFECT_REQUEST, self.on_apply_effect)
        self.event_bus.subscribe(EventName.REMOVE_STATUS_EFFECT_REQUEST, self.on_remove_effect)
        self.event_bus.subscribe(EventName.UPDATE_STATUS_EFFECTS_DURATION_REQUEST, self.on_update_effects_duration)
        self.event_bus.subscribe(EventName.DISPEL_REQUEST, self.on_dispel_effect)
        self.event_bus.subscribe(EventName.STAT_QUERY, self.on_stat_query)
    
    def on_apply_effect(self, event: GameEvent):
        payload: ApplyStatusEffectRequestPayload = event.payload
        target = payload.target
        effect = payload.effect
        container = target.get_component(StatusEffectContainerComponent)

        if not container:
            container = target.add_component(StatusEffectContainerComponent())
        
        # 特殊处理中毒效果 - 可以存在多个独立的中毒状态
        if effect.effect_id == "poison_01":
            # 检查是否达到最大中毒状态数量（10个）
            existing_poison_effects = [e for e in container.effects if e.effect_id == "poison_01"]
            poison_number = effect.poison_number  # 一次性添加的中毒状态数量
            
            if len(existing_poison_effects) >= 10:
                # 如果已经有10个中毒状态，找到层数最低的一个进行叠加
                min_stack_effect = min(existing_poison_effects, key=lambda e: e.stack_count)
                old_stack_count = min_stack_effect.stack_count
                min_stack_effect.stack_count = min(min_stack_effect.stack_count + effect.stack_intensity, effect.max_stacks)
                added_stacks = min_stack_effect.stack_count - old_stack_count
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 的 {effect.name} 效果增加了 {added_stacks} 层，现在总共 {min_stack_effect.stack_count} 层")))
            else:
                # 添加新的中毒状态，根据poison_number决定添加几个
                added_count = 0
                for i in range(poison_number):
                    if len(existing_poison_effects) + added_count >= 10:
                        break  # 达到最大数量限制
                    
                    # 创建新的中毒状态
                    new_poison_effect = StatusEffect(
                        effect_id=effect.effect_id,
                        name=effect.name,
                        duration=effect.duration,
                        category=effect.category,
                        stacking=effect.stacking,
                        max_stacks=effect.max_stacks,
                        stack_count=effect.stack_count,
                        stack_intensity=effect.stack_intensity,
                        poison_number=effect.poison_number,
                        caster=effect.caster,
                        context=effect.context,
                        logic=effect.logic
                    )
                    
                    container.effects.append(new_poison_effect)
                    new_poison_effect.logic.on_apply(target, new_poison_effect, self.event_bus)
                    added_count += 1
                
                total_poison_effects = len([e for e in container.effects if e.effect_id == "poison_01"])
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 获得了 {added_count} 个 {effect.name} 效果，每个 x{effect.stack_count} 层，现在共有 {total_poison_effects} 个中毒状态")))
        else:
            # 其他效果的原有逻辑
            existing_effect = next((e for e in container.effects if e.effect_id == effect.effect_id), None)
            if existing_effect:
                if effect.stacking == "refresh_duration":
                    existing_effect.duration = max(existing_effect.duration, effect.duration)
                    self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 的 {effect.name} 效果持续时间刷新为 {existing_effect.duration} 回合")))
                elif effect.stacking == "stack_intensity":
                    old_stack_count = existing_effect.stack_count
                    existing_effect.stack_count = min(existing_effect.stack_count + effect.stack_intensity, effect.max_stacks)
                    existing_effect.duration = effect.duration
                    added_stacks = existing_effect.stack_count - old_stack_count
                    self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 的 {effect.name} 效果增加了 {added_stacks} 层，现在总共 {existing_effect.stack_count} 层，持续时间刷新为 {existing_effect.duration} 回合")))
                
            else:
                container.effects.append(effect)
                effect.logic.on_apply(target, effect, self.event_bus)
                if effect.stacking == "stack_intensity":
                    self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 获得了 {effect.name} 效果 x{effect.stack_count} 层")))
                else:
                    self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {target.name} 获得了 {effect.name} 效果")))
    
    def on_dispel_effect(self, event: GameEvent):
        payload: DispelRequestPayload = event.payload
        container = payload.target.get_component(StatusEffectContainerComponent)
        if not container: return
        effects_to_dispel = [e for e in container.effects if e.category == payload.category_to_dispel]
        for i in range(min(payload.count, len(effects_to_dispel))):
            effect = effects_to_dispel[i]
            effect.logic.on_remove(payload.target, effect, self.event_bus)
            container.effects.remove(effect)
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {payload.target.name} 的 {effect.name} 效果已移除")))
    
    def on_stat_query(self, event: GameEvent):
        container = event.payload.entity.get_component(StatusEffectContainerComponent)
        if container:
            for effect in container.effects:
                effect.logic.on_stat_query(event.payload, effect)
    
    def on_remove_effect(self, event: GameEvent):
        payload: RemoveStatusEffectRequestPayload = event.payload
        container = payload.target.get_component(StatusEffectContainerComponent)
        if container:
            effect_to_remove = next((e for e in container.effects if e.effect_id == payload.effect_id), None)
            if effect_to_remove:
                effect_to_remove.logic.on_remove(payload.target, effect_to_remove, self.event_bus)
                container.effects.remove(effect_to_remove)
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", f"[{payload.target.name}] 状态效果 {payload.effect_id} 已移除")))
    
    def on_update_effects_duration(self, event: GameEvent):
        payload: UpdateStatusEffectsDurationRequestPayload = event.payload
        container = payload.target.get_component(StatusEffectContainerComponent)
        if container:
            effect = next((e for e in container.effects if e.effect_id == payload.effect_id), None)
            if effect:
                effect.duration += payload.change
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", f"[{payload.target.name}] 状态效果 {payload.effect_id} 的持续时间更新为 {effect.duration} 回合")))

    def on_round_start(self, event: GameEvent):
        """回合开始时，处理所有实体的状态效果"""
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", "---状态效果结算阶段---")))
        for entity in self.world.entities:
            if entity.has_component(DeadComponent):
                continue

            container = entity.get_component(StatusEffectContainerComponent)
            if not container: continue

            # 特殊处理中毒效果
            poison_effects = [e for e in container.effects if e.effect_id == "poison_01"]
            if poison_effects:
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
                    self.event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                        caster=poison_effects[0].caster or entity,
                        target=entity,
                        source_spell_id="poison_01",
                        source_spell_name="中毒",
                        base_damage=total_damage,
                        damage_type="poison",
                        is_reflection=False
                    )))
                
                # 中毒层数减1
                for poison_effect in poison_effects:
                    poison_effect.stack_count -= 1
                
                # 移除层数归0的中毒
                expired_poison_effects = [e for e in poison_effects if e.stack_count <= 0]
                for expired_effect in expired_poison_effects:
                    expired_effect.logic.on_remove(entity, expired_effect, self.event_bus)
                    container.effects.remove(expired_effect)
                
                # 一次性播报移除信息
                if expired_poison_effects:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", f"[{entity.name}] {len(expired_poison_effects)} 个中毒状态层数归0，已移除")))
                    self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {entity.name} 的 {len(expired_poison_effects)} 个中毒状态层数归0，已移除")))
                
                # 播报剩余中毒状态信息
                remaining_poison_effects = [e for e in poison_effects if e.stack_count > 0]
                if remaining_poison_effects:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", f"[{entity.name}] 剩余 {len(remaining_poison_effects)} 个中毒状态")))

            # 处理其他效果（保持原有逻辑）
            other_effects = [e for e in container.effects if e.effect_id != "poison_01"]
            for effect in list(other_effects):
                effect.logic.on_tick(entity, effect, self.event_bus)
                effect.duration -= 1

            # 移除已过期的其他状态效果
            expired_effects = [e for e in other_effects if e.duration <= 0]
            for expired_effect in expired_effects:
                expired_effect.logic.on_remove(entity, expired_effect, self.event_bus)
                container.effects.remove(expired_effect)
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", f"[{entity.name}] 状态效果 {expired_effect.name} 效果已过期")))
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {entity.name} 的 {expired_effect.name} 效果已结束")))
        
        # 状态结算完毕，发出通知
        self.event_bus.dispatch(GameEvent(EventName.STATUS_EFFECTS_RESOLVED))