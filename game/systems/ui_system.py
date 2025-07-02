from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import (RoundStartPayload, UIMessagePayload, UIDisplayOptionsPayload,
                             EffectResolutionPayload, StatQueryPayload)
from ..core.components import (HealthComponent, ManaComponent, DefenseComponent, SpeedComponent,
                              StatusEffectContainerComponent, DeadComponent)
from ..core.entity import Entity

class UISystem:
    """ <<< 职责变更: UI系统 >>>
    仅负责面向玩家的界面呈现，如状态面板、菜单、关键信息提示。
    """
    def __init__(self, event_bus: EventBus, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.world = world # 需要访问世界实体来渲染状态
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
                shield_str = f"Shield: {defense.defense_value:.0f}" if defense else ""
                
                # 获取考虑了状态效果后的最终速度值
                if speed:
                    final_speed = self._get_final_speed(entity, speed.speed)
                    speed_str = f"Speed: {final_speed:.0f}"
                else:
                    speed_str = ""
                
                # debuff,buff显示
                status_effects_str = ""
                if (container := entity.get_component(StatusEffectContainerComponent)) and container.effects:
                    effects_list = []
                    
                    # 特殊处理中毒效果 - 显示多个中毒状态
                    poison_effects = [e for e in container.effects if e.effect_id == "poison_01"]
                    if poison_effects:
                        poison_str = f"中毒 x{len(poison_effects)}个"
                        for i, poison_effect in enumerate(poison_effects, 1):
                            poison_str += f"({poison_effect.stack_count}层)"
                        effects_list.append(poison_str)
                    
                    # 处理其他效果
                    other_effects = [e for e in container.effects if e.effect_id != "poison_01"]
                    for e in other_effects:
                        if e.stacking == "stack_intensity":
                            effects_list.append(f"{e.name} x{e.stack_count} ({e.duration}回合)")
                        else:
                            effects_list.append(f"{e.name} ({e.duration}回合)")
                    
                    status_effects_str = f" | 状态: " + ", ".join(effects_list)

                # 构建状态字符串，过滤空值
                status_parts = [hp_str, mana_str]
                if shield_str: status_parts.append(shield_str)
                if speed_str: status_parts.append(speed_str)
                status_parts.append(status_effects_str)
                
                status_str = f"[{entity.name}] " + " | ".join(status_parts)
            print(status_str)
        print("-" * 40)
    
    def _get_final_speed(self, entity: 'Entity', base_speed: float) -> float: # type: ignore
        """获取考虑了状态效果后的最终速度值"""
        query = StatQueryPayload(entity=entity, stat_name="speed", base_value=base_speed, current_value=base_speed)
        self.event_bus.dispatch(GameEvent(EventName.STAT_QUERY, query))
        return query.current_value

    def on_round_start(self, event: GameEvent):
        payload: RoundStartPayload = event.payload
        print(f"\n{'='*15} 回合 {payload.round_number} {'='*15}")
        # 回合开始时只显示回合信息，不立即显示状态面板
        # 状态面板将在状态效果结算完成后显示

    def on_status_effects_resolved(self, event: GameEvent):
        self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"[UI]**状态效果结算完毕**")))
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
        """UI播报关键结果，包括谁对谁用了什么法术以及最终效果。"""
        payload: EffectResolutionPayload = event.payload
        
        # 构建基础信息
        base_info = f"{payload.caster.name} 对 {payload.target.name} 使用了 {payload.source_spell}"
        
        # 获取最终效果
        final_hp_change = next((r for r in payload.resource_changes if r.resource_name == 'health'), None)
        shield_change = next((r for r in payload.resource_changes if r.resource_name == 'shield'), None)
        
        # 构建完整信息
        if final_hp_change:
            if final_hp_change.change_amount < 0:
                # 伤害情况
                damage_info = f"造成了 {-final_hp_change.change_amount:.0f} 点伤害"
                if payload.shield_blocked > 0:
                    print(f"**战斗**: {base_info}，护盾抵消了 {payload.shield_blocked:.0f} 点伤害，{damage_info}！")
                else:
                    print(f"**战斗**: {base_info}，{damage_info}！")
            elif final_hp_change.change_amount > 0:
                # 治疗情况
                heal_info = f"恢复了 {final_hp_change.change_amount:.0f} 点生命值"
                if shield_change and shield_change.change_amount > 0:
                    print(f"**战斗**: {base_info}，{heal_info}，溢出治疗转化为 {shield_change.change_amount:.0f} 点护盾！")
                else:
                    print(f"**战斗**: {base_info}，{heal_info}！")
            else:
                # 0治疗情况 - 可能是溢疗术
                if shield_change and shield_change.change_amount > 0:
                    print(f"**战斗**: {base_info}，溢出治疗转化为 {shield_change.change_amount:.0f} 点护盾！")
                else:
                    print(f"**战斗**: {base_info}，伤害为0, 生命值不变，法术效果已生效！")
        elif shield_change and shield_change.change_amount > 0:
            # 只有护盾变化的情况
            print(f"**战斗**: {base_info}，获得 {shield_change.change_amount:.0f} 点护盾！")
        else:
            # 无生命值变化
            print(f"**战斗**: {base_info}，生命值未变化，法术效果已生效！")
        
        # 显示被动触发信息
        if payload.passive_triggers:
            for passive_info in payload.passive_triggers:
                print(f"**被动**: {passive_info}")
        
        print()  # 空行分隔