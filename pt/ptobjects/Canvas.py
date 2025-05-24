from typing import Callable
from matplotlib import pyplot as plt
import numpy as np

from ..plotter import Plotter
from .PTObject import PTObject
from ..vectors import Vec2, _compute_rotation_from_opposite_corners


class Canvas(PTObject):
    def __init__(self, size: Vec2, start: Vec2, end: Vec2):
        """
        Create a new Canvas.

        You're probably wondering why it's so complicated to create a canvas.

        Why do we need size AND two corners? Because the canvas can be rotated.
        The first thing we do in this class is to calculate the rotation matrix
        that will allow us to rotate the canvas, so that when you ask for lines
        to be drawn relative to the _canvas_ coordinate system, they will be
        rotated correctly.

        """
        self.size = size
        self.bbox = (start, end)
        self.start = start
        self.end = end
        # We have possibly conflicting information here. The size of the canvas
        # might disagree with the distance between the two corners. i.e., there
        # are an infinite number of canvases that could be created with the
        # two corners if you don't specify the size.
        # So first we'll calculate the vec from start to end, and then we'll
        # rescale end to be the correct distance from start.
        self.vec_to_end = end - start
        diag = (size.x**2 + size.y**2) ** 0.5
        # Create a new end pt that is the correct distance from start
        self._originally_specified_end = end
        self.end = start + self.vec_to_end / np.linalg.norm(self.vec_to_end) * diag

        # Calculate the rotation matrix
        theta = _compute_rotation_from_opposite_corners(
            (start.x, start.y), (self.end.x, self.end.y), size.x, size.y
        )
        self.rotation_matrix = np.array(
            [[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]]
        )
        self.translation = start

    def _local_to_global(self, local: Vec2) -> Vec2:
        return self.rotation_matrix @ local + self.translation  # type: ignore

    def _global_to_local(self, g: Vec2) -> Vec2:
        return np.linalg.inv(self.rotation_matrix) @ (g - self.translation)  # type: ignore

    def get_verbs(self) -> dict[str, Callable]:
        return {"draw_line": self._draw_line}

    def _draw_line(self, plotter: "Plotter") -> Callable:
        def _routine(local_start: Vec2, local_end: Vec2):
            # Rotate the points
            global_start = self._local_to_global(local_start)
            global_end = self._local_to_global(local_end)

            # Move to the start point
            plotter.move_to(global_start)

            # Draw the line
            plotter.line_to(global_end)

        return _routine

    def debug_draw(self, ax):
        # Draw the rotated canvas. Simplest is to draw a Polygon where the
        # corners are the corners of the canvas.
        corners = [
            self._local_to_global(Vec2(0, 0)),
            self._local_to_global(Vec2(self.size.x, 0)),
            self._local_to_global(Vec2(self.size.x, self.size.y)),
            self._local_to_global(Vec2(0, self.size.y)),
        ]
        ax.add_artist(plt.Polygon(corners, fill=False, edgecolor="b"))  # type: ignore

        # Dotted bbox
        max_global = max(corners, key=lambda x: x.x), max(corners, key=lambda x: x.y)
        min_global = min(corners, key=lambda x: x.x), min(corners, key=lambda x: x.y)
        bbox_corners = [
            Vec2(max_global[0].x, min_global[1].y),
            Vec2(min_global[0].x, min_global[1].y),
            Vec2(min_global[0].x, max_global[1].y),
            Vec2(max_global[0].x, max_global[1].y),
        ]
        ax.add_artist(
            plt.Polygon(bbox_corners, fill=False, edgecolor="r", linestyle="--")  # type: ignore
        )

    def contains(self, point: Vec2) -> bool:
        # True if in the bbox
        return (
            self.bbox[0].x <= point.x <= self.bbox[1].x
            and self.bbox[0].y <= point.y <= self.bbox[1].y
        )
