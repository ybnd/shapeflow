from functools import wraps
import time


def restrict(val, minval, maxval):
    """ https://stackoverflow.com/questions/4092528/how-to-clamp-an-integer-to-some-range """
    if val < minval: return minval
    if val > maxval: return maxval
    return val


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