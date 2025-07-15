from typing import Optional, Set
from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import LogRequestPayload

class LogSystem:
    """ <<< 升级: 日志系统支持隐藏功能 >>>
    负责接收并打印所有带标签的内部日志，供开发者调试使用。
    支持全局开关和按标签过滤。
    """
    def __init__(self, event_bus: EventBus, enabled: bool = True, hidden_tags: Optional[Set[str]] = None):
        self.event_bus = event_bus
        self.enabled = enabled  # 全局开关
        self.hidden_tags = hidden_tags or set()  # 隐藏的标签集合
        self.event_bus.subscribe(EventName.LOG_REQUEST, self.on_log_request)
    
    def set_enabled(self, enabled: bool):
        """设置日志系统是否启用"""
        self.enabled = enabled
    
    def hide_tag(self, tag: str):
        """隐藏指定标签的日志"""
        self.hidden_tags.add(tag)
    
    def show_tag(self, tag: str):
        """显示指定标签的日志"""
        self.hidden_tags.discard(tag)
    
    def hide_all_tags(self):
        """隐藏所有标签的日志"""
        self.hidden_tags.clear()
        self.enabled = False
    
    def show_all_tags(self):
        """显示所有标签的日志"""
        self.hidden_tags.clear()
        self.enabled = True
    
    def on_log_request(self, event: GameEvent):
        payload: LogRequestPayload = event.payload
        
        # 检查是否应该打印这条日志
        if not self.enabled:
            return
        
        if payload.tag in self.hidden_tags:
            return
        
        print(f"[{payload.tag}] {payload.message}")