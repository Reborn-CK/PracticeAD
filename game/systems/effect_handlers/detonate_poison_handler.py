from typing import Dict, Any
from .base_handler import EffectHandler
from ...core.entity import Entity
from ...core.components import DeadComponent
from ...core.payloads import EffectResolutionPayload, DetonatePoisonRequestPayload
from ...core.enums import EventName
from ...core.event_bus import GameEvent

class DetonatePoisonHandler(EffectHandler):
    """处理引爆中毒效果"""

    def apply(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        if target.has_component(DeadComponent):
            return

        # 获取伤害倍数
        damage_multiplier = effect.get('damage_multiplier', effect.get('params', {}).get('damage_multiplier', 1.0))
        
        # 获取法术数据
        spell_data = self.data_manager.get_spell_data(payload.source_spell)
        
        # 创建引爆中毒请求负载
        detonate_payload = DetonatePoisonRequestPayload(
            target=target,
            damage_multiplier=damage_multiplier,
            caster=caster,
            source_spell_id=payload.source_spell,
            source_spell_name=spell_data.get('name', payload.source_spell) if spell_data else payload.source_spell
        )
        
        # 派发引爆中毒请求事件，让状态效果系统处理
        self.event_bus.dispatch(GameEvent(EventName.DETONATE_POISON_REQUEST, detonate_payload)) 