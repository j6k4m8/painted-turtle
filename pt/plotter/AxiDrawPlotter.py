from .Plotter import EPenState, Plotter
from ..vectors import Vec2


class AxiDrawPlotter(Plotter):
    def __init__(self, opts: dict | None = None, alignment_offset: Vec2 | None = None):
        """
        Initialize the AxiDraw plotter.

        Arguments:
            opts: Optional dictionary of options to set for the AxiDraw.
            alignment_offset: Optional Vec2 to offset the alignment position.
        """
        if alignment_offset is None:
            alignment_offset = Vec2(0, 0)
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
        self.alignment_offset = alignment_offset

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
        adjusted_pos = Vec2(
            pos.x + self.alignment_offset.x, pos.y + self.alignment_offset.y
        )
        self._path.append((self.pos, adjusted_pos, self.pen_state))
        self.pos = adjusted_pos
        self.ax.goto(*adjusted_pos)

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

    def set_alignment_offsets(self, offset: Vec2):
        """Set the alignment offsets for this plotter."""
        self.alignment_offset = offset

    def reset_alignment_offsets(self):
        """Reset the alignment offsets to zero."""
        self.alignment_offset = Vec2(0, 0)
