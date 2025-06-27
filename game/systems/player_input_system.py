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
            options = [f"{self.data_manager.get_spell_data(sid)['name']} (MP: {self.data_manager.get_spell_cost(sid)})" for sid in spell_comp.spells]
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
        
        if target_type == "enemy":
            # 敌人目标：选择AI控制的实体
            available_targets = [e for e in self.world.entities 
                               if e.has_component(AIControlledComponent) and not e.has_component(DeadComponent)]
            target_descriptions = [f"{e.name} (HP: {e.get_component(HealthComponent).hp:.0f}, Speed: {self._get_final_speed(e, e.get_component(SpeedComponent).speed):.0f})" 
                                 for e in available_targets]
        elif target_type == "ally":
            # 友军目标：选择玩家控制的实体
            available_targets = [e for e in self.world.entities 
                               if e.has_component(PlayerControlledComponent) and not e.has_component(DeadComponent)]
            target_descriptions = [f"{e.name} (HP: {e.get_component(HealthComponent).hp:.0f}, Speed: {self._get_final_speed(e, e.get_component(SpeedComponent).speed):.0f})" 
                                 for e in available_targets]
        else:
            # 其他类型：选择所有活着的实体
            available_targets = [e for e in self.world.entities if not e.has_component(DeadComponent)]
            target_descriptions = [f"{e.name} (HP: {e.get_component(HealthComponent).hp:.0f}, Speed: {self._get_final_speed(e, e.get_component(SpeedComponent).speed):.0f})" 
                                 for e in available_targets]
        
        if not available_targets:
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload("**提示**: 没有可用的目标!")))
            return
        
        # 显示目标选择
        self.event_bus.dispatch(GameEvent(EventName.UI_DISPLAY_OPTIONS, UIDisplayOptionsPayload(
            prompt=f"选择 {spell_data['name']} 的目标:", options=target_descriptions,
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
    
    def _get_final_speed(self, entity: 'Entity', base_speed: float) -> float: # type: ignore
        """获取考虑了状态效果后的最终速度值"""
        query = StatQueryPayload(entity=entity, stat_name="speed", base_value=base_speed, current_value=base_speed)
        self.event_bus.dispatch(GameEvent(EventName.STAT_QUERY, query))
        return query.current_value