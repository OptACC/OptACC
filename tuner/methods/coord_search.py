import math
from ..searchresult import SearchResult
from ..testresult import TestResult
from ..point import Point

DEFAULT_INITIAL_POINT = Point(256, 128)

DEFAULT_INITIAL_STEP_SIZE = 256

BASIS = [ Point(1,0), Point(0,1), Point(0,-1), Point(-1,0) ]

# Amount by which to shrink the step size when polling is unsuccessful
SHRINK = 0.75

# If polling is unsuccessful for MAX_UNSUC consecutive iterations, the search
# will terminate.
MAX_UNSUC = 2

# Using the basis
# BASIS = [ Point(1,0), Point(0,1), Point(-math.sqrt(2)/2,-math.sqrt(2)/2) ]
# and decreasing the size by half after unsuccessful polling
#            SHRINK = 0.5
# also worked reasonably well.

# Rounds num_gangs to a multiple of 32 and vector_length to a power of 2
def _round(x):
    num_gangs = max(round(x[0] / 32.0) * 32.0, 1)
    vector_length = 2**round(math.log(x[1], 2)) if x[1] > 0 else 1
    return Point(num_gangs, vector_length)

def tune_coord_search(objective, opts, maxiter=100):
    '''Optimizes an objective function using a coordinate search algorithm.'''

    pt = DEFAULT_INITIAL_POINT
    sz = DEFAULT_INITIAL_STEP_SIZE

    times = {}
    result = objective(pt)
    times = { pt: result }

    iters = 0
    consecutive_unsucc_iters = 0
    while iters < maxiter and consecutive_unsucc_iters < MAX_UNSUC and sz >= 32:
        # Polls four new points around the current point, in this order:
        #
        #           (2) vector_length++
        #                     |
        #                     |
        # (4) num_gangs-- ----O---- (1) num_gangs++
        #                     |
        #                     |
        #           (3) vector_length--
        #
        # As soon as polling finds a better point, the current point is moved
        # and the process repeats.  If polling is unsuccessful, the distance
        # is decreased, and new points closer to the current point are polled
        # on the next iteration.
        iters += 1
        for poll in [ _round(pt + sz*vec) for vec in BASIS ]:
            if poll not in times:
                result = objective(poll)
                times[poll] = result
                if result < times[pt]:
                    pt = poll
                    poll_successful = True
                    consecutive_unsucc_iters = 0
                    break
        else:
            consecutive_unsucc_iters += 1
            sz = int(sz * SHRINK)

    best = sorted(times, key=lambda x: times[x])[0]
    return SearchResult(best, times, iters)
