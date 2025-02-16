import sys
import random


# Generate a random character from 'A' to 'J'
random_char = chr(random.randint(ord('A'), ord('J')))

# Generate a random digit from '1' to '10'
random_digit = random.randint(1, 10)

# Print the result
print(random_char + str(random_digit))