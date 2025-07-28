#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game.core.event_bus import EventBus
from game.core.entity import Entity
from game.core.components import HealthComponent, ManaComponent, ShieldComponent, StatusEffectContainerComponent, CritComponent, StatsComponent
from game.systems.combat.damage_processors import AttackDefenseHandler
from game.core.pipeline import EffectExecutionContext
from game.core.event_bus import GameEvent
from game.core.enums import EventName
from game.core.payloads import LogRequestPayload

def test_attack_defense_system():
    """测试攻击力和防御力系统"""
    print("=== 测试攻击力和防御力系统 ===")
    
    # 创建事件总线
    event_bus = EventBus()
    
    # 创建测试实体
    attacker = Entity("攻击者", event_bus)
    defender = Entity("防御者", event_bus)
    
    # 添加基础组件
    attacker.add_component(HealthComponent(attacker, event_bus, 100, 100))
    attacker.add_component(ManaComponent(100, 100))
    attacker.add_component(ShieldComponent(0))
    attacker.add_component(StatusEffectContainerComponent())
    attacker.add_component(CritComponent(0.0, 2.0))  # 0%暴击率
    attacker.add_component(StatsComponent(attack=50, defense=0))  # 攻击力50
    
    defender.add_component(HealthComponent(defender, event_bus, 100, 100))
    defender.add_component(ManaComponent(100, 100))
    defender.add_component(ShieldComponent(0))
    defender.add_component(StatusEffectContainerComponent())
    defender.add_component(CritComponent(0.0, 2.0))  # 0%暴击率
    defender.add_component(StatsComponent(attack=0, defense=30))  # 防御力30
    
    # 创建攻击力/防御力处理器
    attack_defense_handler = AttackDefenseHandler(event_bus)
    
    # 订阅日志事件
    def log_handler(event):
        print(f"日志: {event.payload.message}")
    
    event_bus.subscribe(EventName.LOG_REQUEST, log_handler)
    
    # 创建伤害执行上下文
    context = EffectExecutionContext(
        source=attacker,
        target=defender,
        effect_type='damage',
        initial_value=100,  # 基础伤害100
        current_value=100,
        base_damage=100,
        damage_type='physical',
        can_crit=False,
        crit_chance=0.0,
        crit_damage_multiplier=2.0
    )
    
    print(f"攻击者攻击力: {attacker.get_component(StatsComponent).attack}")
    print(f"防御者防御力: {defender.get_component(StatsComponent).defense}")
    print(f"基础伤害: {context.current_value}")
    
    # 执行攻击力/防御力计算
    result_context = attack_defense_handler.process(context)
    
    print(f"最终伤害: {result_context.current_value}")
    
    # 验证计算结果
    expected_attack_bonus = 50 * 0.5  # 攻击力加成
    expected_defense_reduction = 30  # 防御力减免
    expected_damage = 100 + expected_attack_bonus - expected_defense_reduction
    
    print(f"预期攻击力加成: {expected_attack_bonus}")
    print(f"预期防御力减免: {expected_defense_reduction}")
    print(f"预期最终伤害: {expected_damage}")
    
    if abs(result_context.current_value - expected_damage) < 0.1:
        print("✅ 测试通过！攻击力和防御力计算正确")
    else:
        print("❌ 测试失败！计算结果与预期不符")
    
    return result_context.current_value

if __name__ == "__main__":
    test_attack_defense_system() 