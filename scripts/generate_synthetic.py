"""Generate a synthetic 20,000-row spreadsheet: python scripts/generate_synthetic.py"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rfidlib.synthetic import generate, write_csv, write_xlsx

ap = argparse.ArgumentParser()
ap.add_argument("--rows", type=int, default=20000)
ap.add_argument("--invalid", type=int, default=150)
ap.add_argument("--duplicates", type=int, default=100)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--out", default="data/synthetic")
a = ap.parse_args()

out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
rows, expected = generate(a.rows, a.invalid, a.duplicates, a.seed)
write_xlsx(out / "catalogue_20k.xlsx", rows)
write_csv(out / "catalogue_20k.csv", rows)
(out / "expected.json").write_text(json.dumps(expected, indent=2))
print(f"Wrote {out}/catalogue_20k.xlsx and .csv; expected outcome: {expected}")
