# olympiad-books-open-source

Pipeline for building a chunked math textbook dataset from 12 open-source books.

The published dataset is at [huggingface.co/datasets/yoonholee/olympiad-books-open-source](https://huggingface.co/datasets/yoonholee/olympiad-books-open-source).

## Quick start

```bash
# 1. Clone source textbooks
./clone_sources.sh

# 2. Extract chapters to markdown
python extract_all.py          # 4 original books (Napkin + 3 PreTeXt)
python extract_new_books.py    # 8 additional books

# 3. Chunk and produce JSONL
python chunk.py

# 4. Push to HuggingFace
python push_to_hf.py
```

Requires: Python 3.10+, `pandoc`, `datasets` (pip).

## Scripts

| File | Purpose |
|------|---------|
| `clone_sources.sh` | Clone all 12 source repos into `src/` |
| `extract_all.py` | Extract Napkin (LaTeX) and 3 PreTeXt books to markdown |
| `extract_new_books.py` | Extract 8 additional books (4 PreTeXt, 4 LaTeX) to markdown |
| `chunk.py` | Content-aware chunking with metadata (subject, level, part, chapter, section) |
| `push_to_hf.py` | Package JSONL into a HuggingFace dataset and push |

## Books

| Book | Source format | Subject | Level |
|------|-------------|---------|-------|
| An Infinitely Large Napkin | LaTeX | general | advanced |
| Mathematical Reasoning | PreTeXt | proofs | intro |
| Exploring Combinatorial Mathematics | PreTeXt | combinatorics | intro |
| Discrete Mathematics | PreTeXt | discrete-math | intro |
| Abstract Algebra: Theory and Applications | PreTeXt | abstract-algebra | intro |
| Applied Combinatorics | PreTeXt | combinatorics | intro |
| Combinatorics Through Guided Discovery | PreTeXt | combinatorics | intro |
| A First Course in Linear Algebra | PreTeXt | linear-algebra | intro |
| Elementary Number Theory | LaTeX | number-theory | intro |
| Basic Analysis | LaTeX | real-analysis | advanced |
| Introduction to Proof via IBL | LaTeX | proofs | intro |
| Open Logic | LaTeX | logic | advanced |
