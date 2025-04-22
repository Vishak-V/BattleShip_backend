from player import play_bots
from collections import defaultdict
from itertools import combinations
import glob
import os
from player import Player

# def run_tournament(bot_files,num_games:int):
#     scores = defaultdict(int, {bot[:-3]: 0 for bot in bot_files})
#     for bot1, bot2 in combinations(bot_files, 2):
#         for _ in range(num_games):
#             winner = play_bots(bot1, bot2)
#             if winner:
#                 scores[winner] += 1
    
#     rankings = sorted(scores.items(), key=lambda x: x[1], reverse=True)
#     print(rankings)
#     directory = 'uploads/'
#     txt_files = glob.glob(os.path.join(directory, '*.txt'))
#     # Remove each file found
#     for txt_file in txt_files:
#         os.remove(txt_file)
#     return [(index + 1, bot, wins) for index, (bot, wins) in enumerate(rankings)]


def run_tournament(bot_files,num_games:int):
    players_list = []
    for bot_file in bot_files:
        player = Player(bot_file[:-3])    ##edit this line later
        players_list.append(player)
    
    for bot1, bot2 in combinations(players_list, 2):
        for _ in range(num_games):
           play_bots(bot1, bot2)
    
    rankings = sorted(players_list, key=lambda x: x.wins, reverse=True)
    # print(rankings)
    directory = 'uploads/'
    txt_files = glob.glob(os.path.join(directory, '*.txt'))
    # Remove each file found
    for txt_file in txt_files:
        os.remove(txt_file)

    return [(index + 1, player.name, player.wins) for index, player in enumerate(rankings)]
