from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import (ApplyStatusEffectRequestPayload, RemoveStatusEffectRequestPayload,
                             UpdateStatusEffectsDurationRequestPayload, DispelRequestPayload,
                             StatQueryPayload, LogRequestPayload, UIMessagePayload, DamageRequestPayload,
                             AmplifyPoisonRequestPayload, DetonatePoisonRequestPayload,
                             StatusEffectsResolvedPayload, ReduceDebuffsRequestPayload)
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
        self.event_bus.subscribe(EventName.AMPLIFY_POISON_REQUEST, self.on_amplify_poison)
        self.event_bus.subscribe(EventName.DETONATE_POISON_REQUEST, self.on_detonate_poison)
        self.event_bus.subscribe(EventName.REDUCE_DEBUFFS_REQUEST, self.on_reduce_debuffs)
    
    def on_apply_effect(self, event: GameEvent):
        payload: ApplyStatusEffectRequestPayload = event.payload
        target = payload.target
        effect = payload.effect
        container = target.get_component(StatusEffectContainerComponent)

        if not container:
            container = target.add_component(StatusEffectContainerComponent())
        
        # 特殊处理中毒效果
        if effect.effect_id == "poison_01":
            self._apply_poison_effect(target, effect, container)
        else:
            self._apply_normal_effect(target, effect, container)
    
    def _apply_poison_effect(self, target, effect, container):
        """应用中毒效果的特殊逻辑"""
        existing_poison_effects = [e for e in container.effects if e.effect_id == "poison_01"]
        
        # 使用PoisonEffectLogic处理中毒效果的应用
        poison_logic = effect.logic
        if hasattr(poison_logic, 'apply_poison_effects'):
            added_count = poison_logic.apply_poison_effects(target, effect, existing_poison_effects, self.event_bus)
            
            # 创建并添加新的中毒状态
            for i in range(added_count):
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
                if new_poison_effect.logic:
                    new_poison_effect.logic.on_apply(target, new_poison_effect, self.event_bus)
        else:
            # 回退到默认逻辑
            self._apply_normal_effect(target, effect, container)
    
    
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
        
        # 显示应用消息
        if effect.stacking == "stack_intensity":
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                f"**状态效果**: {target.name} 获得了 {effect.name} 效果 x{effect.stack_count} 层"
            )))
        else:
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                f"**状态效果**: {target.name} 获得了 {effect.name} 效果"
            )))
    
    def on_dispel_effect(self, event: GameEvent):
        payload: DispelRequestPayload = event.payload
        container = payload.target.get_component(StatusEffectContainerComponent)
        if not container: return
        if payload.category_to_dispel == "all":
            effects_to_dispel = list(container.effects)  # 复制一份，防止遍历时修改
        else:
            effects_to_dispel = [e for e in container.effects if e.category == payload.category_to_dispel]
        
        # 收集要移除的效果
        removed_effects = []
        for effect in effects_to_dispel[:payload.count]:
            effect.logic.on_remove(payload.target, effect, self.event_bus)
            container.effects.remove(effect)
            removed_effects.append(effect)
        
        # 整合播报消息
        if removed_effects:
            if len(removed_effects) == 1:
                message = f"**状态效果**: {payload.target.name} 的 {removed_effects[0].name} 效果已移除"
            else:
                effect_names = [effect.name for effect in removed_effects]
                message = f"**状态效果**: {payload.target.name} 的 {', '.join(effect_names)} 效果已移除"
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(message)))
    
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
            if effect and effect.duration is not None:
                effect.duration += payload.change
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", f"[{payload.target.name}] 状态效果 {payload.effect_id} 的持续时间更新为 {effect.duration} 回合")))

    def on_round_start(self, event: GameEvent):
        """回合开始时，处理所有实体的状态效果"""
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", "---状态效果结算阶段---")))
        
        # 先进行状态效果结算
        for entity in self.world.entities:
            if entity.has_component(DeadComponent):
                continue

            container = entity.get_component(StatusEffectContainerComponent)
            if not container: continue

            # 特殊处理中毒效果（所有版本）
            poison_effects = [e for e in container.effects if e.effect_id.startswith("poison_")]
            if poison_effects:
                self._tick_poison_effects(entity, poison_effects, container)

            # 处理其他效果
            other_effects = [e for e in container.effects if not e.effect_id.startswith("poison_")]
            self._tick_normal_effects(entity, other_effects, container)
        
        # 状态效果结算完成后，触发UI刷新事件
        self.event_bus.dispatch(GameEvent(EventName.STATUS_EFFECTS_RESOLVED, StatusEffectsResolvedPayload()))
    
    def _tick_poison_effects(self, entity, poison_effects, container):
        """结算中毒效果"""
        if not poison_effects:
            return
            
        # 使用PoisonEffectLogic处理中毒效果的结算
        poison_logic = poison_effects[0].logic
        if hasattr(poison_logic, 'tick_poison_effects'):
            expired_poison_effects = poison_logic.tick_poison_effects(entity, poison_effects, self.event_bus)
            
            # 移除层数归0的中毒效果
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
        else:
            # 回退到默认逻辑
            for effect in poison_effects:
                effect.logic.on_tick(entity, effect, self.event_bus)
    
    def _tick_normal_effects(self, entity, effects, container):
        """结算普通效果"""
        for effect in list(effects):
            effect.logic.on_tick(entity, effect, self.event_bus)
            # 只对有持续时间的效果进行倒计时
            if effect.duration is not None:
                effect.duration -= 1

        # 移除已过期的状态效果
        expired_effects = [e for e in effects if e.duration is not None and e.duration <= 0]
        for expired_effect in expired_effects:
            expired_effect.logic.on_remove(entity, expired_effect, self.event_bus)
            container.effects.remove(expired_effect)
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[STATUS]", f"[{entity.name}] 状态效果 {expired_effect.name} 效果已过期")))
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果**: {entity.name} 的 {expired_effect.name} 效果已结束")))
    
    def on_amplify_poison(self, event: GameEvent):
        payload: AmplifyPoisonRequestPayload = event.payload
        container = payload.target.get_component(StatusEffectContainerComponent)
        if not container: return
        
        poison_effects = [e for e in container.effects if e.effect_id.startswith("poison_")]
        if not poison_effects: return
        
        # 所有层增加
        for poison_effect in poison_effects:
            poison_effect.logic.handle_stacking(payload.target, poison_effect, payload.amplify_amount, self.event_bus)
        added_stacks = len(poison_effects) * payload.amplify_amount
        total_stack_count = 0
        for poison_effect in poison_effects:
            total_stack_count += poison_effect.stack_count

        # min_stack_effect = min(poison_effects, key=lambda e: e.stack_count)
        # old_stack_count = min_stack_effect.stack_count
        # min_stack_effect.stack_count = min(min_stack_effect.stack_count + payload.amplify_amount, min_stack_effect.max_stacks)
        # added_stacks = min_stack_effect.stack_count - old_stack_count
        
        self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
            f"**中毒增强**: {payload.target.name} 的中毒效果增强了 {added_stacks} 层，现在总共 {total_stack_count} 层"
        )))
    
    def on_detonate_poison(self, event: GameEvent):
        payload: DetonatePoisonRequestPayload = event.payload
        container = payload.target.get_component(StatusEffectContainerComponent)
        if not container: return
        
        poison_effects = [e for e in container.effects if e.effect_id.startswith("poison_")]
        if not poison_effects: return
        
        # 计算总伤害：每个中毒状态造成基础伤害 × 层数
        total_damage = 0
        for poison_effect in poison_effects:
            damage_per_round = poison_effect.context.get("damage_per_round", 0)
            total_damage += damage_per_round * poison_effect.stack_count
        
        if total_damage > 0:
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                f"**中毒引爆**: {payload.target.name} 因[{len(poison_effects)}个中毒状态] 受到了 {total_damage:.1f} 点伤害"
            )))
            self.event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                caster=payload.caster or payload.target,
                target=payload.target,
                source_spell_id="poison_detonate",
                source_spell_name="中毒引爆",
                base_damage=total_damage,
                damage_type="poison",
                is_reflection=False,
                can_be_reflected=False
            )))
        
        # 移除所有中毒效果
        for poison_effect in poison_effects:
            poison_effect.logic.on_remove(payload.target, poison_effect, self.event_bus)
            container.effects.remove(poison_effect)
        
        self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
            f"**状态效果**: {payload.target.name} 的所有中毒效果已被引爆并移除"
        )))
    
    def on_reduce_debuffs(self, event: GameEvent):
        """减少所有负面状态的层数或持续时间"""
        payload: ReduceDebuffsRequestPayload = event.payload
        container = payload.target.get_component(StatusEffectContainerComponent)
        if not container: return
        
        # 获取所有负面状态效果
        debuff_effects = [e for e in container.effects if e.category in ["physical_debuff", "magic_debuff", "elemental_debuff"]]
        if not debuff_effects: return
        
        reduced_effects = []
        removed_effects = []
        
        for effect in debuff_effects:
            effect_reduced = False
            
            # 减少层数
            if payload.reduce_stack_count > 0 and hasattr(effect, 'stack_count') and effect.stack_count > 0:
                old_stack_count = effect.stack_count
                effect.stack_count = max(0, effect.stack_count - payload.reduce_stack_count)
                if effect.stack_count == 0:
                    # 层数归0，移除效果
                    effect.logic.on_remove(payload.target, effect, self.event_bus)
                    container.effects.remove(effect)
                    removed_effects.append(effect)
                else:
                    effect_reduced = True
                    reduced_effects.append((effect, f"层数从{old_stack_count}减少到{effect.stack_count}"))
            
            # 减少持续时间
            if payload.reduce_duration_count > 0 and effect.duration is not None:
                old_duration = effect.duration
                effect.duration = max(0, effect.duration - payload.reduce_duration_count)
                if effect.duration == 0:
                    # 持续时间归0，移除效果
                    if effect not in removed_effects:  # 避免重复移除
                        effect.logic.on_remove(payload.target, effect, self.event_bus)
                        container.effects.remove(effect)
                        removed_effects.append(effect)
                else:
                    effect_reduced = True
                    if effect not in [e for e, _ in reduced_effects]:
                        reduced_effects.append((effect, f"持续时间从{old_duration}减少到{effect.duration}"))
        
        # 播报结果
        if removed_effects or reduced_effects:
            messages = []
            
            if removed_effects:
                removed_names = [effect.name for effect in removed_effects]
                messages.append(f"移除了 {', '.join(removed_names)}")
            
            if reduced_effects:
                reduced_names = [f"{effect.name}({desc})" for effect, desc in reduced_effects]
                messages.append(f"减少了 {', '.join(reduced_names)}")
            
            message = f"**净化3**: {payload.target.name} 的负面状态被净化 - " + "，".join(messages)
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(message)))