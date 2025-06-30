#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.core.event_bus import EventBus, GameEvent
from game.core.entity import Entity
from game.core.components import (HealthComponent, StatusEffectContainerComponent, 
                                 DefenseComponent, ResistanceComponent)
from game.systems.data_manager import DataManager
from game.status_effects.status_effect_factory import StatusEffectFactory
from game.systems.interaction_system import InteractionSystem
from game.systems.combat.combat_resolution_system import CombatResolutionSystem
from game.systems.spell_cast_system import SpellCastSystem
from game.systems.status_effect_system import StatusEffectSystem
from game.core.enums import EventName
from game.core.payloads import CastSpellRequestPayload, ApplyStatusEffectRequestPayload

class LogCaptureEventBus(EventBus):
    def __init__(self):
        super().__init__()
        self.logs = []
    
    def dispatch(self, event):
        if event.name == EventName.LOG_REQUEST:
            self.logs.append(f"[{event.payload.tag}] {event.payload.message}")
        super().dispatch(event)

def test_snowball_log():
    print("=== 测试雪球术伤害Log显示 ===")
    
    # 使用日志捕获事件总线
    event_bus = LogCaptureEventBus()
    data_manager = DataManager()
    data_manager.load_spell_data()
    data_manager.load_status_effect_data()
    
    status_effect_factory = StatusEffectFactory(data_manager)
    
    # 按正确顺序初始化系统
    interaction_system = InteractionSystem(event_bus, data_manager, status_effect_factory)
    combat_system = CombatResolutionSystem(event_bus, data_manager)
    spell_cast_system = SpellCastSystem(event_bus, data_manager, status_effect_factory)
    status_effect_system = StatusEffectSystem(event_bus, None)
    
    # 创建测试实体
    player = Entity("测试玩家")
    player.add_component(HealthComponent(player, event_bus, hp=100, max_hp=100))
    player.add_component(StatusEffectContainerComponent())
    player.add_component(DefenseComponent(defense_value=0))
    player.add_component(ResistanceComponent(resistances={}))
    
    enemy = Entity("测试敌人")
    enemy.add_component(HealthComponent(enemy, event_bus, hp=200, max_hp=200))
    enemy.add_component(StatusEffectContainerComponent())
    enemy.add_component(DefenseComponent(defense_value=0))
    enemy.add_component(ResistanceComponent(resistances={}))
    
    print(f"初始状态: 敌人HP: {enemy.get_component(HealthComponent).hp}")
    
    # 1. 先给敌人施加燃烧状态
    print("\n1. 给敌人施加燃烧状态...")
    burning_effect = status_effect_factory.create_effect("burning_01", player)
    if burning_effect:
        event_bus.dispatch(GameEvent(EventName.APPLY_STATUS_EFFECT_REQUEST, 
                                   ApplyStatusEffectRequestPayload(target=enemy, effect=burning_effect)))
    
    # 2. 对燃烧状态的敌人使用雪球术
    print("\n2. 对燃烧状态的敌人使用雪球术...")
    event_bus.dispatch(GameEvent(EventName.CAST_SPELL_REQUEST, CastSpellRequestPayload(
        caster=player,
        target=enemy,
        spell_id="snowball_01"
    )))
    
    print(f"\n最终状态: 敌人HP: {enemy.get_component(HealthComponent).hp}")
    
    # 3. 显示所有日志
    print("\n=== 完整日志输出 ===")
    for i, log in enumerate(event_bus.logs, 1):
        print(f"{i:2d}. {log}")
    
    # 4. 检查关键日志
    print("\n=== 关键日志检查 ===")
    interaction_logs = [log for log in event_bus.logs if "[INTERACTION]" in log]
    combat_logs = [log for log in event_bus.logs if "[COMBAT]" in log and "伤害" in log]
    
    print("交互系统日志:")
    for log in interaction_logs:
        print(f"  {log}")
    
    print("\n战斗系统日志:")
    for log in combat_logs:
        print(f"  {log}")

if __name__ == "__main__":
    test_snowball_log() 