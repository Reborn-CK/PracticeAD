from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# 导入核心定义
from ...core.entity import Entity
from ...core.event_bus import EventBus, GameEvent
from ...core.enums import EventName
from ...core.payloads import LogRequestPayload

# 导入相关组件
from ...core.components import DefenseComponent, ResistanceComponent, GrievousWoundsComponent

@dataclass
class DamageResolutionContext:
    """伤害计算的上下文，在流水线中传递"""
    caster: Entity
    target: Entity
    source_spell_id: str
    damage_type: str
    current_damage: float
    log: list = field(default_factory=list)

class DamageModifier(ABC):
    """伤害修改器的抽象基类"""
    @abstractmethod
    def process(self, context: 'DamageResolutionContext', event_bus: EventBus):
        pass

class DefenseHandler(DamageModifier):
    """处理护盾吸收"""
    def process(self, context: 'DamageResolutionContext', event_bus: EventBus):
        if defense_comp := context.target.get_component(DefenseComponent):
            if defense_comp.defense_value > 0:
                blocked = min(context.current_damage, defense_comp.defense_value)
                event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[COMBAT]", f"护盾抵消了 {blocked:.1f} 点伤害")))
                context.current_damage -= blocked
                defense_comp.defense_value -= blocked

class ResistanceHandler(DamageModifier):
    """处理属性抗性"""
    def process(self, context: 'DamageResolutionContext', event_bus: EventBus):
        # 获取所有抗性组件
        resistance_components = context.target.get_components(ResistanceComponent)
        if not resistance_components:
            return
        
        # 计算总抗性值
        total_resistance = 1.0
        applied_resistances = []
        
        for resistance_comp in resistance_components:
            if resistance_comp.element == context.damage_type and resistance_comp.percentage < 1:
                # 抗性值 = 1 - 减伤百分比
                resistance_value = 1 - resistance_comp.percentage
                total_resistance *= resistance_value
                applied_resistances.append(f"{resistance_comp.element}({resistance_comp.percentage*100:.0f}%)")
        
        # 如果有抗性生效且有实际减伤
        if total_resistance < 1.0:
            original_damage = context.current_damage
            context.current_damage *= total_resistance
            damage_reduced = original_damage - context.current_damage
            
            # 只有当实际减伤大于0时才播报
            if damage_reduced > 0.1:  # 使用0.1作为阈值，避免浮点数精度问题
                resistance_info = ", ".join(applied_resistances)
                event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[COMBAT]", 
                    f"{context.target.name} 的 {resistance_info}抗性抵抗了 {damage_reduced:.1f} 点伤害，伤害从 {original_damage:.1f} 降低到 {context.current_damage:.1f}"
                )))

@dataclass
class HealResolutionContext:
    """治疗计算的上下文"""
    caster: Entity
    target: Entity
    source_spell_id: str
    source_spell_name: str
    current_heal: float
    log: list = field(default_factory=list)

class HealModifier(ABC):
    """治疗修改器的抽象基类"""
    @abstractmethod
    def process(self, context: HealResolutionContext, event_bus: EventBus):
        pass

class GrievousWoundsHandler(HealModifier):
    """处理重伤效果（治疗减益）"""
    def process(self, context: HealResolutionContext, event_bus: EventBus):
        if grievous_comp := context.target.get_component(GrievousWoundsComponent):
            reduction = grievous_comp.reduction_percentage
            context.current_heal *= (1 - reduction)
            event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "COMBAT", f"目标身上的重伤效果使治疗降低了 {reduction*100}%")))