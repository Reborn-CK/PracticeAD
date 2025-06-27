#!/usr/bin/env python3
"""
测试项目结构是否正确
"""

import os
import sys

def test_imports():
    """测试所有关键模块的导入"""
    print("测试项目导入...")
    
    try:
        # 测试核心模块
        from game.core.event_bus import EventBus, GameEvent
        print("✓ EventBus 导入成功")
        
        from game.core.enums import EventName
        print("✓ EventName 导入成功")
        
        from game.core.payloads import DamageRequestPayload
        print("✓ Payloads 导入成功")
        
        from game.core.entity import Entity
        print("✓ Entity 导入成功")
        
        from game.core.components import HealthComponent
        print("✓ Components 导入成功")
        
        # 测试系统模块
        from game.systems.data_manager import DataManager
        print("✓ DataManager 导入成功")
        
        from game.systems.log_system import LogSystem
        print("✓ LogSystem 导入成功")
        
        from game.systems.ui_system import UISystem
        print("✓ UISystem 导入成功")
        
        from game.systems.status_effect_system import StatusEffectSystem
        print("✓ StatusEffectSystem 导入成功")
        
        from game.systems.interaction_system import InteractionSystem
        print("✓ InteractionSystem 导入成功")
        
        from game.systems.spell_cast_system import SpellCastSystem
        print("✓ SpellCastSystem 导入成功")
        
        from game.systems.combat.combat_resolution_system import CombatResolutionSystem
        print("✓ CombatResolutionSystem 导入成功")
        
        # 测试状态效果模块
        from game.status_effects.status_effect import StatusEffect
        print("✓ StatusEffect 导入成功")
        
        from game.status_effects.effect_logic import EffectLogic
        print("✓ EffectLogic 导入成功")
        
        # 测试世界模块
        from game.world import World
        print("✓ World 导入成功")
        
        print("\n🎉 所有模块导入成功！项目结构正确。")
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_data_files():
    """测试数据文件是否存在"""
    print("\n测试数据文件...")
    
    data_files = [
        "data/spells.yaml",
        "data/status_effects.yaml"
    ]
    
    all_exist = True
    for file_path in data_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} 存在")
        else:
            print(f"❌ {file_path} 不存在")
            all_exist = False
    
    return all_exist

def main():
    print("=" * 50)
    print("项目结构测试")
    print("=" * 50)
    
    # 测试导入
    imports_ok = test_imports()
    
    # 测试数据文件
    data_ok = test_data_files()
    
    print("\n" + "=" * 50)
    if imports_ok and data_ok:
        print("✅ 项目结构测试通过！")
        print("现在可以使用以下命令运行游戏：")
        print("python -m game.main")
    else:
        print("❌ 项目结构测试失败！")
        print("请检查上述错误并修复。")
    print("=" * 50)

if __name__ == "__main__":
    main() 