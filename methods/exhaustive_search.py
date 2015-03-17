import math
from searchresult import SearchResult
from point import Point

def _exhaustive_search(objective, points):
    '''Optimizes an objective function using an exhaustive search.

    Arguments:
    objective -- the objective function to optimize.  Receives a Point as input
                 and returns a SearchResult.
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

def tune_exhaustive_pow2(objective, opts):
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
    return _exhaustive_search(objective, generator())

def _tune_exhaustive(objective, opts, mul):
    # Exhaustive search: search multiples of mul within gang/vector ranges
    def generator():
        gmin = opts.num_gangs_min / mul
        gmax = opts.num_gangs_max / mul
        vmin = opts.vector_length_min / mul
        vmax = opts.vector_length_max / mul
        for gang_mult in range(gmin, gmax+1): # +1 since range is exclusive
            for vec_mult in range(vmin, vmax+1):
                num_gangs = max(mul * gang_mult, 1)    # max(_, 1) ensures
                vector_length = max(mul * vec_mult, 1) # these are nonzero
                yield Point(num_gangs, vector_length)
    return _exhaustive_search(objective, generator())

def tune_exhaustive_32(objective, opts):
    return _tune_exhaustive(objective, opts, 32)

def tune_exhaustive_64(objective, opts):
    return _tune_exhaustive(objective, opts, 64)

def tune_exhaustive_128(objective, opts):
    return _tune_exhaustive(objective, opts, 128)

def tune_exhaustive_256(objective, opts):
    return _tune_exhaustive(objective, opts, 256)
