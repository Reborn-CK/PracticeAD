import time
import random
from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import ActionRequestPayload, UIMessagePayload, LogRequestPayload, CastSpellRequestPayload
from ..core.components import AIControlledComponent, SpellListComponent, DeadComponent, PlayerControlledComponent

class EnemyAISystem:
    def __init__(self, event_bus: EventBus, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.world = world
        event_bus.subscribe(EventName.ACTION_REQUEST, self.on_action_request)
        
    def on_action_request(self, event: GameEvent):
        caster = event.payload.acting_entity
        if caster.has_component(AIControlledComponent):
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"[{caster.name}] 的回合...")))
            time.sleep(1) # 模拟思考

            # 简单的AI逻辑：随机选一个技能，打随机一个活着的玩家
            spell_comp = caster.get_component(SpellListComponent)
            if not spell_comp.spells: return

            spell_id = random.choice(spell_comp.spells)
            
            possible_targets = [e for e in self.world.entities if e.has_component(PlayerControlledComponent) and not e.has_component(DeadComponent)]
            if not possible_targets: return

            target = random.choice(possible_targets)
            
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("AI", f"AI {caster.name} 决定对 {target.name} 使用 {spell_id}")))
            self.event_bus.dispatch(GameEvent(EventName.CAST_SPELL_REQUEST, CastSpellRequestPayload(caster, target, spell_id)))