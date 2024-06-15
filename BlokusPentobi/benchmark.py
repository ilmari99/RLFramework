import json
import multiprocessing
import os
import random
import argparse
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import numpy as np
from PentobiGTP import PentobiGTP
from PentobiPlayers import PentobiInternalPlayer, PentobiNNPlayer, PentobiInternalEpsilonGreedyPlayer
from utils import TFLiteModel
import argparse

def play_pentobi(i, seed, player_maker, save_data_file = "", proc_args = {}):
    
    default_proc_args = {
        "command": None,
        "book": None,
        "config": None,
        "game": "classic",
        "level": 1,
        "seed": seed,
        "showboard": False,
        "nobook": False,
        "noresign": True,
        "quiet": False,
        "threads": 1,
    }
    
    proc = PentobiGTP(**{**default_proc_args, **proc_args})
    
    players = player_maker(proc)
    
    np.random.seed(seed)
    random.seed(seed)
    
    num_moves = 0
    while not proc.is_game_finished():
        pid = proc.pid
        #print(f"Player {pid} playing")
        player = players[pid-1]
        player.play_move()
        num_moves += 1
    if save_data_file:
        proc.write_states_to_file(save_data_file)
    score = list(proc.score)
    pl_names = [type(pl).__name__+f"_{i}" for i,pl in enumerate(players)]
    proc.close()
    #print({pl : sc for pl,sc in zip(pl_names, score)})
    return {pl : sc for pl,sc in zip(pl_names, score)}

def shuffle_players_func(players):
    random.shuffle(players)
    for i, player in enumerate(players):
        player.pid = i+1
    return players


def player_maker_benchmark(proc, model_path):
    model = TFLiteModel(model_path)
    player_to_test = PentobiNNPlayer(1,proc,model,move_selection_strategy="best")
    
    opponents = []
    for pid in range(2,5):
        opponents.append(PentobiInternalEpsilonGreedyPlayer(pid,proc,epsilon=0.03))
    
    players = [player_to_test] + opponents
    players = shuffle_players_func(players)
    return players


def play_pentobi_wrapper(args):
    return play_pentobi(*args)

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    
    # Load the environment variables from env.json
    if os.path.exists('env.json'):
        with open('env.json') as f:
            env_vars = json.load(f)
            #print(env_vars)
    else:
        env_vars = {}

    parser = argparse.ArgumentParser()
    parser.add_argument("--num_games", type=int, default=1000, help="Number of games")
    parser.add_argument("--num_cpus", type=int, default=10, help="Number of CPUs")
    parser.add_argument("--pentobi_level", type=int, default=1, help="Level of opponent Pentobi players")
    parser.add_argument("--pentobi_gtp", type=str, default=env_vars.get('pentobi_gtp', None), help="Path to pentobi-gtp")
    parser.add_argument("--model_path", type=str, required=True)
    args = parser.parse_args()
    
    print(args)
    num_games = args.num_games
    num_cpus = args.num_cpus
    os.environ["PENTOBI_GTP"] = os.path.abspath(args.pentobi_gtp)
    model_path = os.path.abspath(args.model_path)
    pentobi_gtp = os.path.abspath(args.pentobi_gtp)

    model = TFLiteModel(model_path)
    
    def _player_maker(proc):
        return player_maker_benchmark(proc, model_path)
    
    def arg_generator(num_games):
        kwargs = {
            "command": pentobi_gtp,
            "level": args.pentobi_level,
            "threads": 1,
            "showboard": False,
            "nobook": False,
            "quiet": True,
        }
        for i in range(num_games):
            seed = np.random.randint(2**32)
            file = f""
            yield (i, seed, _player_maker, file, kwargs)
    
    # Play the games in parallel
    results = []
    with multiprocessing.Pool(num_cpus) as pool:
        gen = pool.imap_unordered(play_pentobi_wrapper, arg_generator(num_games))
        while True:
            try:
                result = next(gen)
                results.append(result)
                if len(results) % 100 == 0:
                    print(f"Games played: {len(results)}", end="\r")
            except StopIteration:
                break
    #print(results)

    class_wins = {}
    class_avg_score = {}
    num_games = 0
    games_per_class = {}
    for res in results:
        scores = list(res.values())
        players = list(res.keys())
        max_sc = max(scores)
        idx = scores.index(max_sc)
        winner_name = players[idx]
        winner_name_splitted = winner_name.split("_")
        winner_name = winner_name_splitted[0:-1]
        winner_class = "".join(winner_name)
        if winner_class not in class_wins:
            class_wins[winner_class] = 0
        class_wins[winner_class] += 1
        
        for sc, pl in zip(scores,players):
            pl_splitted = pl.split("_")
            pl = pl_splitted[0:-1]
            class_ = "".join(pl)
            if class_ not in games_per_class:
                games_per_class[class_] = 0
            games_per_class[class_] += 1
            if class_ not in class_avg_score:
                class_avg_score[class_] = 0
            class_avg_score[class_] += sc
        num_games += 1
    class_avg_score = {k : v/games_per_class[k] for k,v in class_avg_score.items()}
    class_wins = {k : v/games_per_class[k] for k,v in class_wins.items()}
    print(f"Wins",class_wins)
    print(f"Average score", class_avg_score)
    
    print(f"Model {model_path} win percent: {class_wins.get('PentobiNNPlayer',0)}")
    
    # Write the loss percent to a win_rates.json file at the correct index
    model_number = int(model_path.split("/")[-1].split(".")[0].split("_")[-1])
    model_folder = "/".join(model_path.split("/")[:-1])
    win_rate_file = os.path.join(model_folder, "win_rates.json")
    if args.pentobi_level != 1:
        print(f"Not writing win rates, since the level is not 1")
        exit()
    if not os.path.exists(win_rate_file):
        assert model_number == 0, "The first model must be model_0"
        with open(win_rate_file, "w") as f:
            json.dump([class_wins.get('PentobiNNPlayer',0)], f)
    else:
        with open(win_rate_file) as f:
            win_rates = json.load(f)
        assert len(win_rates) == model_number, "The number of models and the number of win rates must be the same"
        win_rates.append(class_wins.get('PentobiNNPlayer',0))
        with open(win_rate_file, "w") as f:
            json.dump(win_rates, f)
    
                
            
        
        