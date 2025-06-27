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
    def process(self, context: DamageResolutionContext, event_bus: EventBus):
        pass

class DefenseHandler(DamageModifier):
    """处理护盾吸收"""
    def process(self, context: DamageResolutionContext, event_bus: EventBus):
        if defense_comp := context.target.get_component(DefenseComponent):
            if defense_comp.defense_value > 0:
                blocked = min(context.current_damage, defense_comp.defense_value)
                event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "COMBAT", f"护盾抵消了 {blocked:.1f} 点伤害")))
                context.current_damage -= blocked
                defense_comp.defense_value -= blocked

class ResistanceHandler(DamageModifier):
    """处理属性抗性"""
    def process(self, context: DamageResolutionContext, event_bus: EventBus):
        if resistance_comp := context.target.get_component(ResistanceComponent):
            # 注意：抗性通常是百分比减免，这里假设1.0为无抗性，0.5为50%减伤
            resistance_multiplier = resistance_comp.resistances.get(context.damage_type, 1.0)
            if resistance_multiplier < 1.0:
                reduced_amount = context.current_damage * (1 - resistance_multiplier)
                event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "COMBAT", f"{context.damage_type.capitalize()}抗性抵抗了 {reduced_amount:.1f} 点伤害")))
                context.current_damage *= resistance_multiplier

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