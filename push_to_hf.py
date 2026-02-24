#!/usr/bin/env python3
"""Package chunks into a HuggingFace dataset and push."""

import json
import subprocess
from collections import Counter
from pathlib import Path
from datasets import Dataset

BASE = Path(__file__).parent
CHUNKS_FILE = BASE / "chunks" / "all.jsonl"
HF_CARD = BASE / "hf_dataset_card.md"
REPO_ID = "yoonholee/olympiad-books-open-source"

records = []
with open(CHUNKS_FILE) as f:
    for line in f:
        r = json.loads(line)
        records.append({
            "text": r["text"],
            "book": r["book"],
            "book_key": r["book_key"],
            "subject": r.get("subject", ""),
            "level": r.get("level", ""),
            "part": r.get("part", ""),
            "chapter": r["chapter"],
            "section": r["section"] or "",
            "source_file": r["source_file"],
            "chunk_id": r["chunk_id"],
            "tokens_est": r["tokens_est"],
        })

print(f"Loaded {len(records)} chunks")
for book, count in Counter(r["book"] for r in records).most_common():
    print(f"  {book}: {count}")

ds = Dataset.from_list(records)
print(f"\n{ds}")
ds.push_to_hub(REPO_ID, private=False)
print(f"\nPushed to https://huggingface.co/datasets/{REPO_ID}")

# Upload dataset card
if HF_CARD.exists():
    subprocess.run(
        ["hf", "upload", REPO_ID, str(HF_CARD), "README.md", "--repo-type", "dataset"],
        check=True,
    )
    print("Uploaded dataset card")
