from abc import ABC, abstractmethod
from typing import List, Any, Dict
from game.core.entity import Entity

class EffectExecutionContext:
    def __init__(self, source: 'Entity', target: 'Entity', effect_type: str, initial_value: float, **kwargs):
        self.source = source
        self.target = target
        self.effect_type = effect_type
        self.initial_value = float(initial_value)
        self.current_value = float(initial_value)
        self.is_cancelled: bool = False
        self.metadata: Dict[str, Any] = {}
        self.metadata.update(kwargs)

    def cancel_effect(self):
        self.is_cancelled = True
        self.current_value = 0

class Processor(ABC):
    @abstractmethod
    def process(self, context: EffectExecutionContext) -> None:
        pass

class Pipeline:
    def __init__(self, processors: List[Processor]):
        self._processors = processors

    def execute(self, context: EffectExecutionContext) -> EffectExecutionContext:
        for processor in self._processors:
            processor.process(context)
            if context.is_cancelled:
                break
        return context