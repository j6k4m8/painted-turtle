from .Plotter import EPenState, Plotter
from ..vectors import Vec2


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
