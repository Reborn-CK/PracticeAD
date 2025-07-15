from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar, Generic, Protocol, TYPE_CHECKING
from .entity import Entity

if TYPE_CHECKING:
    from .entity import Entity

class CancellableContext(Protocol):
    """定义了可取消上下文对象的协议"""
    is_cancelled: bool

T = TypeVar('T', bound=CancellableContext)

class EffectExecutionContext:
    """
    一个封装了效果处理所需所有信息的上下文对象。
    它在管线中的处理器之间传递。
    """
    def __init__(self, source: 'Entity', target: 'Entity', effect_type: str, initial_value: float, **kwargs):
        self.source = source
        self.target = target
        self.effect_type = effect_type      # 'damage' 或 'heal'
        self.initial_value = initial_value  # 初始伤害/治疗值
        self.current_value = initial_value  # 在管线中流动和修改的值
        self.metadata = kwargs              # 一个字典，存放所有额外信息
        self.is_cancelled: bool = False     # 处理器可以调用此标志来中止后续流程

        self.overheal_amount: float = 0.0

    def cancel(self):
        """中止管线的后续执行。"""
        self.is_cancelled = True

class Processor(ABC, Generic[T]):
    """
    管线中处理器的抽象基类。
    """
    @abstractmethod
    def process(self, context: T) -> T:
        """
        处理上下文对象。
        处理器应该读取 context.current_value，进行计算，然后更新它。
        """
        pass

class Pipeline(Generic[T]):
    """
    一个管线，它按顺序执行一系列处理器。
    """
    def __init__(self, processors: list[Processor[T]]):
        self.processors = processors

    def execute(self, context: T) -> T:
        """
        执行管线。
        """
        for processor in self.processors:
            if context.is_cancelled:  # 现在类型检查器知道 context 有 is_cancelled 属性
                break
            context = processor.process(context)
        return context