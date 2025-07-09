from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar, Generic
from .entity import Entity
T = TypeVar('T')

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
            if hasattr(context, 'is_cancelled') and context.is_cancelled:
                break
            context = processor.process(context)
        return context


# from abc import ABC, abstractmethod
# from typing import List, Any, Dict
# from game.core.entity import Entity

# class EffectExecutionContext:
#     def __init__(self, source: 'Entity', target: 'Entity', effect_type: str, initial_value: float, **kwargs):
#         self.source = source
#         self.target = target
#         self.effect_type = effect_type
#         self.initial_value = float(initial_value)
#         self.current_value = float(initial_value)
#         self.is_cancelled: bool = False
#         self.metadata: Dict[str, Any] = {}
#         self.metadata.update(kwargs)

#     def cancel_effect(self):
#         self.is_cancelled = True
#         self.current_value = 0

# class Processor(ABC):
#     @abstractmethod
#     def process(self, context: EffectExecutionContext) -> None:
#         pass

# class Pipeline:
#     def __init__(self, processors: List[Processor]):
#         self._processors = processors

#     def execute(self, context: EffectExecutionContext) -> EffectExecutionContext:
#         for processor in self._processors:
#             processor.process(context)
#             if context.is_cancelled:
#                 break
#         return context