from typing import Dict, Optional, List
from ..core.entity import Entity
from ..core.components import InventoryComponent, HealthComponent, ManaComponent, StatusEffectContainerComponent
from ..core.event_bus import EventBus
from ..core.enums import EventName
from ..core.payloads import LogRequestPayload, DamageRequestPayload, HealRequestPayload, ManaChangeRequestPayload
from ..core.event_bus import GameEvent
from .data_manager import DataManager

class ItemSystem:
    """物品系统，管理物品的使用、效果等"""
    
    def __init__(self, event_bus: EventBus, data_manager: DataManager, world=None):
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.world = world
        
        # 订阅相关事件
        self.event_bus.subscribe(EventName.USE_ITEM_REQUEST, self._on_use_item_request)
    
    def use_item(self, user: Entity, item_id: str, target: Entity = None) -> bool:
        """使用物品"""
        # 检查用户是否有物品栏
        inventory_comp = user.get_component(InventoryComponent)
        if not inventory_comp:
            return False
        
        # 检查是否有该物品
        if not inventory_comp.has_item(item_id):
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[ITEM]", f"❌ {user.name} 没有 {item_id} 这个物品"
            )))
            return False
        
        # 获取物品数据
        item_data = self.data_manager.get_item_data(item_id)
        if not item_data:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[ITEM]", f"❌ 未找到物品数据: {item_id}"
            )))
            return False
        
        # 确定目标
        if target is None:
            target = self._determine_target(user, item_data)
        
        if target is None:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[ITEM]", f"❌ 无法确定 {item_data['name']} 的使用目标"
            )))
            return False
        
        # 检查使用条件
        if not self._check_use_condition(user, target, item_data):
            return False
        
        # 应用物品效果
        success = self._apply_item_effect(user, target, item_data)
        
        if success:
            # 移除物品
            inventory_comp.remove_item(item_id, 1)
            
            # 记录使用日志
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[ITEM]", f"✅ {user.name} 使用了 {item_data['name']}"
            )))
        
        return success
    
    def _determine_target(self, user: Entity, item_data: Dict) -> Optional[Entity]:
        """确定物品使用目标"""
        if not self.world:
            return None
            
        target_type = item_data.get('target_type', 'self')
        
        if target_type == 'self':
            return user
        elif target_type == 'ally':
            # 选择友军目标（玩家控制的实体）
            from ..core.components import PlayerControlledComponent, DeadComponent
            allies = [e for e in self.world.entities 
                     if e.has_component(PlayerControlledComponent) and not e.has_component(DeadComponent)]
            return allies[0] if allies else None
        elif target_type == 'enemy':
            # 选择敌人目标（AI控制的实体）
            from ..core.components import AIControlledComponent, DeadComponent
            enemies = [e for e in self.world.entities 
                      if e.has_component(AIControlledComponent) and not e.has_component(DeadComponent)]
            return enemies[0] if enemies else None
        else:
            # 任意目标
            from ..core.components import DeadComponent
            all_entities = [e for e in self.world.entities if not e.has_component(DeadComponent)]
            return all_entities[0] if all_entities else None
    
    def _check_use_condition(self, user: Entity, target: Entity, item_data: Dict) -> bool:
        """检查物品使用条件"""
        use_condition = item_data.get('use_condition', 'always')
        
        if use_condition == 'always':
            return True
        elif use_condition == 'low_hp':
            # 检查目标生命值是否较低
            health_comp = target.get_component(HealthComponent)
            if health_comp:
                hp_percentage = (health_comp.hp / health_comp.max_hp) * 100
                return hp_percentage < 50  # 生命值低于50%时可以使用
        elif use_condition == 'in_combat':
            # 检查是否在战斗中
            return True  # 简化处理，总是认为在战斗中
        
        return False
    
    def _apply_item_effect(self, user: Entity, target: Entity, item_data: Dict) -> bool:
        """应用物品效果"""
        effect_type = item_data.get('effect_type')
        effect_value = item_data.get('effect_value')
        
        if effect_type == 'heal':
            return self._apply_heal_effect(target, effect_value)
        elif effect_type == 'mana':
            return self._apply_mana_effect(target, effect_value)
        elif effect_type == 'damage':
            damage_type = item_data.get('damage_type', 'pure')
            return self._apply_damage_effect(user, target, effect_value, damage_type)
        elif effect_type == 'cure_status':
            return self._apply_cure_status_effect(target, effect_value)
        elif effect_type == 'status_effect':
            return self._apply_status_effect(user, target, effect_value)
        elif effect_type == 'revive':
            return self._apply_revive_effect(target, effect_value)
        elif effect_type == 'escape':
            return self._apply_escape_effect(user, effect_value)
        elif effect_type == 'experience':
            return self._apply_experience_effect(user, effect_value)
        else:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[ITEM]", f"❌ 未知的物品效果类型: {effect_type}"
            )))
            return False
    
    def _apply_heal_effect(self, target: Entity, heal_amount: float) -> bool:
        """应用治疗效果"""
        self.event_bus.dispatch(GameEvent(EventName.HEAL_REQUEST, HealRequestPayload(
            caster=None,
            target=target,
            source_spell_id="item",
            source_spell_name="物品",
            base_heal=heal_amount,
            heal_type="item"
        )))
        return True
    
    def _apply_mana_effect(self, target: Entity, mana_amount: float) -> bool:
        """应用法力恢复效果"""
        self.event_bus.dispatch(GameEvent(EventName.MANA_CHANGE_REQUEST, ManaChangeRequestPayload(
            target=target,
            amount=mana_amount,
            change_type="restore"
        )))
        return True
    
    def _apply_damage_effect(self, user: Entity, target: Entity, damage_amount: float, damage_type: str) -> bool:
        """应用伤害效果"""
        self.event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
            caster=user,
            target=target,
            source_spell_id="item",
            source_spell_name="物品",
            base_damage=damage_amount,
            damage_type=damage_type
        )))
        return True
    
    def _apply_cure_status_effect(self, target: Entity, status_type: str) -> bool:
        """应用状态效果治疗"""
        # 这里需要实现状态效果移除逻辑
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "[ITEM]", f"✅ {target.name} 的 {status_type} 状态被治愈"
        )))
        return True
    
    def _apply_status_effect(self, user: Entity, target: Entity, status_effect: str) -> bool:
        """应用状态效果"""
        # 这里需要实现状态效果应用逻辑
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "[ITEM]", f"✅ {target.name} 被施加了 {status_effect} 状态"
        )))
        return True
    
    def _apply_revive_effect(self, target: Entity, revive_percentage: float) -> bool:
        """应用复活效果"""
        from ..core.components import DeadComponent, HealthComponent
        
        if not target.has_component(DeadComponent):
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
                "[ITEM]", f"❌ {target.name} 没有死亡，无法复活"
            )))
            return False
        
        # 移除死亡状态
        target.remove_component(DeadComponent)
        
        # 恢复生命值
        health_comp = target.get_component(HealthComponent)
        if health_comp:
            revive_hp = health_comp.max_hp * (revive_percentage / 100)
            health_comp.hp = revive_hp
        
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "[ITEM]", f"⚡ {target.name} 被复活了！"
        )))
        return True
    
    def _apply_escape_effect(self, user: Entity, escape_chance: float) -> bool:
        """应用逃脱效果"""
        # 这里需要实现逃脱逻辑
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "[ITEM]", f"📜 {user.name} 使用了传送卷轴，成功逃脱！"
        )))
        return True
    
    def _apply_experience_effect(self, user: Entity, exp_amount: float) -> bool:
        """应用经验值效果"""
        # 这里需要实现经验值增加逻辑
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload(
            "[ITEM]", f"⭐ {user.name} 获得了 {exp_amount} 点经验值"
        )))
        return True
    
    def _on_use_item_request(self, event):
        """处理使用物品请求事件"""
        payload = event.payload
        user = payload.user
        item_id = payload.item_id
        target = payload.target
        
        self.use_item(user, item_id, target)