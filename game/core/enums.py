from enum import Enum, auto

class EventName(Enum):
    ROUND_START = auto()
    LOG_REQUEST = auto()
    UI_MESSAGE = auto()
    UI_DISPLAY_OPTIONS = auto()
    EFFECT_RESOLUTION_COMPLETE = auto()
    ACTION_REQUEST = auto()
    PLAYER_SPELL_CHOICE = auto()
    PLAYER_TARGET_CHOICE = auto()
    CAST_SPELL_REQUEST = auto()
    MANA_COST_REQUEST = auto()
    DAMAGE_REQUEST = auto()
    HEAL_REQUEST = auto()
    HEALTH_CHANGED = auto()
    GAIN_SHIELD_REQUEST = auto()

    APPLY_STATUS_EFFECT_REQUEST = auto()
    REMOVE_STATUS_EFFECT_REQUEST = auto()
    UPDATE_STATUS_EFFECTS_DURATION_REQUEST = auto()

    STATUS_EFFECTS_RESOLVED = auto()

    STAT_QUERY = auto()
    DISPEL_REQUEST = auto()
    AMPLIFY_POISON_REQUEST = auto()
    DETONATE_POISON_REQUEST = auto()