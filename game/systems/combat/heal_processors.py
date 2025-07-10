from ...core.pipeline import Processor, EffectExecutionContext
from ...core.event_bus import EventBus, GameEvent
from ...core.enums import EventName
from ...core.payloads import LogRequestPayload
from ...core.components import GrievousWoundsComponent, OverhealToShieldComponent, DefenseComponent
from ...core.components import StatusEffectContainerComponent

class BaseProcessor(Processor[EffectExecutionContext]):
    """处理器的基类，方便统一注入EventBus"""
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        if context.is_cancelled:
            return context
        return self._process(context)

    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        raise NotImplementedError

class GrievousWoundsHandler(BaseProcessor):
    """处理重伤效果 (减少治疗)"""
    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        target = context.target
        if grievous_comp := target.get_component(GrievousWoundsComponent):
            original_heal = context.current_value
            context.current_value *= (1 - grievous_comp.reduction)
            heal_reduced = original_heal - context.current_value
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[COMBAT]", 
                f"{target.name} 的重伤效果使治疗降低了 {grievous_comp.reduction*100:.0f}%，治疗从 {original_heal:.1f} 降低到 {context.current_value:.1f}，减少了 {heal_reduced:.1f} 点治疗"
            )))
        return context

class StatusEffectOverhealToShieldHandler(BaseProcessor):
    """处理来自状态效果的“溢出治疗转护盾”逻辑"""
    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        # 1. 检查是否还有剩余的溢出治疗
        if context.overheal_amount <= 0:
            return context
        # 然后检查状态效果带来的溢疗转换
        if container :=context.target.get_component(StatusEffectContainerComponent): # type: ignore
            if container:
                for effect in container.effects:
                    effect.logic.on_heal(context, effect, self.event_bus)
                # 注意：这里不设置 context.overheal_amount = 0.0，让后续处理器也能处理
        
        return context

class SkillOverhealToShieldHandler(BaseProcessor):
    """处理来自技能本身的“溢出治疗转护盾”逻辑"""
    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        # 1. 检查是否有溢出治疗
        if context.overheal_amount <= 0:
            return context

        # 2. 检查上下文中是否有技能带来的配置信息
        config = context.metadata.get("overheal_to_shield_config")
        if not config:
            return context

        # 3. 计算要转换的护盾值
        ratio = config.get("conversion_ratio", 1.0)
        shield_to_add = context.overheal_amount * ratio
        
        if shield_to_add > 0:
            # 4. 为目标增加护盾
            if defense_comp := context.target.get_component(DefenseComponent):
                defense_comp.defense_value += shield_to_add
            else:
                context.target.add_component(DefenseComponent(defense_value=shield_to_add))
            
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[SKILL]", f"📜 技能 [{context.metadata.get('source_spell_name')}] 的效果将 {context.overheal_amount:.1f} 点溢出治疗转化为了 {shield_to_add:.1f} 点护盾！"
            )))

            # 5. 【关键】消耗掉溢出治疗，防止后续处理器重复转化
            context.overheal_amount = 0.0
            
        return context

class OverhealToShieldHandler(BaseProcessor):
    """处理溢出治疗转化为护盾的逻辑"""
    def _process(self, context: EffectExecutionContext) -> EffectExecutionContext:
        # 1. 检查是否有溢出治疗
        if context.overheal_amount <= 0:
            return context

        # 2. 检查目标是否有转护盾的被动组件
        passive_comp = context.target.get_component(OverhealToShieldComponent)
        if not passive_comp:
            return context

        # 3. 计算要转换的护盾值
        shield_to_add = context.overheal_amount * passive_comp.conversion_ratio

        if shield_to_add > 0:
            # 4. 为目标增加护盾 (DefenseComponent)
            if defense_comp := context.target.get_component(DefenseComponent):
                defense_comp.defense_value += shield_to_add
            else:
                # 如果目标没有DefenseComponent，可以动态添加一个
                context.target.add_component(DefenseComponent(defense_value=shield_to_add))
            
            # 5. 派发日志事件
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[PASSIVE]", f"✨ {context.target.name} 的 {context.overheal_amount:.1f} 点溢出治疗转化为了 {shield_to_add:.1f} 点护盾！"
            )))
            
            # 6. 【关键】消耗掉溢出治疗，防止后续处理器重复转化
            context.overheal_amount = 0.0
            
        return context