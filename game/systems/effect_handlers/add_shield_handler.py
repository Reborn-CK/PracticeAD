from typing import Dict, Any
from .base_handler import EffectHandler
from ...core.entity import Entity
from ...core.components import ShieldComponent, DeadComponent
from ...core.payloads import EffectResolutionPayload

class AddShieldHandler(EffectHandler):
    """处理添加护盾效果"""

    def apply(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        if target.has_component(DeadComponent):
            return

        shield_comp = target.get_component(ShieldComponent)
        if not shield_comp:
            shield_comp = target.add_component(ShieldComponent(0))

        # 获取护盾数值
        shield_amount = effect.get('shield_amount', effect.get('params', {}).get('shield_amount', 0))
        
        shield_before = shield_comp.shield_value
        shield_comp.add_shield(shield_amount)
        
        # 记录护盾变化
        payload.shield_changed = True
        payload.shield_before = shield_before
        payload.shield_change_amount = shield_amount
        payload.add_resource_change('shield', shield_amount, shield_comp.shield_value)