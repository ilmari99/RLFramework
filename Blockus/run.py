import multiprocessing
from BlockusGame import BlockusGame
from BlockusPlayer import BlockusPlayer

for i in range(1):
   players = [BlockusPlayer(name="Player 0",
                            logger_args = {
                                  "log_file" : "blockusplayer0.log",
                                  "log_level" : 10,
                                  }),
            BlockusPlayer("Player 1",
                           logger_args = {
                              "log_file" : "blockusplayer1.log",
                              "log_level" : 10,
                           }),
            BlockusPlayer("Player 2",
                           logger_args = {
                              "log_file" : "blockusplayer2.log",
                              "log_level" : 10,
                     }),
            BlockusPlayer("Player 3",
                           logger_args = {
                              "log_file" : "blockusplayer3.log",
                              "log_level" : 10,
                     }),
   ]
   
   game = BlockusGame(board_size=(20, 20), logger_args={"log_file" : "blockusgame.log",
                                                        "log_level" : 10,
                                 },
                     render_mode = "human",
                  gather_data = "blockus_data.csv",
                  timeout=10000,
   )
   
   game.play_game(players)
   #with multiprocessing.Pool(1) as p:
   #   p.map(game.play_game, [players])