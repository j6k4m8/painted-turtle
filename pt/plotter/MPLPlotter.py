from . import Plotter, EPenState
from ..vectors import Vec2


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
