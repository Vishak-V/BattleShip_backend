import subprocess
import os

uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)

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
        self.script = f"{self.name}.py"


    def display_board(self, grid_type='ship'):
        grid = self.ship_grid if grid_type == 'ship' else self.attack_grid
        print(f"{self.name}'s {grid_type.capitalize()} Grid:")
        print("   +" + "---+" * 12)  
        print("   | " + " | ".join(str(i + 1).rjust(2) for i in range(10)) + " |")  
        print("   +" + "---+" * 12) 
        for row in grid:
            print(f" {row} |", end=" ")  
            for cell in grid[row]:
                if grid_type == 'ship':
                    if cell is None:
                        print(" ~ ", end="|")  
                    else:
                        print(f" {cell} ", end="|")  
                else:
                    if cell is None:
                        print(" ~ ", end="|")  # Unexplored or empty cell
                    elif cell == 'H':
                        print(" H ", end="|")  # Hit
                    elif cell == 'M':
                        print(" M ", end="|")  # Miss
            print("\n   +" + "---+" * 12) 

    def reset_board(self):
        """
        Resets both the ship_grid and attack_grid to their original state (all cells set to None).
        Clears the positions of all ships and resets their health to the original values.
        """
        # Reset ship_grid
        for row in self.ship_grid:
            self.ship_grid[row] = [None for _ in range(10)]

        # Reset attack_grid
        for row in self.attack_grid:
            self.attack_grid[row] = [None for _ in range(10)]

        # Clear the positions and reset the health of all ships
        for ship in self.ships.values():
            ship["positions"] = []
            ship["health"] = ship["length"]  # Reset health to the ship's length 

        self.remaining_ships = 5


def start_game(player1, player2):
    """
    Initializes the ship grids for both players based on their respective .txt files.
    Each ship's placement is specified by all its coordinates in the file.
    :param player1: First Player object.
    :param player2: Second Player object.
    :return: 0 if both boards are initialized successfully, -1 otherwise.
    """
    def make_board(player):
        file_name = f"{player.name}.txt"
        board_str = subprocess.run(['py', f'{player.name}.py', 'initialize' ], capture_output=True, text = True).stdout
        board_str = board_str[:-1]    #this generates a new line
        file_path = os.path.join(uploads_dir, file_name)
        with open(file_path, "w") as f:
            f.write(board_str)
        
    make_board(player1)
    make_board(player2)
        
    def read_ship_placement(player):
        """
        Reads the ship placement from the player's .txt file and updates their ship_grid.
        :param player: Player object.
        :return: 0 if successful, -1 if any error occurs.
        """
        filename = f"{player.name}.txt"
        file_path = os.path.join(uploads_dir, filename)
        try:
            with open(file_path, 'r') as file:
                for line in file:
                    # Parse the line: <ship_name>,<row1><col1>,<row2><col2>,...,<rowN><colN>
                    parts = line.strip().split(',')
                    ship_name = parts[0]
                    coordinates = parts[1:]

                    # Get the ship details from the player's ships dictionary
                    ship = player.ships.get(ship_name)
                    if not ship:
                        print(f"Error: Ship '{ship_name}' not found in {player.name}'s fleet.")
                        return -1

                    # Check if the number of coordinates matches the ship's length
                    if len(coordinates) != ship["length"]:
                        print(f"Error: Ship '{ship_name}' requires {ship['length']} coordinates, but {len(coordinates)} were provided.")
                        return -1

                    # Extract rows and columns from coordinates
                    rows = [coord[0] for coord in coordinates]
                    cols = [int(coord[1:]) for coord in coordinates]

                    # Check if the ship is placed horizontally, vertically, or diagonally
                    if all(row == rows[0] for row in rows) and cols == list(range(cols[0], cols[0] + len(cols))):
                        orientation = 'horizontal'
                    elif all(col == cols[0] for col in cols) and [ord(row) for row in rows] == list(range(ord(rows[0]), ord(rows[0]) + len(rows))):
                        orientation = 'vertical'
                    else:
                        print(f"Error: Ship '{ship_name}' is not placed horizontally ors vertically.")
                        return -1

                    # Validate and update coordinates in a single traversal
                    for coord in coordinates:
                        row = coord[0]
                        col = int(coord[1:]) - 1  # Convert to 0-based index

                        # Check if the coordinate is within the grid bounds
                        if row not in player.ship_grid or col < 0 or col >= 10:
                            print(f"Error: Coordinate '{coord}' for {player.name}'s {ship_name} is out of bounds.")
                            return -1

                        # Check if the cell is already occupied
                        if player.ship_grid[row][col] is not None:
                            print(f"Error: Coordinate '{coord}' for {player.name}'s {ship_name} overlaps with another ship.")
                            return -1

                        # Update the board
                        player.ship_grid[row][col] = ship["symbol"]
                        ship["positions"].append((row, col + 1))  # Store 1-based positions
            return 0  # All ships placed successfully
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found for {player.name}.")
            return -1
        except Exception as e:
            print(f"Error reading {player.name}'s ship placement file: {e}")
            return -1


    def get_player_move(current_player):
        """
        Validates the move generated by the player's script and returns it in a usable format.
        :param current_player: The Player object whose turn it is.
        :param move_str: The move string returned by the player's script (e.g., "A1", "B2").
        :return: A tuple (row, col) representing the move, or None if the move is invalid.
        """

        def grid_to_string(attack_grid, ship_grid):
            """
            Converts both attack_grid and ship_grid into string representations.
            :param attack_grid: The attack grid (dictionary of lists).
            :param ship_grid: The ship grid (dictionary of lists).
            :return: A tuple (attack_grid_str, ship_grid_str) representing both grids as strings.
            """
            attack_grid_str = ""
            ship_grid_str = ""
            
            # Convert attack_grid to string
            for row in sorted(attack_grid.keys()):  # Ensure rows are processed in order (A to J)
                for cell in attack_grid[row]:
                    if cell is None:
                        attack_grid_str += "~"  # Unexplored or empty cell
                    elif cell == 'H':
                        attack_grid_str += "H"  # Hit
                    elif cell == 'M':
                        attack_grid_str += "M"  # Miss
                attack_grid_str += "\n"  # Newline after each row
            
            # Convert ship_grid to string
            for row in sorted(ship_grid.keys()):  # Ensure rows are processed in order (A to J)
                for cell in ship_grid[row]:
                    if cell is None:
                        ship_grid_str += "~"  # Unexplored or empty cell
                    else:
                        ship_grid_str += cell  # Exact ship symbol (e.g., 'C', 'B', etc.)
                ship_grid_str += "\n"  # Newline after each row
            
            # Remove trailing newlines and return as a tuple
            return attack_grid_str.strip(), ship_grid_str.strip()


        attack_grid_string, ship_grid_string = grid_to_string(current_player.attack_grid, current_player.ship_grid)


        move_str = subprocess.run(['py', os.path.join(uploads_dir, current_player.script), ship_grid_string, attack_grid_string], capture_output=True, text = True).stdout
        move_str = move_str[:-1]    #this generates a new line
        try:
            # Validate the move string format
            if not isinstance(move_str, str) or len(move_str) < 2 or not move_str[0].isalpha() or not move_str[1:].isdigit():
                print(f"Error: {current_player.name}'s move '{move_str}' is not in the correct format (e.g., 'A1', 'B2').")
                return None

            # Extract row and column from the move string
            row = move_str[0].upper()  # Ensure row is uppercase
            col = int(move_str[1:])    # Convert column to integer

            # Validate the row and column
            if row not in current_player.attack_grid or col < 1 or col > 10:
                print(f"Error: {current_player.name}'s move '{move_str}' is out of bounds.")
                return None

            # Convert col to 0-based index
            col_index = col - 1

            # Check if the move has already been tried
            if current_player.attack_grid[row][col_index] is not None:
                print(f"Error: {current_player.name}'s move '{move_str}' has already been tried.")
                return None

            # If all checks pass, return the move as a tuple
            return (row, col)
        except Exception as e:
            print(f"Error validating {current_player.name}'s move: {e}")
            return None
    

    def apply_move(current_player, opponent, move):
        """
        Applies the move to the opponent's ship_grid and updates the current player's attack_grid.
        :param current_player: The Player object whose turn it is.
        :param opponent: The Player object representing the opponent.
        :param move: A tuple (row, col) representing the move.
        :return: "hit", "miss", or "sunk" depending on the result of the move.
        """
        row, col = move
        col_index = col - 1  # Convert to 0-based index

        # Check if the move hits a ship
        if opponent.ship_grid[row][col_index] is not None:
            # It's a hit
            # print("It's a hit.")
            current_player.attack_grid[row][col_index] = 'H'  # Mark as hit on the attacker's attack_grid
            ship_symbol = opponent.ship_grid[row][col_index]
            opponent.ship_grid[row][col_index] = 'X'  # Mark as hit on the opponent's ship_grid

            # Find the ship that was hit
            for ship_name, ship in opponent.ships.items():
                if ship["symbol"] == ship_symbol:
                    # Decrement the ship's health
                    ship["health"] -= 1

                    # Check if the ship is sunk
                    if ship["health"] == 0:
                        opponent.remaining_ships -= 1
                        return ("sunk", ship_name)
                    return "hit"
        else:
            # It's a miss
            current_player.attack_grid[row][col_index] = 'M'  # Mark as miss on the attacker's attack_grid
            return "miss"


    # Initialize boards for both players
    if read_ship_placement(player1) == -1:
        print(f"{player1.name} failed to initialize their board. {player1.name} loses.")
        player1.reset_board()
        return -1

    if read_ship_placement(player2) == -1:
        print(f"{player2.name} failed to initialize their board. {player2.name} loses.")
        player2.reset_board()
        player1.reset_board()
        return -1

    print("Both Player 1's and Player 2's boards initialized successfully.\n")
    player1.display_board()
    player2.display_board()
    current_player = player1
    opponent = player2

    while True:
        # Display the current state of the boards
        print(f"\n{current_player.name}'s turn:")
        current_player.display_board('attack')
        opponent.display_board('ship')  # For debugging, remove in final version

        # Get the current player's move
        move = get_player_move(current_player)
        if move is None:
            print(f"{current_player.name} made an invalid move. {opponent.name} won.")
            opponent.wins += 1
            current_player.losses += 1
            current_player.reset_board()
            opponent.reset_board()
            return opponent.name
        print(f"Move {move}")
        # Apply the move and check for hits/misses
        result = apply_move(current_player, opponent, move)
        if result == "hit":
            print(f"{current_player.name} hit a ship at {move}!")
        elif result == "miss":
            print(f"{current_player.name} missed at {move}.")
        else:
            print(f"{current_player.name} sunk {opponent.name}'s {result[1]}!")

        # Check if the opponent has lost all ships
        if opponent.remaining_ships == 0:
            print(f"{current_player.name} has sunk all of {opponent.name}'s ships! {current_player.name} wins!")
            current_player.wins += 1
            opponent.losses += 1
            current_player.reset_board()
            opponent.reset_board()
            return current_player.name

        # Switch turns
        current_player, opponent = opponent, current_player




# player1 = Player("Player1")
# player2 = Player("Player2")

# # player1.display_board()
# winner = start_game(player1, player2)
# print(f"The winner is {winner}")
# print("Player 1 wins: {player1.wins}")
# print("Player 2 wins: {player2.wins}")

def play_bots(bot1:str,bot2:str):
    '''
    Takes in the file names and returns a winner
    '''
    player1 = Player("Player1")
    player2 = Player("Player2")

    # player1.display_board()
    winner = start_game(player1, player2)
    print(f"The winner is {winner}")
    print("Player 1 wins: {player1.wins}")
    print("Player 2 wins: {player2.wins}")
    return winner

play_bots("Player1","Player2")

    
