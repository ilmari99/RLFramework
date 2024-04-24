import multiprocessing
from BlockusGame import BlockusGame
from BlockusPlayer import BlockusPlayer
from BlockusNNPlayer import BlockusNNPlayer
from BlockusGreedyPlayer import BlockusGreedyPlayer
from BlockusHumanPlayer import BlockusHumanPlayer

for i in range(1):
   players = [BlockusNNPlayer(name="Player 0",
                            model_path="/home/ilmari/python/RLFramework/BlockusModels/model_15.tflite",
                            move_selection_temp=0.0,
                           logger_args = {
                              "log_file" : "blockusplayer0.log",
                              "log_level" : 10,
                     }),
            BlockusHumanPlayer(name="Player 1",
                            #model_path="/home/ilmari/python/RLFramework/BlockusModelsMahti/model_5.tflite",
                            #move_selection_temp=0.2,
                           logger_args = {
                              "log_file" : "blockusplayer1.log",
                              "log_level" : 10,
                     }),
            BlockusNNPlayer(name="Player 2",
                              model_path="/home/ilmari/python/RLFramework/BlockusModels/model_15.tflite",
                              move_selection_temp=0.0,
                              logger_args = {
                                 "log_file" : "blockusplayer2.log",
                                 "log_level" : 10,
                        }),
            BlockusNNPlayer(name="Player 3",
                              model_path="/home/ilmari/python/RLFramework/BlockusModels/model_15.tflite",
                              move_selection_temp=0.0,
                              logger_args = {
                                 "log_file" : "blockusplayer3.log",
                                 "log_level" : 10,
                        }),
   ]
   
   game = BlockusGame(board_size=(20,20), logger_args={"log_file" : "blockusgame.log",
                                                        "log_level" : 10,
                                 },
                      model_paths=["/home/ilmari/python/RLFramework/BlockusModelsMahti/model_15.tflite"],#,"/home/ilmari/python/RLFramework/BlockusModelsMahti/model_15.tflite"],
                     render_mode = "human",
                  gather_data = "blockus_data.csv",
                  timeout=10000,
   )
   
   game.play_game(players)
   #with multiprocessing.Pool(1) as p:
   #   p.map(game.play_game, [players])