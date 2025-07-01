#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试状态效果伤害不计算反伤
验证所有状态效果的持续伤害都正确设置为is_reflection=False
"""

def test_status_effect_reflection():
    """测试状态效果伤害不计算反伤"""
    print("=== 测试状态效果伤害不计算反伤 ===")
    
    print("🔍 检查内容:")
    print("   1. 燃烧效果的持续伤害")
    print("   2. 中毒效果的持续伤害")
    print("   3. 中毒回合结算的伤害")
    print("   4. 毒爆术的伤害")
    print()
    
    # 测试DamageOverTimeEffect（燃烧等）
    print("1. 检查DamageOverTimeEffect...")
    try:
        from game.status_effects.effect_logic import DamageOverTimeEffect
        print("   ✅ DamageOverTimeEffect 导入成功")
        
        # 检查on_tick方法中的is_reflection设置
        import inspect
        source = inspect.getsource(DamageOverTimeEffect.on_tick)
        if "is_reflection=False" in source:
            print("   ✅ 燃烧等持续伤害已设置为不计算反伤")
        else:
            print("   ❌ 燃烧等持续伤害未设置为不计算反伤")
            return False
    except Exception as e:
        print(f"   ❌ DamageOverTimeEffect 检查失败: {e}")
        return False
    
    # 测试PoisonDotEffect（中毒）
    print("\n2. 检查PoisonDotEffect...")
    try:
        from game.status_effects.effect_logic import PoisonDotEffect
        print("   ✅ PoisonDotEffect 导入成功")
        
        # 检查on_tick方法中的is_reflection设置
        import inspect
        source = inspect.getsource(PoisonDotEffect.on_tick)
        if "is_reflection=False" in source:
            print("   ✅ 中毒持续伤害已设置为不计算反伤")
        else:
            print("   ❌ 中毒持续伤害未设置为不计算反伤")
            return False
    except Exception as e:
        print(f"   ❌ PoisonDotEffect 检查失败: {e}")
        return False
    
    # 测试状态效果系统中的中毒结算
    print("\n3. 检查状态效果系统中的中毒结算...")
    try:
        from game.systems.status_effect_system import StatusEffectSystem
        print("   ✅ StatusEffectSystem 导入成功")
        
        # 检查on_round_start方法中的is_reflection设置
        import inspect
        source = inspect.getsource(StatusEffectSystem.on_round_start)
        if "is_reflection=False" in source:
            print("   ✅ 中毒回合结算已设置为不计算反伤")
        else:
            print("   ❌ 中毒回合结算未设置为不计算反伤")
            return False
    except Exception as e:
        print(f"   ❌ StatusEffectSystem 检查失败: {e}")
        return False
    
    # 测试毒爆术
    print("\n4. 检查毒爆术...")
    try:
        from game.systems.status_effect_system import StatusEffectSystem
        print("   ✅ 毒爆术检查开始")
        
        # 检查on_detonate_poison方法中的is_reflection设置
        import inspect
        source = inspect.getsource(StatusEffectSystem.on_detonate_poison)
        if "is_reflection=False" in source:
            print("   ✅ 毒爆术已设置为不计算反伤")
        else:
            print("   ❌ 毒爆术未设置为不计算反伤")
            return False
    except Exception as e:
        print(f"   ❌ 毒爆术检查失败: {e}")
        return False
    
    print("\n=== 所有检查通过 ===")
    print("✅ 所有状态效果伤害都正确设置为不计算反伤！")
    print()
    
    print("📋 验证结果:")
    print("   - 燃烧持续伤害: is_reflection=False ✅")
    print("   - 中毒持续伤害: is_reflection=False ✅")
    print("   - 中毒回合结算: is_reflection=False ✅")
    print("   - 毒爆术伤害: is_reflection=False ✅")
    print()
    
    print("🎯 设计理念:")
    print("   - 状态效果造成的伤害不应该触发反伤")
    print("   - 只有直接攻击才应该计算反伤")
    print("   - 这符合游戏逻辑和平衡性")
    
    return True

if __name__ == "__main__":
    test_status_effect_reflection() 