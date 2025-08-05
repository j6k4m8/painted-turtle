"""
Common utilities for interactive pen plotter applications.

This module contains shared widgets and functionality used by both
the fiducial finder and alignment wizard applications.
"""

try:
    from pyaxidraw import axidraw
except ImportError:
    axidraw = None

from pt import Vec2

try:
    from textual.app import App
    from textual.widgets import Static
    from textual.binding import Binding
    from rich.text import Text
    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from typing import Optional, List
import math


class BasePositionDisplay(Static):
    """Base widget for displaying position and connection state."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.position = Vec2(0, 0)
        self.delta = 1.0
        self.is_connected = False

    def update_position(self, position: Vec2, delta: float, is_connected: bool = False):
        """Update the position and delta values."""
        self.position = position
        self.delta = delta
        self.is_connected = is_connected
        self.refresh()

    def render(self) -> Panel:
        """Render the position display - to be overridden by subclasses."""
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Property", style="cyan", width=12)
        table.add_column("Value", style="magenta", width=20)

        table.add_row("Mode", "Hardware" if self.is_connected else "Demo")
        table.add_row("X Position", f"{self.position.x:.3f}")
        table.add_row("Y Position", f"{self.position.y:.3f}")
        table.add_row("Delta Step", f"{self.delta:.3f}")

        # Allow subclasses to add more rows
        self._add_custom_rows(table)

        title_color = "green" if self.is_connected else "yellow"
        mode_text = self._get_mode_text()

        return Panel(
            table,
            title=f"[bold {title_color}]{mode_text}[/bold {title_color}]",
            border_style=title_color,
        )

    def _add_custom_rows(self, table: Table):
        """Override in subclasses to add custom rows."""
        pass

    def _get_mode_text(self) -> str:
        """Override in subclasses to customize mode text."""
        return "Connected" if self.is_connected else "Demo Mode"


class BaseStatusLog(Static):
    """Base status log widget with common logging functionality."""

    def __init__(self, max_messages: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.messages: List[str] = []
        self.max_messages = max_messages

    def log_info(self, message: str):
        """Log an informational message."""
        self.messages.append(f"INFO: {message}")
        self._trim_messages()
        self.refresh()

    def log_warning(self, message: str):
        """Log a warning message."""
        self.messages.append(f"WARNING: {message}")
        self._trim_messages()
        self.refresh()

    def log_error(self, message: str):
        """Log an error message."""
        self.messages.append(f"ERROR: {message}")
        self._trim_messages()
        self.refresh()

    def _trim_messages(self):
        """Keep only the most recent messages."""
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def render(self) -> Panel:
        """Render the status log."""
        if not self.messages:
            content = Text("Ready", style="dim")
        else:
            content = Text()
            for msg in self.messages:
                if msg.startswith("ERROR"):
                    content.append(f"{msg}\n", style="red")
                elif msg.startswith("WARNING"):
                    content.append(f"{msg}\n", style="yellow")
                else:
                    content.append(f"{msg}\n", style="white")

        return Panel(
            content,
            title="[bold blue]Status[/bold blue]",
            border_style="blue",
            height=None,
        )


class AxiDrawController:
    """Common AxiDraw control functionality."""

    def __init__(self, opts: Optional[dict] = None):
        self.ax = None
        self.position = Vec2(0, 0)
        self.delta = 1.0
        self.is_connected = False
        self.opts = opts or {}

    def connect(self) -> bool:
        """Connect to AxiDraw device."""
        if axidraw is None:
            return False

        try:
            self.ax = axidraw.AxiDraw()
            self.ax.interactive()

            # Apply user options
            for key, value in self.opts.items():
                if hasattr(self.ax.options, key):
                    setattr(self.ax.options, key, value)

            connected = self.ax.connect()
            if connected:
                self.is_connected = True
                self.position = Vec2(*self.ax.current_pos())
            return connected
        except Exception:
            return False

    def disconnect(self):
        """Disconnect from AxiDraw device."""
        if self.ax and self.is_connected:
            self.ax.disconnect()
            self.is_connected = False

    def move_relative(self, dx: float, dy: float):
        """Move the pen head relatively."""
        new_pos = Vec2(self.position.x + dx, self.position.y + dy)
        self._move_to(new_pos)

    def move_to(self, pos: Vec2):
        """Move the pen head to absolute position."""
        self._move_to(pos)

    def _move_to(self, pos: Vec2):
        """Internal move function."""
        if self.is_connected and self.ax:
            self.ax.goto(pos.x, pos.y)
        self.position = pos

    def pen_up(self):
        """Raise the pen."""
        if self.is_connected and self.ax:
            self.ax.penup()

    def pen_down(self):
        """Lower the pen."""
        if self.is_connected and self.ax:
            self.ax.pendown()

    def disable_motors(self):
        """Disable stepper motors."""
        if self.is_connected and self.ax:
            self.ax.disconnect()

    def go_home(self):
        """Return to origin."""
        self.move_to(Vec2(0, 0))

    def increase_delta(self):
        """Increase movement step size."""
        self.delta = min(self.delta * 2, 100.0)

    def decrease_delta(self):
        """Decrease movement step size."""
        self.delta = max(self.delta / 2, 0.01)

    def draw_dot(self):
        """Draw a small dot."""
        if self.is_connected and self.ax:
            self.pen_down()
            self.pen_up()

    def draw_circle(self, radius: float = 0.5):
        """Draw a small circle."""
        if not (self.is_connected and self.ax):
            return

        # Draw a circle with 16 segments
        segments = 16
        self.pen_down()

        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            x = self.position.x + radius * math.cos(angle)
            y = self.position.y + radius * math.sin(angle)
            self._move_to(Vec2(x, y))

        self.pen_up()


class BaseInteractiveApp(App):
    """Base class for interactive pen plotter applications."""

    # Common movement bindings
    MOVEMENT_BINDINGS = [
        Binding("up", "move_up", "Move Up", priority=True),
        Binding("down", "move_down", "Move Down", priority=True),
        Binding("left", "move_left", "Move Left", priority=True),
        Binding("right", "move_right", "Move Right", priority=True),
        Binding("plus", "increase_delta", "Increase Step", priority=True),
        Binding("equal", "increase_delta", "Increase Step", priority=True),
        Binding("minus", "decrease_delta", "Decrease Step", priority=True),
        Binding("pageup", "pen_up", "Pen Up", priority=True),
        Binding("pagedown", "pen_down", "Pen Down", priority=True),
        Binding("home", "go_home", "Go Home", priority=True),
        Binding("escape", "exit_app", "Exit", priority=True),
        Binding("q", "exit_app", "Exit", priority=True),
    ]

    def __init__(self, opts: Optional[dict] = None, **kwargs):
        super().__init__(**kwargs)
        self.controller = AxiDrawController(opts)
        self.status_log: Optional[BaseStatusLog] = None
        self.position_display: Optional[BasePositionDisplay] = None

    async def on_mount(self) -> None:
        """Initialize the application."""
        if self.status_log:
            self.status_log.log_info("Initializing AxiDraw connection...")

        if self.controller.connect():
            if self.status_log:
                self.status_log.log_info("AxiDraw connected successfully!")
        else:
            if self.status_log:
                self.status_log.log_warning(
                    "Running in demo mode (AxiDraw not connected)"
                )

        self._update_display()

    def _update_display(self):
        """Update the position display."""
        if self.position_display:
            self.position_display.update_position(
                self.controller.position,
                self.controller.delta,
                self.controller.is_connected,
            )

    # Common action implementations
    async def action_move_up(self) -> None:
        """Move the pen up."""
        self.controller.move_relative(0, -self.controller.delta)
        self._update_display()
        if self.status_log:
            self.status_log.log_info(f"Moved up by {self.controller.delta}")

    async def action_move_down(self) -> None:
        """Move the pen down."""
        self.controller.move_relative(0, self.controller.delta)
        self._update_display()
        if self.status_log:
            self.status_log.log_info(f"Moved down by {self.controller.delta}")

    async def action_move_left(self) -> None:
        """Move the pen left."""
        self.controller.move_relative(-self.controller.delta, 0)
        self._update_display()
        if self.status_log:
            self.status_log.log_info(f"Moved left by {self.controller.delta}")

    async def action_move_right(self) -> None:
        """Move the pen right."""
        self.controller.move_relative(self.controller.delta, 0)
        self._update_display()
        if self.status_log:
            self.status_log.log_info(f"Moved right by {self.controller.delta}")

    async def action_increase_delta(self) -> None:
        """Increase the movement step size."""
        old_delta = self.controller.delta
        self.controller.increase_delta()
        self._update_display()
        if self.status_log:
            self.status_log.log_info(
                f"Step size: {old_delta:.3f} → {self.controller.delta:.3f}"
            )

    async def action_decrease_delta(self) -> None:
        """Decrease the movement step size."""
        old_delta = self.controller.delta
        self.controller.decrease_delta()
        self._update_display()
        if self.status_log:
            self.status_log.log_info(
                f"Step size: {old_delta:.3f} → {self.controller.delta:.3f}"
            )

    async def action_pen_up(self) -> None:
        """Raise the pen."""
        self.controller.pen_up()
        if self.status_log:
            self.status_log.log_info("Pen raised")

    async def action_pen_down(self) -> None:
        """Lower the pen."""
        self.controller.pen_down()
        if self.status_log:
            self.status_log.log_info("Pen lowered")

    async def action_go_home(self) -> None:
        """Return to origin."""
        self.controller.go_home()
        self._update_display()
        if self.status_log:
            self.status_log.log_info("Returned to origin")

    async def action_exit_app(self) -> None:
        """Exit the application."""
        self.controller.disconnect()
        self.exit()
