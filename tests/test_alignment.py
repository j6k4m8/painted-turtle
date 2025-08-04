#!/usr/bin/env python3

"""Test script to verify alignment offset functionality."""

from pt import MPLMockPlotter, Vec2


def test_alignment_offsets():
    """Test that alignment offsets work correctly."""
    plotter = MPLMockPlotter()

    # Test initial state
    assert plotter.alignment_offset == Vec2(0, 0)

    # Test setting alignment offsets
    offset = Vec2(0.05, 0.02)
    plotter.set_alignment_offsets(offset)
    assert plotter.alignment_offset == offset

    # Test that movement applies offset
    original_pos = Vec2(1, 1)
    plotter.move_to(original_pos)

    # The actual position should be offset
    expected_pos = Vec2(1.05, 1.02)
    assert plotter.pos == expected_pos

    # Test reset
    plotter.reset_alignment_offsets()
    assert plotter.alignment_offset == Vec2(0, 0)

    # Test movement after reset
    plotter.move_to(Vec2(2, 2))
    assert plotter.pos == Vec2(2, 2)

    print("All alignment offset tests passed!")


if __name__ == "__main__":
    test_alignment_offsets()
