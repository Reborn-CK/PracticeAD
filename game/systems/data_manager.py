import yaml

class DataManager:
    """ <<< 升级: 适配新的结构化法术数据格式 >>> """
    def __init__(self):
        self.spell_data = {}
        self.status_effect_data = {}
        self.character_data = {}
        self.passive_data = {}
        self.equipment_data = {}

    def load_spell_data(self, file_path="data/spells.yaml"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.spell_data = yaml.safe_load(f)
        except Exception as e:
            print(f"[错误] 加载数据文件{file_path}失败: {e}")
            raise

    def load_status_effect_data(self, file_path="data/status_effects.yaml"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.status_effect_data = yaml.safe_load(f)
        except Exception as e:
            print(f"[错误] 加载状态效果数据文件{file_path}失败: {e}")
            raise

    def load_character_data(self, file_path="data/characters.yaml"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.character_data = yaml.safe_load(f)
        except Exception as e:
            print(f"[错误] 加载角色数据文件{file_path}失败: {e}")
            raise
    def load_passive_data(self, file_path="data/passives.yaml"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.passive_data = yaml.safe_load(f)
        except Exception as e:
            print(f"[错误] 加载被动能力数据文件{file_path}失败: {e}")
            raise
    
    def load_equipment_data(self, file_path="data/equipment.yaml"):
        """加载装备数据"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.equipment_data = yaml.safe_load(f)
        except Exception as e:
            print(f"[错误] 加载装备数据文件{file_path}失败: {e}")
            raise
    def get_passive_version_data(self, version_id: str) -> dict | None :
        """根据 version_id获取被动能力版本数据"""
        for passive_id, passive_info in self.passive_data.items():
            for version in passive_info.get('versions', []):
                if version.get('version_id') == version_id:
                    # 将基础信息和版本信息合并
                    result = passive_info.get('effect', {}).copy()
                    result.update(version.get('values', {}))
                    result['name'] = passive_info.get('name', passive_id)
                    result['description'] = passive_info.get('description', '')
                    return result
        return None

    def get_spell_version_data(self, version_id: str) -> dict | None:
        """根据 version_id获取法术版本数据"""
        for spell_id, spell_info in self.spell_data.items():
            for version in spell_info.get('versions', []):
                if version.get('version_id') == version_id:
                    # 将基础信息和版本信息合并
                    result = {
                        'name': version.get('name', spell_info.get('name', spell_id)),
                        'description': version.get('description', spell_info.get('description', '')),
                        'cost': spell_info.get('cost', {}),
                        'target': spell_info.get('target', 'enemy'),
                        'can_be_reflected': version.get('can_be_reflected', spell_info.get('can_be_reflected', False)),
                        # 暴击配置优先级：versions.can_crit > versions.can_be_crit > spell.can_crit > spell.can_be_crit
                        'can_crit': version.get('can_crit', spell_info.get('can_crit', spell_info.get('can_be_crit', False))),
                        'effects': version.get('effects', []),
                        'interactions': version.get('interactions', [])
                    }
                    return result
        return None

    def get_status_effect_version_data(self, version_id: str) -> dict | None:
        """根据 version_id获取状态效果版本数据"""
        for effect_id, effect_info in self.status_effect_data.items():
            for version in effect_info.get('versions', []):
                if version.get('version_id') == version_id:
                    # 将基础信息和版本信息合并
                    result = {
                        'name': version.get('name', effect_info.get('name', effect_id)),
                        'description': version.get('description', effect_info.get('description', '')),
                        'category': effect_info.get('category', 'uncategorized'),
                        'logic': effect_info.get('logic', ''),
                        'stacking': effect_info.get('stacking', 'refresh_duration'),
                        'duration': version.get('duration'),
                        'stack_count': version.get('stack_count'),
                        'stack_intensity': version.get('stack_intensity'),
                        'poison_number': version.get('poison_number'),
                        'max_stacks': version.get('max_stacks'),
                        'context': version.get('context', {})
                    }
                    return result
        return None

    def get_character_data(self, character_id: str):
        """获取角色数据"""
        return self.character_data.get(character_id)

    def get_passive_data(self, passive_id: str):
        """获取被动能力数据"""
        return self.passive_data.get(passive_id)

    def get_spell_data(self, spell_id: str):
        """获取法术数据 - 保持向后兼容性"""
        # 首先尝试直接获取（旧格式）
        if spell_id in self.spell_data:
            return self.spell_data[spell_id]
        
        # 然后尝试作为版本ID获取（新格式）
        version_data = self.get_spell_version_data(spell_id)
        if version_data:
            return version_data
        
        return None

    def get_spell_cost(self, spell_id: str) -> float:
        """获取法术消耗"""
        spell_data = self.get_spell_data(spell_id)
        if not spell_data:
            return 0
        cost_data = spell_data.get('cost', {})
        if isinstance(cost_data, dict):
            return cost_data.get('amount', 0)
        return cost_data  # 兼容旧格式

    def get_status_effect_data(self, status_effect_id: str):
        """获取状态效果数据 - 保持向后兼容性"""
        # 首先尝试直接获取（旧格式）
        if status_effect_id in self.status_effect_data:
            return self.status_effect_data[status_effect_id]
        
        # 然后尝试作为版本ID获取（新格式）
        version_data = self.get_status_effect_version_data(status_effect_id)
        if version_data:
            return version_data
        
        return None

    def get_spell_target_type(self, spell_id: str) -> str:
        """获取法术目标类型"""
        spell_data = self.get_spell_data(spell_id)
        if not spell_data:
            return "enemy"  # 默认敌人
        return spell_data.get('target', 'enemy')

    def get_spell_effects(self, spell_id: str) -> list:
        """获取法术效果列表"""
        spell_data = self.get_spell_data(spell_id)
        return spell_data.get('effects',[]) if spell_data else []

    def get_effect_data(self, spell_id: str, effect_type: str) -> dict:
        """获取指定类型的效果数据"""
        effects = self.get_spell_effects(spell_id)
        for effect in effects:
            if effect.get('type') == effect_type:
                return effect
        return {}

    def get_spell_interactions(self, spell_id: str) -> list:
        spell_data = self.get_spell_data(spell_id)
        return spell_data.get('interactions',[]) if spell_data else []

    def get_all_spell_ids(self) -> list:
        """获取所有法术ID列表"""
        spell_ids = []
        for spell_id, spell_info in self.spell_data.items():
            # 添加基础法术ID
            spell_ids.append(spell_id)
            # 添加所有版本ID
            for version in spell_info.get('versions', []):
                version_id = version.get('version_id')
                if version_id:
                    spell_ids.append(version_id)
        return spell_ids
    
    def get_equipment_data(self, equipment_id: str) -> dict:
        """获取装备数据"""
        # 在所有装备类型中查找
        for category in ['weapons', 'armor', 'accessories']:
            if category in self.equipment_data:
                if equipment_id in self.equipment_data[category]:
                    return self.equipment_data[category][equipment_id]
        return None
    
    def get_all_equipment_ids(self) -> list:
        """获取所有装备ID"""
        equipment_ids = []
        for category in ['weapons', 'armor', 'accessories']:
            if category in self.equipment_data:
                equipment_ids.extend(self.equipment_data[category].keys())
        return equipment_ids