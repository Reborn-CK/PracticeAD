from typing import Dict, Any
from .base_handler import EffectHandler
from ...core.entity import Entity
from ...core.payloads import EffectResolutionPayload

class MultiEffectHandler(EffectHandler):
    """处理复合效果"""

    def __init__(self, event_bus, data_manager, world):
        super().__init__(event_bus, data_manager, world)
        # 关键：这个处理器需要一个对 SpellEffectSystem 的引用来递归调用
        self.spell_effect_system = None 

    def apply(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        if not self.spell_effect_system:
            # 这是一个小小的设计妥协，为了打破循环依赖
            # 我们将在主系统初始化时注入这个引用
            raise RuntimeError("SpellEffectSystem reference not set in MultiEffectHandler")

        sub_effects = effect['params']['effects']
        for sub_effect in sub_effects:
            # 递归调用 SpellEffectSystem 的核心应用逻辑
            self.spell_effect_system._apply_single_effect(caster, target, sub_effect, payload)