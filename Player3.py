import sys
import random

# print("Ship_Grid")

# print(sys.argv[1])
# print("Attack_grid")
# print(sys.argv[2])


# Generate a random character from 'A' to 'J'
random_char = chr(random.randint(ord('A'), ord('J')))

# Generate a random digit from '1' to '10'
random_digit = random.randint(1, 10)

# Print the result
print(random_char + str(random_digit))