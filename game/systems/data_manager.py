import yaml

class DataManager:
    """ <<< 升级: 适配新的结构化法术数据格式 >>> """
    def __init__(self):
        self.spell_data = {}
        self.status_effect_data = {}
        self.character_data = {}
        self.passive_data = {}

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
    def get_character_data(self, character_id: str):
        """获取角色数据"""
        return self.character_data.get(character_id)

    def get_passive_data(self, passive_id: str):
        """获取被动能力数据"""
        return self.passive_data.get(passive_id)

    def get_spell_data(self, spell_id: str):
        return self.spell_data.get(spell_id)

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
        return self.status_effect_data.get(status_effect_id)

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