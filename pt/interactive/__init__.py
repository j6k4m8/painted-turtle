from pyaxidraw import axidraw
from pt import Vec2
from pynput import keyboard


class AxiDrawFiducial:
    """
    This interactive class is used to find a fiducial marker on the canvas.

    Using the L/R and U/D keys, the user can move the AxiDraw head manually,
    and then hit the space bar to capture the current pen position.

    AxiDraw is handled by the pyaxidraw library, which is a wrapper around the
    AxiDraw API. Keyboard input is handled by the keyboard library.

    """

    def __init__(self, outfile: str | None = None, opts: dict | None = None):
        self.outfile = outfile
        self.ax = axidraw.AxiDraw()
        self.ax.interactive()
        self.delta = 1
        if opts:
            for k, v in opts.items():
                setattr(self.ax, k, v)
        if not self.ax.connect():
            raise RuntimeError("Could not connect to AxiDraw")

        self.ax.moveto(0, 0)  # ← set origin safely
        self.ax.penup()

        # Set up keyboard listener
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

        print("Press arrow keys to move the AxiDraw head.")
        print("Press space to capture the current position.")
        print("Press ESC to exit.")

        # Keep the program running
        try:
            self.listener.join()
        except KeyboardInterrupt:
            self.exit()

    def on_key_press(self, key):
        """
        Handle key press events.
        """
        try:
            if key == keyboard.Key.space:
                self.capture_position()
            elif key == keyboard.Key.home:
                self.ax.goto(0, 0)
                print("Homed AxiDraw", end="\r")
            elif key == keyboard.Key.page_up:
                ad = axidraw.AxiDraw()
                ad.plot_setup()
                ad.options.mode = "manual"
                ad.options.manual_cmd = "disable_xy"
                ad.plot_run()
                print("Page up pressed", end="\r")
            elif key == keyboard.Key.page_down:
                self.ax.penup()
                self.ax.pendown()
                self.ax.penup()
                print("Page down pressed", end="\r")
            elif key == keyboard.Key.up:
                self.move_down()
            elif key == keyboard.Key.down:
                self.move_up()
            elif key == keyboard.Key.left:
                self.move_left()
            elif key == keyboard.Key.right:
                self.move_right()
            elif key == keyboard.Key.shift:
                self.delta /= 2
                print(f"Delta: {self.delta}")
            elif key == keyboard.Key.ctrl:
                self.delta *= 2
                print(f"Delta: {self.delta}")
            elif key == keyboard.Key.esc:
                self.exit()
                return False  # Stop listener
        except AttributeError:
            # Handle special keys that don't have a char attribute
            pass

    def capture_position(self):
        """
        Capture the current position of the AxiDraw head and print it.
        """
        self.pos = Vec2(*self.ax.current_pos())
        print(f"\nCaptured position: {self.pos}")
        if self.outfile:
            with open(self.outfile, "a") as f:
                f.write(f"{self.pos.x} {self.pos.y}\n")

    def move_up(self):
        """
        Move the AxiDraw head up by 1 unit.
        """
        self.ax.go(0, 1 * self.delta)
        print(f"Current position: {self.ax.current_pos()}", end="\r")

    def move_down(self):
        """
        Move the AxiDraw head down by 1 unit.
        """
        self.ax.go(0, -1 * self.delta)
        print(f"Current position: {self.ax.current_pos()}", end="\r")

    def move_left(self):
        """
        Move the AxiDraw head left by 1 unit.
        """
        self.ax.go(-1 * self.delta, 0)
        print(f"Current position: {self.ax.current_pos()}", end="\r")

    def move_right(self):
        """
        Move the AxiDraw head right by 1 unit.
        """
        self.ax.go(1 * self.delta, 0)
        print(f"Current position: {self.ax.current_pos()}", end="\r")

    def exit(self):
        """
        Exit the program.
        """
        print("Exiting...")
        if hasattr(self, "listener"):
            self.listener.stop()
        # self.ax.penup()
        # self.ax.pendown()
        # self.ax.penup()
        self.ax.disconnect()
        print("Disconnected from AxiDraw.")
        exit(0)
        # Disconnect from AxiDraw


def main():
    """
    Main entry point for the fiducial finder script.
    """
    import argparse

    parser = argparse.ArgumentParser(description="AxiDraw Fiducial Finder")
    parser.add_argument(
        "-o", "--outfile", type=str, help="Output file to save the fiducial positions"
    )
    args = parser.parse_args()
    AxiDrawFiducial(outfile=args.outfile)


if __name__ == "__main__":
    main()
