#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import traceback

def test_imports():
    """测试所有模块的导入"""
    modules_to_test = [
        "game.core.event_bus",
        "game.core.enums", 
        "game.core.entity",
        "game.core.components",
        "game.core.payloads",
        "game.systems.data_manager",
        "game.systems.log_system",
        "game.systems.ui_system",
        "game.systems.turn_manager_system",
        "game.systems.player_input_system",
        "game.systems.enemy_ai_system",
        "game.systems.spell_cast_system",
        "game.systems.mana_system",
        "game.systems.passive_ability_system",
        "game.systems.combat.combat_resolution_system",
        "game.systems.dead_system",
        "game.status_effects.status_effect",
        "game.status_effects.effect_logic"
    ]
    
    failed_imports = []
    
    for module_name in modules_to_test:
        try:
            print(f"测试导入: {module_name}")
            __import__(module_name)
            print(f"✓ {module_name} 导入成功")
        except Exception as e:
            print(f"✗ {module_name} 导入失败: {e}")
            print(f"  错误详情: {traceback.format_exc()}")
            failed_imports.append((module_name, e))
    
    if failed_imports:
        print(f"\n导入失败的模块数量: {len(failed_imports)}")
        for module_name, error in failed_imports:
            print(f"  - {module_name}: {error}")
        return False
    else:
        print("\n所有模块导入成功!")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1) 