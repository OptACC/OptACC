from .stats import is_diff_significant

EPSILON = 1e-7
class TestResult(object):
    '''Represents the result of testing a single point'''
    def __init__(self, point, average=float('+inf'), stdev=float('+inf'),
            error=None):
        self.point = point
        self.average = average
        self.stdev = stdev
        self.error = error

    @property
    def has_error(self):
        return self.error is not None

    def is_signif_diff(self, other, n):
        return is_diff_significant(self.average, self.stdev, n,
                                   other.average, other.stdev, n)

    def __cmp__(self, other):
        if self.has_error and not other.has_error:
            return 1
        elif other.has_error and not self.has_error:
            return -1

        if abs(self.average - other.average) < EPSILON:
            if abs(self.stdev - other.stdev) < EPSILON:
                return 0
            else:
                return 1 if self.stdev > other.stdev else -1
        else:
            return 1 if self.average > other.average else -1

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __str__(self):
        if self.has_error:
            return ('num_gangs={0:<4.0f} vector_length={1:<4.0f} => error={2}'
                    .format(self.point[0], self.point[1], self.error))
        else:
            return ('num_gangs={0:<4.0f} vector_length={1:<4.0f} => '
                    'time={2} (stdev={3})'.format(
                            self.point[0], self.point[1], self.average,
                            self.stdev))
