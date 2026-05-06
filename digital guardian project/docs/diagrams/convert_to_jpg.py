from pathlib import Path

from PIL import Image


BASE = Path(__file__).resolve().parent
FILES = [
    "database_tables_image.png",
    "dfd_image.png",
    "uml_class_diagram_image.png",
]

for name in FILES:
    source = BASE / name
    target = source.with_suffix(".jpg")
    image = Image.open(source).convert("RGB")
    image.save(target, format="JPEG", quality=95)
    print(target.name)
