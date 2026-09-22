"""Run the complete reproducibility path without language-model API access."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(script: str, *arguments: str) -> None:
    command = [sys.executable, str(ROOT / "scripts" / script), *arguments]
    print(f"\n==> {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    run("reaggregate_articles.py", "fdi_screening")
    run("rebuild_procurement_outputs.py")
    run("sensitivity_analysis.py")
    run("build_review_sample.py")
    run("build_provenance_manifest.py")
    print("\n==> Running verification suite", flush=True)
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()

