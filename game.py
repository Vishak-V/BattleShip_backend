def get_valid_matrix(player_name):
    """Prompts the player to input a valid 10x10 matrix line by line."""
    print(f"{player_name}, enter your 10x10 battleship grid, one row at a time (values separated by spaces):")
    matrix = []
    for i in range(10):
        while True:
            try:
                row = input(f"Row {i + 1}: ").strip()
                row_values = list(map(int, row.split()))
                if len(row_values) != 10:
                    raise ValueError("Each row must have exactly 10 integers.")
                if any(cell not in (0, 1) for cell in row_values):
                    raise ValueError("Row values must be 0 (empty) or 1 (ship).")
                matrix.append(row_values)
                break
            except ValueError as e:
                print(f"Invalid input: {e}. Please re-enter this row.")
    return matrix


def display_matrix(matrix):
    """Displays the matrix with masking for hidden cells."""
    for row in matrix:
        print(" ".join(str(cell) if cell != -1 else "." for cell in row))


def drop_bomb(matrix, x, y):
    """Handles the bomb drop logic, checking for hits and marking ships as destroyed."""
    if matrix[x][y] == 1:
        print("Hit!")
        matrix[x][y] = -1  # Mark the hit
        # Check if the entire ship is sunk
        if check_ship_sunk(matrix, x, y):
            print("You sunk a ship!")
            mark_surroundings(matrix, x, y)
        return True
    elif matrix[x][y] == 0:
        print("Miss!")
        matrix[x][y] = -1  # Mark as missed
        return False
    else:
        print("This cell has already been targeted.")
        return None


def check_ship_sunk(matrix, x, y):
    """Checks if the ship at (x, y) is completely destroyed."""
    # Check in all directions for any part of the ship still intact
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 10 and 0 <= ny < 10 and matrix[nx][ny] == 1:
                return False
    return True


def mark_surroundings(matrix, x, y):
    """Marks surrounding cells as destroyed after a ship is sunk."""
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 10 and 0 <= ny < 10 and matrix[nx][ny] == 0:
                matrix[nx][ny] = -1


def all_ships_destroyed(matrix):
    """Checks if all ships in the matrix are destroyed."""
    return all(cell != 1 for row in matrix for cell in row)


def play_game():
    """Main game logic."""
    print("Welcome to Battleship!")
    player1_matrix = get_valid_matrix("Player 1")
    player2_matrix = get_valid_matrix("Player 2")

    player_turn = 1
    while True:
        if player_turn == 1:
            print("\nPlayer 1's turn:")
            display_matrix(player2_matrix)
            x, y = map(int, input("Enter the row and column to drop the bomb (e.g., '3 4'): ").split())
            drop_bomb(player2_matrix, x, y)
            if all_ships_destroyed(player2_matrix):
                print("Player 1 wins! All ships destroyed.")
                break
        else:
            print("\nPlayer 2's turn:")
            display_matrix(player1_matrix)
            x, y = map(int, input("Enter the row and column to drop the bomb (e.g., '3 4'): ").split())
            drop_bomb(player1_matrix, x, y)
            if all_ships_destroyed(player1_matrix):
                print("Player 2 wins! All ships destroyed.")
                break
        player_turn = 3 - player_turn  # Switch turn between 1 and 2


if __name__ == "__main__":
    play_game()
