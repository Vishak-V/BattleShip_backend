def get_matrix_from_user():
    """Prompts the user to input a 10x10 matrix row by row."""
    print("Enter a 10x10 matrix row by row. Separate numbers with spaces:")
    matrix = []
    for i in range(10):
        while True:
            try:
                row = list(map(int, input(f"Row {i + 1}: ").strip().split()))
                if len(row) != 10:
                    raise ValueError("Each row must have exactly 10 integers.")
                matrix.append(row)
                break
            except ValueError as e:
                print(f"Invalid input: {e}. Please re-enter the row.")
    return matrix

def find_first_zero(matrix):
    """Finds the first row and column that contains a 0."""
    for row_idx, row in enumerate(matrix):
        for col_idx, value in enumerate(row):
            if value == 0:
                return row_idx , col_idx   # 0-based indexing
    return None

def main():
    matrix = get_matrix_from_user()
    result = find_first_zero(matrix)

    if result:
        row, col = result
        print(f"The first 0 is found at row {row}, column {col}.")
    else:
        print("No 0 found in the matrix.")

if __name__ == "__main__":
    main()
