from functools import wraps
import time

def timing(f):
    """
    Function decorator to measure elapsed time.
    :param f: function
    """
    @wraps(f)
    def wrap(*args, **kwargs):
        ts = time.time()
        result = f(*args, **kwargs)
        te = time.time()
        print(f"{f.__name__}() --> {te-ts} s elapsed.")
        return result
    return wrap