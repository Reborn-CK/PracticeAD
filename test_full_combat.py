#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game.core.event_bus import EventBus
from game.core.entity import Entity
from game.core.components import HealthComponent, ManaComponent, ShieldComponent, StatusEffectContainerComponent, CritComponent, StatsComponent, SpellListComponent
from game.systems.combat.combat_resolution_system import CombatResolutionSystem
from game.systems.data_manager import DataManager
from game.systems.passive_ability_system import PassiveAbilitySystem
from game.status_effects.status_effect_factory import StatusEffectFactory
from game.core.event_bus import GameEvent
from game.core.enums import EventName
from game.core.payloads import DamageRequestPayload, LogRequestPayload

def test_full_combat_system():
    """测试完整的战斗系统，包括攻击力和防御力"""
    print("=== 测试完整战斗系统 ===")
    
    # 创建事件总线
    event_bus = EventBus()
    
    # 创建数据管理器
    data_manager = DataManager()
    data_manager.load_spell_data()
    data_manager.load_status_effect_data()
    data_manager.load_character_data()
    data_manager.load_passive_data()
    
    # 创建状态效果工厂
    status_effect_factory = StatusEffectFactory(data_manager)
    
    # 创建被动系统
    passive_system = PassiveAbilitySystem(event_bus)
    
    # 创建战斗解析系统
    combat_system = CombatResolutionSystem(event_bus, data_manager, passive_system, status_effect_factory)
    
    # 创建测试实体
    attacker = Entity("勇者", event_bus)
    defender = Entity("BOSS", event_bus)
    
    # 添加基础组件
    attacker.add_component(HealthComponent(attacker, event_bus, 100, 100))
    attacker.add_component(ManaComponent(500, 500))
    attacker.add_component(ShieldComponent(0))
    attacker.add_component(StatusEffectContainerComponent())
    attacker.add_component(CritComponent(0.1, 2.0))  # 10%暴击率
    attacker.add_component(StatsComponent(attack=50, defense=30))  # 攻击力50，防御力30
    attacker.add_component(SpellListComponent(spells=["normal_attack_01"]))
    
    defender.add_component(HealthComponent(defender, event_bus, 150, 150))
    defender.add_component(ManaComponent(500, 500))
    defender.add_component(ShieldComponent(100))
    defender.add_component(StatusEffectContainerComponent())
    defender.add_component(CritComponent(0.0, 2.0))  # 0%暴击率
    defender.add_component(StatsComponent(attack=80, defense=50))  # 攻击力80，防御力50
    defender.add_component(SpellListComponent(spells=["curse_of_slowness_01"]))
    
    # 订阅日志事件
    def log_handler(event):
        print(f"日志: {event.payload.message}")
    
    event_bus.subscribe(EventName.LOG_REQUEST, log_handler)
    
    print(f"攻击者属性: 攻击力={attacker.get_component(StatsComponent).attack}, 防御力={attacker.get_component(StatsComponent).defense}")
    print(f"防御者属性: 攻击力={defender.get_component(StatsComponent).attack}, 防御力={defender.get_component(StatsComponent).defense}")
    print(f"防御者护盾: {defender.get_component(ShieldComponent).shield_value}")
    
    # 测试普通攻击
    print("\n--- 测试普通攻击 ---")
    damage_payload = DamageRequestPayload(
        caster=attacker,
        target=defender,
        source_spell_id="normal_attack_01",
        source_spell_name="普通攻击1",
        base_damage=100,  # 基础伤害100
        damage_type="physical",
        can_be_reflected=True,
        can_crit=True,
        crit_chance=0.1,
        crit_damage_multiplier=2.0
    )
    
    # 记录攻击前的状态
    defender_health_before = defender.get_component(HealthComponent).hp
    defender_shield_before = defender.get_component(ShieldComponent).shield_value
    
    # 派发伤害请求
    event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, damage_payload))
    
    # 记录攻击后的状态
    defender_health_after = defender.get_component(HealthComponent).hp
    defender_shield_after = defender.get_component(ShieldComponent).shield_value
    
    print(f"防御者生命值变化: {defender_health_before} -> {defender_health_after}")
    print(f"防御者护盾变化: {defender_shield_before} -> {defender_shield_after}")
    
    # 测试反向攻击
    print("\n--- 测试反向攻击 ---")
    reverse_damage_payload = DamageRequestPayload(
        caster=defender,
        target=attacker,
        source_spell_id="normal_attack_01",
        source_spell_name="普通攻击1",
        base_damage=100,  # 基础伤害100
        damage_type="physical",
        can_be_reflected=True,
        can_crit=True,
        crit_chance=0.0,
        crit_damage_multiplier=2.0
    )
    
    # 记录攻击前的状态
    attacker_health_before = attacker.get_component(HealthComponent).hp
    
    # 派发伤害请求
    event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, reverse_damage_payload))
    
    # 记录攻击后的状态
    attacker_health_after = attacker.get_component(HealthComponent).hp
    
    print(f"攻击者生命值变化: {attacker_health_before} -> {attacker_health_after}")
    
    print("\n✅ 完整战斗系统测试完成！")

if __name__ == "__main__":
    test_full_combat_system() 