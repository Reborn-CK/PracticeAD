#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import ActionRequestPayload, CastSpellRequestPayload, LogRequestPayload
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
            
            # 添加调试信息
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[AI DEBUG]", f"{acting_entity.name} 开始AI决策"
            )))
            
            # 生成简单的AI决策
            decision = self.generate_simple_decision(acting_entity)
            if decision:
                # 添加调试信息
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[AI DEBUG]", f"{acting_entity.name} 选择技能 {decision.spell_id} 目标 {decision.target_entity.name}"
                )))
                # 执行AI决策
                self.execute_simple_decision(acting_entity, decision)
            else:
                # 添加调试信息
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[AI DEBUG]", f"{acting_entity.name} 没有找到合适的技能或目标，跳过回合"
                )))
                # 没有合适技能时，直接结束回合
                from ..core.payloads import ActionAfterActPayload
                self.event_bus.dispatch(GameEvent(EventName.ACTION_AFTER_ACT, ActionAfterActPayload(acting_entity)))
    
    def generate_simple_decision(self, enemy: Entity) -> Optional[SimpleAIDecision]:
        """生成简单的AI决策"""
        # 获取可用技能
        available_spells = self.get_available_spells(enemy)
        
        if not available_spells:
            # 添加调试信息
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[AI DEBUG]", f"{enemy.name} 没有可用技能"
            )))
            return None
        
        # 遍历所有可用技能，找到第一个有合适目标的技能
        for spell_id in available_spells:
            # 添加调试信息
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[AI DEBUG]", f"{enemy.name} 尝试技能 {spell_id}"
            )))
            
            # 获取法术的目标类型
            target_type = self.data_manager.get_spell_target_type(spell_id)
            
            # 根据目标类型获取合适的目标
            target = self.get_target_by_spell_type(enemy, target_type)
            
            if target:
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[AI DEBUG]", f"{enemy.name} 找到目标 {target.name} 用于技能 {spell_id}"
                )))
                return SimpleAIDecision(
                    spell_id=spell_id,
                    target_entity=target
                )
            else:
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                    "[AI DEBUG]", f"{enemy.name} 技能 {spell_id} 没有找到合适目标"
                )))
        
        return None
    
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
    
    def get_target_by_spell_type(self, enemy: Entity, target_type: str) -> Optional[Entity]:
        """根据法术目标类型获取合适的目标"""
        if target_type == "enemy":
            # 攻击法术：敌人攻击玩家
            alive_players = [e for e in self.world.entities 
                            if e.has_component(TeamComponent) and 
                            e.get_component(TeamComponent).team_id == "player" and
                            not e.has_component(DeadComponent)]
            
            # 添加调试信息
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[AI DEBUG]", f"{enemy.name} 攻击法术，找到 {len(alive_players)} 个玩家目标"
            )))
            
            return alive_players[0] if alive_players else None
            
        elif target_type == "ally":
            # 治疗法术：敌人治疗自己人
            alive_allies = [e for e in self.world.entities 
                           if e.has_component(TeamComponent) and 
                           e.get_component(TeamComponent).team_id == "enemy" and
                           e != enemy and  # 不包括自己
                           not e.has_component(DeadComponent)]
            return alive_allies[0] if alive_allies else None
            
        elif target_type == "all_enemies":
            # 群体攻击法术：敌人攻击玩家
            alive_players = [e for e in self.world.entities 
                            if e.has_component(TeamComponent) and 
                            e.get_component(TeamComponent).team_id == "player" and
                            not e.has_component(DeadComponent)]
            return alive_players[0] if alive_players else None
            
        elif target_type == "all_allies":
            # 群体治疗法术：敌人治疗自己人
            alive_allies = [e for e in self.world.entities 
                           if e.has_component(TeamComponent) and 
                           e.get_component(TeamComponent).team_id == "enemy" and
                           e != enemy and  # 不包括自己
                           not e.has_component(DeadComponent)]
            return alive_allies[0] if alive_allies else None
            
        else:
            # 默认情况：攻击玩家
            alive_players = [e for e in self.world.entities 
                            if e.has_component(TeamComponent) and 
                            e.get_component(TeamComponent).team_id == "player" and
                            not e.has_component(DeadComponent)]
            return alive_players[0] if alive_players else None
    
    def get_simple_target(self, enemy: Entity) -> Optional[Entity]:
        """获取简单的目标（保持向后兼容）"""
        return self.get_target_by_spell_type(enemy, "enemy")
    
    def execute_simple_decision(self, enemy: Entity, decision: SimpleAIDecision):
        """执行简单的AI决策"""
        # 直接发送施法请求事件
        self.event_bus.dispatch(GameEvent(EventName.CAST_SPELL_REQUEST, CastSpellRequestPayload(
            caster=enemy,
            target=decision.target_entity,
            spell_id=decision.spell_id
        ))) 