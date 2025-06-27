#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("测试导入 StatusEffectFactory...")
    from game.status_effects.status_effect_factory import StatusEffectFactory
    print("✓ StatusEffectFactory 导入成功")
    
    print("测试导入 DataManager...")
    from game.systems.data_manager import DataManager
    print("✓ DataManager 导入成功")
    
    print("测试创建实例...")
    data_manager = DataManager()
    factory = StatusEffectFactory(data_manager)
    print("✓ 实例创建成功")
    
    print("所有导入测试通过！")
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ 其他错误: {e}")
    import traceback
    traceback.print_exc() 