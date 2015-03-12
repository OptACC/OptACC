import math
from collections import namedtuple

ExhaustiveSearchResult = namedtuple('ExhaustiveSearchResult',
        ['optimal', 'tests', 'num_iterations'])

def exhaustive_search(objective, points):
    '''Optimizes an objective function using an exhaustive search.

    Arguments:
    objective -- the objective function to optimize.  Should take a Point as
                 input and return a numeric (int or float) value.
    points -- a generator producing Points at which to evaluate the function.
    '''

    times = {}
    iterations = 0
    for pt in points:
        iterations += 1
        result = objective(pt)
        if not math.isinf(result):
            times[pt] = result

    best = sorted(times, key=lambda x: times[x])[0]
    return ExhaustiveSearchResult(best, times, iterations)
