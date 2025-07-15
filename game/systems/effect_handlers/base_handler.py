from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ...core.entity import Entity
    from ...core.event_bus import EventBus
    from ..data_manager import DataManager
    from ...core.payloads import EffectResolutionPayload

class EffectHandler(ABC):
    """效果处理器的抽象基类"""

    def __init__(self, event_bus: 'EventBus', data_manager: 'DataManager', world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.world = world

    @abstractmethod
    def apply(self, caster: 'Entity', target: 'Entity', effect: Dict[str, Any], payload: 'EffectResolutionPayload'):
        """
        应用法术效果的抽象方法。

        :param caster: 施法者实体
        :param target: 目标实体
        :param effect: 从 data/spells.yaml 中读取的效果数据字典
        :param payload: 用于记录效果解析结果的负载对象
        """
        pass