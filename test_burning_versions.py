#!/usr/bin/env python3
"""
测试燃烧效果的多版本堆叠逻辑
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_burning_versions():
    """测试燃烧效果的多版本堆叠逻辑"""
    print("测试燃烧效果的多版本堆叠逻辑...")
    
    try:
        from game.core.event_bus import EventBus
        from game.core.enums import EventName
        from game.core.event_bus import GameEvent
        from game.core.entity import Entity
        from game.core.components import StatusEffectContainerComponent, HealthComponent
        from game.systems.data_manager import DataManager
        from game.status_effects.status_effect_factory import StatusEffectFactory
        from game.systems.status_effect_system import StatusEffectSystem
        from game.world import World
        from game.core.payloads import ApplyStatusEffectRequestPayload
        
        # 初始化系统
        event_bus = EventBus()
        world = World(event_bus)
        data_manager = DataManager()
        status_effect_factory = StatusEffectFactory(data_manager)
        status_effect_system = StatusEffectSystem(event_bus, world)
        
        # 加载数据
        data_manager.load_status_effect_data()
        
        # 创建测试实体
        test_entity = Entity("测试实体")
        test_entity.add_component(HealthComponent(test_entity, event_bus, 100, 100))
        test_entity.add_component(StatusEffectContainerComponent())
        world.add_entity(test_entity)
        
        print(f"\n测试实体初始状态:")
        print(f"  生命值: {test_entity.get_component(HealthComponent).hp}")
        
        # 测试1: 应用 burning_01
        print(f"\n=== 测试1: 应用 burning_01 ===")
        burning_01 = status_effect_factory.create_effect("burning_01")
        if burning_01:
            event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, 
                ApplyStatusEffectRequestPayload(target=test_entity, effect=burning_01)))
            print(f"✓ 应用 burning_01 成功")
        else:
            print(f"✗ 创建 burning_01 失败")
        
        # 显示当前状态效果
        container = test_entity.get_component(StatusEffectContainerComponent)
        print(f"当前状态效果:")
        for effect in container.effects:
            print(f"  - {effect.effect_id}: {effect.name} (持续时间: {effect.duration})")
        
        # 测试2: 再次应用 burning_01（应该刷新时间）
        print(f"\n=== 测试2: 再次应用 burning_01（应该刷新时间）===")
        burning_01_again = status_effect_factory.create_effect("burning_01")
        if burning_01_again:
            event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, 
                ApplyStatusEffectRequestPayload(target=test_entity, effect=burning_01_again)))
            print(f"✓ 再次应用 burning_01 成功")
        else:
            print(f"✗ 创建 burning_01 失败")
        
        # 显示当前状态效果
        print(f"当前状态效果:")
        for effect in container.effects:
            print(f"  - {effect.effect_id}: {effect.name} (持续时间: {effect.duration})")
        
        # 测试3: 应用 burning_02（应该创建新效果）
        print(f"\n=== 测试3: 应用 burning_02（应该创建新效果）===")
        burning_02 = status_effect_factory.create_effect("burning_02")
        if burning_02:
            event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, 
                ApplyStatusEffectRequestPayload(target=test_entity, effect=burning_02)))
            print(f"✓ 应用 burning_02 成功")
        else:
            print(f"✗ 创建 burning_02 失败")
        
        # 显示当前状态效果
        print(f"当前状态效果:")
        for effect in container.effects:
            print(f"  - {effect.effect_id}: {effect.name} (持续时间: {effect.duration})")
        
        # 测试4: 再次应用 burning_02（应该刷新时间）
        print(f"\n=== 测试4: 再次应用 burning_02（应该刷新时间）===")
        burning_02_again = status_effect_factory.create_effect("burning_02")
        if burning_02_again:
            event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, 
                ApplyStatusEffectRequestPayload(target=test_entity, effect=burning_02_again)))
            print(f"✓ 再次应用 burning_02 成功")
        else:
            print(f"✗ 创建 burning_02 失败")
        
        # 显示当前状态效果
        print(f"当前状态效果:")
        for effect in container.effects:
            print(f"  - {effect.effect_id}: {effect.name} (持续时间: {effect.duration})")
        
        # 测试5: 回合结算
        print(f"\n=== 测试5: 回合结算 ===")
        event_bus.dispatch(GameEvent(EventName.ROUND_START, None))
        
        # 显示回合后的状态
        print(f"回合后的状态:")
        print(f"  生命值: {test_entity.get_component(HealthComponent).hp}")
        print(f"  剩余状态效果:")
        for effect in container.effects:
            print(f"    - {effect.effect_id}: {effect.name} (持续时间: {effect.duration})")
        
        print(f"\n✓ 燃烧效果多版本堆叠测试完成!")
        return True
        
        # 测试6: 回合结算
        print(f"\n=== 测试6: 叠加回合结算 ===")
        event_bus.dispatch(GameEvent(EventName.ROUND_START, None))
        
        # 显示回合后的状态
        print(f"回合后的状态:")
        print(f"  生命值: {test_entity.get_component(HealthComponent).hp}")
        print(f"  剩余状态效果:")
        for effect in container.effects:
            print(f"    - {effect.effect_id}: {effect.name} (持续时间: {effect.duration})")
        
        print(f"\n✓ 燃烧效果多版本堆叠测试完成!")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_burning_versions() 