from typing import Dict, Any
from .base_handler import EffectHandler
from ...core.entity import Entity
from ...core.components import HealthComponent, DeadComponent, StatsComponent
from ...core.payloads import EffectResolutionPayload, HealRequestPayload, LogRequestPayload
from ...core.enums import EventName
from ...core.event_bus import GameEvent

class HealHandler(EffectHandler):
    """处理治疗效果"""

    def apply(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        if target.has_component(DeadComponent):
            return

        # 获取基础治疗值
        base_heal = effect.get('amount', effect.get('params', {}).get('base_heal', 0))
        heal_type = effect.get('heal_type', 'magical')
        
        # 获取治疗百分比和影响属性
        heal_percentage = effect.get('heal_percentage', 1.0)  # 默认100%
        affected_stat = effect.get('affected_stat', 'attack')  # 默认受攻击力影响
        
        # 根据影响属性计算实际治疗量
        actual_heal = self._calculate_heal_with_stat(caster, target, base_heal, heal_percentage, affected_stat)
        
        # 获取法术数据
        spell_data = self.data_manager.get_spell_data(payload.source_spell)
        
        # 创建治疗请求负载，与旧版本保持一致
        heal_payload = HealRequestPayload(
            caster=caster,
            target=target,
            source_spell_id=payload.source_spell,
            source_spell_name=spell_data.get('name', payload.source_spell) if spell_data else payload.source_spell,
            base_heal=actual_heal,  # 使用计算后的实际治疗量
            original_base_heal=base_heal,  # 保留原始基础治疗量
            heal_type=heal_type,
            overheal_to_shield_config=effect.get('overheal_to_shield')
        )
        
        # 派发治疗请求事件，让战斗解析系统处理
        self.event_bus.dispatch(GameEvent(EventName.HEAL_REQUEST, heal_payload))
    
    def _calculate_heal_with_stat(self, caster: Entity, target: Entity, base_heal: float, heal_percentage: float, affected_stat: str) -> float:
        """根据影响属性计算实际治疗量"""
        # 根据影响属性获取对应的属性值
        if affected_stat == "attack":
            # 受施法者攻击力影响
            stats_comp = caster.get_component(StatsComponent)
            if not stats_comp:
                return base_heal
            stat_value = stats_comp.attack
            stat_owner = caster
        elif affected_stat == "defense":
            # 受施法者防御力影响
            stats_comp = caster.get_component(StatsComponent)
            if not stats_comp:
                return base_heal
            stat_value = stats_comp.defense
            stat_owner = caster
        elif affected_stat == "max_hp":
            # 受施法者最大生命值影响
            health_comp = caster.get_component(HealthComponent)
            if not health_comp:
                return base_heal
            stat_value = health_comp.max_hp
            stat_owner = caster
        elif affected_stat == "target_max_hp":
            # 受目标最大生命值影响
            health_comp = target.get_component(HealthComponent)
            if not health_comp:
                return base_heal
            stat_value = health_comp.max_hp
            stat_owner = target
        else:
            # 如果属性不存在，返回基础治疗量
            return base_heal
        
        # 计算实际治疗量：基础治疗量 + 属性值 × 治疗百分比
        actual_heal = base_heal + (stat_value * heal_percentage)
        
        # 记录日志
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, 
            LogRequestPayload(
                "[SPELL]", 
                f"💚 {caster.name} 的治疗受 {stat_owner.name} 的 {affected_stat}({stat_value}) 通过 {heal_percentage*100:.0f}% 加成，治疗从 {base_heal:.1f} 提升至 {actual_heal:.1f}"
            )
        ))
        
        return actual_heal