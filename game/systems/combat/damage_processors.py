import random
from ...core.pipeline import Processor, EffectExecutionContext
from ...core.event_bus import EventBus, GameEvent
from ...core.enums import EventName
from ...core.payloads import LogRequestPayload, HealRequestPayload, DamageRequestPayload
from ...core.components import DefenseComponent, ResistanceComponent, ThornsComponent

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
        if not context.metadata.get("can_crit", False):
            return context

        crit_chance = context.metadata.get("crit_chance", 0.0)
        if random.random() < crit_chance:
            crit_multiplier = context.metadata.get("crit_damage_multiplier", 1.5)
            original_damage = context.current_value
            context.current_value *= crit_multiplier
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[COMBAT]", f"💥 {context.source.name} 的攻击发生了暴击！伤害从 {original_damage:.1f} 提升至 {context.current_value:.1f} (x{crit_multiplier:.2f})！"
            )))
        return context

class DefenseHandler(BaseProcessor):
    """处理护盾/防御值减免"""
    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        target = context.target
        if defense_comp := target.get_component(DefenseComponent):
            if defense_comp.defense_value > 0:
                blocked = min(context.current_value, defense_comp.defense_value)
                context.current_value -= blocked
                # 实际减少护盾值
                defense_comp.defense_value -= blocked
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[COMBAT]", f"🛡️ {target.name} 的护盾抵消了 {blocked:.1f} 点伤害，剩余护盾: {defense_comp.defense_value:.1f}"
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