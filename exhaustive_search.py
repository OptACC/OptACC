import math
from searchresult import SearchResult

def exhaustive_search(objective, points):
    '''Optimizes an objective function using an exhaustive search.

    Arguments:
    objective -- the objective function to optimize.  Receives a Point as input
                 and returns a pair (x, s), where x is a numeric (int or float)
                 value representing the average runtime and s is the standard
                 deviation of the runtimes.
    points -- a generator producing Points at which to evaluate the function.
    '''

    times = {}
    iterations = 0
    for pt in points:
        iterations += 1
        result = objective(pt)
        if not result.has_error:
            times[pt] = result

    best = sorted(times, key=lambda x: times[x])[0]
    return SearchResult(best, times, iterations)
