from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import UltimateChargeChangeRequestPayload, LogRequestPayload, UltimateChargeRequestPayload
from ..core.components import UltimateChargeComponent

class UltimateChargeSystem:
    """终极技能充能系统，管理终极技能的充能和消耗"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.event_bus.subscribe(EventName.ULTIMATE_CHARGE_REQUEST, self._on_ultimate_charge_request)
        self.event_bus.subscribe(EventName.ULTIMATE_CHARGE_CHANGE_REQUEST, self._on_ultimate_charge_change_request)
    
    def _on_ultimate_charge_request(self, event):
        """处理终极技能充能消耗请求"""
        payload = event.payload
        entity = payload.entity
        cost = payload.cost
        
        charge_comp = entity.get_component(UltimateChargeComponent)
        if charge_comp:
            if charge_comp.charge >= cost:
                charge_comp.charge -= cost
                payload.is_affordable = True
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[ULTIMATE]", f"⚡ {entity.name} 消耗了 {cost}% 充能值 (剩余: {charge_comp.charge:.0f}%)"
                )))
            else:
                payload.is_affordable = False
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[ULTIMATE]", f"❌ {entity.name} 充能不足！需要 {cost}%，当前只有 {charge_comp.charge:.0f}%"
                )))
    
    def _on_ultimate_charge_change_request(self, event):
        """处理终极技能充能变化请求"""
        payload = event.payload
        target = payload.target
        amount = payload.amount
        change_type = payload.change_type
        
        charge_comp = target.get_component(UltimateChargeComponent)
        if charge_comp:
            old_charge = charge_comp.charge
            if change_type == "add":
                # 增加充能值
                charge_comp.charge = min(charge_comp.charge + amount, charge_comp.max_charge)
                actual_add = charge_comp.charge - old_charge
                if actual_add > 0:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[ULTIMATE]", f"⚡ {target.name} 获得了 {actual_add:.0f}% 充能值 (当前: {charge_comp.charge:.0f}%)"
                    )))
            elif change_type == "consume":
                # 消耗充能值
                charge_comp.charge = max(charge_comp.charge - amount, 0)
                actual_consume = old_charge - charge_comp.charge
                if actual_consume > 0:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                        "[ULTIMATE]", f"⚡ {target.name} 消耗了 {actual_consume:.0f}% 充能值 (剩余: {charge_comp.charge:.0f}%)"
                    )))
    
    def add_charge_from_spell(self, entity, spell_id, data_manager):
        """从施法中获取充能值"""
        charge_comp = entity.get_component(UltimateChargeComponent)
        if not charge_comp:
            return
        
        # 获取技能的充能值
        charge_value = data_manager.get_spell_ultimate_charge(spell_id)
        if charge_value > 0:
            old_charge = charge_comp.charge
            charge_comp.charge = min(charge_comp.charge + charge_value, charge_comp.max_charge)
            actual_add = charge_comp.charge - old_charge
            if actual_add > 0:
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[ULTIMATE]", f"⚡ {entity.name} 施放技能获得了 {actual_add:.0f}% 充能值"
                )))
    
    def can_cast_ultimate(self, entity, charge_level=100):
        """检查是否可以释放终极技能"""
        charge_comp = entity.get_component(UltimateChargeComponent)
        if charge_comp:
            return charge_comp.charge >= charge_level
        return False
    
    def get_ultimate_version(self, entity):
        """获取可释放的终极技能版本"""
        charge_comp = entity.get_component(UltimateChargeComponent)
        if charge_comp:
            if charge_comp.charge >= 200:
                return "ultimate_02"  # 升级版
            elif charge_comp.charge >= 100:
                return "ultimate_01"  # 基础版
        return None 