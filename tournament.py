from player import play_bots
from collections import defaultdict
from itertools import combinations
import glob
import os

def run_tournament(bot_files,num_games:int):
    scores = defaultdict(int, {bot[:-3]: 0 for bot in bot_files})
    print(bot_files)

    print(scores)
    for bot1, bot2 in combinations(bot_files, 2):
        for _ in range(num_games):
            winner = play_bots(bot1, bot2)
            if winner:
                scores[winner] += 1
    
    rankings = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    print(rankings)
    directory = 'tmp/'
    txt_files = glob.glob(os.path.join(directory, '*.txt'))
    # Remove each file found
    for txt_file in txt_files:
        os.remove(txt_file)
    return [(index + 1, bot, wins) for index, (bot, wins) in enumerate(rankings)]


# # Example usage:
# bot_files = ["Player1", "Player2"]
# rankings = run_tournament(bot_files)
# print(rankings)

