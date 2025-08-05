"""
Alignment calibration wizard for pen plotters as described in alignment.md.

This module implements the interactive alignment wizard that helps users
calibrate alignment offsets between different pens.
"""

try:
    from pyaxidraw import axidraw
except ImportError:
    axidraw = None

from pt import Vec2

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Footer, Header, Static
    from textual.binding import Binding
    from rich.text import Text
    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from typing import Optional
import csv

from .interactive_utils import (
    BasePositionDisplay,
    BaseStatusLog,
    BaseInteractiveApp,
    AxiDrawController,
)


class AlignmentDisplay(BasePositionDisplay):
    """Widget to display current alignment calibration state."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "initial"  # "initial", "continue", "complete"
        self.starting_pos = Vec2(0, 0)
        self.circle_mode = False

    def update_state(
        self,
        position: Vec2,
        delta: float,
        is_connected: bool = False,
        mode: str = "initial",
        starting_pos: Optional[Vec2] = None,
        circle_mode: bool = False,
    ):
        """Update the alignment state."""
        self.mode = mode
        if starting_pos is not None:
            self.starting_pos = starting_pos
        self.circle_mode = circle_mode
        self.update_position(position, delta, is_connected)

    def _add_custom_rows(self, table: Table):
        """Add alignment-specific rows to the display."""
        table.add_row(
            "Starting Pos", f"({self.starting_pos.x:.3f}, {self.starting_pos.y:.3f})"
        )
        table.add_row("Draw Mode", "Circle (1mm)" if self.circle_mode else "Dot")

        if self.mode == "initial":
            table.add_row("Phase", "[yellow]Initial Pen Setup[/yellow]")
        elif self.mode == "continue":
            table.add_row("Phase", "[orange]Second Pen Alignment[/orange]")
        else:
            table.add_row("Phase", "[green]Calibration Complete[/green]")

    def _get_mode_text(self) -> str:
        return "Alignment Wizard"


class AlignmentInstructions(Static):
    """Widget to display alignment instructions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "initial"
        self.circle_mode = False

    def update_mode(self, mode: str, circle_mode: bool = False):
        self.mode = mode
        self.circle_mode = circle_mode
        self.refresh()

    def render(self) -> Panel:
        instructions = Text()

        if self.mode == "initial":
            instructions.append("INITIAL PEN SETUP:\n", style="bold yellow")
            instructions.append(
                "1. Load your first pen into the plotter\n", style="white"
            )
            instructions.append(
                "2. Use arrow keys to position the pen\n", style="white"
            )
            instructions.append("3. Use +/- to adjust step size\n", style="white")
            instructions.append("4. Press Enter to draw a reference ")
            instructions.append(
                "circle\n" if self.circle_mode else "dot\n", style="white"
            )
            instructions.append(
                "5. Press 'q' to quit and make your art\n", style="white"
            )
        elif self.mode == "continue":
            instructions.append("SECOND PEN ALIGNMENT:\n", style="bold orange")
            instructions.append(
                "1. Load your second pen into the plotter\n", style="white"
            )
            instructions.append("2. Use arrow keys to align with the reference ")
            instructions.append(
                "circle\n" if self.circle_mode else "dot\n", style="white"
            )
            instructions.append("3. Use +/- to adjust step size\n", style="white")
            if self.circle_mode:
                instructions.append(
                    "4. Press 'c' to draw test circles\n", style="white"
                )
            instructions.append(
                "5. Press Enter when aligned to save offset\n", style="white"
            )
        else:
            instructions.append("CALIBRATION COMPLETE!\n", style="bold green")
            instructions.append(
                "Alignment offset has been calculated.\n", style="white"
            )
            instructions.append("Press 'q' to exit.\n", style="white")

        instructions.append("\nControls:\n", style="bold cyan")
        instructions.append("  ↑/↓/←/→   Move plotter head\n", style="white")
        instructions.append("  +/-       Adjust step size\n", style="white")
        instructions.append("  PgUp/PgDn Pen up/down\n", style="white")
        instructions.append("  P   Toggle servo power\n", style="white")
        if self.circle_mode and self.mode == "continue":
            instructions.append("  c         Draw test circle\n", style="white")
        instructions.append(
            "  Enter     Draw reference/complete alignment\n", style="white"
        )
        instructions.append("  q/Esc     Exit\n", style="white")

        return Panel(
            instructions,
            title="[bold magenta]Instructions[/bold magenta]",
            border_style="magenta",
        )


class AlignmentStatusLog(BaseStatusLog):
    """Status log for alignment operations."""

    def __init__(self, **kwargs):
        super().__init__(max_messages=100, **kwargs)

    def log_success(self, message: str):
        self.messages.append(f"SUCCESS: {message}")
        self._trim_messages()
        self.refresh()

    def render(self) -> Panel:
        if not self.messages:
            content = Text("Ready to begin alignment calibration...", style="dim")
        else:
            content = Text()
            recent_messages = self.messages[-6:]  # Show last 6 messages
            for msg in recent_messages:
                if msg.startswith("ERROR"):
                    content.append(f"{msg}\n", style="red")
                elif msg.startswith("WARNING"):
                    content.append(f"{msg}\n", style="yellow")
                elif msg.startswith("SUCCESS"):
                    content.append(f"{msg}\n", style="green")
                else:
                    content.append(f"{msg}\n", style="white")

        return Panel(
            content,
            title="[bold red]Status[/bold red]",
            border_style="red",
        )
        self.refresh()


class AlignmentWizardApp(App):
    """Interactive alignment calibration wizard."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-gutter: 1;
    }

    #display {
        column-span: 1;
        row-span: 1;
    }

    #instructions {
        column-span: 1;
        row-span: 2;
    }

    #status {
        column-span: 2;
        row-span: 1;
        max-height: 8;
    }
    """

    BINDINGS = [
        Binding("up", "move_up", "Move Up", priority=True),
        Binding("down", "move_down", "Move Down", priority=True),
        Binding("left", "move_left", "Move Left", priority=True),
        Binding("right", "move_right", "Move Right", priority=True),
        Binding("enter", "draw_reference", "Draw Reference/Complete", priority=True),
        Binding("pageup", "pen_up", "Pen Up", priority=True),
        Binding("pagedown", "pen_down", "Pen Down", priority=True),
        Binding("plus", "increase_delta", "Increase Step", priority=True),
        Binding("equal", "increase_delta", "Increase Step", priority=True),
        Binding("minus", "decrease_delta", "Decrease Step", priority=True),
        Binding("c", "draw_circle", "Draw Circle", priority=True),
        Binding("p", "toggle_servo_power", "Toggle Servo Power", priority=True),
        Binding("escape", "exit_app", "Exit", priority=True),
        Binding("q", "exit_app", "Exit", priority=True),
    ]

    def __init__(
        self,
        continue_alignment: bool = False,
        starting_pos: Optional[Vec2] = None,
        circle_mode: bool = False,
        output_file: Optional[str] = None,
        opts: Optional[dict] = None,
    ):
        super().__init__()
        self.continue_alignment = continue_alignment
        self.starting_pos = starting_pos if starting_pos is not None else Vec2(0, 0)
        self.circle_mode = circle_mode
        self.output_file = output_file
        self.opts = opts or {}
        self.ax = None
        self.delta = 1.0
        self.reference_pos = None  # Position where first pen drew reference
        self.alignment_offset = Vec2(0, 0)
        self.servo_power_enabled = True  # Track servo power state

    def compose(self) -> ComposeResult:
        """Create the TUI layout."""
        yield Header(show_clock=True)

        self.alignment_display = AlignmentDisplay(id="display")
        self.instructions = AlignmentInstructions(id="instructions")
        self.status_log = AlignmentStatusLog(id="status")

        yield self.alignment_display
        yield self.instructions
        yield self.status_log
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the alignment wizard."""
        try:
            self.status_log.log_info("Initializing AxiDraw connection...")

            if axidraw is None:
                raise RuntimeError("pyaxidraw not available")

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

            # Move to starting position and set pen up
            self.ax.moveto(self.starting_pos.x, self.starting_pos.y)
            self.ax.penup()

            mode = "continue" if self.continue_alignment else "initial"
            self.status_log.log_info(f"Started alignment wizard in {mode} mode")

            if self.continue_alignment:
                self.status_log.log_info(
                    "Load your second pen and position it to align with the reference mark"
                )
                # Load reference position if continuing
                self.reference_pos = self.starting_pos
            else:
                self.status_log.log_info(
                    "Load your first pen and position it where you want to draw the reference mark"
                )

            self.update_display()

        except Exception as e:
            self.status_log.log_warning(f"AxiDraw not connected: {e}")
            self.status_log.log_info(
                "Running in demo mode - controls will be simulated"
            )
            self.ax = None
            self.call_after_refresh(self._init_demo_mode)

    def _init_demo_mode(self):
        """Initialize demo mode safely after mount."""
        mode = "continue" if self.continue_alignment else "initial"
        self.alignment_display.update_state(
            self.starting_pos,
            self.delta,
            False,
            mode,
            self.starting_pos,
            self.circle_mode,
        )
        self.instructions.update_mode(mode, self.circle_mode)

    def update_display(self):
        """Update the display with current state."""
        if self.ax:
            current_pos = self.ax.current_pos()
            if hasattr(current_pos, "__len__") and len(current_pos) >= 2:
                position = Vec2(float(current_pos[0]), float(current_pos[1]))
            else:
                position = self.starting_pos
        else:
            position = self.alignment_display.position

        mode = "continue" if self.continue_alignment else "initial"
        self.alignment_display.update_state(
            position,
            self.delta,
            self.ax is not None,
            mode,
            self.starting_pos,
            self.circle_mode,
        )
        self.instructions.update_mode(mode, self.circle_mode)

    def action_move_up(self) -> None:
        """Move the plotter head up."""
        if self.ax:
            self.ax.go(0, self.delta)
            self.update_display()
            self.status_log.log_info(f"Moved up by {self.delta}")
        else:
            current = self.alignment_display.position
            new_pos = Vec2(current.x, current.y + self.delta)
            mode = "continue" if self.continue_alignment else "initial"
            self.alignment_display.update_state(
                new_pos, self.delta, False, mode, self.starting_pos, self.circle_mode
            )
            self.status_log.log_info(f"[Demo] Moved up by {self.delta}")

    def action_move_down(self) -> None:
        """Move the plotter head down."""
        if self.ax:
            self.ax.go(0, -self.delta)
            self.update_display()
            self.status_log.log_info(f"Moved down by {self.delta}")
        else:
            current = self.alignment_display.position
            new_pos = Vec2(current.x, current.y - self.delta)
            mode = "continue" if self.continue_alignment else "initial"
            self.alignment_display.update_state(
                new_pos, self.delta, False, mode, self.starting_pos, self.circle_mode
            )
            self.status_log.log_info(f"[Demo] Moved down by {self.delta}")

    def action_move_left(self) -> None:
        """Move the plotter head left."""
        if self.ax:
            self.ax.go(-self.delta, 0)
            self.update_display()
            self.status_log.log_info(f"Moved left by {self.delta}")
        else:
            current = self.alignment_display.position
            new_pos = Vec2(current.x - self.delta, current.y)
            mode = "continue" if self.continue_alignment else "initial"
            self.alignment_display.update_state(
                new_pos, self.delta, False, mode, self.starting_pos, self.circle_mode
            )
            self.status_log.log_info(f"[Demo] Moved left by {self.delta}")

    def action_move_right(self) -> None:
        """Move the plotter head right."""
        if self.ax:
            self.ax.go(self.delta, 0)
            self.update_display()
            self.status_log.log_info(f"Moved right by {self.delta}")
        else:
            current = self.alignment_display.position
            new_pos = Vec2(current.x + self.delta, current.y)
            mode = "continue" if self.continue_alignment else "initial"
            self.alignment_display.update_state(
                new_pos, self.delta, False, mode, self.starting_pos, self.circle_mode
            )
            self.status_log.log_info(f"[Demo] Moved right by {self.delta}")

    def action_draw_reference(self) -> None:
        """Draw reference mark or complete alignment."""
        if not self.continue_alignment:
            # Initial mode - draw reference mark
            self._draw_reference_mark()
        else:
            # Continue mode - complete alignment
            self._complete_alignment()

    def _draw_reference_mark(self):
        """Draw the reference mark with the first pen."""
        if self.ax:
            current_pos = self.ax.current_pos()
            if hasattr(current_pos, "__len__") and len(current_pos) >= 2:
                pos = Vec2(float(current_pos[0]), float(current_pos[1]))
            else:
                pos = self.starting_pos
        else:
            pos = self.alignment_display.position

        self.reference_pos = pos

        if self.circle_mode:
            self._draw_circle(pos)
            self.status_log.log_success(
                f"Drew reference circle at ({pos.x:.3f}, {pos.y:.3f})"
            )
        else:
            self._draw_dot(pos)
            self.status_log.log_success(
                f"Drew reference dot at ({pos.x:.3f}, {pos.y:.3f})"
            )

        self.status_log.log_info(
            "Reference mark complete. Press 'q' to exit and make your art."
        )
        self.status_log.log_info(
            "When ready for second pen, run: uv run pti --alignment --continue"
        )

    def _complete_alignment(self):
        """Complete the alignment and calculate offset."""
        if self.ax:
            current_pos = self.ax.current_pos()
            if hasattr(current_pos, "__len__") and len(current_pos) >= 2:
                pos = Vec2(float(current_pos[0]), float(current_pos[1]))
            else:
                pos = self.starting_pos
        else:
            pos = self.alignment_display.position

        # Calculate offset (difference between current position and reference)
        if self.reference_pos:
            self.alignment_offset = Vec2(
                pos.x - self.reference_pos.x, pos.y - self.reference_pos.y
            )
        else:
            # If no reference, assume offset from starting position
            self.alignment_offset = Vec2(
                pos.x - self.starting_pos.x, pos.y - self.starting_pos.y
            )

        self.status_log.log_success(
            f"Alignment complete! Offset: ({self.alignment_offset.x:.3f}, {self.alignment_offset.y:.3f})"
        )

        # Save to file if specified
        if self.output_file:
            try:
                with open(self.output_file, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([self.alignment_offset.x, self.alignment_offset.y])
                self.status_log.log_info(f"Offset saved to {self.output_file}")
            except Exception as e:
                self.status_log.log_error(f"Failed to save offset: {e}")

        # Print to console for copying
        print(
            f"\nAlignment offset: {self.alignment_offset.x:.6f},{self.alignment_offset.y:.6f}"
        )
        print("Use this in your code:")
        print(
            f"plotter.set_alignment_offsets(Vec2({self.alignment_offset.x:.6f}, {self.alignment_offset.y:.6f}))"
        )

        # Update mode to complete
        self.continue_alignment = False
        self.alignment_display.update_state(
            pos,
            self.delta,
            self.ax is not None,
            "complete",
            self.starting_pos,
            self.circle_mode,
        )
        self.instructions.update_mode("complete", self.circle_mode)

    def _draw_dot(self, pos: Vec2):
        """Draw a dot at the specified position."""
        if self.ax:
            self.ax.pendown()
            self.ax.penup()
        else:
            self.status_log.log_info("[Demo] Drew dot")

    def _draw_circle(self, pos: Vec2, radius: float = 0.05):
        """Draw a small circle at the specified position."""
        if self.ax:
            # Draw a small circle (1mm radius)
            import math

            self.ax.penup()
            self.ax.goto(pos.x + radius, pos.y)
            self.ax.pendown()

            # Draw circle with small segments
            for i in range(12):  # 10-degree segments
                angle = i * 10 * math.pi / 180
                x = pos.x + radius * math.cos(angle)
                y = pos.y + radius * math.sin(angle)
                self.ax.goto(x, y)

            self.ax.penup()
        else:
            self.status_log.log_info(
                f"[Demo] Drew circle at ({pos.x:.3f}, {pos.y:.3f})"
            )

    def action_draw_circle(self) -> None:
        """Draw a test circle (only in continue mode with circle option)."""
        if self.continue_alignment and self.circle_mode:
            if self.ax:
                current_pos = self.ax.current_pos()
                if hasattr(current_pos, "__len__") and len(current_pos) >= 2:
                    pos = Vec2(float(current_pos[0]), float(current_pos[1]))
                else:
                    pos = self.starting_pos
            else:
                pos = self.alignment_display.position

            self._draw_circle(pos)
            self.status_log.log_info("Drew test circle for alignment")

    def action_pen_up(self) -> None:
        """Raise the pen."""
        if self.ax:
            self.ax.penup()
            self.status_log.log_info("Pen up")
        else:
            self.status_log.log_info("[Demo] Pen up")

    def action_pen_down(self) -> None:
        """Lower the pen."""
        if self.ax:
            self.ax.pendown()
            self.status_log.log_info("Pen down")
        else:
            self.status_log.log_info("[Demo] Pen down")

    def action_increase_delta(self) -> None:
        """Increase movement step size."""
        self.delta *= 2
        self.update_display()
        self.status_log.log_info(f"Increased step size to {self.delta:.3f}")

    def action_decrease_delta(self) -> None:
        """Decrease movement step size."""
        self.delta /= 2
        self.update_display()
        self.status_log.log_info(f"Decreased step size to {self.delta:.3f}")

    def action_exit_app(self) -> None:
        """Exit the alignment wizard."""
        self.exit()

    def action_toggle_servo_power(self) -> None:
        """Toggle servo motor power on/off."""
        try:
            if axidraw is None:
                self.status_log.log_error("pyaxidraw not available for servo control")
                return

            ad = axidraw.AxiDraw()
            ad.plot_setup()
            ad.options.mode = "manual"

            if self.servo_power_enabled:
                # Disable servos
                ad.options.manual_cmd = "disable_xy"
                ad.plot_run()
                self.servo_power_enabled = False
                self.status_log.log_info(
                    "Servo power DISABLED - you can move the head manually"
                )
            else:
                # Enable servos
                ad.options.manual_cmd = "enable_xy"
                ad.plot_run()
                self.servo_power_enabled = True
                self.status_log.log_info("Servo power ENABLED - motors are locked")
        except Exception as e:
            self.status_log.log_error(f"Failed to toggle servo power: {e}")

    async def on_unmount(self) -> None:
        """Clean up when exiting."""
        if self.ax:
            try:
                self.ax.penup()
                self.ax.disconnect()
                self.status_log.log_info("Disconnected from AxiDraw")
            except Exception as e:
                self.status_log.log_error(f"Error disconnecting: {e}")


def main():
    """Main entry point for alignment wizard."""
    import argparse

    parser = argparse.ArgumentParser(description="Alignment Calibration Wizard")
    parser.add_argument(
        "--alignment", action="store_true", help="Start alignment calibration wizard"
    )
    parser.add_argument(
        "--continue",
        action="store_true",
        dest="continue_alignment",
        help="Continue alignment with second pen",
    )
    parser.add_argument(
        "--starting-pos",
        type=str,
        help="Starting position as 'x,y' (e.g., '12.34,56.78')",
    )
    parser.add_argument(
        "--circle", action="store_true", help="Draw circles instead of dots"
    )
    parser.add_argument(
        "--output", type=str, help="Output file to save alignment offset"
    )

    args = parser.parse_args()

    if not args.alignment:
        print("Use --alignment to start the alignment wizard")
        return

    if not TEXTUAL_AVAILABLE:
        print("Alignment wizard requires textual package.")
        print("Install it with: pip install textual")
        return

    starting_pos = Vec2(0, 0)
    if args.starting_pos:
        try:
            x, y = map(float, args.starting_pos.split(","))
            starting_pos = Vec2(x, y)
        except (ValueError, TypeError):
            print("Invalid starting position format. Use 'x,y' format.")
            return

    app = AlignmentWizardApp(
        continue_alignment=args.continue_alignment,
        starting_pos=starting_pos,
        circle_mode=args.circle,
        output_file=args.output,
    )
    app.run()


if __name__ == "__main__":
    main()
