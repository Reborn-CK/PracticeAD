#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
装备系统测试
测试装备的装备、卸下、耐久损耗等功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game.core.event_bus import EventBus
from game.core.entity import Entity
from game.core.components import EquipmentComponent, StatsComponent, HealthComponent
from game.core.enums import EventName
from game.core.payloads import DamageRequestPayload, TurnStartPayload
from game.core.event_bus import GameEvent
from game.systems.data_manager import DataManager
from game.systems.equipment_system import EquipmentSystem

def test_equipment_system():
    """测试装备系统的基本功能"""
    print("=== 装备系统测试 ===")
    
    # 创建事件总线和数据管理器
    event_bus = EventBus()
    data_manager = DataManager()
    
    # 加载数据
    data_manager.load_equipment_data()
    data_manager.load_character_data()
    
    # 创建装备系统
    equipment_system = EquipmentSystem(event_bus, data_manager)
    
    # 创建测试实体
    entity = Entity("测试角色", event_bus)
    entity.add_component(HealthComponent(owner=entity, event_bus=event_bus, hp=100, max_hp=100))
    entity.add_component(StatsComponent(attack=50, defense=30))
    entity.add_component(EquipmentComponent())
    
    # 收集日志
    logs = []
    def log_handler(event):
        logs.append(event.payload.message)
    
    event_bus.subscribe(EventName.LOG_REQUEST, log_handler)
    
    print("\n1. 测试装备铁剑")
    success = equipment_system.equip_item(entity, "iron_sword", "main_hand")
    print(f"装备结果: {success}")
    
    # 检查装备信息
    equipment_info = equipment_system.get_equipment_info(entity)
    print(f"装备信息: {equipment_info}")
    
    # 检查属性变化
    stats_comp = entity.get_component(StatsComponent)
    print(f"装备后属性: 攻击力 {stats_comp.attack:.1f}, 防御力 {stats_comp.defense:.1f}")
    
    print("\n2. 测试攻击损耗耐久")
    # 模拟攻击事件
    damage_payload = DamageRequestPayload(
        caster=entity,
        target=Entity("目标", event_bus),
        base_damage=50,
        original_base_damage=50,
        damage_type="physical",
        source_spell_id="test_spell",
        source_spell_name="测试技能"
    )
    event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, damage_payload))
    
    # 检查耐久度变化
    equipment_info = equipment_system.get_equipment_info(entity)
    print(f"攻击后装备信息: {equipment_info}")
    
    print("\n3. 测试装备皮甲")
    success = equipment_system.equip_item(entity, "leather_armor", "chest")
    print(f"装备皮甲结果: {success}")
    
    equipment_info = equipment_system.get_equipment_info(entity)
    print(f"装备皮甲后信息: {equipment_info}")
    
    stats_comp = entity.get_component(StatsComponent)
    print(f"装备皮甲后属性: 攻击力 {stats_comp.attack:.1f}, 防御力 {stats_comp.defense:.1f}")
    
    print("\n4. 测试被攻击损耗耐久")
    # 模拟被攻击事件
    damage_payload = DamageRequestPayload(
        caster=Entity("攻击者", event_bus),
        target=entity,
        base_damage=30,
        original_base_damage=30,
        damage_type="physical",
        source_spell_id="test_spell",
        source_spell_name="测试技能"
    )
    event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, damage_payload))
    
    equipment_info = equipment_system.get_equipment_info(entity)
    print(f"被攻击后装备信息: {equipment_info}")
    
    print("\n5. 测试装备耐久度耗尽")
    # 快速损耗铁剑耐久度
    equipment_comp = entity.get_component(EquipmentComponent)
    iron_sword = equipment_comp.get_equipped_item("main_hand")
    if iron_sword:
        # 直接设置耐久度为1，然后攻击一次
        iron_sword.current_durability = 1
        print(f"设置铁剑耐久度为1")
        
        # 再次攻击
        damage_payload = DamageRequestPayload(
            caster=entity,
            target=Entity("目标", event_bus),
            base_damage=50,
            original_base_damage=50,
            damage_type="physical",
            source_spell_id="test_spell",
            source_spell_name="测试技能"
        )
        event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, damage_payload))
        
        equipment_info = equipment_system.get_equipment_info(entity)
        print(f"耐久耗尽后装备信息: {equipment_info}")
        
        stats_comp = entity.get_component(StatsComponent)
        print(f"耐久耗尽后属性: 攻击力 {stats_comp.attack:.1f}, 防御力 {stats_comp.defense:.1f}")
    
    print("\n6. 测试装备力量戒指")
    success = equipment_system.equip_item(entity, "strength_ring", "ring")
    print(f"装备戒指结果: {success}")
    
    equipment_info = equipment_system.get_equipment_info(entity)
    print(f"装备戒指后信息: {equipment_info}")
    
    print("\n7. 测试回合损耗耐久")
    # 模拟回合开始事件
    turn_payload = TurnStartPayload(entity=entity)
    event_bus.dispatch(GameEvent(EventName.TURN_START, turn_payload))
    
    equipment_info = equipment_system.get_equipment_info(entity)
    print(f"回合开始后装备信息: {equipment_info}")
    
    print("\n8. 测试卸下装备")
    unequipped_item = equipment_system.unequip_item(entity, "chest")
    print(f"卸下装备: {unequipped_item.name if unequipped_item else None}")
    
    equipment_info = equipment_system.get_equipment_info(entity)
    print(f"卸下装备后信息: {equipment_info}")
    
    stats_comp = entity.get_component(StatsComponent)
    print(f"卸下装备后属性: 攻击力 {stats_comp.attack:.1f}, 防御力 {stats_comp.defense:.1f}")
    
    print("\n=== 测试日志 ===")
    for log in logs:
        print(log)

if __name__ == "__main__":
    test_equipment_system() 