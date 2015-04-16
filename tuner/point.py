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

    def __truediv__(self, other):
        # Division has changed in Python 3
        return self.__div__(other)

    def __radd__(self, other):
        return self.__add__(other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __str__(self):
        return 'Point(' + ', '.join(map(str, self.coords)) + ')'

    def __repr__(self):
        return self.__str__()
