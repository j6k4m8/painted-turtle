from ..vectors import Vec2
import abc
from typing import Callable


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
