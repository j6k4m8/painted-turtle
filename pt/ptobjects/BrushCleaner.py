import numpy as np
import matplotlib.pyplot as plt
from typing import Callable
from .PTObject import PTObject
from ..vectors import Vec2
from ..plotter import Plotter


class BrushCleaner(PTObject):
    """
    A brush cleaner is a clean water container with a paper towel next to it.
    """

    def __init__(self, pos: Vec2, radius: float):
        self.pos = pos
        self.radius = radius
        self.bbox = (pos - Vec2(radius, radius), pos + Vec2(radius, radius))

    def get_verbs(self) -> dict[str, Callable]:
        return {"clean": self._clean}

    def _clean(self, plotter: "Plotter") -> Callable:
        # Raise the brush to enter the cleaner
        def _routine():
            old_pos = plotter.get_pos()
            old_pen_state = plotter.get_pen_state()

            plotter.pen_up()

            # Move to the cleaner
            plotter.move_to(self.pos)

            # Lower the brush
            plotter.pen_down()

            # Move the brush around in a little circle
            for i in range(10):
                plotter.move_to(
                    self.pos
                    + Vec2(np.cos(i / 5 * 2 * np.pi), np.sin(i / 5 * 2 * np.pi))
                    * self.radius
                    * 0.3
                )

            # Raise the brush
            plotter.pen_up()

            # Move back to the original position
            # plotter.move_to(old_pos)
            # plotter.set_pen_state(old_pen_state)

        return _routine

    def contains(self, point: Vec2) -> bool:
        return False

    def debug_draw(self, ax):
        # Draw a circle artist, centered at pos
        circle = plt.Circle(self.pos, self.radius, fill=True, edgecolor="r")  # type: ignore
        ax.add_artist(circle)
