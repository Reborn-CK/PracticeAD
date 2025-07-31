#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName
from ..core.payloads import ActionRequestPayload, PlayerSpellChoicePayload, PlayerTargetChoicePayload
from ..core.components import (AIComponent, TeamComponent, HealthComponent, ManaComponent, 
                              EnergyComponent, SpellListComponent, UltimateSpellListComponent,
                              DeadComponent, PositionComponent)
from ..core.entity import Entity
from ..systems.data_manager import DataManager

@dataclass
class AIDecision:
    """AI决策结果"""
    spell_id: str
    target_entity: Entity
    decision_type: str  # "attack", "heal", "defend", "ultimate"
    confidence: float  # 决策置信度 0.0-1.0

class EnemyAISystem:
    """敌人AI系统，控制敌人的智能行为"""
    
    def __init__(self, event_bus: EventBus, data_manager: DataManager, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.world = world
        
        # 订阅相关事件
        self.event_bus.subscribe(EventName.ACTION_REQUEST, self.on_action_request)
        self.event_bus.subscribe(EventName.ENTITY_DEATH, self.on_entity_death)
    
    def on_action_request(self, event: GameEvent):
        """处理行动请求事件"""
        payload: ActionRequestPayload = event.payload
        acting_entity = payload.acting_entity
        
        # 检查是否是敌人且具有AI组件
        if (acting_entity.has_component(TeamComponent) and 
            acting_entity.get_component(TeamComponent).team_id == "enemy" and
            acting_entity.has_component(AIComponent)):
            
            # 生成AI决策
            decision = self.generate_ai_decision(acting_entity)
            if decision:
                # 执行AI决策
                self.execute_ai_decision(acting_entity, decision)
    
    def generate_ai_decision(self, enemy: Entity) -> Optional[AIDecision]:
        """生成AI决策"""
        ai_comp = enemy.get_component(AIComponent)
        if not ai_comp:
            return None
        
        # 检查行动冷却
        current_time = time.time()
        if current_time - ai_comp.last_action_time < ai_comp.action_cooldown:
            return None
        
        # 获取AI模板数据
        ai_template = self.data_manager.get_ai_template(ai_comp.ai_template)
        if not ai_template:
            return None
        
        # 分析战场情况
        battlefield_analysis = self.analyze_battlefield(enemy)
        
        # 根据AI模板生成决策
        decision = self.apply_ai_template(ai_comp, ai_template, battlefield_analysis, enemy)
        
        return decision
    
    def analyze_battlefield(self, enemy: Entity) -> Dict[str, Any]:
        """分析战场情况"""
        # 获取所有存活的实体
        alive_entities = [e for e in self.world.entities if not e.has_component(DeadComponent)]
        
        # 分类实体
        allies = [e for e in alive_entities if e.has_component(TeamComponent) and 
                 e.get_component(TeamComponent).team_id == "enemy" and e != enemy]
        enemies = [e for e in alive_entities if e.has_component(TeamComponent) and 
                  e.get_component(TeamComponent).team_id == "player"]
        
        # 分析血量情况
        ally_health_analysis = self.analyze_health(allies)
        enemy_health_analysis = self.analyze_health(enemies)
        
        # 分析威胁度
        threat_analysis = self.analyze_threats(enemy, enemies)
        
        return {
            "allies": allies,
            "enemies": enemies,
            "ally_health": ally_health_analysis,
            "enemy_health": enemy_health_analysis,
            "threats": threat_analysis,
            "self_health": self.get_entity_health_ratio(enemy)
        }
    
    def analyze_health(self, entities: List[Entity]) -> Dict[str, Any]:
        """分析实体血量情况"""
        if not entities:
            return {"lowest": None, "highest": None, "average": 0.0}
        
        health_ratios = []
        for entity in entities:
            health_ratio = self.get_entity_health_ratio(entity)
            health_ratios.append((entity, health_ratio))
        
        # 排序
        health_ratios.sort(key=lambda x: x[1])
        
        return {
            "lowest": health_ratios[0] if health_ratios else None,
            "highest": health_ratios[-1] if health_ratios else None,
            "average": sum(ratio for _, ratio in health_ratios) / len(health_ratios) if health_ratios else 0.0
        }
    
    def analyze_threats(self, enemy: Entity, enemies: List[Entity]) -> List[tuple]:
        """分析威胁度"""
        threats = []
        enemy_health = self.get_entity_health_ratio(enemy)
        
        for entity in enemies:
            # 计算威胁度（基于攻击力、血量、距离等）
            threat_score = self.calculate_threat_score(enemy, entity)
            threats.append((entity, threat_score))
        
        # 按威胁度排序
        threats.sort(key=lambda x: x[1], reverse=True)
        return threats
    
    def calculate_threat_score(self, enemy: Entity, target: Entity) -> float:
        """计算威胁度分数"""
        # 基础威胁度计算
        threat_score = 0.0
        
        # 基于血量（血量越低威胁越大）
        target_health = self.get_entity_health_ratio(target)
        threat_score += (1.0 - target_health) * 0.4
        
        # 基于攻击力（攻击力越高威胁越大）
        target_atk = target.get_final_stat("attack", 0)
        threat_score += min(target_atk / 100.0, 1.0) * 0.3
        
        # 基于位置（前排威胁更大）
        if target.has_component(TeamComponent):
            position = target.get_component(TeamComponent).position
            if position == "front":
                threat_score += 0.2
        
        # 基于位置ID（位置ID小的优先）
        if target.has_component(PositionComponent):
            position_id = target.get_component(PositionComponent).position_id
            threat_score += (1.0 / position_id) * 0.1
        
        return min(threat_score, 1.0)
    
    def get_entity_health_ratio(self, entity: Entity) -> float:
        """获取实体血量比例"""
        health_comp = entity.get_component(HealthComponent)
        if not health_comp:
            return 0.0
        
        if health_comp.max_health <= 0:
            return 0.0
        
        return health_comp.hp / health_comp.max_health
    
    def apply_ai_template(self, ai_comp: AIComponent, ai_template: Dict[str, Any], 
                         battlefield_analysis: Dict[str, Any], enemy: Entity) -> Optional[AIDecision]:
        """应用AI模板生成决策"""
        behavior_patterns = ai_template.get('behavior_patterns', [])
        
        # 获取可用技能
        available_spells = self.get_available_spells(enemy)
        
        # 根据行为模式选择技能和目标
        for pattern in behavior_patterns:
            pattern_type = pattern.get('type')
            
            if pattern_type == "target_selection":
                target = self.select_target(pattern, battlefield_analysis)
                if not target:
                    continue
            
            elif pattern_type == "spell_selection":
                spell_id = self.select_spell(pattern, available_spells, battlefield_analysis)
                if not spell_id:
                    continue
                
                # 找到对应的目标选择模式
                target_pattern = next((p for p in behavior_patterns if p.get('type') == "target_selection"), None)
                target = self.select_target(target_pattern, battlefield_analysis) if target_pattern else None
                
                if spell_id and target:
                    return AIDecision(
                        spell_id=spell_id,
                        target_entity=target,
                        decision_type=self.get_decision_type(spell_id),
                        confidence=0.8
                    )
        
        # 如果没有找到合适的决策，使用默认攻击
        return self.get_default_decision(enemy, battlefield_analysis)
    
    def select_target(self, pattern: Dict[str, Any], battlefield_analysis: Dict[str, Any]) -> Optional[Entity]:
        """选择目标"""
        priority = pattern.get('priority', 'lowest_health')
        target_filter = pattern.get('filter', 'enemy')
        
        if target_filter == "enemy":
            candidates = battlefield_analysis['enemies']
        elif target_filter == "ally":
            candidates = battlefield_analysis['allies']
        else:
            return None
        
        if not candidates:
            return None
        
        if priority == "lowest_health":
            # 选择血量最低的目标
            return min(candidates, key=lambda e: self.get_entity_health_ratio(e))
        
        elif priority == "highest_threat":
            # 选择威胁最大的目标
            threats = battlefield_analysis['threats']
            return threats[0][0] if threats else candidates[0]
        
        elif priority == "ally_lowest_health":
            # 选择血量最低的队友
            return min(candidates, key=lambda e: self.get_entity_health_ratio(e))
        
        # 默认选择第一个目标
        return candidates[0]
    
    def select_spell(self, pattern: Dict[str, Any], available_spells: List[str], 
                    battlefield_analysis: Dict[str, Any]) -> Optional[str]:
        """选择技能"""
        priority = pattern.get('priority', 'basic_attack')
        fallback = pattern.get('fallback', 'basic_attack')
        
        # 检查资源管理
        if not self.check_resource_requirements(pattern, battlefield_analysis):
            return fallback
        
        # 根据优先级选择技能
        if priority == "physical_damage":
            return self.select_physical_spell(available_spells)
        elif priority == "magic_damage":
            return self.select_magic_spell(available_spells)
        elif priority == "high_damage":
            return self.select_high_damage_spell(available_spells)
        elif priority == "ultimate_skill":
            return self.select_ultimate_spell(available_spells)
        elif priority == "healing":
            return self.select_healing_spell(available_spells)
        elif priority == "defensive_skill":
            return self.select_defensive_spell(available_spells)
        
        return fallback
    
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
    
    def check_resource_requirements(self, pattern: Dict[str, Any], battlefield_analysis: Dict[str, Any]) -> bool:
        """检查资源要求"""
        energy_threshold = pattern.get('energy_threshold', 0.0)
        mana_threshold = pattern.get('mana_threshold', 0.0)
        
        # 这里需要根据实际实体检查资源
        # 简化实现，假设资源充足
        return True
    
    def select_physical_spell(self, available_spells: List[str]) -> Optional[str]:
        """选择物理技能"""
        # 简化实现，返回第一个可用技能
        return available_spells[0] if available_spells else None
    
    def select_magic_spell(self, available_spells: List[str]) -> Optional[str]:
        """选择魔法技能"""
        # 简化实现，返回第一个可用技能
        return available_spells[0] if available_spells else None
    
    def select_high_damage_spell(self, available_spells: List[str]) -> Optional[str]:
        """选择高伤害技能"""
        # 简化实现，返回第一个可用技能
        return available_spells[0] if available_spells else None
    
    def select_ultimate_spell(self, available_spells: List[str]) -> Optional[str]:
        """选择终极技能"""
        # 简化实现，返回第一个可用技能
        return available_spells[0] if available_spells else None
    
    def select_healing_spell(self, available_spells: List[str]) -> Optional[str]:
        """选择治疗技能"""
        # 简化实现，返回第一个可用技能
        return available_spells[0] if available_spells else None
    
    def select_defensive_spell(self, available_spells: List[str]) -> Optional[str]:
        """选择防御技能"""
        # 简化实现，返回第一个可用技能
        return available_spells[0] if available_spells else None
    
    def get_decision_type(self, spell_id: str) -> str:
        """获取决策类型"""
        # 根据技能ID判断决策类型
        if "ultimate" in spell_id:
            return "ultimate"
        elif "heal" in spell_id or "shield" in spell_id:
            return "defend"
        else:
            return "attack"
    
    def get_default_decision(self, entity: Entity, battlefield_analysis: Dict[str, Any]) -> Optional[AIDecision]:
        """获取默认决策"""
        enemies = battlefield_analysis['enemies']
        if not enemies:
            return None
        
        # 默认攻击第一个敌人
        target = enemies[0]
        available_spells = self.get_available_spells(entity)
        spell_id = available_spells[0] if available_spells else "basic_attack"
        
        return AIDecision(
            spell_id=spell_id,
            target_entity=target,
            decision_type="attack",
            confidence=0.5
        )
    
    def execute_ai_decision(self, enemy: Entity, decision: AIDecision):
        """执行AI决策"""
        ai_comp = enemy.get_component(AIComponent)
        if not ai_comp:
            return
        
        # 更新行动时间
        ai_comp.last_action_time = time.time()
        
        # 直接发送施法请求事件
        from ..core.payloads import CastSpellRequestPayload
        self.event_bus.dispatch(GameEvent(EventName.CAST_SPELL_REQUEST, CastSpellRequestPayload(
            caster=enemy,
            target=decision.target_entity,
            spell_id=decision.spell_id
        )))
    
    def on_entity_death(self, event: GameEvent):
        """处理实体死亡事件"""
        # 可以在这里实现AI对队友死亡的响应
        pass