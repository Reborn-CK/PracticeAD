from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from ...core.event_bus import EventBus, GameEvent
from ...core.enums import EventName
from ...core.payloads import (DamageRequestPayload, HealRequestPayload, GainShieldPayload,
                              EffectResolutionPayload, ResourceChangeEntry, LogRequestPayload,
                              UIMessagePayload)
from ...core.components import (HealthComponent, DefenseComponent, ThornsComponent)
from .damage_modifiers import DamageModifier, DefenseHandler, ResistanceHandler
from .heal_modifiers import HealModifier, GrievousWoundsHandler

# 依赖的系统和数据管理器
from ..data_manager import DataManager
from ..passive_ability_system import PassiveAbilitySystem
from ...core.entity import Entity

@dataclass
class DamageResolutionContext: 
    caster: 'Entity'; 
    target: 'Entity'; 
    source_spell: str; 
    damage_type: str; 
    current_damage: float; 
    log: list = field(default_factory=list)

@dataclass
class HealResolutionContext: 
    caster: 'Entity'; 
    target: 'Entity'; 
    source_spell_id: str
    source_spell_name: str
    current_heal: float; 
    log: list = field(default_factory=list)

class CombatResolutionSystem:
    """ <<< 职责变更: 伤害计算的每一步都派发LOG事件 >>> """
    def __init__(self, event_bus: EventBus, data_manager: 'DataManager' = None, passive_system: 'PassiveAbilitySystem' = None): # type: ignore
        self.event_bus = event_bus
        self.data_manager = data_manager
        self.passive_system = passive_system  # 添加对被动系统的引用
        self.damage_pipeline: list[DamageModifier] = [DefenseHandler(),ResistanceHandler()]
        self.heal_pipeline: list[HealModifier] = [GrievousWoundsHandler()]
        event_bus.subscribe(EventName.DAMAGE_REQUEST, self.on_damage_request)
        event_bus.subscribe(EventName.HEAL_REQUEST, self.on_heal_request)
        event_bus.subscribe(EventName.GAIN_SHIELD_REQUEST, self.on_gain_shield_request)
    
    def on_damage_request(self, event: GameEvent):
        payload: DamageRequestPayload = event.payload
        
        # 获取原始伤害和当前伤害
        original_damage = payload.original_base_damage or payload.base_damage
        current_damage = payload.base_damage
        
        context = DamageResolutionContext(
            caster=payload.caster, 
            target=payload.target, 
            source_spell=payload.source_spell_id,
            damage_type=payload.damage_type, 
            current_damage=payload.base_damage,
            log=[]
        )
        
        # 如果原始伤害和当前伤害不同，说明有交互修改
        if abs(original_damage - current_damage) > 0.1:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[COMBAT]", f"原始伤害: {original_damage:.1f}，交互后基础伤害: {current_damage:.1f}")))
        else:
            self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[COMBAT]", f"基础伤害: {context.current_damage:.1f}")))
        
        # 记录护盾抵消的伤害
        shield_blocked = 0.0
        original_damage = context.current_damage
        
        for modifier in self.damage_pipeline:
            if isinstance(modifier, DefenseHandler):
                # 在护盾处理前记录当前伤害
                pre_shield_damage = context.current_damage
                modifier.process(context, self.event_bus)
                # 计算护盾抵消的伤害
                shield_blocked += pre_shield_damage - context.current_damage
            else:
                modifier.process(context, self.event_bus)
        
        final_damage = context.current_damage
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[COMBAT]", f"最终伤害: {final_damage:.1f}")))
        
        if (health_comp := payload.target.get_component(HealthComponent)):
            health_comp.hp -= final_damage

            # 获取被动触发信息
            passive_triggers = []
            if self.passive_system:
                passive_triggers = self.passive_system.get_and_clear_pending_triggers()
            
            # 准备资源变化列表
            resource_changes = [ResourceChangeEntry("health", -final_damage, health_comp.hp, health_comp.max_hp)]
            
            # 检查是否是反伤伤害
            is_reflection = payload.is_reflection
            
            # 先发送主伤害的播报事件
            self.event_bus.dispatch(GameEvent(EventName.EFFECT_RESOLUTION_COMPLETE, EffectResolutionPayload(
                caster=payload.caster, 
                target=payload.target, 
                source_spell=payload.source_spell_id,
                resource_changes=resource_changes,
                shield_blocked=shield_blocked,
                passive_triggers=passive_triggers,
                log_reflection=is_reflection
            )))
            
            # --- 反伤处理逻辑（在主伤害播报之后） ---
            if final_damage > 0 and payload.can_be_reflected and not payload.is_reflection and (thorns_comp := payload.target.get_component(ThornsComponent)):
                reflection_damage = final_damage * thorns_comp.thorns_percentage
                self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[PASSIVE]", f"{payload.target.name} 的反伤对 {payload.caster.name} 造成了 {reflection_damage:.1f} 点伤害")))
                self.event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, DamageRequestPayload(
                    caster=payload.target, 
                    target=payload.caster,
                    source_spell_id=payload.source_spell_id,
                    source_spell_name=payload.source_spell_name,
                    base_damage=reflection_damage, 
                    damage_type=payload.damage_type,
                    is_reflection=True
                )))
            
            # --- 生命偷取处理逻辑（在主伤害播报之后） ---
            if final_damage > 0 and payload.lifesteal_ratio:
                lifesteal_amount = final_damage * payload.lifesteal_ratio
                if lifesteal_amount > 0:
                    self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[COMBAT]", f"生命偷取: {lifesteal_amount:.1f} 点")))
                    self.event_bus.dispatch(GameEvent(EventName.HEAL_REQUEST, HealRequestPayload(
                        caster=payload.caster, 
                        target=payload.caster,
                        source_spell_id="lifesteal",
                        source_spell_name="吸血",
                        base_heal=lifesteal_amount,
                        heal_type="blood",
                        overheal_amount=0
                    )))
    
    def on_heal_request(self, event: GameEvent):
        payload: HealRequestPayload = event.payload
        context = HealResolutionContext(
            caster=payload.caster, 
            target=payload.target, 
            source_spell_id=payload.source_spell_id,
            source_spell_name=payload.source_spell_name,
            current_heal=payload.base_heal
        )
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[COMBAT]", f"基础治疗: {context.current_heal:.1f}")))
        for modifier in self.heal_pipeline:
            modifier.process(context, self.event_bus)
        final_heal = context.current_heal
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[COMBAT]", f"最终治疗: {final_heal:.1f}")))
        if (health_comp := payload.target.get_component(HealthComponent)):
            old_hp = health_comp.hp
            health_comp.hp = min(health_comp.hp + final_heal, health_comp.max_hp)
            actual_heal = health_comp.hp - old_hp
            # 计算溢出量
            payload.overheal_amount = max(0, final_heal - actual_heal)

            # 检查是否有溢出治疗buff
            if payload.overheal_amount > 0:
                # 首先检查法术本身的溢疗转换
                if payload.overheal_conversion_rate is not None:
                    shield_gain = payload.overheal_amount * payload.overheal_conversion_rate
                    if shield_gain > 0:
                        self.event_bus.dispatch(GameEvent(EventName.UI_MESSAGE, UIMessagePayload(
                            f"**溢疗转换**: {payload.target.name} 将 {payload.overheal_amount:.1f} 点溢出治疗转化为 {shield_gain:.1f} 点护盾"
                        )))
                        self.event_bus.dispatch(GameEvent(EventName.GAIN_SHIELD_REQUEST, GainShieldPayload(
                            target=payload.target, source=payload.source_spell_name, amount=shield_gain
                        )))
                
                # 然后检查状态效果带来的溢疗转换
                container = payload.target.get_component('StatusEffectContainerComponent') # type: ignore
                if container:
                    for effect in container.effects:
                        effect.logic.on_heal(payload, effect, self.event_bus)
            # 获取被动触发信息
            passive_triggers = []
            if self.passive_system:
                passive_triggers = self.passive_system.get_and_clear_pending_triggers()
            
            # 准备资源变化列表
            resource_changes = [ResourceChangeEntry("health", actual_heal, health_comp.hp, health_comp.max_hp)]
            
            # 如果有护盾变化，添加到资源变化列表
            if payload.overheal_amount > 0 and payload.overheal_conversion_rate is not None:
                shield_gain = payload.overheal_amount * payload.overheal_conversion_rate
                if shield_gain > 0:
                    defense_comp = payload.target.get_component(DefenseComponent)
                    if defense_comp:
                        resource_changes.append(ResourceChangeEntry("shield", shield_gain, defense_comp.defense_value, None))
            
            self.event_bus.dispatch(GameEvent(EventName.EFFECT_RESOLUTION_COMPLETE, EffectResolutionPayload(
                caster=payload.caster, 
                target=payload.target, 
                source_spell=payload.source_spell_id,
                resource_changes=resource_changes,
                shield_blocked=0.0,
                passive_triggers=passive_triggers
            )))

    def on_gain_shield_request(self, event: GameEvent):
        payload: GainShieldPayload = event.payload
        if (defense_comp := payload.target.get_component(DefenseComponent)):
            defense_comp.defense_value += payload.amount
        else:
            defense_comp = payload.target.add_component(DefenseComponent(defense_value=payload.amount))
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, LogRequestPayload("[COMBAT]", f"来源[{payload.source}] 获得了 {payload.amount:.1f} 点护盾")))