import time
from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName, BattleTurnRule
from ..core.payloads import ActionRequestPayload, CastSpellRequestPayload, UIMessagePayload, LogRequestPayload, ActionAfterActPayload
from ..core.components import AIControlledComponent, SpellListComponent, DeadComponent
from .ui_system import UISystem
from .turn_manager_system import TurnManagerSystem

class EnemyAISystem:
    def __init__(self, event_bus, world):
        self.event_bus = event_bus; self.world = world
        event_bus.subscribe(EventName.ACTION_REQUEST, self.on_action_request)
    def on_action_request(self, event):
        caster = event.payload.acting_entity
        if caster.has_component(AIControlledComponent):
            turn_manager = self.world.get_system(TurnManagerSystem)
            if turn_manager.battle_turn_rule == BattleTurnRule.AP_BASED:
                self.world.get_system(UISystem).display_status_panel()
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"[{caster.name}] 的回合...")))
            time.sleep(1)
            spell_id = caster.get_component(SpellListComponent).spells[0]
            target = self.world.get_entity_by_name("勇者")
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[AI]", f"AI决定对{target.name}使用{spell_id}")))
            if target and not target.has_component(DeadComponent):
                self.event_bus.dispatch(GameEvent(EventName.CAST_SPELL_REQUEST, CastSpellRequestPayload(caster, target, spell_id)))
            self.event_bus.dispatch(GameEvent(EventName.ACTION_AFTER_ACT, ActionAfterActPayload(caster)))