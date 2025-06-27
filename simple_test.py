#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_imports():
    """测试基本导入"""
    try:
        print("测试基本导入...")
        
        # 测试核心模块
        from game.core.event_bus import EventBus, GameEvent
        print("✓ EventBus 导入成功")
        
        from game.core.enums import EventName
        print("✓ EventName 导入成功")
        
        from game.core.entity import Entity
        print("✓ Entity 导入成功")
        
        from game.core.components import HealthComponent
        print("✓ HealthComponent 导入成功")
        
        from game.core.payloads import LogRequestPayload
        print("✓ LogRequestPayload 导入成功")
        
        # 测试数据管理器
        from game.systems.data_manager import DataManager
        print("✓ DataManager 导入成功")
        
        # 测试世界
        from game.world import World
        print("✓ World 导入成功")
        
        return True
        
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_functionality():
    """测试基本功能"""
    try:
        print("\n测试基本功能...")
        
        # 创建事件总线
        from game.core.event_bus import EventBus, GameEvent
        from game.core.enums import EventName
        from game.core.payloads import LogRequestPayload
        
        event_bus = EventBus()
        print("✓ EventBus 创建成功")
        
        # 创建事件
        event = GameEvent(EventName.LOG_REQUEST, LogRequestPayload("TEST", "测试消息"))
        print("✓ GameEvent 创建成功")
        
        # 创建实体
        from game.core.entity import Entity
        entity = Entity("测试实体")
        print("✓ Entity 创建成功")
        
        # 创建数据管理器
        from game.systems.data_manager import DataManager
        data_manager = DataManager()
        print("✓ DataManager 创建成功")
        
        # 测试数据加载
        data_manager.load_spell_data()
        data_manager.load_status_effect_data()
        print("✓ 数据加载成功")
        
        return True
        
    except Exception as e:
        print(f"✗ 功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始测试...")
    
    if test_basic_imports():
        print("基本导入测试通过!")
    else:
        print("基本导入测试失败!")
        sys.exit(1)
    
    if test_basic_functionality():
        print("基本功能测试通过!")
    else:
        print("基本功能测试失败!")
        sys.exit(1)
    
    print("\n所有测试通过!") 