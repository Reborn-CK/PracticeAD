#!/usr/bin/env python3
"""
游戏运行脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        print("启动游戏...")
        from game.main import main as game_main
        game_main()
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保所有依赖都已安装")
    except Exception as e:
        print(f"运行错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()