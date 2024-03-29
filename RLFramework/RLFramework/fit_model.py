from typing import Callable, List

import tensorflow as tf
from .simulate import simulate_games
from RLFramework import Game, Player
from RLFramework.read_to_dataset import read_to_dataset
from RLFramework.utils import convert_model_to_tflite

"""
A basic loop to fit a model through the RLFramework.

The loop works as follows:
1. Get as input:
    - A player constructor(int, str) -> List[Player], where the first argument is the index of the player and the second is the model path.
    Note, that if no model path is given, the player should default to some other behaviour.
    - A game constructor(int) -> Game, where the argument is the index of the game.
    - A model fit(tf.data.Dataset, int) -> str, where the first argument is the dataset and the second is the index number.
    The function should return the path to the saved model.

    - num_epochs: How many simulate -> train cycles to run.
    
    - The number of games to simulate in each epoch.
    - The number of files to save the results to.
    - The number of cpus to use.
    - The folder to save the results to.
    - Whether to keep old datasets or not.
"""

class PickleableFunction:
    """ Create a Callable object that takes in a global function,
    and wraps it by giving it some default arguments.
    """
    def __init__(self, func, **pargs):
        self.func = func
        self.pargs = pargs
        
    def __call__(self, *args, **kwargs):
        return self.func(*args, **self.pargs, **kwargs)

def fit_model(
        player_constructor : Callable[[int, str], List[Player]],
        game_constructor : Callable[[int], Game],
        model_fit : Callable[[tf.data.Dataset, int], str],
        starting_model_path : str = None,
        num_epochs : int = 10,
        num_games : int = 1000,
        num_files : int = -1,
        num_cpus : int = -1,
        folder : str = "RLData",
        starting_epoch : int = 0,
    ):
    """ Fit a model to play a game.
    The model is fitted by alternating between simulating games, and training a model.
    When a model is trained, it is then used to play the games in the next epoch.
    """
    if starting_epoch > 0 and not starting_model_path:
        raise ValueError("starting_model_path must be specified when starting_epoch > 0")
    ds = None
    base_folder = folder
    model_path = starting_model_path
    for epoch in range(starting_epoch, num_epochs):
        folder = f"{base_folder}/epoch_{epoch}"
        player_constructor_temp = PickleableFunction(player_constructor, model_path=model_path)
        # Simulate the games
        print("Simulating games...")
        
        simulate_games(game_constructor, player_constructor_temp, folder, num_games, num_files, num_cpus, exists_ok=False)
        # Read the data
        print("Reading data...")
        ds,nfiles, num_samples = read_to_dataset([folder])
        # Fit the model
        print("Fitting model...")
        model_path = model_fit(ds, epoch, num_samples)
        model_path = convert_model_to_tflite(model_path)
        
        print(f"Model path: {model_path}")
    
    
        
        


