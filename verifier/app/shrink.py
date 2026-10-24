import time


def shrink(args: dict, fails, valid, max_steps: int = 200, max_seconds: float = 8.0) -> dict:
    """
    args:  the failing input (dict of JSON values)
    fails: callable(candidate) -> bool, True if the mismatch still happens
    valid: callable(candidate) -> bool, True if it satisfies the problem's constraints
    returns the smallest failing, valid input found
    """
    deadline = time.monotonic() + max_seconds
    steps = 0
    best = args

    def accept(candidate) -> bool:
        nonlocal steps
        steps += 1
        return valid(candidate) and fails(candidate)

    # TODO: loop until a full pass makes no progress
    #   for each key in best:
    #       if list:  try dropping halves, then quarters, then single elements
    #       if int:   try 0, then halve toward 0, then +/-1
    #       if str:   same as list, character by character
    #   stop when steps > max_steps or time.monotonic() > deadline
    return best