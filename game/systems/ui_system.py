import os
import time
from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName, BattleTurnRule
from ..core.payloads import (RoundStartPayload, UIMessagePayload, UIDisplayOptionsPayload,
                             EffectResolutionPayload, StatQueryPayload)
from ..core.components import (HealthComponent, ManaComponent, ShieldComponent, SpeedComponent,
                              StatusEffectContainerComponent, DeadComponent)
from ..core.entity import Entity
from .turn_manager_system import TurnManagerSystem

class UISystem:
    UI_REFRESH_INTERVAL = 1.0 / 10 # 10 FPS

    def __init__(self, event_bus: EventBus, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.world = world # 需要访问世界实体来渲染状态
        self.last_refresh_time = 0
        self.event_bus.subscribe(EventName.UI_MESSAGE, lambda e: print(e.payload.message))
        self.event_bus.subscribe(EventName.ROUND_START, self.on_round_start)
        self.event_bus.subscribe(EventName.UI_DISPLAY_OPTIONS, self.on_display_options)
        self.event_bus.subscribe(EventName.EFFECT_RESOLUTION_COMPLETE, self.on_effect_resolution)
        self.event_bus.subscribe(EventName.STATUS_EFFECTS_RESOLVED, self.on_status_effects_resolved)

    def update(self):
        turn_manager = self.world.get_system(TurnManagerSystem)
        if turn_manager.battle_turn_rule == BattleTurnRule.AP_BASED:
            current_time = time.time()
            if current_time - self.last_refresh_time >= self.UI_REFRESH_INTERVAL:
                self.display_status_panel()

    def _clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def _generate_ap_bar(self, current_ap, max_ap, length=20):
        progress = int((current_ap / max_ap) * length)
        return f"[{'|' * progress}{'-' * (length - progress)}]"

    def display_status_panel(self):
        """渲染所有角色的详细状态面板。"""
        self._clear_screen()
        print("-" * 40)

        turn_manager = self.world.get_system(TurnManagerSystem)
        is_ap_based = turn_manager.battle_turn_rule == BattleTurnRule.AP_BASED
        
        for entity in self.world.entities:
            if entity.has_component(DeadComponent):
                status_str = f"[{entity.name}] (已倒下)"
            else:
                hp = entity.get_component(HealthComponent)
                mana = entity.get_component(ManaComponent)
                shield = entity.get_component(ShieldComponent)
                speed = entity.get_component(SpeedComponent)
                
                ap_str = ""
                if is_ap_based:
                    ap_value = turn_manager.ap_bars.get(entity.name, 0)
                    ap_bar = self._generate_ap_bar(ap_value, turn_manager.AP_THRESHOLD)
                    ap_str = f"AP: {ap_bar} {ap_value:.0f}/{turn_manager.AP_THRESHOLD}"

                hp_str = f"HP: {hp.hp:.0f}/{hp.max_hp:.0f}" if hp else "HP: N/A"
                mana_str = f"Mana: {mana.mana:.0f}/{mana.max_mana:.0f}" if mana else "Mana: N/A"
                shield_str = f"Shield: {shield.shield_value:.0f}" if shield else ""
                
                # 获取考虑了状态效果后的最终速度值
                if speed:
                    #final_speed = self._get_final_speed(entity, speed.speed)
                    final_speed = entity.get_final_stat("speed", speed.speed)
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
                            duration_str = f"({e.duration}回合)" if e.duration is not None else "(永久)"
                            effects_list.append(f"{e.name} x{e.stack_count} {duration_str}")
                        else:
                            duration_str = f"({e.duration}回合)" if e.duration is not None else "(永久)"
                            effects_list.append(f"{e.name} {duration_str}")
                    
                    status_effects_str = f" | 状态: " + ", ".join(effects_list)

                # 构建状态字符串，过滤空值
                status_parts = [hp_str, mana_str]
                if ap_str: status_parts.append(ap_str)
                if shield_str: status_parts.append(shield_str)
                if speed_str: status_parts.append(speed_str)
                status_parts.append(status_effects_str)
                
                status_str = f"[{entity.name}] " + " | ".join(status_parts)
            print(status_str)
        print("-" * 40)
        self.last_refresh_time = time.time()
    
    def on_round_start(self, event: GameEvent):
        turn_manager = self.world.get_system(TurnManagerSystem)
        if turn_manager.battle_turn_rule == BattleTurnRule.AP_BASED:
            return # AP模式下不显示回合信息
        payload: RoundStartPayload = event.payload
        print(f"\n{'='*15} 回合 {payload.round_number} {'='*15}")
        # 回合开始时只显示回合信息，不立即显示状态面板
        # 状态面板将在状态效果结算完成后显示

    def on_status_effects_resolved(self, event: GameEvent):
        turn_manager = self.world.get_system(TurnManagerSystem)
        if turn_manager.battle_turn_rule == BattleTurnRule.TURN_BASED:
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"[UI]**状态效果结算完毕**")))
        self.display_status_panel()

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
        
        # 检查是否是反伤伤害
        is_thorns_reflection = payload.log_reflection
        is_dot_damage = getattr(payload, 'is_dot_damage', False)
        
        # 构建基础信息
        if is_thorns_reflection:
            base_info = f"{payload.caster.name} 的反伤对 {payload.target.name}"
        elif is_dot_damage:
            base_info = f"{payload.target.name} 因 {payload.caster.name} 施加的 {payload.source_spell} 战斗战斗持续伤害"
        else:
            base_info = f"{payload.caster.name} 对 {payload.target.name} 使用了 {payload.source_spell}"
        
        # 获取最终效果
        final_hp_change = next((r for r in payload.resource_changes if r['resource_name'] == 'health'), None)
        shield_change = next((r for r in payload.resource_changes if r['resource_name'] == 'shield'), None)
        
        # 根据效果变化信息构建播报内容
        if payload.no_effect_produced:
            # 没有产生任何效果
            if is_dot_damage:
                print(f"**战斗持续伤害**: {base_info}，但没有产生任何效果！")
            else:
                print(f"**战斗**: {base_info}，但没有产生任何效果！")
        else:
            # 有实际效果产生，显示具体变化
            effect_parts = []
            
            # 生命值变化
            if payload.health_changed and final_hp_change:
                if final_hp_change['change_amount'] < 0:
                    # 伤害情况
                    damage_amount = -final_hp_change['change_amount']
                    old_hp = final_hp_change['current_value'] - final_hp_change['change_amount']
                    new_hp = final_hp_change['current_value']
                    if is_thorns_reflection:
                        effect_parts.append(f"{payload.target.name} 生命值 {old_hp:.0f} → {new_hp:.0f} (减少 {damage_amount:.0f} 点)")
                    else:
                        damage_info = f"{payload.target.name} 生命值 {old_hp:.0f} → {new_hp:.0f} (减少 {damage_amount:.0f} 点)"
                        if payload.shield_blocked > 0:
                            effect_parts.append(f"{payload.target.name} 护盾抵消 {payload.shield_blocked:.0f} 点伤害，{damage_info}")
                        else:
                            effect_parts.append(damage_info)
                elif final_hp_change['change_amount'] > 0:
                    # 治疗情况
                    old_hp = final_hp_change['current_value'] - final_hp_change['change_amount']
                    new_hp = final_hp_change['current_value']
                    effect_parts.append(f"{payload.target.name} 生命值 {old_hp:.0f} → {new_hp:.0f} (恢复 {final_hp_change['change_amount']:.0f} 点)")
            
            # 护盾变化
            if payload.shield_changed:
                if payload.shield_change_amount > 0:
                    old_shield = payload.shield_before
                    new_shield = payload.shield_before + payload.shield_change_amount
                    effect_parts.append(f"{payload.target.name} 护盾 {old_shield:.0f} → {new_shield:.0f} (增加 {payload.shield_change_amount:.0f} 点)")
                elif payload.shield_change_amount < 0:
                    old_shield = payload.shield_before
                    new_shield = payload.shield_before + payload.shield_change_amount
                    effect_parts.append(f"{payload.target.name} 护盾 {old_shield:.0f} → {new_shield:.0f} (减少 {abs(payload.shield_change_amount):.0f} 点)")
                else:
                    # 护盾被消耗但没有具体数值变化记录
                    effect_parts.append(f"{payload.target.name} 护盾被消耗")
            
            # 状态效果变化
            if payload.new_status_effects:
                # 获取目标当前的状态效果
                status_container = payload.target.get_component(StatusEffectContainerComponent)
                if status_container and status_container.effects:
                    # 显示新获得的状态效果
                    new_effects = []
                    for effect in status_container.effects:
                        if effect.stacking == "stack_intensity":
                            new_effects.append(f"{effect.name} x{effect.stack_count} ({effect.duration}回合)")
                        else:
                            new_effects.append(f"{effect.name} ({effect.duration}回合)")
                    
                    if new_effects:
                        effect_parts.append(f"{payload.target.name} 获得状态效果: {', '.join(new_effects)}")
                else:
                    effect_parts.append(f"{payload.target.name} 获得新的状态效果")
            
            # 组合所有效果信息
            if effect_parts:
                effects_str = "，".join(effect_parts)
                if is_dot_damage:
                    print(f"**战斗持续伤害**: {base_info}，{effects_str}！")
                else:
                    print(f"**战斗**: {base_info}，{effects_str}！")
            else:
                # 有变化但无法具体描述的情况
                if is_dot_damage:
                    print(f"**战斗持续伤害**: {base_info}，产生了效果！")
                else:
                    print(f"**战斗**: {base_info}，产生了效果！")
        
        # 显示被动触发信息
        if payload.passive_triggers:
            for passive_info in payload.passive_triggers:
                print(f"**被动**: {passive_info}")
        
        print()  # 空行分隔