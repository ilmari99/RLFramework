


from typing import Dict, List, Set, TYPE_CHECKING
from RLFramework.Action import Action
from RLFramework.Game import Game
from RLFramework.Player import Player
import numpy as np
from utils import get_killable_mapping

if TYPE_CHECKING:
    from MoskaGameState import MoskaGameState
    from MoskaAction import MoskaAction
    from Card import Card
    from MoskaGame import MoskaGame
 
class MoskaPlayer(Player):
    
    def __init__(self, name : str = "MoskaPlayer", max_moves_to_consider : int = 1000, logger_args : dict = None):
        super().__init__(name, logger_args)
        self.game : 'MoskaGame' = None
        self.max_moves_to_consider = max_moves_to_consider
        self.has_received_reward = False
        #self.ready = False
        return
    
    @property
    def hand(self) -> List['Card']:
        return self.game.player_full_cards[self.pid]
    
    @property
    def public_hand(self) -> List['Card']:
        return self.game.player_public_cards[self.pid]
    
    @property
    def ready(self) -> bool:
        return self.game.players_ready[self.pid]
    
    def choose_move(self, game: Game) -> Action:
        act = super().choose_move(game)
        #print(f"Player {self.pid} chose action: {act}")
        return act
    
    def get_possible_kill_mapping(self) -> Dict['Card', List['Card']]:
        """ Get the possible kill mapping.
        """
        return get_killable_mapping(self.hand, self.game.cards_to_kill, self.game.trump_suit)
        
    def initialize_player(self, game: 'MoskaGame') -> None:
        """ Called when a game begins.
        """
        self.game : MoskaGame = game
        self.has_received_reward = False
        return
    
    def get_playable_ranks_from_hand(self) -> Set[int]:
        own_ranks = set([card.rank for card in self.hand])
        return self.game.get_ranks_on_table().intersection(own_ranks)
            
    def evaluate_states(self, states : List['MoskaGameState']) -> List[float]:
        """ Evaluate the states.
        """
        return [np.random.random() for _ in states]
        
    def select_action_strategy(self, evaluations: List[float]) -> int:
        return super()._select_best_action(evaluations)
            
         