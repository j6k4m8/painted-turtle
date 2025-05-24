from .. import Vec2, EPenState


class AxiDrawFiducial:
    """
    This interactive class is used to find a fiducial marker on the canvas.

    Using the L/R and U/D keys, the user can move the AxiDraw head manually,
    and then hit the space bar to capture the current pen position.
    """

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
