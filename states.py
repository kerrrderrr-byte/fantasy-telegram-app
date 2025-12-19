# states.py
from aiogram.fsm.state import State, StatesGroup

class AdventureStates(StatesGroup):
    in_adventure = State()