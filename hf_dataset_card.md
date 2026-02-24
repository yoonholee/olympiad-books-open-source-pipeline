---
license: cc-by-sa-4.0
task_categories:
  - text-retrieval
  - question-answering
language:
  - en
tags:
  - mathematics
  - textbooks
  - proofs
  - combinatorics
  - algebra
  - topology
size_categories:
  - 1K<n<10K
---

# olympiad-books-open-source

Chunked content from 12 open-source mathematics textbooks, suitable for retrieval (RAG), embedding, and math reasoning research.

## Books

| Book | Author(s) | License | Source |
|------|-----------|---------|--------|
| An Infinitely Large Napkin | Evan Chen | CC BY-SA 4.0 / GPL v3 | [GitHub](https://github.com/vEnhance/napkin) |
| Mathematical Reasoning: Writing and Proof | Ted Sundstrom | CC BY-NC-SA 3.0 | [GitHub](https://github.com/gvsuoer/sundstrom-textbook) |
| Exploring Combinatorial Mathematics | Richard Grassl, Oscar Levin | GFDL | [GitHub](https://github.com/oscarlevin/ecm) |
| Discrete Mathematics: An Open Introduction | Oscar Levin | CC BY-SA 4.0 | [GitHub](https://github.com/oscarlevin/discrete-book) |
| Abstract Algebra: Theory and Applications | Tom Judson | GFDL | [GitHub](https://github.com/twjudson/aata) |
| Applied Combinatorics | Mitchel Keller, William Trotter | CC BY-SA 4.0 | [GitHub](https://github.com/mitchkeller/applied-combinatorics) |
| Combinatorics Through Guided Discovery | Kenneth Bogart | GFDL | [GitHub](https://github.com/OpenMathBooks/bogart) |
| A First Course in Linear Algebra | Robert Beezer | GFDL | [GitHub](https://github.com/rbeezer/fcla) |
| Elementary Number Theory | William Stein | Free (Springer agreement) | [GitHub](https://github.com/williamstein/ent) |
| Basic Analysis | Jiri Lebl | CC BY-NC-SA 4.0 + CC BY-SA 4.0 | [GitHub](https://github.com/jirilebl/ra) |
| An Introduction to Proof via Inquiry-Based Learning | Dana Ernst | CC BY-SA 4.0 | [GitHub](https://github.com/dcernst/IBL-IntroToProof) |
| Open Logic | Open Logic Project | CC BY 4.0 | [GitHub](https://github.com/OpenLogicProject/OpenLogic) |

## Schema

| Field | Type | Description |
|-------|------|-------------|
| `text` | string | Chunk content (markdown with LaTeX math) |
| `book` | string | Full book title |
| `book_key` | string | Short identifier (e.g. `napkin`, `aata`, `openlogic`) |
| `subject` | string | Math subject area: `general`, `abstract-algebra`, `combinatorics`, `discrete-math`, `linear-algebra`, `logic`, `number-theory`, `proofs`, `real-analysis` |
| `level` | string | `intro` (undergrad) or `advanced` (upper-division / graduate) |
| `part` | string | Part/unit grouping within a book (e.g. "Group Theory", "Single Variable") |
| `chapter` | string | Chapter title (e.g. "Groups", "Real Numbers") |
| `section` | string | Section title (empty if chunk is in chapter intro) |
| `source_file` | string | Original markdown filename |
| `chunk_id` | int | Sequential chunk index within chapter |
| `tokens_est` | int | Estimated token count (~3.5 chars/token) |

## Stats

| Book | Chunks | Median tokens | Total tokens |
|------|--------|---------------|--------------|
| An Infinitely Large Napkin | 794 | 1446 | 945K |
| Open Logic | 480 | 1464 | 645K |
| Basic Analysis | 408 | 1056 | 418K |
| A First Course in Linear Algebra | 370 | 1184 | 389K |
| Abstract Algebra: Theory and Applications | 330 | 1080 | 335K |
| Mathematical Reasoning | 274 | 1014 | 270K |
| Applied Combinatorics | 229 | 1001 | 226K |
| Discrete Mathematics | 205 | 1087 | 214K |
| Combinatorics Through Guided Discovery | 124 | 930 | 112K |
| Elementary Number Theory | 116 | 1056 | 118K |
| Exploring Combinatorial Mathematics | 90 | 1156 | 94K |
| An Introduction to Proof via IBL | 86 | 1491 | 112K |
| **Total** | **3506** | | **3.88M** |

## Chunking method

Content-aware chunking from source files (LaTeX/PreTeXt), not PDF extraction:

1. **Section boundaries** (`##`/`###` headers) always start a new chunk
2. **Math environments** (Theorem, Definition, Example, Proof, etc.) are kept intact
3. **Paragraph splits** used only when a block exceeds the max token limit
4. **Math blocks** (`$$...$$`) are never split
5. Small adjacent chunks merged up to the max token limit (default 512-1536 tokens)

## Topics covered

- **Napkin**: Abstract algebra, topology, linear algebra, representation theory, complex analysis, measure theory, differential geometry, algebraic number theory, algebraic topology, category theory, algebraic geometry, set theory
- **Open Logic**: Propositional logic, first-order logic, modal logic, intuitionistic logic, computability, incompleteness, set theory, model theory
- **Basic Analysis**: Real numbers, sequences, series, continuous functions, derivatives, integrals, metric spaces, multivariable calculus
- **First Course in Linear Algebra**: Systems of equations, vectors, matrices, determinants, eigenvalues, linear transformations, vector spaces
- **Abstract Algebra**: Groups, cyclic groups, permutation groups, cosets, isomorphisms, normal subgroups, homomorphisms, rings, integral domains, fields, vector spaces, Galois theory
- **Mathematical Reasoning**: Logic, proof techniques, set theory, functions, equivalence relations, number theory
- **Applied Combinatorics**: Strings/sequences, induction, generating functions, graph theory, inclusion-exclusion, network flows, partially ordered sets
- **Discrete Mathematics**: Logic, graph theory, counting, sequences, mathematical structures
- **Combinatorics Through Guided Discovery**: Counting, generating functions, distribution problems, graph theory, Polya enumeration
- **Elementary Number Theory**: Prime numbers, congruences, quadratic reciprocity, continued fractions, elliptic curves
- **Exploring Combinatorial Mathematics**: Pascal's triangle, binomial coefficients, generating functions, Stirling numbers, partitions, inclusion-exclusion
- **Introduction to Proof via IBL**: Logic, set theory, induction, real number axioms, topology of reals, sequences, continuity

## Usage

```python
from datasets import load_dataset

ds = load_dataset("yoonholee/olympiad-books-open-source", split="train")

# Filter by book
napkin = ds.filter(lambda x: x["book_key"] == "napkin")

# Filter by subject
algebra = ds.filter(lambda x: x["subject"] == "abstract-algebra")

# Filter by level
intro = ds.filter(lambda x: x["level"] == "intro")

# Filter by part within a book
groups = ds.filter(lambda x: x["book_key"] == "aata" and x["part"] == "Group Theory")
```
