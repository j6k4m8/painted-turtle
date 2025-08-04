import numpy as np
import math


class Vec2(np.ndarray):
    def __new__(cls, x, y):
        return np.array([x, y], dtype=float).view(cls)

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    def __eq__(self, other):
        """Override equality operator to properly compare Vec2 objects."""
        if not isinstance(other, Vec2):
            return False
        return abs(self.x - other.x) < 1e-10 and abs(self.y - other.y) < 1e-10


def _compute_rotation_from_opposite_corners(a, c, w, h):
    # Extract coordinates of points a and c
    x1, y1 = a
    x2, y2 = c

    # Calculate the vector from a to c
    dx = x2 - x1
    dy = y2 - y1

    # Calculate the angle of this vector with respect to the x-axis
    angle = math.atan2(dy, dx)

    # The angle should be offset by what we Eexpect the angle to be,
    # which is the angle of the vector from a to b
    angle -= math.atan2(h, w)

    return angle
