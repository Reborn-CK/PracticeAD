from typing import Dict, Any
from .base_handler import EffectHandler
from ...core.entity import Entity
from ...core.components import HealthComponent, DeadComponent
from ...core.payloads import EffectResolutionPayload, HealRequestPayload
from ...core.enums import EventName
from ...core.event_bus import GameEvent

class HealHandler(EffectHandler):
    """处理治疗效果"""

    def apply(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        if target.has_component(DeadComponent):
            return

        # 获取基础治疗值
        base_heal = effect.get('amount', effect.get('params', {}).get('base_heal', 0))
        heal_type = effect.get('heal_type', 'magical')
        
        # 获取法术数据
        spell_data = self.data_manager.get_spell_data(payload.source_spell)
        
        # 创建治疗请求负载，与旧版本保持一致
        heal_payload = HealRequestPayload(
            caster=caster,
            target=target,
            source_spell_id=payload.source_spell,
            source_spell_name=spell_data.get('name', payload.source_spell) if spell_data else payload.source_spell,
            base_heal=base_heal,
            heal_type=heal_type,
            overheal_to_shield_config=effect.get('overheal_to_shield')
        )
        
        # 派发治疗请求事件，让战斗解析系统处理
        self.event_bus.dispatch(GameEvent(EventName.HEAL_REQUEST, heal_payload))