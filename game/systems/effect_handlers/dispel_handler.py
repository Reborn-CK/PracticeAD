from typing import Dict, Any
from .base_handler import EffectHandler
from ...core.entity import Entity
from ...core.components import StatusEffectContainerComponent, DeadComponent
from ...core.payloads import EffectResolutionPayload, DispelRequestPayload
from ...core.enums import EventName
from ...core.event_bus import GameEvent

class DispelHandler(EffectHandler):
    """处理驱散效果"""

    def apply(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        if target.has_component(DeadComponent):
            return

        # 获取驱散参数
        num_to_dispel = effect.get('count', effect.get('params', {}).get('count', 1))
        dispel_type = effect.get('category', effect.get('params', {}).get('dispel_type', 'debuff'))
        
        # 创建驱散请求负载，与旧版本保持一致
        dispel_payload = DispelRequestPayload(
            target=target,
            category_to_dispel=dispel_type,
            count=num_to_dispel
        )
        
        # 派发驱散请求事件，让状态效果系统处理
        self.event_bus.dispatch(GameEvent(EventName.DISPEL_REQUEST, dispel_payload))