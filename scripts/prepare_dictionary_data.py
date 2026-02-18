from __future__ import annotations

import argparse
import sys
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.dictionary_loader import DictionaryLoader


DEFAULT_OUT_DIR = Path("data/dictionaries")
DEFAULT_CEDICT_NAME = "cc-cedict.u8"
DEFAULT_CANTO_NAME = "cc-canto.u8"


def _copy(src: Path, dst: Path) -> None:
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"Missing source file: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _validate(path: Path, source: str, min_terms: int) -> int:
    loader = DictionaryLoader()
    parsed = loader.load_file(path, source=source)
    term_count = len(parsed)
    if term_count < min_terms:
        raise ValueError(
            f"Parsed too few terms from {path} ({term_count}). Expected >= {min_terms}."
        )
    return term_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy and validate dictionary source files for local dictionary mode."
    )
    parser.add_argument("--cedict", required=True, help="Path to CC-CEDICT source file")
    parser.add_argument("--cccanto", required=True, help="Path to CC-Canto source file")
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="Output directory for normalized dictionary files",
    )
    parser.add_argument(
        "--min-terms",
        type=int,
        default=1000,
        help="Minimum parsed term count required per file",
    )

    args = parser.parse_args()

    cedict_src = Path(args.cedict)
    canto_src = Path(args.cccanto)
    out_dir = Path(args.out_dir)

    cedict_dst = out_dir / DEFAULT_CEDICT_NAME
    canto_dst = out_dir / DEFAULT_CANTO_NAME

    _copy(cedict_src, cedict_dst)
    _copy(canto_src, canto_dst)

    cedict_terms = _validate(cedict_dst, source="cc-cedict", min_terms=args.min_terms)
    canto_terms = _validate(canto_dst, source="cc-canto", min_terms=args.min_terms)

    print(f"ok: {cedict_dst} terms={cedict_terms}")
    print(f"ok: {canto_dst} terms={canto_terms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
