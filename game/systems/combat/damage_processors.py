import random
from ...core.pipeline import Processor, EffectExecutionContext
from ...core.event_bus import EventBus, GameEvent
from ...core.enums import EventName
from ...core.payloads import LogRequestPayload, HealRequestPayload, DamageRequestPayload, ApplyStatusEffectRequestPayload
from ...core.components import ShieldComponent, ResistanceComponent, ThornsComponent, AttackTriggerPassiveComponent

class BaseProcessor(Processor[EffectExecutionContext]):
    """处理器的基类，方便统一注入EventBus"""
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        if context.is_cancelled:
            return context
        return self._process(context)

    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        # 子类需要实现这个方法
        raise NotImplementedError

# --- 伤害计算阶段的处理器 ---

class CritHandler(BaseProcessor):
    """处理暴击"""
    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        can_crit = context.metadata.get("can_crit", False)
        crit_chance = context.metadata.get("crit_chance", 0.0)
        crit_damage_multiplier = context.metadata.get("crit_damage_multiplier", 1.5)
        random_roll = random.random()
        compare_tip = f"(判定: random_roll={random_roll:.3f} {'<' if random_roll < crit_chance else '≥'} crit_chance={crit_chance:.3f}，{'会暴击' if random_roll < crit_chance else '不会暴击'})"
        log_prefix = f"[暴击判定] can_crit={can_crit}, crit_chance={crit_chance:.3f}, crit_damage_multiplier={crit_damage_multiplier:.2f}, random_roll={random_roll:.3f} {compare_tip}"

        if not can_crit:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[COMBAT]", f"{log_prefix} → 未暴击 - 原因：该技能不支持暴击"
            )))
            return context

        if crit_chance <= 0.0:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[COMBAT]", f"{log_prefix} → 未暴击 - 原因：暴击率为 0%"
            )))
            return context

        if random_roll < crit_chance:
            original_damage = context.current_value
            context.current_value *= crit_damage_multiplier
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[COMBAT]", f"{log_prefix} → 💥 暴击成功！伤害从 {original_damage:.1f} 提升至 {context.current_value:.1f} (x{crit_damage_multiplier:.2f})"
            )))
        else:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[COMBAT]", f"{log_prefix} → 未暴击 - 原因：暴击判定失败 (暴击率: {crit_chance*100:.1f}%)"
            )))
        return context

class ShieldHandler(BaseProcessor):
    """处理护盾/防御值减免"""
    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        target = context.target
        if shield_comp := target.get_component(ShieldComponent):
            if shield_comp.shield_value > 0:
                blocked = min(context.current_value, shield_comp.shield_value)
                context.current_value -= blocked
                # 实际减少护盾值
                shield_comp.shield_value -= blocked
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[COMBAT]", f"🛡️ {target.name} 的护盾抵消了 {blocked:.1f} 点伤害，剩余护盾: {shield_comp.shield_value:.1f}"
                )))
        return context

class ResistanceHandler(BaseProcessor):
    """处理元素抗性减免"""
    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        target = context.target
        damage_type = context.metadata.get("damage_type")
        if not damage_type:
            return context

        # 获取所有抗性组件
        resistance_components = target.get_components(ResistanceComponent)
        if not resistance_components:
            return context
        
        # 计算总抗性值
        total_resistance = 1.0
        applied_resistances = []
        
        for resistance_comp in resistance_components:
            if resistance_comp.element == damage_type and resistance_comp.percentage < 1:
                # 抗性值 = 1 - 减伤百分比
                resistance_value = 1 - resistance_comp.percentage
                total_resistance *= resistance_value
                applied_resistances.append(f"{resistance_comp.element}({resistance_comp.percentage*100:.0f}%)")
        
        # 如果有抗性生效且有实际减伤
        if total_resistance < 1.0:
            original_damage = context.current_value
            context.current_value *= total_resistance
            damage_reduced = original_damage - context.current_value
            
            # 只有当实际减伤大于0时才播报
            if damage_reduced > 0.1:  # 使用0.1作为阈值，避免浮点数精度问题
                resistance_info = ", ".join(applied_resistances)
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[COMBAT]", 
                    f"{target.name} 的 {resistance_info}抗性抵抗了 {damage_reduced:.1f} 点伤害，伤害从 {original_damage:.1f} 降低到 {context.current_value:.1f}"
                )))
        
        return context

# --- 造成伤害后阶段的处理器 ---

class LifestealHandler(BaseProcessor):
    """处理吸血"""
    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        lifesteal_ratio = context.metadata.get("lifesteal_ratio", 0.0)
        if lifesteal_ratio > 0 and context.current_value > 0:
            heal_amount = context.current_value * lifesteal_ratio
            self.event_bus.dispatch(GameEvent(EventName.HEAL_REQUEST, HealRequestPayload(
                caster=context.source,
                target=context.source,
                source_spell_id="lifesteal",
                source_spell_name="吸血",
                base_heal=heal_amount,
                heal_type="blood",
                can_be_modified=False # 吸血通常不应被重伤等效果影响
            )))
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[COMBAT]", f"🩸 {context.source.name} 通过吸血恢复了 {heal_amount:.1f} 点生命"
            )))
        return context

class ThornsHandler(BaseProcessor):
    """处理反伤"""
    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        if context.current_value <= 0 or context.metadata.get("is_reflection", False):
            return context
        if not context.metadata.get("can_be_reflected", True):
            return context
        # 被动伤害不被反伤
        if context.metadata.get("is_passive_damage", False):
            return context
        
        if thorns_comp := context.target.get_component(ThornsComponent):
            if thorns_comp.thorns_percentage > 0:
                reflection_damage = context.current_value * thorns_comp.thorns_percentage
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[PASSIVE]", f"🌵 {context.target.name} 的反伤对 {context.source.name} 造成了 {reflection_damage:.1f} 点伤害"
                )))
                self.event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                    caster=context.target,
                    target=context.source,
                    source_spell_id="thorns",
                    source_spell_name="反伤",
                    base_damage=reflection_damage,
                    original_base_damage=reflection_damage,
                    damage_type="pure",
                    is_reflection=True, # 标记为反射伤害，防止无限反弹
                    can_crit=False      # 反伤通常不能暴击
                )))
        return context

class AttackTriggerPassiveHandler(BaseProcessor):
    """处理攻击触发的被动效果"""
    def __init__(self, event_bus: EventBus, status_effect_factory=None):
        super().__init__(event_bus)
        self.status_effect_factory = status_effect_factory
    
    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        # 如果是被动伤害，不触发攻击被动效果，防止无限循环
        if context.metadata.get("is_passive_damage", False):
            return context
        
        # 检查攻击者是否有攻击触发被动组件
        attack_trigger_passives = context.source.get_components(AttackTriggerPassiveComponent)
        if not attack_trigger_passives:
            return context
        
        # 根据数据驱动的触发条件处理被动效果
        for passive_comp in attack_trigger_passives:
            # 检查触发概率
            if random.random() > passive_comp.trigger_chance:
                continue
            
            # 根据触发条件判断是否应该触发
            if not self._should_trigger_passive(context, passive_comp):
                continue
            
            # 根据效果类型执行不同的逻辑
            if passive_comp.effect_type == "damage":
                self._handle_damage_effect(context, passive_comp)
            elif passive_comp.effect_type == "heal":
                self._handle_heal_effect(context, passive_comp)
            elif passive_comp.effect_type == "status_effect":
                self._handle_status_effect(context, passive_comp)
        
        return context
    
    def _handle_damage_effect(self, context: EffectExecutionContext, passive_comp: AttackTriggerPassiveComponent):
        """处理伤害效果"""
        # 确定目标
        target = self._get_effect_target(context, passive_comp.effect_target)
        if not target:
            return
        
        # 计算伤害数值
        if passive_comp.use_damage_ratio:
            # 使用伤害比例模式：基于实际造成伤害值计算
            damage_amount = context.current_value * passive_comp.damage_ratio
        else:
            # 使用固定数值模式：即使攻击被护盾完全抵消也能造成伤害
            damage_amount = passive_comp.effect_value
        
        if damage_amount > 0:
            # 显示不同的日志信息
            if passive_comp.use_damage_ratio:
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[PASSIVE]", f"⚡ {context.source.name} 的 {passive_comp.effect_name} 对 {target.name} 造成了额外 {damage_amount:.1f} 点伤害 (基于实际伤害的 {passive_comp.damage_ratio*100:.0f}%)"
                )))
            else:
                # 固定数值模式，即使攻击被护盾抵消也能触发
                if context.current_value <= 0:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[PASSIVE]", f"⚡ {context.source.name} 的 {passive_comp.effect_name} 附加伤害, 对 {target.name} 造成了 {damage_amount:.1f} 点伤害"
                    )))
                else:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[PASSIVE]", f"⚡ {context.source.name} 的 {passive_comp.effect_name} 对 {target.name} 造成了 {damage_amount:.1f} 点伤害"
                    )))
            
            self.event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                caster=context.source,
                target=target,
                source_spell_id=passive_comp.passive_id,
                source_spell_name=passive_comp.effect_name,
                base_damage=damage_amount,
                damage_type=passive_comp.damage_type,
                can_be_reflected=False,  # 被动伤害通常不被反伤
                is_reflection=False,
                is_passive_damage=True  # 标记为被动伤害，防止无限循环
            )))
    
    def _handle_heal_effect(self, context: EffectExecutionContext, passive_comp: AttackTriggerPassiveComponent):
        """处理治疗效果"""
        # 确定目标
        target = self._get_effect_target(context, passive_comp.effect_target)
        if not target:
            return
        
        # 计算治疗数值
        if passive_comp.use_damage_ratio:
            # 使用伤害比例模式：基于实际造成伤害值计算
            heal_amount = context.current_value * passive_comp.damage_ratio
        else:
            # 使用固定数值模式：即使攻击被护盾完全抵消也能治疗
            heal_amount = passive_comp.effect_value
        
        if heal_amount > 0:
            # 显示不同的日志信息
            if passive_comp.use_damage_ratio:
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[PASSIVE]", f"💚 {context.source.name} 的 {passive_comp.effect_name} 为 {target.name} 恢复了 {heal_amount:.1f} 点生命 (基于实际伤害的 {passive_comp.damage_ratio*100:.0f}%)"
                )))
            else:
                # 固定数值模式，即使攻击被护盾抵消也能触发
                if context.current_value <= 0:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[PASSIVE]", f"💚 {context.source.name} 的 {passive_comp.effect_name} 附加治疗, 为 {target.name} 恢复了 {heal_amount:.1f} 点生命"
                    )))
                else:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[PASSIVE]", f"💚 {context.source.name} 的 {passive_comp.effect_name} 为 {target.name} 恢复了 {heal_amount:.1f} 点生命"
                    )))
            
            self.event_bus.dispatch(GameEvent(EventName.HEAL_REQUEST, HealRequestPayload(
                caster=context.source,
                target=target,
                source_spell_id=passive_comp.passive_id,
                source_spell_name=passive_comp.effect_name,
                base_heal=heal_amount,
                heal_type="passive",
                can_be_modified=True
            )))
    
    def _handle_status_effect(self, context: EffectExecutionContext, passive_comp: AttackTriggerPassiveComponent):
        """处理状态效果"""
        if not self.status_effect_factory or not passive_comp.status_effect_id:
            return
        
        # 确定目标
        target = self._get_effect_target(context, passive_comp.effect_target)
        if not target:
            return
        
        # 创建状态效果
        effect = self.status_effect_factory.create_effect(passive_comp.status_effect_id)
        if effect:
            effect.caster = context.source
            # 显示不同的日志信息
            if context.current_value <= 0:
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[PASSIVE]", f"✨ {context.source.name} 的 {passive_comp.effect_name} 穿透护盾为 {target.name} 施加了 {effect.name} 效果"
                )))
            else:
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[PASSIVE]", f"✨ {context.source.name} 的 {passive_comp.effect_name} 为 {target.name} 施加了 {effect.name} 效果"
                )))
            self.event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, ApplyStatusEffectRequestPayload(
                target=target,
                effect=effect
            )))
    
    def _should_trigger_passive(self, context: EffectExecutionContext, passive_comp: AttackTriggerPassiveComponent) -> bool:
        """根据触发条件判断是否应该触发被动效果"""
        trigger_condition = passive_comp.trigger_condition
        
        if trigger_condition == "always":
            # 总是触发（无论是否造成伤害）
            return True
        elif trigger_condition == "on_damage":
            # 只有在造成伤害时才触发
            # 注意：这里应该检查初始伤害值，而不是经过护盾减免后的值
            return context.initial_value > 0
        elif trigger_condition == "on_hit":
            # 只要攻击命中就触发（即使被护盾抵消）
            return True
        else:
            # 默认总是触发
            return True
    
    def _get_effect_target(self, context: EffectExecutionContext, target_type: str):
        """根据目标类型获取实际目标"""
        if target_type == "self":
            return context.source
        elif target_type == "target":
            return context.target
        elif target_type == "random":
            # 随机选择目标（这里简化为攻击者自己）
            return context.source
        else:
            return context.source  # 默认返回攻击者