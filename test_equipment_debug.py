#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
装备系统调试测试
测试装备被摧毁后角色基础属性是否正确保持
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game.core.event_bus import EventBus
from game.core.entity import Entity
from game.core.components import (HealthComponent, ManaComponent, SpeedComponent, 
                                 SpellListComponent, ShieldComponent, StatusEffectContainerComponent,
                                 StatsComponent, EquipmentComponent, EquipmentItem)
from game.systems.data_manager import DataManager
from game.systems.equipment_system import EquipmentSystem
from game.systems.character_factory import CharacterFactory
from game.world import World

def test_equipment_destruction():
    """测试装备被摧毁后角色属性保持"""
    print("=== 装备系统调试测试 ===")
    
    # 初始化系统
    event_bus = EventBus()
    data_manager = DataManager()
    world = World(event_bus)
    
    # 加载数据
    data_manager.load_character_data()
    data_manager.load_equipment_data()
    
    # 创建装备系统
    equipment_system = EquipmentSystem(event_bus, data_manager)
    
    # 创建角色工厂
    character_factory = CharacterFactory(event_bus, data_manager)
    
    # 创建角色
    hero = character_factory.create_character("hero", world)
    
    print(f"\n1. 角色创建完成: {hero.name}")
    
    # 获取初始属性
    stats_comp = hero.get_component(StatsComponent)
    equipment_comp = hero.get_component(EquipmentComponent)
    
    print(f"   基础攻击力: {stats_comp._base_attack}")
    print(f"   基础防御力: {stats_comp._base_defense}")
    print(f"   当前攻击力: {stats_comp.attack}")
    print(f"   当前防御力: {stats_comp.defense}")
    
    # 检查装备
    equipped_items = equipment_comp.get_all_equipped_items()
    print(f"   已装备物品数量: {len(equipped_items)}")
    
    if equipped_items:
        for item in equipped_items:
            print(f"   - {item.name}: 耐久度 {item.current_durability}/{item.max_durability}")
    
    # 模拟装备被摧毁
    print(f"\n2. 模拟装备被摧毁...")
    
    # 手动摧毁所有装备
    destroyed_items = []
    for equipment_item in equipped_items:
        # 直接设置耐久度为0
        equipment_item.current_durability = 0
        destroyed_items.append(equipment_item)
        print(f"   💥 {equipment_item.name} 被摧毁")
    
    # 移除被摧毁的装备
    for destroyed_item in destroyed_items:
        for slot, equipment_id in equipment_comp.equipment_slots.items():
            if equipment_id == destroyed_item.equipment_id:
                equipment_comp.unequip_item(slot)
                break
    
    # 更新角色属性
    equipment_system._update_entity_stats(hero)
    
    print(f"\n3. 装备摧毁后的属性:")
    print(f"   基础攻击力: {stats_comp._base_attack}")
    print(f"   基础防御力: {stats_comp._base_defense}")
    print(f"   当前攻击力: {stats_comp.attack}")
    print(f"   当前防御力: {stats_comp.defense}")
    
    # 验证基础属性是否保持
    if stats_comp.attack == stats_comp._base_attack and stats_comp.defense == stats_comp._base_defense:
        print(f"   ✅ 测试通过: 装备被摧毁后，角色属性正确回归到基础值")
    else:
        print(f"   ❌ 测试失败: 装备被摧毁后，角色属性没有正确回归到基础值")
        print(f"      期望攻击力: {stats_comp._base_attack}, 实际攻击力: {stats_comp.attack}")
        print(f"      期望防御力: {stats_comp._base_defense}, 实际防御力: {stats_comp.defense}")
    
    # 测试重新装备
    print(f"\n4. 测试重新装备...")
    
    # 重新装备铁剑
    success = equipment_system.equip_item(hero, "iron_sword", "main_hand")
    if success:
        print(f"   ✅ 重新装备铁剑成功")
        print(f"   当前攻击力: {stats_comp.attack}")
        print(f"   当前防御力: {stats_comp.defense}")
    else:
        print(f"   ❌ 重新装备铁剑失败")
    
    print(f"\n=== 测试完成 ===")

if __name__ == "__main__":
    test_equipment_destruction()