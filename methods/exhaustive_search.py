import math
from searchresult import SearchResult
from point import Point

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

def tune_pow2(objective, opts):
    # Exhaustive search: search powers of 2 within gang/vector ranges
    def ilog2(x):
        return int(math.floor(math.log(x, 2)))
    def generator():
        gmin = ilog2(opts.num_gangs_min)
        gmax = ilog2(opts.num_gangs_max)
        vmin = ilog2(opts.vector_length_min)
        vmax = ilog2(opts.vector_length_max)
        for gang_pow2 in range(gmin, gmax+1): # +1 since range is exclusive
            for vec_pow2 in range(vmin, vmax+1):
                yield Point(1 << gang_pow2, 1 << vec_pow2)
    return exhaustive_search(objective, generator())

def tune_32(objective, opts):
    # Exhaustive search: search multiples of 32 within gang/vector ranges
    def generator():
        gmin = opts.num_gangs_min / 32
        gmax = opts.num_gangs_max / 32
        vmin = opts.vector_length_min / 32
        vmax = opts.vector_length_max / 32
        for gang_mult in range(gmin, gmax+1): # +1 since range is exclusive
            for vec_mult in range(vmin, vmax+1):
                num_gangs = max(32 * gang_mult, 1)    # max(_, 1) ensures
                vector_length = max(32 * vec_mult, 1) # these are nonzero
                yield Point(num_gangs, vector_length)
    return exhaustive_search(objective, generator())
