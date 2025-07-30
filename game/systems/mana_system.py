from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import ManaChangeRequestPayload, LogRequestPayload
from ..core.components import ManaComponent

class ManaSystem:
    """法力系统，管理法力值的消耗和恢复"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.event_bus.subscribe(EventName.MANA_COST_REQUEST, self._on_mana_cost_request)
        self.event_bus.subscribe(EventName.MANA_CHANGE_REQUEST, self._on_mana_change_request)
    
    def _on_mana_cost_request(self, event):
        """处理法力消耗请求"""
        payload = event.payload
        entity = payload.entity
        cost = payload.cost
        
        mana_comp = entity.get_component(ManaComponent)
        if mana_comp:
            if mana_comp.mana >= cost:
                mana_comp.mana -= cost
                payload.is_affordable = True
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[MANA]", f"💙 {entity.name} 消耗了 {cost} 点法力值 (剩余: {mana_comp.mana:.0f})"
                )))
            else:
                payload.is_affordable = False
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[MANA]", f"❌ {entity.name} 法力值不足！需要 {cost} 点，当前只有 {mana_comp.mana:.0f} 点"
                )))
    
    def _on_mana_change_request(self, event):
        """处理法力值变化请求"""
        payload = event.payload
        target = payload.target
        amount = payload.amount
        change_type = payload.change_type
        
        mana_comp = target.get_component(ManaComponent)
        if mana_comp:
            old_mana = mana_comp.mana
            if change_type == "restore":
                # 恢复法力值
                mana_comp.mana = min(mana_comp.mana + amount, mana_comp.max_mana)
                actual_restore = mana_comp.mana - old_mana
                if actual_restore > 0:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[MANA]", f"💙 {target.name} 恢复了 {actual_restore:.0f} 点法力值 (当前: {mana_comp.mana:.0f}/{mana_comp.max_mana:.0f})"
                    )))
            elif change_type == "consume":
                # 消耗法力值
                mana_comp.mana = max(mana_comp.mana - amount, 0)
                actual_consume = old_mana - mana_comp.mana
                if actual_consume > 0:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[MANA]", f"💙 {target.name} 消耗了 {actual_consume:.0f} 点法力值 (剩余: {mana_comp.mana:.0f})"
                    )))