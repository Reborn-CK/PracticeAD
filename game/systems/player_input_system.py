# game/systems/player_input_system.py
from ..core.event_bus import EventBus, GameEvent
from ..core.enums import EventName, BattleTurnRule
from ..core.payloads import (ActionRequestPayload, UIDisplayOptionsPayload, 
                             UIMessagePayload, CastSpellRequestPayload, StatQueryPayload, ActionAfterActPayload,
                             UseItemRequestPayload)
from ..core.components import (PlayerControlledComponent, SpellListComponent, UltimateSpellListComponent,
                               AIControlledComponent, DeadComponent, HealthComponent, SpeedComponent,
                               InventoryComponent, ManaComponent, EnergyComponent, UltimateChargeComponent)
from .data_manager import DataManager
from ..core.entity import Entity
from .ui_system import UISystem
from .turn_manager_system import TurnManagerSystem
import time

class PlayerInputSystem:
    def __init__(self, event_bus: EventBus, data_manager: DataManager, world: 'World'): # type: ignore
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.world = world
        event_bus.subscribe(EventName.ACTION_REQUEST, self.on_action_request)
        event_bus.subscribe(EventName.PLAYER_SPELL_CHOICE, self.on_player_spell_choice)
        event_bus.subscribe(EventName.PLAYER_TARGET_CHOICE, self.on_player_target_choice)
        event_bus.subscribe(EventName.PLAYER_ITEM_CHOICE, self.on_player_item_choice)
        event_bus.subscribe(EventName.PLAYER_ITEM_TARGET_CHOICE, self.on_player_item_target_choice)
    
    def on_action_request(self, event: GameEvent):
        actor = event.payload.acting_entity
        if actor.has_component(PlayerControlledComponent):
            turn_manager = self.world.get_system(TurnManagerSystem)
            if turn_manager and turn_manager.battle_turn_rule == BattleTurnRule.AP_BASED:
                ui_system = self.world.get_system(UISystem)
                if ui_system:
                    ui_system.display_status_panel()
            
            # 显示主菜单
            self._show_main_menu(actor)
    
    def _show_main_menu(self, actor: Entity):
        """显示主菜单"""
        options = ["法术", "终极技能", "物品", "查看状态"]
        self.event_bus.dispatch(GameEvent(EventName.UI_DISPLAY_OPTIONS, UIDisplayOptionsPayload(
            prompt=f"[{actor.name}] 的回合，请选择行动:",
            options=options,
            response_event_name=EventName.PLAYER_SPELL_CHOICE,  # 复用事件名
            context={"actor": actor, "menu_type": "main"}
        )))
    
    def _show_spell_menu(self, actor: Entity):
        """显示法术菜单"""
        spell_comp = actor.get_component(SpellListComponent)
        options = []
        
        for sid in spell_comp.spells:
            spell_data = self.data_manager.get_spell_data(sid)
            spell_name = spell_data.get('name', '未知法术') if spell_data else '未知法术'
            
            # 获取法力消耗、能量消耗和终极技能消耗
            mana_cost = self.data_manager.get_spell_cost(sid)
            energy_cost = self.data_manager.get_spell_energy_cost(sid)
            ultimate_cost = self.data_manager.get_spell_ultimate_cost(sid)
            
            # 检查资源类型
            cost_data = spell_data.get('cost', {}) if spell_data else {}
            resource_type = cost_data.get('resource', 'mana') if isinstance(cost_data, dict) else 'mana'
            
            # 构建消耗显示字符串
            cost_str = ""
            if resource_type == 'null':
                cost_str = "(无消耗)"
            elif resource_type == 'ultimate':
                # 获取当前充能量
                ultimate_comp = actor.get_component(UltimateChargeComponent)
                current_charge = ultimate_comp.charge if ultimate_comp else 0
                cost_str = f"(充能量: {current_charge:.0f}%)"
            elif mana_cost > 0 and energy_cost > 0:
                cost_str = f"(MP: {mana_cost}, Energy: {energy_cost})"
            elif mana_cost > 0:
                cost_str = f"(MP: {mana_cost})"
            elif energy_cost > 0:
                cost_str = f"(Energy: {energy_cost})"
            else:
                cost_str = "(无消耗)"
            
            options.append(f"{spell_name} {cost_str}")
        
        # 添加返回选项
        options.append("返回上级菜单")
        # 添加结束回合选项
        options.append("结束回合")
        
        self.event_bus.dispatch(GameEvent(EventName.UI_DISPLAY_OPTIONS, UIDisplayOptionsPayload(
            prompt=f"选择法术:",
            options=options,
            response_event_name=EventName.PLAYER_SPELL_CHOICE,
            context={"actor": actor, "menu_type": "spell"}
        )))
    
    def _show_ultimate_spell_menu(self, actor: Entity):
        """显示终极技能菜单"""
        options = []
        
        # 从角色的终极技能列表中获取技能
        ultimate_comp = actor.get_component(UltimateSpellListComponent)
        if not ultimate_comp or not ultimate_comp.ultimate_spells:
            options.append("没有可用的终极技能")
        else:
            for spell_id in ultimate_comp.ultimate_spells:
                spell_data = self.data_manager.get_spell_data(spell_id)
                if spell_data:
                    spell_name = spell_data.get('name', '未知终极技能')
                    ultimate_cost = self.data_manager.get_spell_ultimate_cost(spell_id)
                    
                    # 获取当前充能量
                    charge_comp = actor.get_component(UltimateChargeComponent)
                    current_charge = charge_comp.charge if charge_comp else 0
                    
                    # 检查是否有足够的充能
                    if current_charge >= ultimate_cost:
                        cost_str = f"(消耗: {ultimate_cost}% 充能)"
                    else:
                        cost_str = f"(充能不足: 需要{ultimate_cost}%, 当前{current_charge:.0f}%)"
                    
                    options.append(f"{spell_name} {cost_str}")
        
        # 添加返回选项
        options.append("返回上级菜单")
        
        self.event_bus.dispatch(GameEvent(EventName.UI_DISPLAY_OPTIONS, UIDisplayOptionsPayload(
            prompt=f"选择终极技能:",
            options=options,
            response_event_name=EventName.PLAYER_SPELL_CHOICE,
            context={"actor": actor, "menu_type": "ultimate", "ultimate_spells": ultimate_comp.ultimate_spells if ultimate_comp else []}
        )))
    
    def _show_item_menu(self, actor: Entity):
        """显示物品菜单"""
        inventory_comp = actor.get_component(InventoryComponent)
        options = []
        
        if inventory_comp:
            items = inventory_comp.get_all_items()
            if items:
                for item in items:
                    item_data = self.data_manager.get_item_data(item.item_id)
                    if item_data:
                        item_name = item_data.get('name', '未知物品')
                        item_icon = item_data.get('icon', '📦')
                        options.append(f"{item_icon} {item_name} x{item.quantity}")
            else:
                options.append("物品栏为空")
        else:
            options.append("没有物品栏")
        
        # 添加返回选项
        options.append("返回上级菜单")
        
        self.event_bus.dispatch(GameEvent(EventName.UI_DISPLAY_OPTIONS, UIDisplayOptionsPayload(
            prompt=f"选择物品:",
            options=options,
            response_event_name=EventName.PLAYER_ITEM_CHOICE,
            context={"actor": actor, "menu_type": "item"}
        )))
    
    def _show_status_menu(self, actor: Entity):
        """显示状态菜单"""
        # 获取角色状态信息
        from ..core.components import (HealthComponent, ManaComponent, StatsComponent, 
                                      EquipmentComponent, SpeedComponent, ShieldComponent,
                                      StatusEffectContainerComponent)
        
        health_comp = actor.get_component(HealthComponent)
        mana_comp = actor.get_component(ManaComponent)
        stats_comp = actor.get_component(StatsComponent)
        equipment_comp = actor.get_component(EquipmentComponent)
        speed_comp = actor.get_component(SpeedComponent)
        shield_comp = actor.get_component(ShieldComponent)
        status_comp = actor.get_component(StatusEffectContainerComponent)
        
        # 构建状态信息
        status_lines = []
        status_lines.append(f"**{actor.name} 的状态**")
        status_lines.append("=" * 30)
        
        # 基础属性
        if health_comp:
            status_lines.append(f"生命值: {health_comp.hp:.0f}/{health_comp.max_hp:.0f}")
        if mana_comp:
            status_lines.append(f"法力值: {mana_comp.mana:.0f}/{mana_comp.max_mana:.0f}")
        
        # 速度
        if speed_comp:
            base_speed = speed_comp.speed
            final_speed = actor.get_final_stat("speed", base_speed)
            speed_bonus = final_speed - base_speed
            if speed_bonus > 0:
                status_lines.append(f"速度: {base_speed:.0f} + {speed_bonus:.0f} = {final_speed:.0f}")
            else:
                status_lines.append(f"速度: {final_speed:.0f}")
        
        # 护盾
        if shield_comp and shield_comp.shield_value > 0:
            status_lines.append(f"护盾: {shield_comp.shield_value:.0f}")
        
        # 攻击力和防御力分解
        if stats_comp:
            # 获取基础属性
            base_attack = getattr(stats_comp, '_base_attack', 0)
            base_defense = getattr(stats_comp, '_base_defense', 0)
            
            # 获取装备加成
            equipment_bonus_attack = 0
            equipment_bonus_defense = 0
            if equipment_comp:
                for equipment_item in equipment_comp.get_all_equipped_items():
                    current_stats = equipment_item.get_current_stats()
                    equipment_bonus_attack += current_stats.get('attack', 0)
                    equipment_bonus_defense += current_stats.get('defense', 0)
            
            # 计算buff加成
            buff_attack = stats_comp.attack - base_attack - equipment_bonus_attack
            buff_defense = stats_comp.defense - base_defense - equipment_bonus_defense
            
            # 显示攻击力分解
            attack_line = f"攻击力: {base_attack:.1f}"
            if equipment_bonus_attack > 0:
                attack_line += f" + {equipment_bonus_attack:.1f}(装备)"
            if buff_attack > 0:
                attack_line += f" + {buff_attack:.1f}(增益)"
            elif buff_attack < 0:
                attack_line += f" - {abs(buff_attack):.1f}(减益)"
            attack_line += f" = {stats_comp.attack:.1f}"
            status_lines.append(attack_line)
            
            # 显示防御力分解
            defense_line = f"防御力: {base_defense:.1f}"
            if equipment_bonus_defense > 0:
                defense_line += f" + {equipment_bonus_defense:.1f}(装备)"
            if buff_defense > 0:
                defense_line += f" + {buff_defense:.1f}(增益)"
            elif buff_defense < 0:
                defense_line += f" - {abs(buff_defense):.1f}(减益)"
            defense_line += f" = {stats_comp.defense:.1f}"
            status_lines.append(defense_line)
        
        # 装备信息
        if equipment_comp:
            equipped_items = equipment_comp.get_all_equipped_items()
            if equipped_items:
                status_lines.append("")
                status_lines.append("**装备信息**")
                status_lines.append("-" * 20)
                
                for equipment_item in equipped_items:
                    durability_percent = equipment_item.get_durability_percentage()
                    durability_color = "🟢" if durability_percent > 50 else "🟡" if durability_percent > 20 else "🔴"
                    status_lines.append(f"{durability_color} {equipment_item.name}")
                    status_lines.append(f"   耐久: {equipment_item.current_durability}/{equipment_item.max_durability} ({durability_percent:.1f}%)")
                    
                    # 显示装备属性
                    current_stats = equipment_item.get_current_stats()
                    if current_stats:
                        stat_lines = []
                        for stat_name, stat_value in current_stats.items():
                            if stat_value > 0:
                                stat_lines.append(f"{stat_name}: +{stat_value:.1f}")
                        if stat_lines:
                            status_lines.append(f"   属性: {', '.join(stat_lines)}")
            else:
                status_lines.append("")
                status_lines.append("**装备信息**")
                status_lines.append("-" * 20)
                status_lines.append("无装备")
        
        # 状态效果
        if status_comp and status_comp.effects:
            status_lines.append("")
            status_lines.append("**状态效果**")
            status_lines.append("-" * 20)
            
            # 分离buff和debuff
            buffs = []
            debuffs = []
            
            for effect in status_comp.effects:
                effect_info = f"{effect.name}"
                if effect.duration > 0:
                    effect_info += f" ({effect.duration}回合)"
                if effect.stacking == "stack_intensity" and effect.stack_count > 1:
                    effect_info += f" x{effect.stack_count}"
                
                # 根据效果类型分类
                if effect.category in ["buff", "heal", "shield"]:
                    buffs.append(f"✅ {effect_info}")
                else:
                    debuffs.append(f"❌ {effect_info}")
            
            # 显示buff
            if buffs:
                status_lines.append("增益效果:")
                for buff in buffs:
                    status_lines.append(f"  {buff}")
            
            # 显示debuff
            if debuffs:
                if buffs:  # 如果有buff，添加空行
                    status_lines.append("")
                status_lines.append("减益效果:")
                for debuff in debuffs:
                    status_lines.append(f"  {debuff}")
        elif status_comp:
            status_lines.append("")
            status_lines.append("**状态效果**")
            status_lines.append("-" * 20)
            status_lines.append("无状态效果")
        
        # 显示状态信息
        status_text = "\n".join(status_lines)
        self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(status_text)))
        
        # 直接返回主菜单，不需要额外的按键确认
        self._show_main_menu(actor)
    
    def on_player_spell_choice(self, event: GameEvent):
        context = event.payload["context"]
        actor = context["actor"]
        menu_type = context.get("menu_type", "spell")
        choice_index = event.payload["choice_index"]
        
        if menu_type == "main":
            # 主菜单选择
            if choice_index == 0:  # 法术
                self._show_spell_menu(actor)
            elif choice_index == 1:  # 终极技能
                self._show_ultimate_spell_menu(actor)
            elif choice_index == 2:  # 物品
                self._show_item_menu(actor)
            elif choice_index == 3:  # 查看状态
                self._show_status_menu(actor)
        elif menu_type == "spell":
            # 法术菜单选择
            spell_comp = actor.get_component(SpellListComponent)
            if choice_index < len(spell_comp.spells):
                # 选择了法术
                spell_id = spell_comp.spells[choice_index]
                self._handle_spell_selection(actor, spell_id)
            elif choice_index == len(spell_comp.spells):
                # 选择了返回
                self._show_main_menu(actor)
            elif choice_index == len(spell_comp.spells) + 1:
                # 选择了结束回合
                self.event_bus.dispatch(GameEvent(EventName.ACTION_AFTER_ACT, ActionAfterActPayload(actor)))
        elif menu_type == "ultimate":
            # 终极技能菜单选择
            ultimate_spells = context.get("ultimate_spells", [])
            if choice_index < len(ultimate_spells):
                # 选择了终极技能
                spell_id = ultimate_spells[choice_index]
                self._handle_spell_selection(actor, spell_id)
            else:
                # 选择了返回
                self._show_main_menu(actor)
        elif menu_type == "status":
            # 状态菜单选择 - 这个分支现在不会被执行，因为状态查看直接返回主菜单
            pass
    
    def _handle_spell_selection(self, actor: Entity, spell_id: str):
        """处理法术选择"""
        spell_data = self.data_manager.get_spell_data(spell_id)
        target_type = self.data_manager.get_spell_target_type(spell_id)
        
        # 在目标选择前检查技能消耗
        mana_cost = self.data_manager.get_spell_cost(spell_id)
        energy_cost = self.data_manager.get_spell_energy_cost(spell_id)
        ultimate_cost = self.data_manager.get_spell_ultimate_cost(spell_id)
        
        # 检查是否是终极技能
        is_ultimate = False
        ultimate_comp = actor.get_component(UltimateSpellListComponent)
        if ultimate_comp and spell_id in ultimate_comp.ultimate_spells:
            is_ultimate = True
        
        # 检查法力消耗
        if mana_cost > 0:
            mana_comp = actor.get_component(ManaComponent)
            if not mana_comp or mana_comp.mana < mana_cost:
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**提示**: [{actor.name}] 法力不足！需要 {mana_cost} 点法力值")))
                if is_ultimate:
                    self._show_ultimate_spell_menu(actor)
                else:
                    self._show_spell_menu(actor)
                return
        
        # 检查能量消耗
        if energy_cost > 0:
            energy_comp = actor.get_component(EnergyComponent)
            if not energy_comp or energy_comp.energy < energy_cost:
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**提示**: [{actor.name}] 能量不足！需要 {energy_cost} 点能量值")))
                if is_ultimate:
                    self._show_ultimate_spell_menu(actor)
                else:
                    self._show_spell_menu(actor)
                return
        
        # 检查终极技能消耗
        if ultimate_cost > 0:
            ultimate_comp = actor.get_component(UltimateChargeComponent)
            if not ultimate_comp or ultimate_comp.charge < ultimate_cost:
                self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(f"**提示**: [{actor.name}] 充能未就绪！需要 {ultimate_cost}% 充能值，当前 {ultimate_comp.charge:.0f}%")))
                if is_ultimate:
                    self._show_ultimate_spell_menu(actor)
                else:
                    self._show_spell_menu(actor)
                return
        
        # 根据法术目标类型确定可选目标
        available_targets = []
        target_descriptions = []

        def get_desc(e: Entity)->str:
            hp_comp = e.get_component(HealthComponent)
            speed_comp = e.get_component(SpeedComponent)
            hp = hp_comp.hp if hp_comp else 0
            speed = speed_comp.speed if speed_comp else 0
            final_speed = e.get_final_stat("speed", speed)
            return f"{e.name} (HP: {hp:.0f}, Speed: {final_speed:.0f})"
        
        if target_type == "enemy":
            available_targets = [e for e in self.world.entities if e.has_component(AIControlledComponent) and not e.has_component(DeadComponent)]
            target_descriptions = [get_desc(e) for e in available_targets]
        elif target_type == "ally":
            available_targets = [e for e in self.world.entities if e.has_component(PlayerControlledComponent) and not e.has_component(DeadComponent)]
            target_descriptions = [get_desc(e) for e in available_targets]
        else:
            available_targets = [e for e in self.world.entities if not e.has_component(DeadComponent)]
            target_descriptions = [get_desc(e) for e in available_targets]
        
        if not available_targets:
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload("**提示**: 没有可用的目标!")))
            if is_ultimate:
                self._show_ultimate_spell_menu(actor)
            else:
                self._show_spell_menu(actor)
            return
        
        # 添加返回选项
        if is_ultimate:
            target_descriptions.append("返回终极技能菜单")
        else:
            target_descriptions.append("返回法术菜单")
        
        # 显示目标选择
        spell_name = spell_data.get('name', '未知法术') if spell_data else '未知法术'
        self.event_bus.dispatch(GameEvent(EventName.UI_DISPLAY_OPTIONS, UIDisplayOptionsPayload(
            prompt=f"选择 {spell_name} 的目标:",
            options=target_descriptions,
            response_event_name=EventName.PLAYER_TARGET_CHOICE,
            context={"caster": actor, "spell_id": spell_id, "available_targets": available_targets, "is_ultimate": is_ultimate}
        )))
    
    def on_player_target_choice(self, event: GameEvent):
        context = event.payload["context"]
        caster = context["caster"]
        spell_id = context["spell_id"]
        available_targets = context["available_targets"]
        is_ultimate = context.get("is_ultimate", False)
        choice_index = event.payload["choice_index"]
        
        if choice_index < len(available_targets):
            # 选择了目标
            target = available_targets[choice_index]
            # 只派发施法请求，不立即结束回合
            # 施法系统会在施法成功后派发ACTION_AFTER_ACT事件
            self.event_bus.dispatch(GameEvent(EventName.CAST_SPELL_REQUEST, CastSpellRequestPayload(caster, target, spell_id)))
        else:
            # 选择了返回
            if is_ultimate:
                self._show_ultimate_spell_menu(caster)
            else:
                self._show_spell_menu(caster)
    
    def on_player_item_choice(self, event: GameEvent):
        context = event.payload["context"]
        actor = context["actor"]
        choice_index = event.payload["choice_index"]
        
        inventory_comp = actor.get_component(InventoryComponent)
        if not inventory_comp:
            self._show_main_menu(actor)
            return
        
        items = inventory_comp.get_all_items()
        if choice_index < len(items):
            # 选择了物品
            item = items[choice_index]
            self._handle_item_selection(actor, item)
        else:
            # 选择了返回
            self._show_main_menu(actor)
    
    def _handle_item_selection(self, actor: Entity, item):
        """处理物品选择"""
        from ..core.components import HealthComponent, ManaComponent
        
        item_data = self.data_manager.get_item_data(item.item_id)
        if not item_data:
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload("**错误**: 物品数据不存在!")))
            self._show_item_menu(actor)
            return
        
        target_type = item_data.get('target_type', 'self')
        
        # 根据物品目标类型确定可选目标
        available_targets = []
        target_descriptions = []

        def get_desc(e: Entity)->str:
            hp_comp = e.get_component(HealthComponent)
            mana_comp = e.get_component(ManaComponent)
            hp = hp_comp.hp if hp_comp else 0
            max_hp = hp_comp.max_hp if hp_comp else 0
            mana = mana_comp.mana if mana_comp else 0
            max_mana = mana_comp.max_mana if mana_comp else 0
            return f"{e.name} (HP: {hp:.0f}/{max_hp:.0f}, MP: {mana:.0f}/{max_mana:.0f})"
        
        if target_type == "self":
            available_targets = [actor]
            target_descriptions = [get_desc(actor)]
        elif target_type == "ally":
            available_targets = [e for e in self.world.entities if e.has_component(PlayerControlledComponent) and not e.has_component(DeadComponent)]
            target_descriptions = [get_desc(e) for e in available_targets]
        elif target_type == "enemy":
            available_targets = [e for e in self.world.entities if e.has_component(AIControlledComponent) and not e.has_component(DeadComponent)]
            target_descriptions = [get_desc(e) for e in available_targets]
        else:
            available_targets = [e for e in self.world.entities if not e.has_component(DeadComponent)]
            target_descriptions = [get_desc(e) for e in available_targets]
        
        if not available_targets:
            self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload("**提示**: 没有可用的目标!")))
            self._show_item_menu(actor)
            return
        
        # 添加返回选项
        target_descriptions.append("返回物品菜单")
        
        # 显示目标选择
        item_name = item_data.get('name', '未知物品')
        self.event_bus.dispatch(GameEvent(EventName.UI_DISPLAY_OPTIONS, UIDisplayOptionsPayload(
            prompt=f"选择 {item_name} 的使用目标:",
            options=target_descriptions,
            response_event_name=EventName.PLAYER_ITEM_TARGET_CHOICE,
            context={"user": actor, "item": item, "available_targets": available_targets}
        )))
    
    def on_player_item_target_choice(self, event: GameEvent):
        context = event.payload["context"]
        user = context["user"]
        item = context["item"]
        available_targets = context["available_targets"]
        choice_index = event.payload["choice_index"]
        
        if choice_index < len(available_targets):
            # 选择了目标
            target = available_targets[choice_index]
            self.event_bus.dispatch(GameEvent(EventName.USE_ITEM_REQUEST, UseItemRequestPayload(user, item.item_id, target)))
            self.event_bus.dispatch(GameEvent(EventName.ACTION_AFTER_ACT, ActionAfterActPayload(user)))
        else:
            # 选择了返回
            self._show_item_menu(user)