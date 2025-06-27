from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import (RoundStartPayload, UIDisplayOptionsPayload, 
                             EffectResolutionPayload, UIMessagePayload, StatQueryPayload)
from ..core.components import (DeadComponent, HealthComponent, ManaComponent, 
                               DefenseComponent, SpeedComponent, StatusEffectContainerComponent)
from ..core.entity import Entity

class UISystem:
    """仅负责面向玩家的界面呈现，如状态面板、菜单、关键信息提示。"""
    def __init__(self, event_bus: EventBus, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.world = world
        self.event_bus.subscribe(EventName.UI_MESSAGE, lambda e: print(e.payload.message))
        self.event_bus.subscribe(EventName.ROUND_START, self.on_round_start)
        self.event_bus.subscribe(EventName.UI_DISPLAY_OPTIONS, self.on_display_options)
        self.event_bus.subscribe(EventName.EFFECT_RESOLUTION_COMPLETE, self.on_effect_resolution)
        self.event_bus.subscribe(EventName.STATUS_EFFECTS_RESOLVED, self.on_status_effects_resolved)

    def _display_status_panel(self):
        """渲染所有角色的详细状态面板。"""
        print("-" * 40)
        for entity in self.world.entities:
            if entity.has_component(DeadComponent):
                status_str = f"[{entity.name}] (已倒下)"
            else:
                hp = entity.get_component(HealthComponent)
                mana = entity.get_component(ManaComponent)
                defense = entity.get_component(DefenseComponent)
                speed = entity.get_component(SpeedComponent)
                
                hp_str = f"HP: {hp.hp:.0f}/{hp.max_hp:.0f}" if hp else "HP: N/A"
                mana_str = f"Mana: {mana.mana:.0f}/{mana.max_mana:.0f}" if mana else "Mana: N/A"
                shield_str = f"Shield: {defense.defense_value:.0f}" if defense and defense.defense_value > 0 else ""
                
                if speed:
                    final_speed = self._get_final_stat(entity, "speed", speed.speed)
                    speed_str = f"Speed: {final_speed:.0f}"
                else:
                    speed_str = ""
                
                status_effects_str = ""
                if (container := entity.get_component(StatusEffectContainerComponent)) and container.effects:
                    effects_list = [f"{e.name}({e.duration if e.duration > 0 else '∞'})" for e in container.effects]
                    status_effects_str = f" | 状态: " + ", ".join(effects_list)

                status_parts = [part for part in [hp_str, mana_str, shield_str, speed_str] if part]
                status_str = f"[{entity.name}] " + " | ".join(status_parts) + status_effects_str
            print(status_str)
        print("-" * 40)
    
    def _get_final_stat(self, entity: Entity, stat_name: str, base_value: float) -> float:
        query = StatQueryPayload(entity=entity, stat_name=stat_name, base_value=base_value, current_value=base_value)
        self.event_bus.dispatch(GameEvent(EventName.STAT_QUERY, query))
        return query.current_value

    def on_round_start(self, event: GameEvent):
        payload: RoundStartPayload = event.payload
        print(f"\n{'='*15} 回合 {payload.round_number} {'='*15}")
        self._display_status_panel()

    def on_status_effects_resolved(self, event: GameEvent):
        self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**状态效果结算完毕**")))
        self._display_status_panel()

    def on_display_options(self, event: GameEvent):
        payload: UIDisplayOptionsPayload = event.payload
        print(payload.prompt)
        for i, option in enumerate(payload.options): print(f"  {i + 1}. {option}")
        while True:
            try:
                choice = int(input("请输入数字选择: ")) - 1
                if 0 <= choice < len(payload.options):
                    self.event_bus.dispatch(GameEvent(
                        payload.response_event_name,
                        {"choice_index": choice, "context": payload.context}
                    ))
                    break
                else: print("无效选择，请重新输入。")
            except ValueError: print("请输入一个有效的数字。")
    
    def on_effect_resolution(self, event: GameEvent):
        payload: EffectResolutionPayload = event.payload
        caster_name = payload.caster.name if payload.caster else "环境"
        base_info = f"{caster_name} 对 {payload.target.name} 使用了 {payload.source_spell}"
        
        # ... (此部分逻辑与原文件相同, 此处为简化版，您可以复制原文件的完整逻辑) ...
        details = []
        if payload.shield_blocked > 0:
            details.append(f"护盾抵消了 {payload.shield_blocked:.0f} 点伤害")
        
        final_hp_change = next((r for r in payload.resource_changes if r.resource_name == 'health'), None)
        if final_hp_change:
            if final_hp_change.change_amount < 0:
                details.append(f"造成了 {-final_hp_change.change_amount:.0f} 点伤害")
            elif final_hp_change.change_amount > 0:
                 details.append(f"恢复了 {final_hp_change.change_amount:.0f} 点生命值")

        if payload.passive_triggers:
            for passive_info in payload.passive_triggers:
                print(f"**被动**: {passive_info}")
        
        if details:
            print(f"**战斗**: {base_info}，" + "，".join(details) + "！")
        else:
            print(f"**战斗**: {base_info}，效果已生效！")