import yaml

class DataManager:
    """ <<< 升级: 适配新的结构化法术数据格式 >>> """
    def __init__(self):
        self.spell_data = {}
        self.status_effect_data = {}
        self.character_data = {}
        self.passive_data = {}
        self.equipment_data = {}
        self.item_data = {}

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

    def load_item_data(self, file_path="data/items.yaml"):
        """加载物品数据"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.item_data = yaml.safe_load(f)
        except Exception as e:
            print(f"[错误] 加载物品数据文件{file_path}失败: {e}")
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

    def _merge_version_data(self, base_data: dict, version_data: dict) -> dict:
        """智能合并基础数据和版本数据
        
        规则：
        1. 如果版本数据中有某个属性，使用版本数据中的值
        2. 如果版本数据中没有某个属性，使用基础数据中的值
        3. 特殊处理嵌套结构（如effects、interactions等）
        """
        result = dict(base_data)
        
        for key, version_value in version_data.items():
            if key in ['effects', 'interactions']:
                # 对于数组类型的属性，直接使用版本数据中的值
                result[key] = version_value
            else:
                # 对于其他属性，如果版本数据中有值就使用，否则保持基础数据的值
                result[key] = version_value
        
        return result

    def get_spell_version_data(self, version_id: str) -> dict | None:
        """根据 version_id获取法术版本数据"""
        for spell_id, spell_info in self.spell_data.items():
            for version in spell_info.get('versions', []):
                if version.get('version_id') == version_id:
                    # 使用智能合并方法
                    result = self._merge_version_data(spell_info, version)
                    
                    # 确保版本ID正确
                    result['version_id'] = version_id
                    
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
        """获取法术法力消耗"""
        spell_data = self.get_spell_data(spell_id)
        if not spell_data:
            return 0
        cost_data = spell_data.get('cost', {})
        if isinstance(cost_data, dict):
            # 如果是新格式，检查资源类型
            resource_type = cost_data.get('resource', 'mana')
            if resource_type == 'mana':
                return cost_data.get('amount', 0)
            elif resource_type == 'null':
                return 0  # null资源类型不消耗法力
            else:
                return 0  # 非法力消耗返回0
        return cost_data  # 兼容旧格式

    def get_spell_energy_cost(self, spell_id: str) -> float:
        """获取法术能量点消耗"""
        spell_data = self.get_spell_data(spell_id)
        if not spell_data:
            return 0
        cost_data = spell_data.get('cost', {})
        if isinstance(cost_data, dict):
            # 检查资源类型是否为energy
            resource_type = cost_data.get('resource', 'mana')
            if resource_type == 'energy':
                return cost_data.get('amount', 0)
            else:
                return 0  # 非能量消耗返回0
        return 0  # 旧格式不支持能量点消耗

    def get_spell_ultimate_cost(self, spell_id: str) -> float:
        """获取法术终极技能消耗"""
        spell_data = self.get_spell_data(spell_id)
        if not spell_data:
            return 0
        cost_data = spell_data.get('cost', {})
        if isinstance(cost_data, dict):
            # 检查资源类型是否为ultimate
            resource_type = cost_data.get('resource', 'mana')
            if resource_type == 'ultimate':
                return cost_data.get('amount', 0)
            else:
                return 0  # 非终极技能消耗返回0
        return 0  # 旧格式不支持终极技能消耗

    def get_spell_ultimate_charge(self, spell_id: str) -> float:
        """获取法术的充能值"""
        # 首先尝试直接获取基础技能数据
        if spell_id in self.spell_data:
            return self.spell_data[spell_id].get('ultimate_charge', 0)
        
        # 如果是版本ID，需要从版本数据中获取（版本数据会覆盖基础数据）
        version_data = self.get_spell_version_data(spell_id)
        if version_data:
            # 版本数据中的ultimate_charge会覆盖基础数据
            return version_data.get('ultimate_charge', 0)
        
        return 0

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

    def get_item_data(self, item_id: str) -> dict:
        """获取物品数据"""
        # 在所有物品类型中查找
        for category in ['consumables', 'battle_items', 'special_items']:
            if category in self.item_data:
                if item_id in self.item_data[category]:
                    return self.item_data[category][item_id]
        return None
    
    def get_all_item_ids(self) -> list:
        """获取所有物品ID"""
        item_ids = []
        for category in ['consumables', 'battle_items', 'special_items']:
            if category in self.item_data:
                item_ids.extend(self.item_data[category].keys())
        return item_ids