from player_sonam import play_bots
from collections import defaultdict
from itertools import combinations

def run_tournament(bot_files):
    scores = defaultdict(int, {bot: 0 for bot in bot_files})
    num_games = 2
    print(scores)
    for bot1, bot2 in combinations(bot_files, 2):
        for _ in range(num_games):
            winner = play_bots(bot1, bot2)
            if winner:
                scores[winner] += 1
    
    rankings = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [(index + 1, bot, wins) for index, (bot, wins) in enumerate(rankings)]

# # Example usage:
# bot_files = ["Player1", "Player2","Player3"]
# rankings = run_tournament(bot_files)
# print(rankings)
