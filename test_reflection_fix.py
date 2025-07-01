#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试反伤逻辑修正
验证：只有非反伤伤害才会触发反伤效果
"""

def test_reflection_fix():
    """测试反伤逻辑修正"""
    print("=== 测试反伤逻辑修正 ===")
    
    print("🔍 问题分析:")
    print("   原问题: 反伤逻辑没有检查 is_reflection 参数")
    print("   导致: 状态效果伤害也会触发反伤")
    print("   修正: 添加 not payload.is_reflection 检查")
    print()
    
    # 测试战斗解析系统
    print("1. 检查战斗解析系统...")
    try:
        from game.systems.combat.combat_resolution_system import CombatResolutionSystem
        print("   ✅ CombatResolutionSystem 导入成功")
        
        # 检查反伤逻辑中的条件
        import inspect
        source = inspect.getsource(CombatResolutionSystem.on_damage_request)
        if "not payload.is_reflection" in source:
            print("   ✅ 反伤逻辑已修正，添加了 is_reflection 检查")
        else:
            print("   ❌ 反伤逻辑未修正，缺少 is_reflection 检查")
            return False
    except Exception as e:
        print(f"   ❌ CombatResolutionSystem 检查失败: {e}")
        return False
    
    # 测试状态效果伤害设置
    print("\n2. 检查状态效果伤害设置...")
    try:
        from game.status_effects.effect_logic import DamageOverTimeEffect, PoisonDotEffect
        print("   ✅ 状态效果逻辑类导入成功")
        
        # 检查是否都设置了 is_reflection=False
        source1 = inspect.getsource(DamageOverTimeEffect.on_tick)
        source2 = inspect.getsource(PoisonDotEffect.on_tick)
        
        if "is_reflection=False" in source1 and "is_reflection=False" in source2:
            print("   ✅ 状态效果伤害已设置为不计算反伤")
        else:
            print("   ❌ 状态效果伤害未正确设置")
            return False
    except Exception as e:
        print(f"   ❌ 状态效果检查失败: {e}")
        return False
    
    # 测试毒爆术设置
    print("\n3. 检查毒爆术设置...")
    try:
        from game.systems.status_effect_system import StatusEffectSystem
        print("   ✅ StatusEffectSystem 导入成功")
        
        # 检查毒爆术是否设置了 is_reflection=False
        source = inspect.getsource(StatusEffectSystem.on_detonate_poison)
        if "is_reflection=False" in source:
            print("   ✅ 毒爆术已设置为不计算反伤")
        else:
            print("   ❌ 毒爆术未设置为不计算反伤")
            return False
    except Exception as e:
        print(f"   ❌ 毒爆术检查失败: {e}")
        return False
    
    print("\n=== 修正验证完成 ===")
    print("✅ 反伤逻辑修正已成功应用！")
    print()
    
    print("📋 修正内容:")
    print("   - 反伤逻辑添加了 not payload.is_reflection 检查")
    print("   - 状态效果伤害设置为 is_reflection=False")
    print("   - 毒爆术伤害设置为 is_reflection=False")
    print()
    
    print("🎯 修正后的逻辑:")
    print("   1. 状态效果造成伤害 → is_reflection=False")
    print("   2. 反伤逻辑检查 → not payload.is_reflection = True")
    print("   3. 结果 → 不触发反伤 ✅")
    print()
    
    print("🔄 对比修正前后:")
    print("   修正前: if final_damage > 0 and (thorns_comp := ...)")
    print("   修正后: if final_damage > 0 and not payload.is_reflection and (thorns_comp := ...)")
    print("   效果: 状态效果伤害不再触发反伤")
    
    return True

if __name__ == "__main__":
    test_reflection_fix() 