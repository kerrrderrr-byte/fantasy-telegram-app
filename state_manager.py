# state_manager.py
from typing import Dict
from storyteller import PlayerState
import json

# В памяти (для демо). В продакшене → Redis / PostgreSQL.
_user_sessions: Dict[str, PlayerState] = {}

def get_player_state(user_id: str) -> PlayerState:
    if user_id not in _user_sessions:
        _user_sessions[user_id] = PlayerState()
    return _user_sessions[user_id]

def save_player_state(user_id: str, state: PlayerState):
    _user_sessions[user_id] = state

# Пример использования в main.py:
# state = get_player_state(user_id)
# state.inventory["Бутерброд"] = state.inventory.get("Бутерброд", 0) + 1
# save_player_state(user_id, state)