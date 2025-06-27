from .core.event_bus import EventBus
from .world import World
from .systems.data_manager import DataManager
# ... 导入所有需要的系统和组件 ...
# (这里需要从 game.core, game.systems 等导入所有类)
from .core.entity import Entity
from .core.components import (PlayerControlledComponent, HealthComponent, ResistanceComponent, 
                              ManaComponent, DefenseComponent, GrievousWoundsComponent, 
                              SpeedComponent, StatusEffectContainerComponent, SpellListComponent, 
                              AIControlledComponent, ThornsComponent)

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


def setup_and_run_game():
    """初始化并运行游戏世界"""
    print("游戏启动中...")
    # 1. 初始化核心服务
    event_bus = EventBus()
    data_manager = DataManager()
    print("加载法术数据...")
    data_manager.load_spell_data()
    data_manager.load_status_effect_data()
    world = World(event_bus)

    # 2. 创建并注册所有系统
    print("注册系统...")
    log_system = LogSystem(event_bus, enabled=True)
    world.add_system(log_system)
    
    world.add_system(UISystem(event_bus, world))
    world.add_system(StatusEffectSystem(event_bus, world))
    world.add_system(InteractionSystem(event_bus, data_manager))
    world.add_system(TurnManagerSystem(event_bus, world), priority=50)
    world.add_system(PlayerInputSystem(event_bus, data_manager, world), priority=100)
    world.add_system(EnemyAISystem(event_bus, world), priority=100)
    world.add_system(SpellCastSystem(event_bus, data_manager))
    world.add_system(ManaSystem(event_bus))
    passive_system = PassiveAbilitySystem(event_bus)
    world.add_system(passive_system)
    world.add_system(CombatResolutionSystem(event_bus, data_manager, passive_system))
    world.add_system(DeadSystem(event_bus, world), priority=200)

    # 3. 创建实体并添加组件
    print("创建游戏实体...")
    player = world.add_entity(Entity("勇者"))
    player.add_component(PlayerControlledComponent())
    # ... (此处省略所有 add_component 的代码, 和原文件一样)
    player.add_component(HealthComponent(player, event_bus, hp=100, max_hp=100))
    player.add_component(ResistanceComponent(resistances={"fire": 0.5}))
    player.add_component(ManaComponent(mana=500, max_mana=500))
    player.add_component(DefenseComponent(defense_value=0))
    player.add_component(GrievousWoundsComponent(reduction_percentage=0.5))
    player.add_component(SpeedComponent(speed=60))
    player.add_component(StatusEffectContainerComponent())
    player.add_component(SpellListComponent(spells=[
        "fireball_01", "vampiric_touch_01", "heal_01", "heal_02", "snowball_01", 
        "wind_01", "combust_01", "blessing_stance_01", "poison_cloud_01",
        "curse_of_slowness_01", "haste_01", "purify_01"
    ]))

    enemy = world.add_entity(Entity("BOSS"))
    enemy.add_component(AIControlledComponent())
    enemy.add_component(HealthComponent(enemy, event_bus, hp=150, max_hp=150))
    enemy.add_component(ManaComponent(mana=500, max_mana=500))
    enemy.add_component(DefenseComponent(defense_value=100))
    enemy.add_component(SpeedComponent(speed=50))
    enemy.add_component(ThornsComponent(thorns_percentage=0.5))
    enemy.add_component(StatusEffectContainerComponent())
    enemy.add_component(SpellListComponent(spells=["fireball_01"]))


    # 4. 启动游戏世界
    print("开始游戏...")
    world.start()