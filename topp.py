import torch
import numpy as np
import config as cfg
from state_manager import StateManager
from mcts import MCTS
from NN_architectures.hex_ann import HexANN
from NN_architectures.hex_res_ann import HexResANN
from NN_architectures.hex_demo import HexDemo
from trained_models.res_net_3_128 import architecture as res_128_3
from trained_models.hex_6_res_temperature import architecture as res_64_2
from trained_models.hex_5 import architecture as hex_5
from ann import ANN

class TOPP:
    def __init__(
        self, 
        num_contenders, 
        num_games, 
        contenders, 
        search=True, 
        search_time=1.4, 
        display_first=False
    ):
        self.num_contenders = num_contenders
        self.num_games = num_games
        self.search = search
        self.search_time = search_time
        self.display_first = display_first

        # Create a list of contender models
        self.contenders = contenders

        print(self.contenders)

    def create_tournament_matchings(self):
        """
        Returns an array of tuples with indices to the contender list
        representing the matchings for the tournament
        """
        matchings = []
        for i in range(self.num_contenders):
            for j in range(i+1, self.num_contenders):
                matchings.append((i, j))

        return matchings

    def play_tournament(self):
        matchings = self.create_tournament_matchings()

        # Create a dictionary to hold the tournament results
        results = {}
        for i in range(self.num_contenders):
            results[i] = [0 for i in range(self.num_contenders)]

        for match in matchings:
            print(match, flush=True)
            model_1 = self.contenders[match[0]]
            model_2 = self.contenders[match[1]]
            m1_results, m2_results = self.play_match(model_1, model_2)
            print(f"M1: {m1_results} M2: {m2_results}")
            if m1_results > m2_results:
                results[match[0]][match[1]] = 1
                results[match[1]][match[0]] = -1
            elif m2_results > m1_results:
                results[match[1]][match[0]] = 1
                results[match[0]][match[1]] = -1
            # If match is drawn, then the initialised 0 remains
        return results

    def play_match(self, model_1, model_2):
        m1_results = 0
        m2_results = 0
        halfway_point = self.num_games//2
        # Model 1 starts all matches in first half
        for i in range(halfway_point):
            # Alternate colors to start to test more of the network
            starting_color = i % 2 + 1
            result = self.play_game(model_1, model_2, starting_color)
            self.display_first = False
            if cfg.TRAIN_game_params["display_game"]:
                self.display_first = True
                

            # Model 1 is starting player, so if starting color wins then model 1 wins
            if result == starting_color:
                m1_results += 1
            else:
                m2_results += 1

            #print("M1:", m1_results, "M2:", m2_results, flush=True)
        for i in range(halfway_point):
            # Alternate colors to start to test more of the network
            starting_color = i % 2 + 1
            result = self.play_game(model_2, model_1, starting_color)

            # Model 2 is starting player, so if starting color wins then model 2 wins
            if result == starting_color:
                m2_results += 1
            else:
                m1_results += 1
            #print("M1:", m1_results, "M2:", m2_results, flush=True)
                
        return m1_results, m2_results

    def play_game(self, p1, p2, starting_color=1):
        # Initialize game and greedy settings for MCTS
        game = StateManager(starting_color, cfg.TRAIN_game_params, display_game=self.display_first)
        m1 = MCTS(game, p1, eps=0.1, c_ucb=1, search_time=self.search_time) 
        m2 = MCTS(game, p2, eps=0.1, c_ucb=1, search_time=self.search_time)
        s = game.get_game_state()
        while True:
            # TODO add actual game update for potential display of game
      
            action = np.argmax(m1.getActionProb(s, self.search))
            a = game.one_hot_to_action(action)
            if self.display_first:
                game.update_game_state(a)
            s = game.generate_next_state(s, a)
            result = game.check_game_ended(s)
            if result:
                return result
            action = np.argmax(m2.getActionProb(s, self.search))
            a = game.one_hot_to_action(action)
            if self.display_first:
                game.update_game_state(a)
            s = game.generate_next_state(s, a)
            result = game.check_game_ended(s)
            if result:
                return result

    def print_tournament_results(self, results):

        total_scores = [sum(results[i]) for i in range(self.num_contenders)]

        for i in range(self.num_contenders):
            print("-----------------------------------------------")
            print(f"Contender {i}")
            print("Results:", results[i])
            print("Total score:", total_scores[i])
            


if __name__ == "__main__":
    
    # TODO add config to topp
    contenders = []
    # Get game info to properly load model
    game = StateManager(game_params=cfg.TRAIN_game_params)
    input_size = game.get_game_size()
    output_size = len(game.generate_legal_moves(game.get_game_state()))

    folderpath = cfg.TOPP_SETTINGS["model_path"]
    for path in cfg.TOPP_SETTINGS["models"]:
        ann = ANN(input_size, output_size, cfg.TOPP_SETTINGS["ann"])
        ann.model.load_state_dict(torch.load(folderpath+path))
        ann.model.eval()
        contenders.append(ann.model)

    """
    for path in multiple_paths:
        model = res_64_2.HexResANN(input_size, output_size)
        model.load_state_dict(torch.load(path_multiple+path))
        model.eval()
        contenders.append(model)

    for path in contender_paths:
        model = res_64_2.HexResANN(input_size, output_size)
        model.load_state_dict(torch.load(path_res_2_long+path))
        model.eval()
        contenders.append(model)
    
    for path in contender_paths_res_3:
            model = res_128_3.HexResANN(input_size, output_size)
            model.load_state_dict(torch.load(path_res_3+path))
            model.eval()
            contenders.append(model)
    """
    

    tournament = TOPP(
        num_contenders=len(contenders), 
        num_games=cfg.TOPP_SETTINGS["num_games"], 
        contenders=contenders, 
        search=cfg.TOPP_SETTINGS["search"],
        search_time=cfg.TOPP_mcts["search_time"],
        display_first=cfg.TOPP_SETTINGS["display_first"]
        )

    results = tournament.play_tournament()
    tournament.print_tournament_results(results)


