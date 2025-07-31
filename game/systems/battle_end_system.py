#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import UIMessagePayload
from ..core.components import BattlefieldComponent, TeamComponent, DeadComponent
from ..core.entity import Entity

class BattleEndSystem:
    """战斗结束系统，处理战场完成后的逻辑"""
    
    def __init__(self, event_bus: EventBus, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.world = world
        
        # 订阅战场完成事件
        self.event_bus.subscribe(EventName.BATTLEFIELD_COMPLETE, self.on_battlefield_complete)
    
    def on_battlefield_complete(self, event: GameEvent):
        """处理战场完成事件"""
        payload = event.payload
        battlefield_id = payload.get("battlefield_id")
        result = payload.get("result")  # "victory" 或 "defeat"
        
        if result == "victory":
            self.handle_victory(battlefield_id)
        elif result == "defeat":
            self.handle_defeat(battlefield_id)
        
        # 清理战场实体
        self.cleanup_battlefield()
        
        # 显示游戏结束信息
        self.show_game_end_message(result)
    
    def handle_victory(self, battlefield_id: str):
        """处理胜利逻辑"""
        self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
            "🎉 **恭喜！战斗胜利！** 🎉\n"
            "你成功击败了所有敌人！\n"
            "游戏结束。"
        )))
    
    def handle_defeat(self, battlefield_id: str):
        """处理失败逻辑"""
        self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
            "💀 **战斗失败！** 💀\n"
            "你的队伍被击败了。\n"
            "游戏结束。"
        )))
    
    def cleanup_battlefield(self):
        """清理战场实体"""
        # 移除所有实体（除了系统实体）
        entities_to_remove = []
        
        for entity in self.world.entities:
            # 保留系统实体，移除游戏实体
            if not entity.name.startswith("System_"):
                entities_to_remove.append(entity)
        
        for entity in entities_to_remove:
            self.world.remove_entity(entity)
        
        print(f"[BATTLE_END] 清理了 {len(entities_to_remove)} 个实体")
    
    def show_game_end_message(self, result: str):
        """显示游戏结束信息"""
        if result == "victory":
            message = (
                "🏆 **游戏胜利！** 🏆\n"
                "感谢你完成了这场战斗！\n"
                "你可以重新开始游戏来体验更多内容。"
            )
        else:
            message = (
                "😔 **游戏结束** 😔\n"
                "虽然这次失败了，但不要气馁！\n"
                "你可以重新开始游戏，尝试不同的策略。"
            )
        
        self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(message))) 