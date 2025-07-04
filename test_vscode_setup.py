# This file has intentional errors to test VS Code extensions


# Missing type annotation - FIXED
def bad_function(x: int) -> int:
    return x + 1


# Unused import - REMOVED


# Bad formatting - FIXED
def poorly_formatted() -> int:
    return 1 + 2


# Missing docstring - FIXED
def no_docstring() -> None:
    """Function with no meaningful docstring."""


# Unused variable - FIXED
def unused_var() -> str:
    result = "hello"  # Now used
    return result


# Bad quotes - FIXED
message = "This uses single quotes"

# Too long line - FIXED
very_long_line = (
    "This is a very long line that exceeds the 100 character limit "
    "and should be flagged by the linter for being too long"
)

# Print statement (should be logging) - FIXED
import logging

# Exception handling - FIXED
try:
    result = 1 / 0
except ZeroDivisionError:
    logging.warning("Division by zero attempted")

# Global variable - FIXED
global_var = 42


def modify_global() -> None:
    """Modify the global variable."""
    global global_var  # Keep global since it's at module level
    global_var = 100
