# 测试Python语法高亮
from typing import Optional, List, Dict, Any

class TestClass:
    def __init__(self, name: Optional[str] = None):
        self.name = name
        self.is_active = True
        self.is_visible = False
        self.count = 0
        
    def test_method(self, param: Optional[str] = None) -> bool:
        if param is None:
            return False
        elif param == "":
            return True
        else:
            return len(param) > 0
    
    def test_control_flow(self, items: List[str]) -> None:
        for item in items:
            if item is None:
                continue
            elif item == "":
                break
            else:
                print(f"Processing: {item}")
        
        while self.count < 10:
            self.count += 1
            if self.count == 5:
                break
        
        try:
            result = self.test_method("test")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            print("Cleanup")

# 测试常量
NONE_VALUE = None
TRUE_VALUE = True
FALSE_VALUE = False

# 测试逻辑操作
result = TRUE_VALUE and FALSE_VALUE
result = TRUE_VALUE or FALSE_VALUE
result = not FALSE_VALUE

# 测试比较
if result is None:
    print("Result is None")
elif result is True:
    print("Result is True")
elif result is False:
    print("Result is False") 