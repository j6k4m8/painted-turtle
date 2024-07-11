import abc
import enum
from typing import Callable, Protocol
from matplotlib import pyplot as plt
import numpy as np


class Vec2(np.ndarray):

    def __new__(cls, x, y):
        return np.array([x, y], dtype=float).view(cls)

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]


class PTObject(abc.ABC):

    bbox = tuple[Vec2, Vec2]

    @abc.abstractmethod
    def get_verbs(self) -> dict[str, Callable]:
        """
        Returns the list of verbs that can be used on this object.
        """
        ...

    @abc.abstractmethod
    def contains(self, point: Vec2) -> bool:
        """
        Returns True if the point is inside the object.
        """
        ...

    @abc.abstractmethod
    def debug_draw(self, ax):
        """
        Draws the object on the screen for debugging purposes.
        """
        ...


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
        circle = plt.Circle(self.pos, self.radius, fill=True, edgecolor="r")
        ax.add_artist(circle)


import math


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
        return self.rotation_matrix @ local + self.translation

    def _global_to_local(self, g: Vec2) -> Vec2:
        return np.linalg.inv(self.rotation_matrix) @ (g - self.translation)

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
        ax.add_artist(plt.Polygon(corners, fill=False, edgecolor="b"))

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
            plt.Polygon(bbox_corners, fill=False, edgecolor="r", linestyle="--")
        )

    def contains(self, point: Vec2) -> bool:
        # True if in the bbox
        return (
            self.bbox[0].x <= point.x <= self.bbox[1].x
            and self.bbox[0].y <= point.y <= self.bbox[1].y
        )


class EPenState(enum.Enum):
    UP = enum.auto()
    DOWN = enum.auto()


class Plotter(Protocol):

    def pen_up(self): ...

    def pen_down(self): ...

    def set_pen_state(self, state: EPenState): ...

    def move_to(self, pos: Vec2): ...

    def line_to(self, pos: Vec2): ...

    def get_pos(self) -> Vec2: ...

    def get_pen_state(self) -> EPenState: ...

    def get_path(self) -> list[tuple[Vec2, Vec2, EPenState]]: ...


class MPLMockPlotter(Plotter):

    def __init__(self):
        self.pos = Vec2(0, 0)
        self.pen_state = EPenState.UP
        self._path = []

    def pen_up(self):
        self.pen_state = EPenState.UP

    def pen_down(self):
        self.pen_state = EPenState.DOWN

    def set_pen_state(self, state: EPenState):
        self.pen_state = state

    def move_to(self, pos: Vec2):
        # Draw if pen is down
        self._path.append((self.pos, pos, self.pen_state))
        self.pos = pos

    def line_to(self, pos: Vec2):
        self.pen_down()
        self.move_to(pos)

    def get_pos(self) -> Vec2:
        return self.pos

    def get_pen_state(self) -> EPenState:
        return self.pen_state

    def get_path(self) -> list[tuple[Vec2, Vec2, EPenState]]:
        return self._path


class AxiDrawPlotter(Plotter):

    def __init__(self, opts: dict | None = None):
        from pyaxidraw import axidraw

        self.ax = axidraw.AxiDraw()
        self.ax.interactive()
        if opts:
            for k, v in opts.items():
                setattr(self.ax, k, v)
        if not self.ax.connect():
            raise RuntimeError("Could not connect to AxiDraw")
        self.pen_state = EPenState.UP
        self._path = []
        self.pos = Vec2(0, 0)

    def pen_up(self):
        self.ax.penup()
        self.pen_state = EPenState.UP

    def pen_down(self):
        self.ax.pendown()
        self.pen_state = EPenState.DOWN

    def set_pen_state(self, state: EPenState):
        if state == EPenState.UP:
            self.pen_up()
        else:
            self.pen_down()

    def move_to(self, pos: Vec2):
        self._path.append((self.pos, pos, self.pen_state))
        self.pos = pos
        self.ax.goto(*pos)

    def line_to(self, pos: Vec2):
        self.pen_down()
        self.move_to(pos)

    def get_pos(self) -> Vec2:
        return Vec2(*self.ax.current_pos())

    def get_pen_state(self) -> EPenState:
        return EPenState.UP if self.ax.current_pen() == "up" else EPenState.DOWN

    def get_path(self) -> list[tuple[Vec2, Vec2, EPenState]]:
        return self._path

    def align(self):
        self.ax.plot_setup()
        self.ax.options.pen_pos_up = 100
        self.ax.options.mode = "align"
        self.ax.plot_run()

    def complete_alignment(self):
        self.ax.interactive()


class Studio:

    pt_objects: dict[str, PTObject]

    def __init__(self, plotter: Plotter, bbox: tuple[Vec2, Vec2] | None = None):
        self.pt_objects = {}
        self.bbox = bbox or (Vec2(0, 0), Vec2(6, 4))
        self.plotter = plotter

    def add_object(self, obj: PTObject, name: str = None):
        self.pt_objects[name or f"ptobj{len(self.pt_objects)}"] = obj

    def get_objects(self) -> dict[str, PTObject]:
        return self.pt_objects

    def get_object(self, name: str) -> PTObject:
        return self.pt_objects[name]

    # Dot-notation access to objects
    def __getattr__(self, name: str) -> Callable:
        if name in self.pt_objects:
            return self.pt_objects[name]
        elif (obj_name := name.split("_")[0]) in self.pt_objects:
            return self.pt_objects[obj_name].get_verbs()[name[len(obj_name) + 1 :]](
                self.plotter
            )
        else:
            return super().__getattr__(name)

    def debug_draw(self):
        plt.figure(
            figsize=(self.bbox[1].x - self.bbox[0].x, self.bbox[1].y - self.bbox[0].y)
        )
        for _, obj in self.pt_objects.items():
            obj.debug_draw(plt.gca())

        for line in self.plotter.get_path():
            if line[2] == EPenState.DOWN:
                plt.gca().plot([line[0].x, line[1].x], [line[0].y, line[1].y], "k-")
            else:
                plt.gca().plot(
                    [line[0].x, line[1].x], [line[0].y, line[1].y], "r--", alpha=0.5
                )

        plt.gca().set_xlim(self.bbox[0].x, self.bbox[1].x)
        plt.gca().set_ylim(self.bbox[0].y, self.bbox[1].y)
        plt.gca().invert_yaxis()
        plt.show()
