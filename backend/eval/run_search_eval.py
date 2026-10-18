"""Runs your ground-truth list through the running backend and writes a hit-rate report.

Usage (backend must be running; set EVAL_EMAIL and EVAL_PASSWORD to an existing account):
    python eval/run_search_eval.py eval/ground_truth.csv

CSV columns: name, name_type, expected_url_contains
  name_type  = common / rare / initials / south_asian / arabic / non_latin (your own labels)
  expected_url_contains = a piece of the correct profile URL, e.g. linkedin.com/in/handle
Only use people who agreed to be tested and well-known public figures.
"""
import csv
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

API = "http://localhost:8000"


def main(path: str, engine: str = "auto") -> None:
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)
    results, by_type = [], defaultdict(lambda: [0, 0])
    with httpx.Client(timeout=60) as c:
        login = c.post(f"{API}/api/auth/login", json={"email": os.environ.get("EVAL_EMAIL", ""), "password": os.environ.get("EVAL_PASSWORD", "")})
        if login.status_code != 200:
            sys.exit("Sign-in failed. Set EVAL_EMAIL and EVAL_PASSWORD for an existing account.")
        c.headers["Authorization"] = "Bearer " + login.json()["access_token"]
        for i, row in enumerate(rows, 1):
            name, expect = row["name"].strip(), row["expected_url_contains"].strip().lower()
            if name.startswith("REPLACE"):
                continue
            r = c.post(f"{API}/api/search", json={"name": name, "consent": True})
            if r.status_code != 200:
                print(f"[{i}] {name}: ERROR {r.json().get('detail')}")
                continue
            d = r.json()
            rank = next((k + 1 for k, x in enumerate(d["results"]) if expect in x["profile_url"].lower()), 0)
            hit = rank > 0
            by_type[row["name_type"]][0] += int(hit)
            by_type[row["name_type"]][1] += 1
            results.append({"name": name, "type": row["name_type"], "hit": int(hit), "rank": rank,
                            "n_results": len(d["results"]), "seconds": round(d["took_ms"] / 1000, 2)})
            print(f"[{i}/{len(rows)}] {name}: {'HIT rank ' + str(rank) if hit else 'miss'} ({d['took_ms']} ms)")
            time.sleep(1.2)  # stay under the search API rate limit

    stamp = time.strftime("%Y%m%d-%H%M%S")
    csv_path = out_dir / f"search_eval_{stamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else ["name"])
        w.writeheader(); w.writerows(results)
    total_hits = sum(v[0] for v in by_type.values()); total = sum(v[1] for v in by_type.values())
    print("\n=== Hit rate in top 5 ===")
    for t, (h, n) in sorted(by_type.items()):
        print(f"{t:14s} {h}/{n}  {100 * h / n:.0f}%")
    if total:
        print(f"{'ALL':14s} {total_hits}/{total}  {100 * total_hits / total:.0f}%")
        print(f"avg seconds {sum(r['seconds'] for r in results) / len(results):.2f}")
    print(f"Saved {csv_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "auto")
