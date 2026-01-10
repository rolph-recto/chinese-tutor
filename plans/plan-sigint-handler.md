# Plan: SIGINT Handler for "q" Key Behavior

## Problem
Currently, the "q" key handling is duplicated 4 times in `main.py` (lines 234-237, 254-257, 274-277, 296-299), each doing the same thing. Additionally, pressing Ctrl+C (SIGINT) doesn't save student state, leading to lost progress.

## Solution

### 1. Create helper function for quit handling
```python
def handle_quit(student_state: StudentState) -> None:
    """Print quit message, save state, and exit."""
    print("\nGoodbye! Your progress has been saved.")
    save_student_state(student_state)
```

### 2. Add SIGINT handler
```python
import signal
import sys

def create_sigint_handler(student_state: StudentState):
    def sigint_handler(signum, frame):
        print("\nGoodbye! Your progress has been saved.")
        save_student_state(student_state)
        sys.exit(0)
    return sigint_handler
```

### 3. Register handler in run_interactive()
Register the SIGINT handler at the start of the interactive session.

### 4. Refactor all 4 "q" checks
Replace duplicated code with calls to `handle_quit()`.

## Benefits
- Consistent quit behavior for both "q" key and Ctrl+C
- No code duplication
- Easier to test and maintain
