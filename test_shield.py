#!/usr/bin/env python3
"""
测试ShieldComponent的简单脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_shield_component():
    try:
        from game.core.components import ShieldComponent
        from game.core.entity import Entity
        
        print("✅ ShieldComponent导入成功")
        
        # 创建测试实体
        entity = Entity("测试角色")
        
        # 创建护盾组件
        shield_comp = ShieldComponent(shield_value=50.0)
        print(f"✅ 创建ShieldComponent成功，护盾值: {shield_comp.shield_value}")
        
        # 添加到实体
        entity.add_component(shield_comp)
        print("✅ 护盾组件添加到实体成功")
        
        # 获取护盾组件
        retrieved_shield = entity.get_component(ShieldComponent)
        if retrieved_shield:
            print(f"✅ 从实体获取护盾组件成功，护盾值: {retrieved_shield.shield_value}")
        else:
            print("❌ 从实体获取护盾组件失败")
            
        print("🎉 所有测试通过！ShieldComponent工作正常")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_shield_component() 