from typing import Dict, Any
from .base_handler import EffectHandler
from ...core.entity import Entity
from ...core.components import DeadComponent
from ...core.payloads import EffectResolutionPayload, ReduceDebuffsRequestPayload
from ...core.enums import EventName
from ...core.event_bus import GameEvent

class ReduceDebuffsHandler(EffectHandler):
    """处理减少减益效果"""

    def apply(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        if target.has_component(DeadComponent):
            return

        # 获取减少参数
        reduce_stack_count = effect.get('reduce_stack_count', effect.get('params', {}).get('reduce_stack_count', 0))
        reduce_duration_count = effect.get('reduce_duration_count', effect.get('params', {}).get('reduce_duration_count', 0))
        
        # 创建减少减益请求负载
        reduce_payload = ReduceDebuffsRequestPayload(
            target=target,
            reduce_stack_count=reduce_stack_count,
            reduce_duration_count=reduce_duration_count
        )
        
        # 派发减少减益请求事件，让状态效果系统处理
        self.event_bus.dispatch(GameEvent(EventName.REDUCE_DEBUFFS_REQUEST, reduce_payload)) 