#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Dict, Any
from ..core.event_bus import EventBus, GameEvent, EventName
from ..core.entity import Entity
from ..core.components import (BattlefieldComponent, BattlefieldConfigComponent, 
                              EnemyWaveComponent, TeamComponent, DeadComponent, PositionComponent)
from ..core.payloads import UIMessagePayload
from ..systems.data_manager import DataManager
from ..systems.character_factory import CharacterFactory

class BattlefieldSystem:
    """战场系统，负责管理战场状态、敌人波次和胜利条件"""
    
    def __init__(self, event_bus: EventBus, data_manager: DataManager, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.world = world
        self.character_factory = CharacterFactory(event_bus, data_manager)
        
        # 注册事件监听器
        self.event_bus.subscribe(EventName.BATTLEFIELD_INIT_REQUEST, self.on_battlefield_init_request)
        self.event_bus.subscribe(EventName.ROUND_END, self.on_round_end)
        self.event_bus.subscribe(EventName.ENTITY_DEATH, self.on_entity_death)
    
    def on_battlefield_init_request(self, event: GameEvent):
        """处理战场初始化请求"""
        battlefield_id = event.payload["battlefield_id"]
        self.init_battlefield(battlefield_id)
    
    def init_battlefield(self, battlefield_id: str):
        """初始化战场"""
        # 加载战场配置
        battlefield_data = self.data_manager.get_battlefield_data(battlefield_id)
        if not battlefield_data:
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, 
                {"message": f"**错误**: 找不到战场配置 {battlefield_id}"}))
            return
        
        # 创建战场实体
        battlefield_entity = Entity(f"Battlefield_{battlefield_id}", self.event_bus)
        
        # 添加战场组件
        config = battlefield_data.get('config', {})
        battlefield_entity.add_component(BattlefieldComponent(
            battlefield_id=battlefield_id,
            current_round=1,
            max_rounds=config.get('max_rounds', 1),
            victory_condition=config.get('victory_condition', 'all_enemies_defeated'),
            defeat_condition=config.get('defeat_condition', 'all_players_defeated')
        ))
        
        # 添加战场配置组件
        battlefield_entity.add_component(BattlefieldConfigComponent(
            name=battlefield_data.get('name', battlefield_id),
            description=battlefield_data.get('description', ''),
            max_players=battlefield_data.get('player_team', {}).get('max_players', 1),
            starting_avatars=battlefield_data.get('player_team', {}).get('starting_avatars', []),
            battlefield_id=battlefield_id
        ))
        
        # 添加敌人波次组件
        enemy_teams = battlefield_data.get('enemy_teams', {})
        if enemy_teams:
            stages_enemies = enemy_teams.get('stages_enemies', [])
            if stages_enemies:
                battlefield_entity.add_component(EnemyWaveComponent(
                    round_number=1,  # 从第1轮开始
                    enemies=stages_enemies[0] if stages_enemies else []  # 第一波敌人
                ))
        
        # 将战场实体添加到世界
        self.world.add_entity(battlefield_entity)
        
        # 生成玩家队伍
        self.spawn_player_team(battlefield_entity)
        
        # 生成第一波敌人
        self.spawn_enemy_wave(battlefield_entity)
        
        # 发送战场初始化完成事件
        self.event_bus.dispatch(GameEvent(EventName.BATTLEFIELD_INIT_COMPLETE, {
            "battlefield_id": battlefield_id
        }))
        
        # 显示战场信息
        self.display_battlefield_info(battlefield_entity)
    
    def spawn_player_team(self, battlefield_entity: Entity):
        """生成玩家队伍"""
        config_comp = battlefield_entity.get_component(BattlefieldConfigComponent)
        if not config_comp:
            return
        
        # 获取战场配置数据以读取位置分配
        battlefield_data = self.data_manager.get_battlefield_data(config_comp.battlefield_id)
        positions_config = battlefield_data.get('player_team', {}).get('positions', {})
        
        # 根据位置配置创建玩家角色
        for position_id, position_config in positions_config.items():
            avatar_template = position_config.get('avatar')
            if not avatar_template:
                continue
                
            # 创建玩家角色
            player_entity = self.character_factory.create_character_from_template(
                avatar_template, avatar_template  # 使用avatar模板名称作为实体名称
            )
            
            if player_entity:
                # 添加队伍组件
                player_entity.add_component(TeamComponent(
                    team_id="player",
                    position="front"  # 玩家默认在前排
                ))
                
                # 添加位置组件（从战场配置中获取位置ID）
                player_entity.add_component(PositionComponent(position_id=int(position_id)))
                
                # 添加到世界
                self.world.add_entity(player_entity)
    
    def spawn_enemy_wave(self, battlefield_entity: Entity):
        """生成敌人波次"""
        wave_comp = battlefield_entity.get_component(EnemyWaveComponent)
        if not wave_comp or wave_comp.is_spawned:
            return
        
        # 获取战场配置数据
        config_comp = battlefield_entity.get_component(BattlefieldConfigComponent)
        if not config_comp:
            return
            
        battlefield_data = self.data_manager.get_battlefield_data(config_comp.battlefield_id)
        enemy_teams_config = battlefield_data.get('enemy_teams', {})
        positions_config = enemy_teams_config.get('positions', {})
        
        # 根据位置配置创建敌人
        for position_id, position_config in positions_config.items():
            enemy_template = position_config.get('enemy')
            if not enemy_template:
                continue
                
            # 创建敌人
            enemy_entity = self.character_factory.create_character_from_template(
                enemy_template, f"{enemy_template}_{position_id}"
            )
            
            if enemy_entity:
                # 添加队伍组件
                enemy_entity.add_component(TeamComponent(
                    team_id="enemy",
                    position="front"  # 默认前排
                ))
                
                # 添加位置组件
                enemy_entity.add_component(PositionComponent(position_id=int(position_id)))
                
                # 添加到世界
                self.world.add_entity(enemy_entity)
        
        # 标记波次已生成
        wave_comp.is_spawned = True
    
    def apply_level_adjustment(self, entity: Entity, level: int):
        """应用等级调整"""
        # 这里可以实现等级调整逻辑
        # 例如：根据等级调整生命值、攻击力等属性
        pass
    
    def on_round_end(self, event: GameEvent):
        """处理回合结束事件"""
        # 检查是否需要生成下一波敌人
        battlefield_entities = [e for e in self.world.entities if e.has_component(BattlefieldComponent)]
        
        for battlefield_entity in battlefield_entities:
            battlefield_comp = battlefield_entity.get_component(BattlefieldComponent)
            if not battlefield_comp:
                continue
            
            # 检查当前波次是否完成
            if self.is_current_wave_completed(battlefield_entity):
                # 进入下一轮
                self.next_round(battlefield_entity)
    
    def is_current_wave_completed(self, battlefield_entity: Entity) -> bool:
        """检查当前波次是否完成"""
        # 检查是否还有存活的敌人
        alive_enemies = [e for e in self.world.entities 
                        if e.has_component(TeamComponent) 
                        and e.get_component(TeamComponent).team_id == "enemy"
                        and not e.has_component(DeadComponent)]
        
        return len(alive_enemies) == 0
    
    def next_round(self, battlefield_entity: Entity):
        """进入下一轮"""
        battlefield_comp = battlefield_entity.get_component(BattlefieldComponent)
        config_comp = battlefield_entity.get_component(BattlefieldConfigComponent)
        
        if not battlefield_comp or not config_comp:
            return
        
        current_round = battlefield_comp.current_round
        max_rounds = battlefield_comp.max_rounds
        
        if current_round >= max_rounds:
            # 所有轮次完成，检查胜利条件
            self.check_victory_condition(battlefield_entity)
            return
        
        # 进入下一轮
        battlefield_comp.current_round += 1
        
        # 加载下一波敌人配置
        battlefield_data = self.data_manager.get_battlefield_data(battlefield_comp.battlefield_id)
        if battlefield_data:
            enemy_teams = battlefield_data.get('enemy_teams', {})
            stages_enemies = enemy_teams.get('stages_enemies', [])
            
            if battlefield_comp.current_round <= len(stages_enemies):
                # 移除旧的波次组件
                battlefield_entity.remove_component(EnemyWaveComponent)
                
                # 添加新的波次组件
                battlefield_entity.add_component(EnemyWaveComponent(
                    round_number=battlefield_comp.current_round,
                    enemies=stages_enemies[battlefield_comp.current_round - 1]  # 数组索引从0开始
                ))
                
                # 生成新波次敌人
                self.spawn_enemy_wave(battlefield_entity)
                
                # 显示新波次信息
                self.display_wave_info(battlefield_entity)
    
    def on_entity_death(self, event: GameEvent):
        """处理实体死亡事件"""
        dead_entity = event.payload.get("entity")
        if not dead_entity:
            return
        
        # 检查胜利/失败条件
        battlefield_entities = [e for e in self.world.entities if e.has_component(BattlefieldComponent)]
        
        for battlefield_entity in battlefield_entities:
            self.check_victory_condition(battlefield_entity)
    
    def check_victory_condition(self, battlefield_entity: Entity):
        """检查胜利条件"""
        battlefield_comp = battlefield_entity.get_component(BattlefieldComponent)
        if not battlefield_comp or battlefield_comp.is_completed:
            return
        
        # 获取存活的玩家和敌人
        alive_players = [e for e in self.world.entities 
                        if e.has_component(TeamComponent) 
                        and e.get_component(TeamComponent).team_id == "player"
                        and not e.has_component(DeadComponent)]
        
        alive_enemies = [e for e in self.world.entities 
                        if e.has_component(TeamComponent) 
                        and e.get_component(TeamComponent).team_id == "enemy"
                        and not e.has_component(DeadComponent)]
        
        # 检查胜利条件
        if battlefield_comp.victory_condition == "all_enemies_defeated" and len(alive_enemies) == 0:
            self.declare_victory(battlefield_entity)
        elif battlefield_comp.defeat_condition == "all_players_defeated" and len(alive_players) == 0:
            self.declare_defeat(battlefield_entity)
    
    def declare_victory(self, battlefield_entity: Entity):
        """宣布胜利"""
        battlefield_comp = battlefield_entity.get_component(BattlefieldComponent)
        config_comp = battlefield_entity.get_component(BattlefieldConfigComponent)
        
        battlefield_comp.is_completed = True
        
        self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
            f"**胜利！** 你成功完成了 {config_comp.name}！"
        )))
        
        self.event_bus.dispatch(GameEvent(EventName.BATTLEFIELD_COMPLETE, {
            "battlefield_id": battlefield_comp.battlefield_id,
            "result": "victory"
        }))
    
    def declare_defeat(self, battlefield_entity: Entity):
        """宣布失败"""
        battlefield_comp = battlefield_entity.get_component(BattlefieldComponent)
        config_comp = battlefield_entity.get_component(BattlefieldConfigComponent)
        
        battlefield_comp.is_completed = True
        
        self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
            f"**失败！** 你在 {config_comp.name} 中被击败了。"
        )))
        
        self.event_bus.dispatch(GameEvent(EventName.BATTLEFIELD_COMPLETE, {
            "battlefield_id": battlefield_comp.battlefield_id,
            "result": "defeat"
        }))
    
    def display_battlefield_info(self, battlefield_entity: Entity):
        """显示战场信息"""
        config_comp = battlefield_entity.get_component(BattlefieldConfigComponent)
        battlefield_comp = battlefield_entity.get_component(BattlefieldComponent)
        
        if config_comp and battlefield_comp:
            message = f"**{config_comp.name}**\n"
            message += f"描述: {config_comp.description}\n"
            message += f"当前轮次: {battlefield_comp.current_round}/{battlefield_comp.max_rounds}\n"
            message += f"最大玩家数: {config_comp.max_players}"
            
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(message)))
    
    def display_wave_info(self, battlefield_entity: Entity):
        """显示波次信息"""
        battlefield_comp = battlefield_entity.get_component(BattlefieldComponent)
        wave_comp = battlefield_entity.get_component(EnemyWaveComponent)
        
        if battlefield_comp and wave_comp:
            message = f"**第 {battlefield_comp.current_round} 轮敌人出现！**\n"
            
            for enemy_config in wave_comp.enemies:
                template = enemy_config.get('template')
                count = enemy_config.get('count', 1)
                level = enemy_config.get('level', 1)
                
                # 获取敌人名称
                enemy_data = self.data_manager.get_enemy_data(template)
                enemy_name = enemy_data.get('name', template) if enemy_data else template
                
                message += f"- {enemy_name} x{count} (等级 {level})\n"
            
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(message))) 