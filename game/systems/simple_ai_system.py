#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import ActionRequestPayload, CastSpellRequestPayload
from ..core.components import (AIComponent, TeamComponent, HealthComponent, 
                              SpellListComponent, UltimateSpellListComponent,
                              DeadComponent)
from ..core.entity import Entity
from ..systems.data_manager import DataManager

@dataclass
class SimpleAIDecision:
    """简化的AI决策结果"""
    spell_id: str
    target_entity: Entity

class SimpleEnemyAISystem:
    """简化的敌人AI系统"""
    
    def __init__(self, event_bus: EventBus, data_manager: DataManager, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.world = world
        
        # 订阅相关事件
        self.event_bus.subscribe(EventName.ACTION_REQUEST, self.on_action_request)
    
    def on_action_request(self, event: GameEvent):
        """处理行动请求事件"""
        payload: ActionRequestPayload = event.payload
        acting_entity = payload.acting_entity
        
        # 检查是否是敌人且具有AI组件
        if (acting_entity.has_component(TeamComponent) and 
            acting_entity.get_component(TeamComponent).team_id == "enemy" and
            acting_entity.has_component(AIComponent)):
            
            # 生成简单的AI决策
            decision = self.generate_simple_decision(acting_entity)
            if decision:
                # 执行AI决策
                self.execute_simple_decision(acting_entity, decision)
    
    def generate_simple_decision(self, enemy: Entity) -> Optional[SimpleAIDecision]:
        """生成简单的AI决策"""
        # 获取可用技能
        available_spells = self.get_available_spells(enemy)
        
        if not available_spells:
            return None
        
        # 获取敌人目标
        target = self.get_simple_target(enemy)
        
        if not target:
            return None
        
        # 选择第一个可用技能
        spell_id = available_spells[0]
        
        return SimpleAIDecision(
            spell_id=spell_id,
            target_entity=target
        )
    
    def get_available_spells(self, entity: Entity) -> List[str]:
        """获取可用技能列表"""
        spells = []
        
        # 普通技能
        spell_comp = entity.get_component(SpellListComponent)
        if spell_comp:
            spells.extend(spell_comp.spells)
        
        # 终极技能
        ultimate_comp = entity.get_component(UltimateSpellListComponent)
        if ultimate_comp:
            spells.extend(ultimate_comp.ultimate_spells)
        
        return spells
    
    def get_simple_target(self, enemy: Entity) -> Optional[Entity]:
        """获取简单的目标"""
        # 获取所有存活的玩家实体
        alive_players = [e for e in self.world.entities 
                        if e.has_component(TeamComponent) and 
                        e.get_component(TeamComponent).team_id == "player" and
                        not e.has_component(DeadComponent)]
        
        # 返回第一个玩家
        return alive_players[0] if alive_players else None
    
    def execute_simple_decision(self, enemy: Entity, decision: SimpleAIDecision):
        """执行简单的AI决策"""
        # 直接发送施法请求事件
        self.event_bus.dispatch(GameEvent(EventName.CAST_SPELL_REQUEST, CastSpellRequestPayload(
            caster=enemy,
            target=decision.target_entity,
            spell_id=decision.spell_id
        ))) 