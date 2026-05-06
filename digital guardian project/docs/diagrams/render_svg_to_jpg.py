from pathlib import Path

from PIL import Image
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg


BASE = Path(__file__).resolve().parent

DIAGRAMS = [
    ("database_tables.svg", "database_tables_structured.jpg"),
    ("dfd.svg", "dfd_structured.jpg"),
    ("uml_class_diagram.svg", "uml_class_diagram_structured.jpg"),
]


def main():
    for source_name, target_name in DIAGRAMS:
        source = BASE / source_name
        target = BASE / target_name

        drawing = svg2rlg(str(source))
        image = renderPM.drawToPIL(drawing, dpi=180)
        rgb = image.convert("RGB")
        rgb.save(target, format="JPEG", quality=95)
        print(target.name)


if __name__ == "__main__":
    main()
