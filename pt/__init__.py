from typing import Callable
from matplotlib import pyplot as plt

from .plotter import Plotter, EPenState
from .ptobjects.PTObject import PTObject
from .vectors import Vec2


class Studio:
    pt_objects: dict[str, PTObject]

    def __init__(self, plotter: Plotter, bbox: tuple[Vec2, Vec2] | None = None):
        self.pt_objects = {}
        self.bbox = bbox or (Vec2(0, 0), Vec2(6, 4))
        self.plotter = plotter

    def add_object(self, obj: PTObject, name: str | None = None):
        self.pt_objects[name or f"ptobj{len(self.pt_objects)}"] = obj

    def get_objects(self) -> dict[str, PTObject]:
        return self.pt_objects

    def get_object(self, name: str) -> PTObject:
        return self.pt_objects[name]

    # Dot-notation access to objects
    def __getattr__(self, name: str) -> Callable:
        if name in self.pt_objects:
            return self.pt_objects[name]
        elif (obj_name := name.split("_")[0]) in self.pt_objects:
            return self.pt_objects[obj_name].get_verbs()[name[len(obj_name) + 1 :]](
                self.plotter
            )
        else:
            return super().__getattr__(name)

    def debug_draw(self):
        plt.figure(
            figsize=(self.bbox[1].x - self.bbox[0].x, self.bbox[1].y - self.bbox[0].y)
        )
        for _, obj in self.pt_objects.items():
            obj.debug_draw(plt.gca())

        for line in self.plotter.get_path():
            if line[2] == EPenState.DOWN:
                plt.gca().plot([line[0].x, line[1].x], [line[0].y, line[1].y], "k-")
            else:
                plt.gca().plot(
                    [line[0].x, line[1].x], [line[0].y, line[1].y], "r--", alpha=0.5
                )

        plt.gca().set_xlim(self.bbox[0].x, self.bbox[1].x)
        plt.gca().set_ylim(self.bbox[0].y, self.bbox[1].y)
        plt.gca().invert_yaxis()
        plt.show()
