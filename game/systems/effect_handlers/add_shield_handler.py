from typing import Dict, Any
from .base_handler import EffectHandler
from ...core.entity import Entity
from ...core.components import ShieldComponent, DeadComponent
from ...core.payloads import EffectResolutionPayload, GainShieldPayload
from ...core.event_bus import GameEvent
from ...core.enums import EventName

class AddShieldHandler(EffectHandler):
    """处理添加护盾效果"""

    def apply(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        if target.has_component(DeadComponent):
            return

        # 获取护盾数值
        shield_amount = effect.get('amount', 0)
        
        # 获取当前护盾值用于记录
        shield_comp = target.get_component(ShieldComponent)
        shield_before = shield_comp.shield_value if shield_comp else 0
        
        # 使用事件系统来添加护盾，而不是直接操作组件
        shield_request = GainShieldPayload(
            target=target,
            source=f"{caster.name}的护盾法术",
            amount=shield_amount
        )
        self.event_bus.dispatch(GameEvent(EventName.GAIN_SHIELD_REQUEST, shield_request))
        
        # 记录护盾变化（CombatResolutionSystem会处理实际的护盾添加）
        payload.shield_changed = True
        payload.shield_before = shield_before
        payload.shield_change_amount = shield_amount
        
        # 获取更新后的护盾值
        updated_shield_comp = target.get_component(ShieldComponent)
        current_shield = updated_shield_comp.shield_value if updated_shield_comp else 0
        payload.add_resource_change('shield', shield_amount, current_shield)