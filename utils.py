from functools import wraps
import time

def timing(f):
    ""
    @wraps(f)
    def wrap(*args, **kwargs):
        ts = time.time()
        result = f(*args, **kwargs)
        te = time.time()
        print(f"{f.__name__}() --> {te-ts} s elapsed.")
        return result
    return wrap