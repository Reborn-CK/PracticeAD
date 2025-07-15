from typing import Dict, Any
from .base_handler import EffectHandler
from ...core.entity import Entity
from ...core.components import StatusEffectContainerComponent, DeadComponent
from ...core.payloads import EffectResolutionPayload, ApplyStatusEffectRequestPayload
from ...core.enums import EventName
from ...core.event_bus import GameEvent
from game.status_effects.status_effect_factory import StatusEffectFactory

class ApplyStatusEffectHandler(EffectHandler):
    """处理施加状态效果"""

    def __init__(self, event_bus, data_manager, world):
        super().__init__(event_bus, data_manager, world)
        self.status_effect_factory = StatusEffectFactory(self.data_manager)

    def apply(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        if target.has_component(DeadComponent):
            return

        # 获取效果ID，支持旧版本和新版本的数据结构
        effect_id = effect.get('status_effect_id') or effect.get('params', {}).get('effect_id')
        if not effect_id:
            return
            
        # 创建状态效果
        new_effect = self.status_effect_factory.create_effect(effect_id, caster)
        
        if new_effect:
            # 创建状态效果请求负载，与旧版本保持一致
            status_effect_payload = ApplyStatusEffectRequestPayload(
                target=target,
                effect=new_effect
            )
            
            # 派发状态效果请求事件，让状态效果系统处理
            self.event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, status_effect_payload))
            
            # 记录新状态效果
            payload.new_status_effects.append(new_effect)