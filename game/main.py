from .core.event_bus import EventBus
from .core.entity import Entity
from .core.enums import BattleTurnRule
from .world import World
from .systems.data_manager import DataManager
from .systems.log_system import LogSystem
from .systems.ui_system import UISystem
from .systems.status_effect_system import StatusEffectSystem
from .systems.interaction_system import InteractionSystem
from .systems.turn_manager_system import TurnManagerSystem
from .systems.player_input_system import PlayerInputSystem
from .systems.simple_ai_system import SimpleEnemyAISystem
from .systems.spell_cast_system import SpellCastSystem
from .systems.mana_system import ManaSystem
from .systems.energy_system import EnergySystem
from .systems.ultimate_charge_system import UltimateChargeSystem
from .systems.passive_ability_system import PassiveAbilitySystem
from .systems.combat.combat_resolution_system import CombatResolutionSystem
from .systems.dead_system import DeadSystem
from .systems.character_factory import CharacterFactory
from .systems.equipment_system import EquipmentSystem
from .systems.item_system import ItemSystem
from .systems.battlefield_system import BattlefieldSystem
from .systems.battle_end_system import BattleEndSystem
from .status_effects.status_effect_factory import StatusEffectFactory

def main():
    print("游戏启动中...")
    # 1. 初始化核心服务
    event_bus = EventBus()
    data_manager = DataManager()
    status_effect_factory = StatusEffectFactory(data_manager)
    print("加载游戏数据...")
    data_manager.load_spell_data()
    data_manager.load_status_effect_data()
    data_manager.load_passive_data()
    data_manager.load_character_data()
    data_manager.load_avatar_data()
    data_manager.load_enemy_data()
    data_manager.load_battlefield_data()
    data_manager.load_enemy_ai_data("data/enemies_ai.yaml")
    data_manager.load_equipment_data()
    data_manager.load_item_data()
    world = World(event_bus)

    # 2. 创建并注册所有系统
    print("注册系统...")
    log_system = LogSystem(event_bus)  # 创建日志系统实例以便控制
    world.add_system(log_system) # 首先注册日志系统
    
    # 日志系统控制示例（可以取消注释来测试）
    # log_system.hide_tag("[COMBAT]")  # 隐藏战斗详细日志
    # log_system.hide_tag("[SPELL]")   # 隐藏施法日志
    # log_system.hide_tag("[AI]")      # 隐藏AI决策日志
    # log_system.hide_tag("[SYSTEM]")  # 隐藏系统日志
    log_system.set_enabled(True)    # 启用日志系统
    
    world.add_system(UISystem(event_bus, world)) # UI系统需要world来渲染状态
    world.add_system(StatusEffectSystem(event_bus, world))
    world.add_system(InteractionSystem(event_bus, data_manager, status_effect_factory))

    # --- 核心循环系统 ---
    energy_system = EnergySystem(event_bus)
    turn_manager_system = TurnManagerSystem(event_bus, world, energy_system)
    world.add_system(turn_manager_system, priority=50)
    #turn_manager_system.set_battle_turn_rule(BattleTurnRule.AP_BASED)
    turn_manager_system.set_battle_turn_rule(BattleTurnRule.AP_BASED)


    world.add_system(PlayerInputSystem(event_bus, data_manager, world), priority=100)
    world.add_system(SimpleEnemyAISystem(event_bus, data_manager, world), priority=100)
    
    # --- 纯事件驱动，无update，优先级无所谓 ---
    ultimate_charge_system = UltimateChargeSystem(event_bus)
    world.add_system(SpellCastSystem(event_bus, data_manager, world, ultimate_charge_system))
    world.add_system(ManaSystem(event_bus))
    world.add_system(energy_system)  # 使用之前创建的energy_system实例
    world.add_system(ultimate_charge_system)
    world.add_system(PassiveAbilitySystem(event_bus))
    world.add_system(CombatResolutionSystem(event_bus, data_manager, PassiveAbilitySystem(event_bus), status_effect_factory))
    world.add_system(DeadSystem(event_bus, world))
    world.add_system(EquipmentSystem(event_bus, data_manager))
    world.add_system(ItemSystem(event_bus, data_manager, world))
    world.add_system(BattlefieldSystem(event_bus, data_manager, world))
    world.add_system(BattleEndSystem(event_bus, world))

    # 3. 创建角色（可选：使用战场系统或直接创建角色）
    print("创建角色...")
    character_factory = CharacterFactory(event_bus, data_manager)
    
    # 方式1：使用战场系统（推荐）
    # 初始化战场
    from .core.event_bus import GameEvent
    from .core.enums import EventName
    event_bus.dispatch(GameEvent(EventName.BATTLEFIELD_INIT_REQUEST, {"battlefield_id": "tutorial_battlefield"}))
    
    # 方式2：直接创建角色（向后兼容）
    # hero = character_factory.create_character("hero", world)
    # boss = character_factory.create_character("boss", world)
    # print(f"角色创建完成: {hero.name}, {boss.name}")

    print("游戏开始!")

    # 4. 开始游戏循环
    world.start()

if __name__ == "__main__":
    main()