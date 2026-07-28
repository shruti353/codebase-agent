"""
This is a sample Python file for testing AST parsing.
"""

import math
import os
from datetime import datetime

PI = 3.14159


def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"


def factorial(n: int) -> int:
    """Calculate factorial recursively."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)


class Calculator:
    """Simple calculator class."""

    def __init__(self):
        self.history = []

    def add(self, a: int, b: int) -> int:
        result = a + b
        self.history.append(("add", a, b, result))
        return result

    def multiply(self, a: int, b: int) -> int:
        result = a * b
        self.history.append(("multiply", a, b, result))
        return result


def process_numbers(numbers):
    squares = [x * x for x in numbers if x % 2 == 0]

    for num in squares:
        if num > 50:
            print(f"Large square: {num}")
        else:
            print(f"Small square: {num}")

    return squares


def divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None
    finally:
        print("Division attempted")


if __name__ == "__main__":
    print(greet("Shruti"))

    calc = Calculator()

    print(calc.add(10, 20))
    print(calc.multiply(5, 6))

    print(factorial(5))

    nums = [1, 2, 3, 4, 5, 6, 7, 8]
    print(process_numbers(nums))

    print(divide(10, 2))
    print(divide(10, 0))

    current_time = datetime.now()
    print("Current time:", current_time)

    print("Square root of 81:", math.sqrt(81))