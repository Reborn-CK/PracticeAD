# game/systems/player_input_system.py
from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import (ActionRequestPayload, UIDisplayOptionsPayload, 
                             UIMessagePayload, CastSpellRequestPayload, StatQueryPayload)
from ..core.components import (PlayerControlledComponent, SpellListComponent, 
                               AIControlledComponent, DeadComponent, HealthComponent, SpeedComponent)
from .data_manager import DataManager
from ..core.entity import Entity

class PlayerInputSystem:
    def __init__(self, event_bus: EventBus, data_manager: DataManager, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.world = world
        event_bus.subscribe(EventName.ACTION_REQUEST, self.on_action_request)
        event_bus.subscribe(EventName.PLAYER_SPELL_CHOICE, self.on_player_spell_choice)
        event_bus.subscribe(EventName.PLAYER_TARGET_CHOICE, self.on_player_target_choice)
    
    def on_action_request(self, event: GameEvent):
        actor = event.payload.acting_entity
        if actor.has_component(PlayerControlledComponent):
            spell_comp = actor.get_component(SpellListComponent)
            options = []
            for sid in spell_comp.spells:
                spell_data = self.data_manager.get_spell_data(sid)
                spell_name = spell_data.get('name', '未知法术') if spell_data else '未知法术'
                spell_cost = self.data_manager.get_spell_cost(sid)
                options.append(f"{spell_name} (MP: {spell_cost})")
            self.event_bus.dispatch(GameEvent(EventName.UI_DISPLAY_OPTIONS, UIDisplayOptionsPayload(
                prompt=f"[{actor.name}] 的回合，请选择法术:", options=options,
                response_event_name=EventName.PLAYER_SPELL_CHOICE, context={"caster": actor}
            )))
    
    def on_player_spell_choice(self, event: GameEvent):
        caster = event.payload["context"]["caster"]
        spell_id = caster.get_component(SpellListComponent).spells[event.payload["choice_index"]]
        spell_data = self.data_manager.get_spell_data(spell_id)
        target_type = self.data_manager.get_spell_target_type(spell_id)
        
        # 根据法术目标类型确定可选目标
        available_targets = []
        target_descriptions = []

        def get_desc(e: Entity)->str:
            hp_comp = e.get_component(HealthComponent)
            speed_comp = e.get_component(SpeedComponent)
            hp = hp_comp.hp if hp_comp else 0
            speed = speed_comp.speed if speed_comp else 0
            final_speed = e.get_final_stat("speed", speed)
            return f"{e.name} (HP: {hp:.0f}, Speed: {final_speed:.0f})"
        
        if target_type == "enemy":
            available_targets = [e for e in self.world.entities if e.has_component(AIControlledComponent) and not e.has_component(DeadComponent)]
            target_descriptions = [get_desc(e) for e in available_targets]
        elif target_type == "ally":
            available_targets = [e for e in self.world.entities if e.has_component(PlayerControlledComponent) and not e.has_component(DeadComponent)]
            target_descriptions = [get_desc(e) for e in available_targets]
        else:
            available_targets = [e for e in self.world.entities if not e.has_component(DeadComponent)]
            target_descriptions = [get_desc(e) for e in available_targets]
        # if target_type == "enemy":
        #     # 敌人目标：选择AI控制的实体
        #     available_targets = [e for e in self.world.entities 
        #                        if e.has_component(AIControlledComponent) and not e.has_component(DeadComponent)]
        #     target_descriptions = [f"{e.name} (HP: {e.get_component(HealthComponent).hp:.0f}, Speed: {self._get_final_speed(e, e.get_component(SpeedComponent).speed):.0f})" 
        #                          for e in available_targets]
        # elif target_type == "ally":
        #     # 友军目标：选择玩家控制的实体
        #     available_targets = [e for e in self.world.entities 
        #                        if e.has_component(PlayerControlledComponent) and not e.has_component(DeadComponent)]
        #     target_descriptions = [f"{e.name} (HP: {e.get_component(HealthComponent).hp:.0f}, Speed: {self._get_final_speed(e, e.get_component(SpeedComponent).speed):.0f})" 
        #                          for e in available_targets]
        # else:
        #     # 其他类型：选择所有活着的实体
        #     available_targets = [e for e in self.world.entities if not e.has_component(DeadComponent)]
        #     target_descriptions = [f"{e.name} (HP: {e.get_component(HealthComponent).hp:.0f}, Speed: {self._get_final_speed(e, e.get_component(SpeedComponent).speed):.0f})" 
        #                          for e in available_targets]
        
        if not available_targets:
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload("**提示**: 没有可用的目标!")))
            return
        
        # 显示目标选择
        spell_name = spell_data.get('name', '未知法术') if spell_data else '未知法术'
        self.event_bus.dispatch(GameEvent(EventName.UI_DISPLAY_OPTIONS, UIDisplayOptionsPayload(
            prompt=f"选择 {spell_name} 的目标:", options=target_descriptions,
            response_event_name=EventName.PLAYER_TARGET_CHOICE, 
            context={"caster": caster, "spell_id": spell_id, "available_targets": available_targets}
        )))
    
    def on_player_target_choice(self, event: GameEvent):
        context = event.payload["context"]
        caster = context["caster"]
        spell_id = context["spell_id"]
        available_targets = context["available_targets"]
        target = available_targets[event.payload["choice_index"]]
        
        self.event_bus.dispatch(GameEvent(EventName.CAST_SPELL_REQUEST, CastSpellRequestPayload(caster, target, spell_id)))