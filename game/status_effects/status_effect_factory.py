from typing import Optional

from ..core.entity import Entity
from ..systems.data_manager import DataManager
from .status_effect import StatusEffect
from .effect_logic import DamageOverTimeEffect, StatModificationLogic, OverhealConversionLogic, EffectLogic, PoisonDotEffect, PoisonEffectLogic, StunEffectLogic, HealOverTimeEffect

# 效果逻辑的映射表，现在集中存放在这里
EFFECT_LOGIC_MAP = {
    "dot": DamageOverTimeEffect,
    "poison_dot": PoisonDotEffect,
    "poison": PoisonEffectLogic,  # 新增专门的中毒效果逻辑
    "stat_mod": StatModificationLogic,
    "overheal": OverhealConversionLogic,
    "stun": StunEffectLogic,  # 新增击晕效果逻辑
    "heal": HealOverTimeEffect,  # 新增持续恢复效果逻辑
}

class StatusEffectFactory:
    """
    一个专门用于创建状态效果实例的工厂。
    """
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def create_effect(self, effect_id: str, caster: Optional[Entity] = None) -> Optional[StatusEffect]:
        """
        根据效果ID和施法者，从数据文件中创建并返回一个完整的StatusEffect实例。
        支持新的版本化结构和旧的直接ID结构。
        """
        effect_data = self.data_manager.get_status_effect_data(effect_id)
        if not effect_data:
            # 在未来，这里可以替换为日志系统事件
            print(f"[ERROR][StatusEffectFactory] 未找到ID为 '{effect_id}' 的状态效果数据。")
            return None

        logic_key = effect_data.get("logic", "")
        # 如果找不到对应的逻辑，则使用一个不执行任何操作的默认逻辑，保证程序健壮性
        logic_class = EFFECT_LOGIC_MAP.get(logic_key, EffectLogic)

        # 获取版本数据
        version_data = self.data_manager.get_status_effect_version_data(effect_id)
        if version_data:
            # 合并基础数据和版本数据
            merged_data = self.data_manager._merge_version_data(effect_data, version_data)
        else:
            merged_data = effect_data

        return StatusEffect(
            effect_id=effect_id,
            name=merged_data.get('name', '未命名效果'),
            duration=merged_data.get('duration', None),
            category=merged_data.get("category", "uncategorized"),
            stacking=merged_data.get("stacking", "refresh_duration"),
            max_stacks=merged_data.get("max_stacks", 1),
            stack_count=merged_data.get("duration", 3),  # 层数等于持续回合数
            stack_intensity=merged_data.get("stack_intensity", 1),
            poison_number=merged_data.get("poison_number", 1),  # 一次性添加的中毒状态数量
            heal_number=merged_data.get("heal_number", 1),  # 一次性添加的持续恢复状态数量
            caster=caster,
            context=merged_data.get("context", {}),
            logic=logic_class() # 创建逻辑类的实例
        )