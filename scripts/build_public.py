"""Refresh the static visualization files served from public/."""

from pathlib import Path
from shutil import copyfile


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
FILES = {
    "appalti_it_network.html": "index.html",
    "heatmaps.json": "heatmaps.json",
    "splits.json": "splits.json",
}


def main() -> None:
    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing visualization source files: {missing}")

    PUBLIC.mkdir(exist_ok=True)
    for source_name, public_name in FILES.items():
        copyfile(ROOT / source_name, PUBLIC / public_name)
        print(f"{source_name} -> public/{public_name}")


if __name__ == "__main__":
    main()
