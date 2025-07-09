#!/usr/bin/env python3
"""
测试净化3技能的脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_purify3():
    try:
        from game.core.event_bus import EventBus
        from game.core.enums import EventName
        from game.core.event_bus import GameEvent
        from game.core.payloads import CastSpellRequestPayload, ApplyStatusEffectRequestPayload
        from game.core.entity import Entity
        from game.core.components import HealthComponent, ManaComponent, StatusEffectContainerComponent
        from game.systems.data_manager import DataManager
        from game.systems.spell_cast_system import SpellCastSystem
        from game.status_effects.status_effect_factory import StatusEffectFactory
        from game.systems.status_effect_system import StatusEffectSystem
        from game.systems.mana_system import ManaSystem
        from game.world import World
        
        print("测试净化3技能...")
        
        # 创建事件总线
        event_bus = EventBus()
        
        # 创建测试实体
        test_entity = Entity("测试角色")
        test_entity.add_component(HealthComponent(test_entity, event_bus, 100, 100))
        test_entity.add_component(ManaComponent(500, 500))
        test_entity.add_component(StatusEffectContainerComponent())
        
        # 创建系统
        world = World(event_bus)
        world.add_entity(test_entity)
        
        data_manager = DataManager()
        data_manager.load_spell_data()
        data_manager.load_status_effect_data()
        status_effect_factory = StatusEffectFactory(data_manager)
        spell_cast_system = SpellCastSystem(event_bus, data_manager, status_effect_factory)
        status_effect_system = StatusEffectSystem(event_bus, world)
        mana_system = ManaSystem(event_bus)
        
        # 添加一些负面状态效果
        print("添加负面状态效果...")
        
        # 添加燃烧效果
        burning_effect = status_effect_factory.create_effect("burning_01", test_entity)
        if burning_effect:
            event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, ApplyStatusEffectRequestPayload(
                target=test_entity,
                effect=burning_effect
            )))
        
        # 添加中毒效果
        poison_effect = status_effect_factory.create_effect("poison_01", test_entity)
        if poison_effect:
            event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, ApplyStatusEffectRequestPayload(
                target=test_entity,
                effect=poison_effect
            )))
        
        # 添加缓慢效果
        slow_effect = status_effect_factory.create_effect("speedup_01", test_entity)
        if slow_effect:
            event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, ApplyStatusEffectRequestPayload(
                target=test_entity,
                effect=slow_effect
            )))
        
        # 检查状态效果
        container = test_entity.get_component(StatusEffectContainerComponent)
        print(f"施放净化3前，状态效果数量: {len(container.effects)}")
        for effect in container.effects:
            print(f"  - {effect.name}: 持续时间={effect.duration}, 层数={getattr(effect, 'stack_count', 'N/A')}")
        
        # 施放净化3
        print("\n施放净化3...")
        event_bus.dispatch(GameEvent(EventName.CAST_SPELL_REQUEST, CastSpellRequestPayload(
            caster=test_entity,
            target=test_entity,
            spell_id="dispel_01"
        )))
        
        # 检查净化后的状态效果
        print(f"\n施放净化3后，状态效果数量: {len(container.effects)}")
        for effect in container.effects:
            print(f"  - {effect.name}: 持续时间={effect.duration}, 层数={getattr(effect, 'stack_count', 'N/A')}")
        
        print("\n测试完成！")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_purify3() 