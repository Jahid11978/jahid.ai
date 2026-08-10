from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "AGENTS.md",
    "AGENT_GOVERNANCE.md",
    "GOVERNANCE.md",
    "README.md",
    "VERSION",
    "backend/reliability/engine.py",
    "backend/tests/test_reliability.py",
    ".github/workflows/codeql.yml",
    ".github/workflows/memory.yml",
    ".github/workflows/reliability.yml",
    ".github/workflows/ci.yml",
)

FORBIDDEN_PLACEHOLDERS = (
    "api.jarvis-system.dev",
    "example.com",
    "your-token-here",
)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.exists():
            errors.append(f"missing required file: {relative}")
        elif path.is_file() and path.stat().st_size == 0:
            errors.append(f"required file is empty: {relative}")

    version_path = ROOT / "VERSION"
    if version_path.exists():
        version = version_path.read_text(encoding="utf-8").strip()
        parts = version.split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            errors.append(f"invalid VERSION value: {version!r}")

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for placeholder in FORBIDDEN_PLACEHOLDERS:
            if placeholder in text:
                warnings.append(f"placeholder reference {placeholder!r}: {path.relative_to(ROOT)}")

    if (ROOT / "src").exists():
        warnings.append("unexpected root src/ directory: confirm frontend ownership")

    print("JAHID.AI repository doctor")
    print(f"root: {ROOT}")
    print(f"errors: {len(errors)}")
    print(f"warnings: {len(warnings)}")
    for message in errors:
        print(f"ERROR: {message}")
    for message in warnings:
        print(f"WARNING: {message}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
