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
from game.systems.spell_cast_system import SpellCastSystem
from game.core.event_bus import GameEvent
from game.core.enums import EventName
from game.core.payloads import CastSpellRequestPayload, LogRequestPayload

def test_clean_damage_calculation():
    """测试清理后的伤害计算逻辑：基础伤害 + 攻击力×百分比 - 防御力减免"""
    print("=== 测试清理后的伤害计算逻辑 ===")
    
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
    
    # 创建技能施放系统
    spell_system = SpellCastSystem(event_bus, data_manager, status_effect_factory)
    
    # 订阅日志事件
    def log_handler(event):
        print(f"日志: {event.payload.message}")
    
    event_bus.subscribe(EventName.LOG_REQUEST, log_handler)
    
    # 测试用例：不同攻击力和防御力组合
    test_cases = [
        (50, 0, "normal_attack_01", "基础攻击无防御"),
        (50, 25, "normal_attack_01", "基础攻击低防御"),
        (100, 50, "normal_attack_01", "高攻击中等防御"),
        (50, 100, "normal_attack_01", "低攻击高防御"),
        (50, 0, "fireball_01", "魔法攻击无防御"),
        (50, 50, "fireball_01", "魔法攻击中等防御"),
    ]
    
    for attack_value, defense_value, spell_id, description in test_cases:
        print(f"\n--- 测试{description}（攻击力={attack_value}, 防御力={defense_value}） ---")
        
        # 获取技能数据
        spell_data = data_manager.get_spell_data(spell_id)
        if not spell_data:
            print(f"❌ 未找到技能数据: {spell_id}")
            continue
            
        # 获取伤害效果
        damage_effect = None
        for effect in spell_data.get('effects', []):
            if effect.get('type') == 'damage':
                damage_effect = effect
                break
        
        if not damage_effect:
            print(f"❌ 技能 {spell_id} 没有伤害效果")
            continue
        
        # 计算理论伤害
        base_damage = damage_effect.get('amount', 0)
        damage_percentage = damage_effect.get('damage_percentage', 1.0)
        affected_stat = damage_effect.get('affected_stat', 'attack')
        
        # 理论伤害计算：基础伤害 + 攻击力×百分比
        theoretical_damage = base_damage + (attack_value * damage_percentage)
        
        # 理论防御力减免
        defense_percentage = defense_value / (100 + defense_value)
        theoretical_final_damage = theoretical_damage * (1 - defense_percentage)
        
        print(f"技能: {spell_data.get('name', spell_id)}")
        print(f"基础伤害: {base_damage}")
        print(f"伤害百分比: {damage_percentage*100:.0f}%")
        print(f"影响属性: {affected_stat}")
        print(f"理论伤害: {base_damage} + {attack_value} × {damage_percentage} = {theoretical_damage}")
        print(f"理论防御力减伤: {defense_percentage*100:.1f}%")
        print(f"理论最终伤害: {theoretical_final_damage:.1f}")
        
        # 创建测试实体
        attacker = Entity("攻击者", event_bus)
        defender = Entity(f"防御者(防御{defense_value})", event_bus)
        
        # 添加基础组件
        attacker.add_component(HealthComponent(attacker, event_bus, 100, 100))
        attacker.add_component(ManaComponent(500, 500))
        attacker.add_component(ShieldComponent(0))
        attacker.add_component(StatusEffectContainerComponent())
        attacker.add_component(CritComponent(0.0, 2.0))  # 0%暴击率
        attacker.add_component(StatsComponent(attack=attack_value, defense=0))
        attacker.add_component(SpellListComponent(spells=[spell_id]))
        
        defender.add_component(HealthComponent(defender, event_bus, 200, 200))
        defender.add_component(ManaComponent(500, 500))
        defender.add_component(ShieldComponent(0))
        defender.add_component(StatusEffectContainerComponent())
        defender.add_component(CritComponent(0.0, 2.0))  # 0%暴击率
        defender.add_component(StatsComponent(attack=0, defense=defense_value))
        defender.add_component(SpellListComponent(spells=[]))
        
        # 记录攻击前的状态
        defender_health_before = defender.get_component(HealthComponent).hp
        
        # 施放技能
        cast_payload = CastSpellRequestPayload(
            caster=attacker,
            target=defender,
            spell_id=spell_id
        )
        
        # 派发施法请求
        event_bus.dispatch(GameEvent(EventName.CAST_SPELL_REQUEST, cast_payload))
        
        # 记录攻击后的状态
        defender_health_after = defender.get_component(HealthComponent).hp
        actual_damage = defender_health_before - defender_health_after
        
        print(f"实际造成伤害: {actual_damage}")
        print(f"防御者生命值变化: {defender_health_before} -> {defender_health_after}")
        
        # 验证计算结果
        damage_difference = abs(actual_damage - theoretical_final_damage)
        if damage_difference < 1:  # 允许1点误差
            print("✅ 测试通过！实际伤害与理论伤害基本一致")
        else:
            print(f"❌ 测试失败！实际伤害({actual_damage})与理论伤害({theoretical_final_damage})差异较大")
            print(f"差异: {damage_difference:.1f}")
    
    print("\n✅ 清理后的伤害计算测试完成！")

if __name__ == "__main__":
    test_clean_damage_calculation() 