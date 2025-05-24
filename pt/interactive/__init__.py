from pyaxidraw import axidraw
from pt import Vec2
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static
from textual.binding import Binding
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich import box
from typing import Optional


class PositionDisplay(Static):
    """A widget to display the current AxiDraw position."""

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
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Property", style="cyan", width=12)
        table.add_column("Value", style="magenta", width=20)

        table.add_row("Mode", "Hardware" if self.is_connected else "Demo")
        table.add_row("X Position", f"{self.position.x:.3f}")
        table.add_row("Y Position", f"{self.position.y:.3f}")
        table.add_row("Delta Step", f"{self.delta:.3f}")

        title_color = "green" if self.is_connected else "yellow"
        mode_text = "Connected" if self.is_connected else "Demo Mode"

        return Panel(
            table,
            title=f"[bold {title_color}]{mode_text}[/bold {title_color}]",
            border_style=title_color,
        )


class SavedPointsTable(Static):
    """A widget to display saved fiducial points."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.points = []

    def add_point(self, point: Vec2):
        self.points.append(point)
        self.refresh()

    def render(self) -> Panel:
        if not self.points:
            content = Text("No points captured yet", style="dim")
        else:
            table = Table(show_header=True, box=box.SIMPLE)
            table.add_column("#", style="cyan", width=4)
            table.add_column("X", style="green", width=12)
            table.add_column("Y", style="green", width=12)

            for i, point in enumerate(self.points, 1):
                table.add_row(str(i), f"{point.x:.3f}", f"{point.y:.3f}")
            content = table

        return Panel(
            content,
            title=f"[bold green]Saved Points ({len(self.points)})[/bold green]",
            border_style="green",
        )


class ControlPanel(Static):
    """A widget to display control instructions."""

    def render(self) -> Panel:
        instructions = Text()
        instructions.append("Movement Controls:\n", style="bold cyan")
        instructions.append("  ↑/↓/←/→   Move AxiDraw head\n", style="white")
        instructions.append("  +/-       Adjust step size\n", style="white")
        instructions.append("\n")
        instructions.append("Actions:\n", style="bold yellow")
        instructions.append("  Space     Capture position\n", style="white")
        instructions.append("  Home      Return to origin\n", style="white")
        instructions.append("  PgUp      Disable motors\n", style="white")
        instructions.append("  PgDn      Test pen up/down\n", style="white")
        instructions.append("  Escape    Exit application\n", style="white")

        return Panel(
            instructions,
            title="[bold magenta]Controls[/bold magenta]",
            border_style="magenta",
        )


class StatusLog(Static):
    """A custom scrolling log widget for status messages."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages = []
        self.max_messages = 100

    def render(self) -> Panel:
        if not self.messages:
            content = Text("Ready...", style="dim")
        else:
            content = Text()
            # Show the last few messages, with newest at bottom
            recent_messages = self.messages[-8:]  # Show last 8 messages
            for msg in recent_messages:
                content.append(msg + "\n")

        return Panel(
            content,
            title="[bold red]Status Log[/bold red]",
            border_style="red",
        )

    def log_info(self, message: str):
        self.messages.append(f"INFO: {message}")
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        self.refresh()

    def log_success(self, message: str):
        self.messages.append(f"SUCCESS: {message}")
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        self.refresh()

    def log_warning(self, message: str):
        self.messages.append(f"WARNING: {message}")
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        self.refresh()

    def log_error(self, message: str):
        self.messages.append(f"ERROR: {message}")
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        self.refresh()


class AxiDrawFiducialApp(App):
    """A beautiful Textual TUI for AxiDraw fiducial finding."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 3;
        grid-gutter: 1;
    }

    #position {
        column-span: 1;
        row-span: 1;
    }

    #controls {
        column-span: 1;
        row-span: 2;
    }

    #points {
        column-span: 1;
        row-span: 2;
    }

    #status {
        column-span: 3;
        row-span: 1;
        max-height: 10;
    }
    """

    BINDINGS = [
        Binding("up", "move_up", "Move Up", priority=True),
        Binding("down", "move_down", "Move Down", priority=True),
        Binding("left", "move_left", "Move Left", priority=True),
        Binding("right", "move_right", "Move Right", priority=True),
        Binding("space", "capture_position", "Capture Position", priority=True),
        Binding("home", "go_home", "Go Home", priority=True),
        Binding("pageup", "disable_motors", "Disable Motors", priority=True),
        Binding("pagedown", "test_pen", "Test Pen", priority=True),
        Binding("plus", "increase_delta", "Increase Step", priority=True),
        Binding(
            "equal", "increase_delta", "Increase Step", priority=True
        ),  # For + without shift
        Binding("minus", "decrease_delta", "Decrease Step", priority=True),
        Binding("escape", "exit_app", "Exit", priority=True),
        Binding("q", "exit_app", "Exit", priority=True),
    ]

    def __init__(self, outfile: Optional[str] = None, opts: Optional[dict] = None):
        super().__init__()
        self.outfile = outfile
        self.opts = opts or {}
        self.ax = None
        self.delta = 1.0
        self.saved_points = []

    def compose(self) -> ComposeResult:
        """Create the TUI layout."""
        yield Header(show_clock=True)

        self.position_display = PositionDisplay(id="position")
        self.control_panel = ControlPanel(id="controls")
        self.points_table = SavedPointsTable(id="points")
        self.status_log = StatusLog(id="status")

        yield self.position_display
        yield self.control_panel
        yield self.points_table
        yield self.status_log

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the AxiDraw when the app starts."""
        try:
            self.status_log.log_info("Initializing AxiDraw connection...")

            self.ax = axidraw.AxiDraw()
            self.ax.interactive()

            # Apply any custom options
            for k, v in self.opts.items():
                setattr(self.ax, k, v)

            # Try to connect to AxiDraw
            connected = self.ax.connect()
            if not connected:
                raise RuntimeError("Could not connect to AxiDraw")

            self.status_log.log_success("Connected to AxiDraw successfully!")

            # Set origin and pen up
            self.ax.moveto(0, 0)
            self.ax.penup()

            self.status_log.log_info("AxiDraw initialized and ready")
            self.update_position_display()

        except Exception as e:
            self.status_log.log_warning(f"AxiDraw not connected: {e}")
            self.status_log.log_info(
                "Running in demo mode - controls will be simulated"
            )
            self.ax = None
            # Initialize with demo position - use call_after_refresh to avoid reactive issues
            self.call_after_refresh(self._init_demo_position)

    def _init_demo_position(self):
        """Initialize the demo position safely after mount."""
        self.position_display.update_position(Vec2(0, 0), self.delta, False)

    async def on_key(self, event) -> None:
        """Handle key events that might not be caught by bindings."""
        key = event.key

        # Movement keys
        if key == "down":
            self.action_move_up()
        elif key == "up":
            self.action_move_down()
        elif key == "left":
            self.action_move_left()
        elif key == "right":
            self.action_move_right()
        # Modifier combinations
        elif key == "plus" or key == "equal":
            self.action_increase_delta()
        elif key == "minus":
            self.action_decrease_delta()
        # Action keys
        elif key == "space":
            self.action_capture_position()
        elif key == "home":
            self.action_go_home()
        elif key == "pageup":
            self.action_disable_motors()
        elif key == "pagedown":
            self.action_test_pen()
        elif key == "escape" or key == "q":
            self.action_exit_app()
        else:
            # Let other keys pass through
            event.prevent_default = False

    def update_position_display(self):
        """Update the position display with current coordinates."""
        if self.ax:
            current_pos = self.ax.current_pos()
            # Handle the case where current_pos might be a numpy array
            if hasattr(current_pos, "__len__") and len(current_pos) >= 2:
                position = Vec2(float(current_pos[0]), float(current_pos[1]))
            else:
                position = Vec2(0, 0)
            self.position_display.update_position(position, self.delta, True)

    def action_move_up(self) -> None:
        """Move the AxiDraw head up."""
        if self.ax:
            self.ax.go(0, self.delta)
            self.update_position_display()
            self.status_log.log_info(f"Moved up by {self.delta}")
        else:
            # Demo mode - simulate movement
            current = self.position_display.position
            new_pos = Vec2(current.x, current.y + self.delta)
            self.position_display.update_position(new_pos, self.delta, False)
            self.status_log.log_info(f"[Demo] Moved up by {self.delta}")

    def action_move_down(self) -> None:
        """Move the AxiDraw head down."""
        if self.ax:
            self.ax.go(0, -self.delta)
            self.update_position_display()
            self.status_log.log_info(f"Moved down by {self.delta}")
        else:
            # Demo mode - simulate movement
            current = self.position_display.position
            new_pos = Vec2(current.x, current.y - self.delta)
            self.position_display.update_position(new_pos, self.delta, False)
            self.status_log.log_info(f"[Demo] Moved down by {self.delta}")

    def action_move_left(self) -> None:
        """Move the AxiDraw head left."""
        if self.ax:
            self.ax.go(-self.delta, 0)
            self.update_position_display()
            self.status_log.log_info(f"Moved left by {self.delta}")
        else:
            # Demo mode - simulate movement
            current = self.position_display.position
            new_pos = Vec2(current.x - self.delta, current.y)
            self.position_display.update_position(new_pos, self.delta, False)
            self.status_log.log_info(f"[Demo] Moved left by {self.delta}")

    def action_move_right(self) -> None:
        """Move the AxiDraw head right."""
        if self.ax:
            self.ax.go(self.delta, 0)
            self.update_position_display()
            self.status_log.log_info(f"Moved right by {self.delta}")
        else:
            # Demo mode - simulate movement
            current = self.position_display.position
            new_pos = Vec2(current.x + self.delta, current.y)
            self.position_display.update_position(new_pos, self.delta, False)
            self.status_log.log_info(f"[Demo] Moved right by {self.delta}")

    def action_capture_position(self) -> None:
        """Capture the current position as a fiducial point."""
        if self.ax:
            current_pos = self.ax.current_pos()
            # Handle the case where current_pos might be a numpy array
            if hasattr(current_pos, "__len__") and len(current_pos) >= 2:
                pos = Vec2(float(current_pos[0]), float(current_pos[1]))
            else:
                pos = Vec2(0, 0)
        else:
            # Demo mode - use simulated position
            pos = self.position_display.position

        self.saved_points.append(pos)
        self.points_table.add_point(pos)

        self.status_log.log_success(f"Captured position: ({pos.x:.3f}, {pos.y:.3f})")

        # Save to file if specified
        if self.outfile:
            try:
                with open(self.outfile, "a") as f:
                    f.write(f"{pos.x} {pos.y}\n")
                self.status_log.log_info(f"Saved to {self.outfile}")
            except Exception as e:
                self.status_log.log_error(f"Failed to save to file: {e}")

    def action_go_home(self) -> None:
        """Return the AxiDraw head to origin."""
        if self.ax:
            self.ax.goto(0, 0)
            self.update_position_display()
            self.status_log.log_info("Returned to home position (0, 0)")
        else:
            # Demo mode - simulate going home
            self.position_display.update_position(Vec2(0, 0), self.delta, False)
            self.status_log.log_info("[Demo] Returned to home position (0, 0)")

    def action_disable_motors(self) -> None:
        """Disable the AxiDraw motors."""
        try:
            ad = axidraw.AxiDraw()
            ad.plot_setup()
            ad.options.mode = "manual"
            ad.options.manual_cmd = "disable_xy"
            ad.plot_run()
            self.status_log.log_info("Motors disabled - you can move the head manually")
        except Exception as e:
            self.status_log.log_error(f"Failed to disable motors: {e}")

    def action_test_pen(self) -> None:
        """Test pen up/down movement."""
        if self.ax:
            self.ax.penup()
            self.ax.pendown()
            self.ax.penup()
            self.status_log.log_info("Pen test completed (up → down → up)")
        else:
            self.status_log.log_info("[Demo] Pen test simulated (up → down → up)")

    def action_decrease_delta(self) -> None:
        """Decrease the movement step size."""
        self.delta /= 2
        self.position_display.update_position(
            self.position_display.position, self.delta, self.ax is not None
        )
        self.status_log.log_info(f"Decreased step size to {self.delta:.3f}")

    def action_increase_delta(self) -> None:
        """Increase the movement step size."""
        self.delta *= 2
        self.position_display.update_position(
            self.position_display.position, self.delta, self.ax is not None
        )
        self.status_log.log_info(f"Increased step size to {self.delta:.3f}")

    def action_exit_app(self) -> None:
        """Exit the application."""
        self.exit()

    async def on_unmount(self) -> None:
        """Clean up when the app exits."""
        if self.ax:
            try:
                self.ax.disconnect()
                self.status_log.log_info("Disconnected from AxiDraw")
            except Exception as e:
                self.status_log.log_error(f"Error disconnecting: {e}")


# Legacy class for backward compatibility
class AxiDrawFiducial:
    """Legacy wrapper for the original keyboard-based interface."""

    def __init__(self, outfile: str | None = None, opts: dict | None = None):
        # Launch the new TUI app instead
        app = AxiDrawFiducialApp(outfile=outfile, opts=opts)
        app.run()


def main():
    """Main entry point for the fiducial finder script."""
    import argparse

    parser = argparse.ArgumentParser(description="AxiDraw Fiducial Finder TUI")
    parser.add_argument(
        "-o", "--outfile", type=str, help="Output file to save the fiducial positions"
    )
    args = parser.parse_args()

    app = AxiDrawFiducialApp(outfile=args.outfile)
    app.run()


if __name__ == "__main__":
    main()
