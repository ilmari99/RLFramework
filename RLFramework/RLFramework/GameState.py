from abc import ABC, abstractmethod
import functools as ft
from typing import Any, Dict, List, SupportsFloat, TYPE_CHECKING
import json

import numpy as np

if TYPE_CHECKING:
    from .Game import Game
    from .Action import Action
    from .Player import Player

class GameState(ABC):
    """ A class representing a state of a game.
    The game state is a snapshot of the current game. It should contain ALL
    information needed to restore the game to exactly the same state as it was when the snapshot was taken.

    In games with hidden information, this class contains all the information that is available to the player,
    AND the information that is hidden from the player.

    The GameState is used to evaluate the game state, and to restore the game state to a previous state.

    The gamestate must be deepcopiable, and the copy must be independent of the original game state.
    """

    def __init__(self, state_json):
        """ Initialize the game state.
        If copy is True, the values of the GameState will be deepcopies
        (if possible) of the values of the Game instance.
        """
        self._state_json = state_json
        self.unfinished_players = []
        self.finished_players = []
        self.current_pid = 0
        self.perspective_pid = 0
        self.previous_turns = []
        self.player_scores = []
        self.game_states = []
        self.finishing_order = []
        #self.check_state_json_has_required_keys(state_json)
        self.initialize(state_json)

    def update_state_json(self):
        """ Update the state json.
        """
        for k, v in self.__dict__.items():
            if k in self._state_json:
                self._state_json[k] = v

    @property
    def state_json(self) -> Dict:
        self.update_state_json()
        return self._state_json
        
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.game_to_state_json = cls.game_to_state_json_decorator()(cls.game_to_state_json)

    def deepcopy(self):
        """ Return a deepcopy of the game state.
        """
        return self.__class__(json.loads(json.dumps(self._state_json)))
    
        
    @classmethod
    def game_to_state_json_decorator(cls):
        """ Decorator for the game_to_state_json method."""
        def decorator(func):
            @ft.wraps(func)
            def wrapper(game : 'Game', player : 'Player' = None):
                if player is None:
                    player = game.players[game.current_pid]
                state_json = func(cls, game, player)
                # Add the required keys
                state_json["unfinished_players"] = game.unfinished_players
                state_json["current_pid"] = game.current_pid
                state_json["previous_turns"] = game.previous_turns
                state_json["player_scores"] = game.player_scores
                state_json["finishing_order"] = game.finishing_order
                state_json["perspective_pid"] = player.pid
                #state_json["game_states"] = game.game_states if self.copy_game_states else []
                return state_json
            return wrapper
        return decorator
    
    @classmethod
    def from_game(cls, game : 'Game', player : 'Player' = None, copy : bool = True):
        """ Create a GameState from a Game instance.
        If copy is True, the values of the GameState will be deepcopies
        """
        state_json = cls.game_to_state_json(game, player)
        state = cls(state_json)
        if copy:
            # "Deepcopy" the state_json
            #state_json = json.loads(json.dumps(state_json))
            state = state.deepcopy()
        return state
    
    def initialize(self, state_json : Dict) -> None:
        """ Save the variables from the state_json.
        """
        for key, value in state_json.items():
            setattr(self, key, value)
            
    def set_game_state(self, game : 'Game') -> None:
        """ Restore the state of the game to match the state of the GameState.
        """
        for key, value in self.state_json.items():
            setattr(game, key, value)
            
    def check_is_game_equal(self, game : 'Game', player : 'Player' = None) -> bool:
        """ Check if the state of the game matches the state of the GameState.
        """
        suc = self.state_json == self.__class__.game_to_state_json(game, player)
        if not suc:
            print(f"self.state_json: {self.state_json}")
            print(f"game.state_json: {self.__class__.game_to_state_json(game, player)}")
        return suc
    
    def __bool__(self) -> bool:
        return True
    
    
    def __repr__(self) -> str:
        #return np.array(self.state_json["board"]).__repr__()
        return f"{self.__class__.__name__}({self.state_json})"
    
    def __hash__(self) -> int:
        return hash(tuple(self.to_vector()))
    
    
    @classmethod
    @abstractmethod
    def game_to_state_json(cls, game : 'Game', player : 'Player' = None) -> Dict:
        """ Convert the game to a state json.
        """
        pass


    @abstractmethod
    def to_vector(self, perspective_pid : int = None) -> List[SupportsFloat]:
        """ Return a vector representation of the game state.
        """
        pass