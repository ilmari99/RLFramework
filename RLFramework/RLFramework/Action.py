from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING
from .GameState import GameState
if TYPE_CHECKING:
    from .Game import Game
    from .Player import Player

class Action(ABC):
    """ Action -class contains information about the proposed changes to the game.
    The action class is passed to the the Game.step() -method, which then returns the new state of the game.
    """
    def __init__(self):
        raise NotImplementedError("When subclassing Action, you must implement the __init__ method.")
    
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.modify_game = cls.modify_game_decorator()(cls.modify_game)
    
    @staticmethod
    def modify_game_decorator():
        """ Decorator for the modify_game method.
        The decorator checks if the action is legal in the given game state.
        Also, If the inplace argument is False, then this wrapper saves
        the game state, modifies the game, and then restores the game state.
        """
        def decorator(func):
            def wrapper(self : 'Action', game: 'Game', inplace: bool = False) -> GameState:
                if not self.check_action_is_legal(game):
                    raise ValueError("The action is not legal in the given game state.")
                
                if inplace:
                    return func(self, game)
                
                # Save the game state
                game_state = game.game_state_class.from_game(game, copy = True)
                # Modify the game
                new_state = func(self, game)
                # Restore the game state
                game.restore_game(game_state)
                # Return the modifed game state
                return new_state
            return wrapper
        return decorator
    
    @modify_game_decorator()
    @abstractmethod
    def modify_game(self, game: 'Game', inplace = False) -> GameState:
        """ Modify the game instance according to the action.
        """
        pass

    @abstractmethod
    def check_action_is_legal(self, game: 'Game') -> bool:
        """ Check if the action is legal in the given game state.
        """
        pass
    
    @classmethod
    def check_action_is_legal_from_args(cls, game: 'Game', *args) -> bool:
        """ Check if the action is legal in the given game state.
        """
        return cls(*args).check_action_is_legal(game)