from typing import Dict, Any
from .base_handler import EffectHandler
from ...core.entity import Entity
from ...core.components import HealthComponent, ShieldComponent, DeadComponent, CritComponent, StatsComponent
from ...core.payloads import EffectResolutionPayload, DamageRequestPayload
from ...core.enums import EventName
from ...core.event_bus import GameEvent

class DirectDamageHandler(EffectHandler):
    """处理直接伤害效果"""

    def apply(self, caster: Entity, target: Entity, effect: Dict[str, Any], payload: EffectResolutionPayload):
        if target.has_component(DeadComponent):
            return

        # 获取基础伤害值
        base_damage = effect.get('amount', effect.get('params', {}).get('base_damage', 0))
        damage_type = effect.get('damage_type', 'physical')
        
        # 获取伤害百分比和影响属性
        damage_percentage = effect.get('damage_percentage', 1.0)  # 默认100%
        affected_stat = effect.get('affected_stat', 'attack')  # 默认受攻击力影响
        
        # 根据影响属性计算实际伤害
        actual_damage = self._calculate_damage_with_stat(caster, base_damage, damage_percentage, affected_stat)
        
        # 获取暴击信息
        crit_comp = caster.get_component(CritComponent)
        crit_chance = crit_comp.crit_chance if crit_comp else 0.0
        crit_damage_multiplier = crit_comp.crit_damage_multiplier if crit_comp else 2.0
        
        # 获取法术数据
        spell_data = self.data_manager.get_spell_data(payload.source_spell)
        
        # 创建伤害请求负载，与旧版本保持一致
        damage_payload = DamageRequestPayload(
            caster=caster,
            target=target,
            source_spell_id=payload.source_spell,
            source_spell_name=spell_data.get('name', payload.source_spell) if spell_data else payload.source_spell,
            base_damage=actual_damage,  # 使用计算后的实际伤害
            original_base_damage=base_damage,  # 保留原始基础伤害
            damage_type=damage_type,
            lifesteal_ratio=effect.get('lifesteal_ratio', 0),
            is_reflection=effect.get('is_reflection', False),
            can_be_reflected=spell_data.get('can_be_reflected', False) if spell_data else False,
            can_crit=spell_data.get('can_crit', False) if spell_data else False,
            crit_chance=crit_chance,
            crit_damage_multiplier=crit_damage_multiplier,
            # 新增：传递 trigger_on_attack 字段
            trigger_on_attack=spell_data.get('trigger_on_attack', True) if spell_data else True
        )
        
        # 派发伤害请求事件，让战斗解析系统处理
        self.event_bus.dispatch(GameEvent(EventName.DAMAGE_REQUEST, damage_payload))
    
    def _calculate_damage_with_stat(self, caster: Entity, base_damage: float, damage_percentage: float, affected_stat: str) -> float:
        """根据影响属性计算实际伤害"""
        # 获取施法者的属性组件
        stats_comp = caster.get_component(StatsComponent)
        if not stats_comp:
            return base_damage
        
        # 根据影响属性获取对应的属性值
        if affected_stat == "attack":
            stat_value = stats_comp.attack
        elif affected_stat == "defense":
            stat_value = stats_comp.defense
        else:
            # 如果属性不存在，返回基础伤害
            return base_damage
        
        # 计算实际伤害：基础伤害 + 属性值 × 伤害百分比
        actual_damage = base_damage + (stat_value * damage_percentage)
        
        # 记录日志
        from ...core.payloads import LogRequestPayload
        self.event_bus.dispatch(GameEvent(EventName.LOG_REQUEST, 
            LogRequestPayload(
                "[SPELL]", 
                f"💥 {caster.name} 的 {affected_stat}({stat_value}) 通过 {damage_percentage*100:.0f}% 加成，伤害从 {base_damage:.1f} 提升至 {actual_damage:.1f}"
            )
        ))
        
        return actual_damage