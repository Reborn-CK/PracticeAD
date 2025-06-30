#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("开始测试...")
    
    from game.core.event_bus import EventBus, GameEvent
    from game.core.entity import Entity
    from game.core.components import HealthComponent, StatusEffectContainerComponent
    from game.systems.data_manager import DataManager
    from game.status_effects.status_effect_factory import StatusEffectFactory
    from game.systems.interaction_system import InteractionSystem
    from game.systems.combat.combat_resolution_system import CombatResolutionSystem
    from game.systems.spell_cast_system import SpellCastSystem
    from game.core.enums import EventName
    from game.core.payloads import CastSpellRequestPayload, ApplyStatusEffectRequestPayload
    
    print("✓ 所有导入成功")
    
    # 初始化系统
    event_bus = EventBus()
    data_manager = DataManager()
    data_manager.load_spell_data()
    data_manager.load_status_effect_data()
    
    status_effect_factory = StatusEffectFactory(data_manager)
    interaction_system = InteractionSystem(event_bus, data_manager, status_effect_factory)
    combat_system = CombatResolutionSystem(event_bus, data_manager)
    spell_cast_system = SpellCastSystem(event_bus, data_manager, status_effect_factory)
    
    print("✓ 系统初始化成功")
    
    # 创建测试实体
    player = Entity("测试玩家")
    player.add_component(HealthComponent(player, event_bus, hp=100, max_hp=100))
    player.add_component(StatusEffectContainerComponent())
    
    enemy = Entity("测试敌人")
    enemy.add_component(HealthComponent(enemy, event_bus, hp=200, max_hp=200))
    enemy.add_component(StatusEffectContainerComponent())
    
    print("✓ 实体创建成功")
    
    # 测试雪球术
    print("\n测试雪球术...")
    event_bus.dispatch(GameEvent(EventName.CAST_SPELL_REQUEST, CastSpellRequestPayload(
        caster=player,
        target=enemy,
        spell_id="snowball_01"
    )))
    
    print(f"敌人最终HP: {enemy.get_component(HealthComponent).hp}")
    print("测试完成！")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc() 