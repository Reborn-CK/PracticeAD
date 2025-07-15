from typing import Dict, Any
from .base_handler import EffectHandler
from ...core.entity import Entity
from ...core.components import DeadComponent
from ...core.payloads import EffectResolutionPayload, AmplifyPoisonRequestPayload
from ...core.enums import EventName
from ...core.event_bus import GameEvent

class AmplifyPoisonHandler(EffectHandler):
    """处理放大中毒效果"""

    def apply(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        if target.has_component(DeadComponent):
            return

        # 获取放大数量
        amplify_amount = effect.get('amplify_amount', effect.get('params', {}).get('amplify_amount', 2))
        
        # 获取法术数据
        spell_data = self.data_manager.get_spell_data(payload.source_spell)
        
        # 创建放大中毒请求负载
        amplify_payload = AmplifyPoisonRequestPayload(
            target=target,
            amplify_amount=amplify_amount,
            caster=caster,
            source_spell_id=payload.source_spell,
            source_spell_name=spell_data.get('name', payload.source_spell) if spell_data else payload.source_spell
        )
        
        # 派发放大中毒请求事件，让状态效果系统处理
        self.event_bus.dispatch(GameEvent(EventName.AMPLIFY_POISON_REQUEST, amplify_payload)) 