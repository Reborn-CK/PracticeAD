#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法术测试文件
测试spells.yaml中所有法术的功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game.world import World
from game.core.entity import Entity
from game.core.components import (HealthComponent, ManaComponent, ShieldComponent, 
                                  StatusEffectContainerComponent, CritComponent)
from game.core.event_bus import EventBus, GameEvent
from game.systems.spell_cast_system import SpellCastSystem
from game.systems.data_manager import DataManager
from game.systems.mana_system import ManaSystem
from game.systems.passive_ability_system import PassiveAbilitySystem
from game.systems.combat.combat_resolution_system import CombatResolutionSystem
from game.systems.status_effect_system import StatusEffectSystem
from game.systems.ui_system import UISystem
from game.systems.log_system import LogSystem
from game.status_effects.status_effect_factory import StatusEffectFactory
from game.core.enums import EventName
from game.core.payloads import CastSpellRequestPayload
from typing import Dict, List

class SpellTester:
    def __init__(self):
        """初始化测试环境"""
        self.event_bus = EventBus()
        self.data_manager = DataManager()
        
        # 加载数据
        self.data_manager.load_spell_data()
        self.data_manager.load_status_effect_data()
        self.data_manager.load_character_data()
        self.data_manager.load_passive_data()
        
        self.world = World(event_bus=self.event_bus)
        self.status_effect_factory = StatusEffectFactory(self.data_manager)
        
        # 初始化所有系统
        self.spell_system = SpellCastSystem(self.event_bus, self.data_manager, self.world)
        self.mana_system = ManaSystem(self.event_bus)
        self.passive_system = PassiveAbilitySystem(self.event_bus)
        self.combat_system = CombatResolutionSystem(self.event_bus, self.data_manager, self.passive_system, self.status_effect_factory)
        self.status_effect_system = StatusEffectSystem(self.event_bus, self.world)
        self.ui_system = UISystem(self.event_bus, self.world)
        self.log_system = LogSystem(self.event_bus)
        
        # 创建测试实体
        self.player = self._create_test_entity("玩家", 1000, 1000, 100)
        self.enemy = self._create_test_entity("敌人", 1000, 1000, 100)
        
        print("=== 法术测试系统初始化完成 ===")
        player_health = self.player.get_component(HealthComponent)
        player_mana = self.player.get_component(ManaComponent)
        enemy_health = self.enemy.get_component(HealthComponent)
        enemy_mana = self.enemy.get_component(ManaComponent)
        
        if all([player_health, player_mana, enemy_health, enemy_mana]):
            # 类型检查器需要明确的非空断言
            assert player_health is not None
            assert player_mana is not None
            assert enemy_health is not None
            assert enemy_mana is not None
            print(f"玩家: HP={player_health.hp}, MP={player_mana.mana}")
            print(f"敌人: HP={enemy_health.hp}, MP={enemy_mana.mana}")
        else:
            print("警告：实体组件初始化失败")
        print()

    def _create_test_entity(self, name: str, hp: int, mana: int, shield: int = 0) -> Entity:
        """创建测试实体"""
        entity = Entity(name, event_bus=self.event_bus)
        entity.add_component(HealthComponent(entity, self.event_bus, hp, hp))
        entity.add_component(ManaComponent(mana, mana))
        entity.add_component(ShieldComponent(shield))
        entity.add_component(StatusEffectContainerComponent())
        entity.add_component(CritComponent(0.1, 2.0))  # 10%暴击率，2倍暴击伤害
        return entity

    def test_spell(self, spell_id: str, caster: Entity, target: Entity, description: str = ""):
        """测试单个法术"""
        print(f"=== 测试法术: {spell_id} ===")
        if description:
            print(f"描述: {description}")
        
        # 记录施法前状态
        caster_health = caster.get_component(HealthComponent)
        caster_mana = caster.get_component(ManaComponent)
        target_health = target.get_component(HealthComponent)
        target_shield = target.get_component(ShieldComponent)
        target_status = target.get_component(StatusEffectContainerComponent)
        
        if not all([caster_health, caster_mana, target_health, target_shield, target_status]):
            print("错误：实体缺少必要的组件！")
            return
        
        # 断言确保组件不为 None
        assert caster_health is not None
        assert caster_mana is not None
        assert target_health is not None
        assert target_shield is not None
        assert target_status is not None
        
        caster_hp_before = caster_health.hp
        caster_mana_before = caster_mana.mana
        target_hp_before = target_health.hp
        target_shield_before = target_shield.shield_value
        target_effects_before = len(target_status.effects)
        
        print(f"施法前状态:")
        print(f"  施法者: HP={caster_hp_before}, MP={caster_mana_before}")
        print(f"  目标: HP={target_hp_before}, 护盾={target_shield_before}, 状态效果={target_effects_before}")
        
        # 施放法术
        spell_request = CastSpellRequestPayload(caster=caster, target=target, spell_id=spell_id)
        event = GameEvent(EventName.CAST_SPELL_REQUEST, spell_request)
        self.event_bus.dispatch(event)
        
        # 记录施法后状态
        caster_hp_after = caster_health.hp
        caster_mana_after = caster_mana.mana
        target_hp_after = target_health.hp
        target_shield_after = target_shield.shield_value
        target_effects_after = len(target_status.effects)
        
        print(f"施法后状态:")
        print(f"  施法者: HP={caster_hp_after}, MP={caster_mana_after}")
        print(f"  目标: HP={target_hp_after}, 护盾={target_shield_after}, 状态效果={target_effects_after}")
        
        # 计算变化
        hp_change = target_hp_after - target_hp_before
        shield_change = target_shield_after - target_shield_before
        effects_change = target_effects_after - target_effects_before
        mana_cost = caster_mana_before - caster_mana_after
        
        print(f"效果总结:")
        if hp_change != 0:
            print(f"  生命值变化: {hp_change:+d}")
        if shield_change != 0:
            print(f"  护盾变化: {shield_change:+.1f}")
        if effects_change != 0:
            print(f"  状态效果变化: {effects_change:+d}")
        if mana_cost > 0:
            print(f"  法力消耗: {mana_cost}")
        
        print("-" * 50)
        print()

    def test_all_spells(self):
        """测试所有法术"""
        print("开始测试所有法术...")
        print("=" * 80)
        
        # 获取所有法术ID
        all_spells = self.data_manager.get_all_spell_ids()
        
        for spell_id in all_spells:
            spell_data = self.data_manager.get_spell_data(spell_id)
            if not spell_data:
                continue
                
            # 根据目标类型选择施法者和目标
            target_type = spell_data.get('target', 'enemy')
            if target_type == 'enemy':
                caster, target = self.player, self.enemy
            else:  # ally
                caster, target = self.player, self.player
            
            # 测试法术
            self.test_spell(spell_id, caster, target, spell_data.get('description', ''))
            
            # 重置状态（除了生命值和法力值）
            self._reset_entity_status(target)
        
        print("所有法术测试完成！")

    def _reset_entity_status(self, entity: Entity):
        """重置实体状态（保留生命值和法力值）"""
        # 重置护盾
        shield_comp = entity.get_component(ShieldComponent)
        if shield_comp:
            shield_comp.shield_value = 0
        
        # 清除状态效果
        status_comp = entity.get_component(StatusEffectContainerComponent)
        if status_comp:
            status_comp.effects.clear()

    def test_specific_spell(self, spell_id: str):
        """测试特定法术"""
        spell_data = self.data_manager.get_spell_data(spell_id)
        if not spell_data:
            print(f"法术 {spell_id} 不存在！")
            return
        
        target_type = spell_data.get('target', 'enemy')
        if target_type == 'enemy':
            caster, target = self.player, self.enemy
        else:
            caster, target = self.player, self.player
        
        self.test_spell(spell_id, caster, target, spell_data.get('description', ''))

    def test_spell_interactions(self):
        """测试法术交互效果"""
        print("=== 测试法术交互效果 ===")
        
        # 测试燃烧 + 燃烬
        print("测试燃烧 + 燃烬交互:")
        self.test_spell("fireball_01", self.player, self.enemy)  # 施加燃烧
        self.test_spell("combust_01", self.player, self.enemy)   # 引爆燃烧
        
        # 重置状态
        self._reset_entity_status(self.enemy)
        
        # 测试燃烧 + 雪球术
        print("测试燃烧 + 雪球术交互:")
        self.test_spell("fireball_01", self.player, self.enemy)  # 施加燃烧
        self.test_spell("snowball_01", self.player, self.enemy)  # 熄灭燃烧
        
        # 重置状态
        self._reset_entity_status(self.enemy)
        
        # 测试燃烧 + 风刃术
        print("测试燃烧 + 风刃术交互:")
        self.test_spell("fireball_01", self.player, self.enemy)  # 施加燃烧
        self.test_spell("wind_01", self.player, self.enemy)      # 延长燃烧
        
        print("法术交互测试完成！")

def main():
    """主函数"""
    tester = SpellTester()
    
    # 测试所有法术
    tester.test_all_spells()
    
    # 测试法术交互
    tester.test_spell_interactions()
    
    # 可以测试特定法术
    # tester.test_specific_spell("fireball_01")

if __name__ == "__main__":
    main() 