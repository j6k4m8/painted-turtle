# Alignment Calibration

One of the annoying things about pen plotters is that once you take a pen off and put a new one on, the precise alignment between their tips is often off (generally because the pen radii are different or the tip is not perfectly aligned with the pen's center of rotation). This can cause misalignment in the drawings, especially when switching between pens. It's sad!! Unless you're trying to do a cool broken-registration effect, in which case it's cool. But usually sad.

To fix this, you can use the `alignment` script to calibrate the alignment of your pens. This script will help you find the offsets between the pens and adjust the drawing accordingly.

```bash
uv run pti --alignment
```

This will walk you through a wizard. Here are the steps you should follow:

FIRST: Before you continue, you should make sure that the plotter has a little bit of "wiggle room" around it; in other words, don't start the alignment process at exactly the physical corner of the plotter's range of motion. This is because the alignment process will move the pen around a bit, and if you start at the edge, you might run into the edge of the plotter's range of motion.

1. **Load a pen.** Put the first pen into the plotter.
2. **Start the calibration by running `uv run pti --alignment`.** This will move the pen to a starting position, in the UP position. You can adjust this position with the arrow keys, and with +/- to change the pen's delta size. If you have a position in mind before starting, you can pass `--starting-pos 12.34,56.78` to start at that position instead of the default (0, 0). (This is useful when you have 3D features on the canvas that you don't want to bump. Note that when you pass `--starting-pos`, the wizard will move to the starting position when you start the `pti` alignment script, so make sure there is a clear path to that position.)
3. When you're ready (i.e., no art underneath the pen), **press Enter to draw a dot.** (If you pass `--circle`, the wizard will draw a tiny (1mm) circle instead of a dot. This is useful for media that don't leave a dot, like pencils.)
4. `q` to quit, and then **make your art as usual.** You don't even have to use `pt` for it.
5. **Load a new pen.** Put the second pen into the plotter.
6. **Run `uv run pti --alignment --continue` again.** This will move the pen to the same starting position as before.
7. **Use the arrow keys to adjust the position of the pen.** The goal is to align the tip of the new pen with the dot you drew with the first pen. You can use `+` and `-` to adjust the delta of the movement, and page up and page down to raise and lower the pen. In `--circle` mode, you can also use `c` to draw a circle instead of a dot, which can help you see the alignment better.
8. When you're satisfied with the alignment, **press Enter.** This will print the offset to the console, or save it to a file as a headerless csv (`x,y` format) if you pass `--output <file>`. You can use this offset in your code to adjust the drawing position of the new pen:

```python
from pt import Studio, MPLMockPlotter, Vec2

plotter = MPLMockPlotter()
studio = Studio(plotter)

# Replace with the offsets you got from the alignment script
alignment_offsets = Vec2(0.05, 0.02)

# Use the offsets to adjust the drawing position
studio.plotter.set_alignment_offsets(alignment_offsets)
# Now you can draw with the new pen, and it will be aligned with the previous pen.

# Example of using the alignment offsets
studio.canvas_draw_line(Vec2(1, 1), Vec2(2, 1))

# Resetting Alignment Offsets
# If you want to reset the alignment offsets to zero, you can do so with:
studio.plotter.reset_alignment_offsets()
# Same as:
studio.plotter.set_alignment_offsets(Vec2(0, 0))
```
