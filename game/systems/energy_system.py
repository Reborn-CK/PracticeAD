from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import EnergyChangeRequestPayload, LogRequestPayload, EnergyCostRequestPayload
from ..core.components import EnergyComponent

class EnergySystem:
    """能量点系统，管理能量点的消耗和恢复"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.event_bus.subscribe(EventName.ENERGY_COST_REQUEST, self._on_energy_cost_request)
        self.event_bus.subscribe(EventName.ENERGY_CHANGE_REQUEST, self._on_energy_change_request)
    
    def _on_energy_cost_request(self, event):
        """处理能量点消耗请求"""
        payload = event.payload
        entity = payload.entity
        cost = payload.cost
        
        energy_comp = entity.get_component(EnergyComponent)
        if energy_comp:
            if energy_comp.energy >= cost:
                energy_comp.energy -= cost
                payload.is_affordable = True
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[ENERGY]", f"⚡ {entity.name} 消耗了 {cost} 点能量 (剩余: {energy_comp.energy:.0f})"
                )))
            else:
                payload.is_affordable = False
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[ENERGY]", f"❌ {entity.name} 能量不足！需要 {cost} 点，当前只有 {energy_comp.energy:.0f} 点"
                )))
    
    def _on_energy_change_request(self, event):
        """处理能量点变化请求"""
        payload = event.payload
        target = payload.target
        amount = payload.amount
        change_type = payload.change_type
        
        energy_comp = target.get_component(EnergyComponent)
        if energy_comp:
            old_energy = energy_comp.energy
            if change_type == "restore":
                # 恢复能量点
                energy_comp.energy = min(energy_comp.energy + amount, energy_comp.max_energy)
                actual_restore = energy_comp.energy - old_energy
                if actual_restore > 0:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[ENERGY]", f"⚡ {target.name} 恢复了 {actual_restore:.0f} 点能量 (当前: {energy_comp.energy:.0f}/{energy_comp.max_energy:.0f})"
                    )))
            elif change_type == "consume":
                # 消耗能量点
                energy_comp.energy = max(energy_comp.energy - amount, 0)
                actual_consume = old_energy - energy_comp.energy
                if actual_consume > 0:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[ENERGY]", f"⚡ {target.name} 消耗了 {actual_consume:.0f} 点能量 (剩余: {energy_comp.energy:.0f})"
                    )))
    
    def restore_energy_at_turn_end(self, entity):
        """回合结束时恢复能量点"""
        energy_comp = entity.get_component(EnergyComponent)
        if energy_comp:
            recovery_amount = energy_comp.recovery_per_turn
            if recovery_amount > 0:
                old_energy = energy_comp.energy
                energy_comp.energy = min(energy_comp.energy + recovery_amount, energy_comp.max_energy)
                actual_restore = energy_comp.energy - old_energy
                if actual_restore > 0:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[ENERGY]", f"⚡ {entity.name} 回合结束，恢复了 {actual_restore:.0f} 点能量 (当前: {energy_comp.energy:.0f}/{energy_comp.max_energy:.0f})"
                    ))) 