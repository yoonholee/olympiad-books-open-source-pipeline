# olympiad-books-open-source

Pipeline for building a chunked math textbook dataset from 12 open-source books.

The published dataset is at [huggingface.co/datasets/yoonholee/olympiad-books-open-source](https://huggingface.co/datasets/yoonholee/olympiad-books-open-source).

## Quick start

```bash
./clone_sources.sh          # clone all 12 source repos
python extract.py           # extract chapters to markdown
python chunk.py             # content-aware chunking -> JSONL
python push_to_hf.py        # push to HuggingFace
```

Requires: Python 3.10+, `pandoc`, `datasets` (pip).

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
