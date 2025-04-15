from openai import OpenAI
import sys
import os 
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("API_KEY")

board = sys.argv[2]

client = OpenAI(api_key=api_key)

message = board + '''\n\nThis battleship board contains the history of your past moves. The board is a 10x10 grid, 
                        with rows labeled 'A' to 'J' and columns labeled 1 to 10. The board uses the following symbols: 'H' for a hit, 
                        'M' for a miss, and '~' for an unexplored grid cell. Your task is to: \n
                        (1) analyze the board state,\n 
                        (2) DO NOT SELECT PREVIOUSLY ATTEMPTED MOVES. So, if a grid has a 'H' or 'M' in E5 poistion,
                            do not choose E5.\n
                        (3) return only a single move as a string in the format 'RowColumn' (e.g., 'A6', 'B8'). \n
                        (4) This is the most importnat thing: DO NOT INCLUDE EXPLANATIONS about the move you chose—only return the optimal move as a string.\n\n'''

response = client.chat.completions.create(
model="gpt-4o",
messages=[
    {"role": "system", "content": "You are an expert Battleship player with a deep understanding of optimal strategies. Given a Battleship grid that records previous moves, you can analyze the board state and predict the best possible move to maximize the chances of hitting an opponent's ship."},
    {"role": "user", "content": message}
]
)
x = response.choices[0].message.content
print(x)