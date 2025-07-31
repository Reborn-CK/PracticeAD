from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName, BattleTurnRule
from ..core.payloads import RoundStartPayload, ActionRequestPayload, StatQueryPayload, ActionAfterActPayload, PostActionSettlementPayload
from ..core.components import DeadComponent, SpeedComponent, PositionComponent
from ..core.entity import Entity

class TurnManagerSystem:
    AP_THRESHOLD = 100
    AP_RECOVERY_RATE = 0.1

    def __init__(self, event_bus: EventBus, world: 'World', energy_system: 'EnergySystem' = None): # type: ignore
        self.event_bus = event_bus
        self.world = world
        self.energy_system = energy_system
        self.round_number = 0
        self.turn_queue = []
        self.battle_turn_rule = BattleTurnRule.TURN_BASED
        self.ap_bars = {entity.name: 0 for entity in self.world.entities if not entity.has_component(DeadComponent)}
        self.is_waiting_for_action = False
        self.acting_entity = None
        self.event_bus.subscribe(EventName.ACTION_AFTER_ACT, self.on_action_after_act)


    def update(self):
        if self.battle_turn_rule == BattleTurnRule.AP_BASED:
            if self.is_waiting_for_action:
                return
            self.update_ap_based()
        else:
            self.update_turn_based()

    def update_turn_based(self):
        if not self.turn_queue:
            self.round_number += 1
            living_entities = [e for e in self.world.entities if not e.has_component(DeadComponent)]
            if len(living_entities) < 2:
                self.world.is_running = False
                return

            # 过滤掉没有SpeedComponent的实体
            living_entities = [e for e in living_entities if e.get_component(SpeedComponent) is not None]
            # 按速度排序，如果速度相等则按位置ID排序（位置ID小的先手）
            living_entities.sort(key=lambda e: (e.get_final_stat("speed", e.get_component(SpeedComponent).speed), -e.get_component(PositionComponent).position_id if e.get_component(PositionComponent) else 0), reverse=True)
            self.turn_queue = living_entities
            
            # 先触发状态效果结算事件
            self.event_bus.dispatch(GameEvent(EventName.ROUND_START, RoundStartPayload(self.round_number)))
            
            # 等待状态效果结算完成后再刷新UI
            # 状态效果系统会在结算完成后触发 STATUS_EFFECTS_RESOLVED 事件

        if self.turn_queue:
            acting_entity = self.turn_queue.pop(0)
            self.event_bus.dispatch(GameEvent(EventName.ACTION_REQUEST, ActionRequestPayload(acting_entity)))

    def update_ap_based(self):
        ready_entities = []
        
        living_entities = [e for e in self.world.entities if not e.has_component(DeadComponent)]
        
        # 过滤掉没有SpeedComponent的实体（如战场实体等）
        living_entities = [e for e in living_entities if e.get_component(SpeedComponent) is not None]
        
        if len(living_entities) < 2:
            self.world.is_running = False
            return

        for entity in living_entities:
            if entity.name not in self.ap_bars:
                self.ap_bars[entity.name] = 0
            
            # 安全检查：确保实体有SpeedComponent
            speed_comp = entity.get_component(SpeedComponent)
            if not speed_comp:
                # 如果没有SpeedComponent，跳过这个实体
                continue
                
            speed = entity.get_final_stat("speed", speed_comp.speed)
            self.ap_bars[entity.name] += speed * self.AP_RECOVERY_RATE
            if self.ap_bars[entity.name] >= self.AP_THRESHOLD:
                ready_entities.append(entity)
        
        if ready_entities:
            # 按AP值排序，如果AP值相等则按位置ID排序（位置ID小的先手）
            ready_entities.sort(key=lambda e: (self.ap_bars[e.name], -e.get_component(PositionComponent).position_id if e.get_component(PositionComponent) else 0), reverse=True)
            self.acting_entity = ready_entities[0]
            self.is_waiting_for_action = True
            
            # 强制刷新UI以显示最新的AP值
            from .ui_system import UISystem
            ui_system = self.world.get_system(UISystem)
            if ui_system:
                ui_system.display_status_panel()
            
            self.event_bus.dispatch(GameEvent(EventName.ACTION_REQUEST, ActionRequestPayload(self.acting_entity)))

    def on_action_after_act(self, event: GameEvent):
        payload: ActionAfterActPayload = event.payload
        if self.is_waiting_for_action and self.acting_entity and payload.acting_entity.name == self.acting_entity.name:
            if self.acting_entity.name in self.ap_bars:
                self.ap_bars[self.acting_entity.name] -= self.AP_THRESHOLD
            
            # 恢复能量点
            if self.energy_system:
                self.energy_system.restore_energy_at_turn_end(self.acting_entity)
            
            # 派发行动后结算事件
            self.event_bus.dispatch(GameEvent(EventName.POST_ACTION_SETTLEMENT, PostActionSettlementPayload(self.acting_entity)))
            
            self.acting_entity = None
            self.is_waiting_for_action = False

    def set_battle_turn_rule(self, rule: BattleTurnRule):
        self.battle_turn_rule = rule
        self.round_number = 0
        self.turn_queue = []
        self.ap_bars = {entity.name: 0 for entity in self.world.entities if not entity.has_component(DeadComponent)}