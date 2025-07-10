from .core.event_bus import EventBus
from .core.entity import Entity
from .world import World
from .systems.data_manager import DataManager
from .systems.log_system import LogSystem
from .systems.ui_system import UISystem
from .systems.status_effect_system import StatusEffectSystem
from .systems.interaction_system import InteractionSystem
from .systems.turn_manager_system import TurnManagerSystem
from .systems.player_input_system import PlayerInputSystem
from .systems.enemy_ai_system import EnemyAISystem
from .systems.spell_cast_system import SpellCastSystem
from .systems.mana_system import ManaSystem
from .systems.passive_ability_system import PassiveAbilitySystem
from .systems.combat.combat_resolution_system import CombatResolutionSystem
from .systems.dead_system import DeadSystem
from .systems.character_factory import CharacterFactory
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
    log_system.set_enabled(True)    # 完全关闭日志系统
    
    world.add_system(UISystem(event_bus, world)) # UI系统需要world来渲染状态
    world.add_system(StatusEffectSystem(event_bus, world))
    world.add_system(InteractionSystem(event_bus, data_manager, status_effect_factory))

    # --- 核心循环系统 ---
    world.add_system(TurnManagerSystem(event_bus, world), priority=50)

    world.add_system(PlayerInputSystem(event_bus, data_manager, world), priority=100)
    world.add_system(EnemyAISystem(event_bus, world), priority=100)
    
    # --- 纯事件驱动，无update，优先级无所谓 ---
    world.add_system(SpellCastSystem(event_bus, data_manager, status_effect_factory))
    world.add_system(ManaSystem(event_bus))
    
    # 先创建被动系统
    passive_system = PassiveAbilitySystem(event_bus)
    world.add_system(passive_system)
    
    # 然后创建战斗系统，并传入被动系统的引用和状态效果工厂
    world.add_system(CombatResolutionSystem(event_bus, data_manager, passive_system, status_effect_factory))

    # --- 优先级200，死亡检查 ---
    world.add_system(DeadSystem(event_bus, world), priority=200)

    # 3. 创建角色工厂和游戏实体
    print("创建游戏实体...")
    character_factory = CharacterFactory(event_bus, data_manager)
    
    # 使用配置文件创建角色
    player = character_factory.create_character("hero", world)
    enemy = character_factory.create_character("boss", world)

    # 4. 启动游戏世界
    print("开始游戏...")
    world.start()

if __name__ == "__main__":
    main()