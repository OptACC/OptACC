import math
from searchresult import SearchResult
from testresult import TestResult
from point import Point

DEFAULT_INITIAL_POINT = Point(256, 128)

DEFAULT_INITIAL_STEP_SIZE = 256 #128

#BASIS = [ Point(1,0), Point(0,1), Point(-1,0), Point(0,-1) ]
#BASIS = [ Point(1,0), Point(0,1), Point(-1,-1) ]
BASIS = [ Point(1,0), Point(0,1), Point(-math.sqrt(2)/2,-math.sqrt(2)/2) ]
#BASIS = [ Point(-math.sqrt(2)/2,-math.sqrt(2)/2), Point(1,0), Point(0,1) ]
#BASIS = [ Point(-math.sqrt(2)/2,-math.sqrt(2)/2), Point(0,1), Point(1,0) ]

MAX_UNSUC = 2

# Rounds to nearest multiple of 32
#def _round(x):
#    num_gangs = max(round(x[0] / 32.0) * 32.0, 1)
#    vector_length = max(round(x[1] / 32.0) * 32.0, 1)
#    return Point(num_gangs, vector_length)

# Rounds to nearest power of 2
def _round(x):
    num_gangs = round(x[0] / 32.0) * 32.0
    #num_gangs = 2**round(math.log(x[0], 2)) if x[0] > 0 else 1
    vector_length = 2**round(math.log(x[1], 2)) if x[1] > 0 else 1
    return Point(num_gangs, vector_length)

def tune_coord_search(objective, opts, maxiter=100):
    '''Optimizes an objective function using a coord search algorithm.'''

    pt = DEFAULT_INITIAL_POINT
    sz = DEFAULT_INITIAL_STEP_SIZE

    times = {}
    result = objective(pt)
    times = { pt: result }

    iters = 0
    consecutive_unsucc_iters = 0
    while iters < maxiter and consecutive_unsucc_iters < MAX_UNSUC and sz >= 32:
        iters += 1
        poll_successful = False
        for poll in [ _round(pt + sz*vec) for vec in BASIS ]:
            print('Polling {0}'.format(poll))
            result = objective(poll)
            times[poll] = result
            if result < times[pt]:
                pt = poll
                poll_successful = True
                break
        if poll_successful:
            consecutive_unsucc_iters = 0
            print('  Polling successful!')
        else:
            consecutive_unsucc_iters += 1
            sz /= 2
            print('  Polling unsucc; size is now {0}'.format(sz))

    best = sorted(times, key=lambda x: times[x])[0]
    return SearchResult(best, times, iters)
