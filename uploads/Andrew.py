import sys
import random

def get_ships():
    ships = [
        ("Carrier", "A1", "A2", "A3", "A4", "A5"),
        ("Battleship", "B2", "C2", "D2", "E2"),
        ("Cruiser", "C3", "D3", "E3"),
        ("Submarine", "D6", "E6", "F6"),
        ("Destroyer", "E7", "E8")
    ]

    # Create the rows for each ship
    rows = [",".join(ship) for ship in ships]
    
    # Join rows with newlines
    result = "\n".join(rows)

    return result

# Check if the first command-line argument is "initialize"
if len(sys.argv) > 1 and sys.argv[1].lower() == "initialize":
    print(get_ships())
else:
    # Generate a random character from 'A' to 'J'
    moves_str = sys.argv[3]
    moves_list = moves_str.split(" ")

    while True:
        random_char = chr(random.randint(ord('A'), ord('J')))

        # Generate a random digit from '1' to '10'
        random_digit = random.randint(1, 10)

        move = random_char + str(random_digit)

        if move in moves_list:
            continue
        else:
            print(move)
            break
