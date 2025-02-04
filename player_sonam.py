class Player:
    def __init__(self, name):
        self.name = name
        self.ship_grid = {chr(65 + i): [None for _ in range(10)] for i in range(10)}  
        self.attack_grid = {chr(65 + i): [None for _ in range(10)] for i in range(10)} 
        self.ships = {
            "Carrier": {"length": 5, "health": 5, "positions": [], "symbol": "C"},
            "Battleship": {"length": 4, "health": 4, "positions": [], "symbol": "B"},
            "Cruiser": {"length": 3, "health": 3, "positions": [], "symbol": "R"},
            "Submarine": {"length": 3, "health": 3, "positions": [], "symbol": "S"},
            "Destroyer": {"length": 2, "health": 2, "positions": [], "symbol": "D"},
        }
        self.wins = 0
        self.losses = 0
        self.remaining_ships = 5
        self.last_attack = None
        self.is_turn = False


    def display_board(self, grid_type='ship'):
        """
        Displays the specified grid (ship_grid or attack_grid) with row letters and column numbers.
        Adds borders and separators for better visual appeal.
        :param grid_type: 'ship' to display ship_grid, 'attack' to display attack_grid
        """
        grid = self.ship_grid if grid_type == 'ship' else self.attack_grid
        print(f"{self.name}'s {grid_type.capitalize()} Grid:")
        print("   +" + "---+" * 12)  # Top border
        print("   | " + " | ".join(str(i + 1).rjust(2) for i in range(10)) + " |")  # Column numbers (1 to 10)
        print("   +" + "---+" * 12)  # Separator
        for row in grid:
            print(f" {row} |", end=" ")  # Row letter (A to J)
            for cell in grid[row]:
                if grid_type == 'ship':
                    # For ship_grid, show ship symbols or '~' for empty cells
                    if cell is None:
                        print(" ~ ", end="|")  # Unexplored or empty cell
                    else:
                        print(f" {cell} ", end="|")  # Ship symbol (e.g., 'C', 'B', etc.)
                else:
                    # For attack_grid, show hits, misses, or '~' for unexplored cells
                    if cell is None:
                        print(" ~ ", end="|")  # Unexplored or empty cell
                    elif cell == 'H':
                        print(" H ", end="|")  # Hit
                    elif cell == 'M':
                        print(" M ", end="|")  # Miss
            print("\n   +" + "---+" * 12)  # Bottom border for each row


player1 = Player("Player 1")

# Place a Carrier at positions A1 to A5
for i in range(5):
    player1.ship_grid['A'][i] = player1.ships["Carrier"]["symbol"]
    player1.ships["Carrier"]["positions"].append(('A', i + 1))

# Place a Battleship at positions B1 to B4
for i in range(4):
    player1.ship_grid['B'][i] = player1.ships["Battleship"]["symbol"]
    player1.ships["Battleship"]["positions"].append(('B', i + 1))

# Display the ship_grid
player1.display_board('ship')