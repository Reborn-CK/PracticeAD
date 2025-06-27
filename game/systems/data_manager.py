import yaml

class DataManager:
    def __init__(self):
        self.spell_data = {}
        self.status_effect_data = {}

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

    # ... (所有 get_... 方法保持不变) ...
    def get_spell_data(self, spell_id: str): return self.spell_data.get(spell_id)
    def get_spell_cost(self, spell_id: str) -> float:
        spell_data = self.get_spell_data(spell_id)
        if not spell_data: return 0
        cost_data = spell_data.get('cost', {})
        if isinstance(cost_data, dict): return cost_data.get('amount', 0)
        return cost_data
    def get_status_effect_data(self, status_effect_id: str): return self.status_effect_data.get(status_effect_id)
    def get_spell_target_type(self, spell_id: str) -> str:
        spell_data = self.get_spell_data(spell_id)
        if not spell_data: return "enemy"
        return spell_data.get('target', 'enemy')
    def get_spell_effects(self, spell_id: str) -> list:
        spell_data = self.get_spell_data(spell_id)
        return spell_data.get('effects',[]) if spell_data else []
    def get_effect_data(self, spell_id: str, effect_type: str) -> dict:
        effects = self.get_spell_effects(spell_id)
        for effect in effects:
            if effect.get('type') == effect_type:
                return effect
        return {}
    def get_spell_interactions(self, spell_id: str) -> list:
        spell_data = self.get_spell_data(spell_id)
        return spell_data.get('interactions',[]) if spell_data else []