from __future__ import print_function
import math
from collections import namedtuple

class Point(object):
    '''Represents a point in n-dimensional real space.'''

    def __init__(self, *args):
        # For consistency, make sure coords is a list of floats
        self.coords = list(map(float, args))

    def __hash__(self):
        return tuple(self.coords).__hash__()

    def __eq__(self, other):
        if not isinstance(other, Point):
            return False

        return self.coords == other.coords

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        return len(self.coords)

    def __getitem__(self, key):
        return self.coords[key]

    def __iter__(self):
        return self.coords.__iter__()

    def __add__(self, other):
        # Hack to make sum() work
        if isinstance(other, int) and other == 0:
            return Point(*tuple(self.coords))

        coords = tuple(self.coords[i] + other.coords[i]
                for i in range(len(self)))
        return Point(*coords)

    def __sub__(self, other):
        coords = tuple(self.coords[i] - other.coords[i]
                for i in range(len(self)))
        return Point(*coords)

    def __mul__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            # Scalar multiplication
            coords = tuple(self.coords[i] * other
                    for i in range(len(self)))
            return Point(*coords)
        else:
            raise ArgumentError('Only scalar multiplication is allowed')

    def __div__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            # Scalar multiplication
            coords = tuple(self.coords[i] / other
                    for i in range(len(self)))
            return Point(*coords)
        else:
            raise ArgumentError('Only scalar division is allowed')

    def __radd__(self, other):
        return self.__add__(other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __str__(self):
        return 'Point(' + ', '.join(map(str, self.coords)) + ')'

    def __repr__(self):
        return self.__str__()

NelderMeadResult = namedtuple('NelderMeadResult', ['optimal', 'tests'])

def nelder_mead(objective, initial, neighbors, roundfn, maxiter=100):
    '''Optimizes the objective function using a modified Nelder-Mead algorithm.

    Arguments:
    objective -- the objective function to optimize.  Should take a Point as
                 input and return a numeric (int or float) value.
    initial -- A Point representing the initial point to test.
    neighbors -- a function that accepts a Point and returns an iterable of
                 Points neighboring the input.
    roundfn -- a function that accepts a Point and returns a Point, rounded
               according to the rules necessary to produce a valid input to the
               objective function.
    maxiter -- The maximum number of iterations of the algorithm to run before
               aborting and returning the result.  Default 100.
    '''

    # Wrap the objective function in a memoized function.  This serves two
    # purposes: to prevent calling the objective function on the same point
    # multiple times, and to keep a record of every point tested to include in
    # the results.
    eval_cache = {}
    def f(point):
        if point not in eval_cache:
            eval_cache[point] = objective(point)

        return eval_cache[point]

    N = len(initial)
    RHO = 1
    CHI = 2
    GAMMA = 0.5
    SIGMA = 0.5

    # Generate initial simplex
    simplex = [initial] + neighbors(initial)[:N]

    visited = set()

    def shrink():
        '''Performs the shrink step from the Nelder-Mead algorithm.'''
        for i in range(1, N + 1):
            xi = simplex[0] + SIGMA*(simplex[i] - simplex[0])
            xi = roundfn(xi)
            if xi == simplex[i]:
                for point in neighbors(simplex[0]):
                    if point not in visited:
                        xi = point

            visited.add(xi)
            simplex[i] = xi

    iterations = 1
    while iterations < maxiter:
        # Test for convergence
        # If every point in the simplex is the same, the algorithm terminates
        x0 = simplex[0]
        converged = True
        for xi in simplex[1:]:
            if xi != x0:
                converged = False
                break

        if converged:
            break

        # Step 1: Order simplex by objective value
        simplex = list(sorted(simplex, key=f))

        # Compute the centroid of the best N points of the simplex
        xbar = sum(simplex[:N]) / N

        # Step 2: Compute the reflection point xr
        xr = xbar + RHO*(xbar - simplex[-1])
        xr = roundfn(xr)
        visited.add(xr)

        if f(simplex[0]) <= f(xr) < f(simplex[-2]):
            # Accept xr
            simplex[-1] = xr
        elif f(xr) < f(simplex[0]):
            # Step 3: Calculate expansion point xe
            xe = xbar + CHI*(xr - xbar)
            xe = roundfn(xe)
            visited.add(xe)

            if f(xe) < f(xr):
                # Accept xe
                simplex[-1] = xe
            else: # f(xe) >= f(xr)
                # Accept xr
                simplex[-1] = xr
        else: # f(xr) >= f(xn)
            # Step 4: Contract
            if f(xr) < f(simplex[-1]):
                # Outside contraction
                xc = xbar + GAMMA*(xr - xbar)
                xc = roundfn(xc)
                if xc == xr:
                    for point in neighbors(simplex[0]):
                        if point not in visited:
                            xc = point
                            break

                visited.add(xc)
                if f(xc) <= f(xr):
                    # Accept xc
                    simplex[-1] = xc
                else:
                    shrink()
            else:
                # Inside contraction
                xc = xbar - GAMMA*(xbar - simplex[-1])
                xc = roundfn(xc)
                if xc == simplex[-1]:
                    for point in neighbors(simplex[0]):
                        if point not in visited:
                            xc = point
                            break

                visited.add(xc)
                if f(xc) < f(simplex[-1]):
                    # Accept xc
                    simplex[-1] = xc
                else:
                    shrink()

        iterations += 1
    return NelderMeadResult(simplex[0], eval_cache)

def round_acc(x):
    num_gangs = round(x[0] / 32.0) * 32.0
    vector_length = 2**round(math.log(x[1], 2)) if x[1] > 0 else 1
    return Point(num_gangs, vector_length)

def neighbors_acc(x):
    round_acc(x)
    n = []
    for i in [-32, 0, 32]:
        for j in [0.5, 1, 2]:
            if i == 0 and j == 1:
                continue
            n.append(Point(x[0]+i, x[1]*j))
    return n

def twomm_test():
    times = {}
    for line in open('twomm_dummy'):
        ng, vl, t = map(float, line.split(','))
        times[Point(ng, vl)] = t

    def objective(p):
        if p[0] <= 0 or p[1] <= 0 or p[0] > 1024 or p[1] > 1024:
            return float('inf')
        return times[p]

    result = nelder_mead(objective, Point(256, 256), neighbors_acc,
            round_acc)
    print(result, objective(result.optimal))

if __name__ == '__main__':
    twomm_test()
