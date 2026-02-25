#!/usr/bin/env python3
"""Content-aware chunking for math textbook markdown files.

Usage:
    python chunk.py
    python chunk.py --min-tokens 256 --max-tokens 1024
    python chunk.py --book napkin
"""

import argparse
import json
import re
from pathlib import Path

BASE = Path(__file__).parent
CHAPTERS_DIR = BASE / "chapters"
OUT = BASE / "chunks"

CHARS_PER_TOKEN = 3.5

BOOKS = {
    "napkin": "An Infinitely Large Napkin",
    "mathematical-reasoning": "Mathematical Reasoning: Writing and Proof",
    "exploring-combinatorial-math": "Exploring Combinatorial Mathematics",
    "discrete-mathematics": "Discrete Mathematics: An Open Introduction",
    "aata": "Abstract Algebra: Theory and Applications",
    "applied-combinatorics": "Applied Combinatorics",
    "bogart": "Combinatorics Through Guided Discovery",
    "fcla": "A First Course in Linear Algebra",
    "ent": "Elementary Number Theory",
    "ra": "Basic Analysis",
    "ibl-intro-proof": "An Introduction to Proof via Inquiry-Based Learning",
    "openlogic": "Open Logic",
}

BOOK_SUBJECT = {
    "napkin": "general",
    "mathematical-reasoning": "proofs",
    "exploring-combinatorial-math": "combinatorics",
    "discrete-mathematics": "discrete-math",
    "aata": "abstract-algebra",
    "applied-combinatorics": "combinatorics",
    "bogart": "combinatorics",
    "fcla": "linear-algebra",
    "ent": "number-theory",
    "ra": "real-analysis",
    "ibl-intro-proof": "proofs",
    "openlogic": "logic",
}

BOOK_LEVEL = {
    "napkin": "advanced",
    "mathematical-reasoning": "intro",
    "exploring-combinatorial-math": "intro",
    "discrete-mathematics": "intro",
    "aata": "intro",
    "applied-combinatorics": "intro",
    "bogart": "intro",
    "fcla": "intro",
    "ent": "intro",
    "ra": "advanced",
    "ibl-intro-proof": "intro",
    "openlogic": "advanced",
}

CHAPTER_PARTS = {
    "aata": {
        "Preliminaries": "Foundations",
        "The Integers": "Foundations",
        "Groups": "Group Theory",
        "Cyclic Groups": "Group Theory",
        "Permutation Groups": "Group Theory",
        "Cosets and Lagrange's Theorem": "Group Theory",
        "Introduction to Cryptography": "Group Theory",
        "Algebraic Coding Theory": "Group Theory",
        "Isomorphisms": "Group Theory",
        "Normal Subgroups and Factor Groups": "Group Theory",
        "Homomorphisms": "Group Theory",
        "Matrix Groups and Symmetry": "Group Theory",
        "The Structure of Groups": "Group Theory",
        "Group Actions": "Group Theory",
        "The Sylow Theorems": "Group Theory",
        "Rings": "Rings and Fields",
        "Polynomials": "Rings and Fields",
        "Integral Domains": "Rings and Fields",
        "Lattices and Boolean Algebras": "Rings and Fields",
        "Vector Spaces": "Rings and Fields",
        "Fields": "Rings and Fields",
        "Finite Fields": "Rings and Fields",
        "Galois Theory": "Rings and Fields",
    },
    "applied-combinatorics": {
        "Prologue": "Foundations",
        "An Introduction to Combinatorics": "Foundations",
        "Strings, Sets, and Binomial Coefficients": "Foundations",
        "Combinatorial Basics": "Foundations",
        "Induction": "Foundations",
        "The Many Faces of Combinatorics": "Enumeration",
        "Generating Functions": "Enumeration",
        "Recurrence Equations": "Enumeration",
        "Inclusion-Exclusion": "Enumeration",
        "Graph Theory": "Graph Theory and Networks",
        "Graph Algorithms": "Graph Theory and Networks",
        "Network Flows": "Graph Theory and Networks",
        "Combinatorial Applications of Network Flows": "Graph Theory and Networks",
        "Partially Ordered Sets": "Advanced Topics",
        "Probability": "Advanced Topics",
        "Applying Probability to Combinatorics": "Advanced Topics",
        "P\u00f3lya's Enumeration Theorem": "Advanced Topics",
        "P&#243;lya\u2019s Enumeration Theorem": "Advanced Topics",
        "P&#243;lya's Enumeration Theorem": "Advanced Topics",
    },
    "fcla": {
        "Systems of Linear Equations": "Core Linear Algebra",
        "Vectors": "Core Linear Algebra",
        "Matrices": "Core Linear Algebra",
        "Vector Spaces": "Core Linear Algebra",
        "Determinants": "Advanced Topics",
        "Eigenvalues": "Advanced Topics",
        "Linear Transformations": "Advanced Topics",
        "Representations": "Advanced Topics",
    },
    "ra": {
        "Introduction": "Foundations",
        "Real Numbers": "Foundations",
        "Sequences and Series": "Single Variable",
        "Continuous Functions": "Single Variable",
        "The Derivative": "Single Variable",
        "The Riemann Integral": "Single Variable",
        "Sequences of Functions": "Single Variable",
        "Metric Spaces": "Metric Spaces and Several Variables",
        "Several Variables and Partial Derivatives": "Metric Spaces and Several Variables",
        "One-dimensional Integrals in Several Variables": "Metric Spaces and Several Variables",
        "Multivariable Integral": "Metric Spaces and Several Variables",
        "Functions as Limits": "Metric Spaces and Several Variables",
    },
    "openlogic": {
        "Sets, Relations, and Functions": "Foundations",
        "Propositional Logic": "Propositional and First-Order Logic",
        "First-Order Logic": "Propositional and First-Order Logic",
        "Model Theory": "Propositional and First-Order Logic",
        "Computability": "Computability and Incompleteness",
        "Turing Machines": "Computability and Incompleteness",
        "Lambda Calculus": "Computability and Incompleteness",
        "Incompleteness": "Computability and Incompleteness",
        "Second-Order Logic": "Non-Classical and Higher-Order Logic",
        "Intuitionistic Logic": "Non-Classical and Higher-Order Logic",
        "Many-Valued Logic": "Non-Classical and Higher-Order Logic",
        "Normal Modal Logic": "Non-Classical and Higher-Order Logic",
        "Set Theory": "Set Theory",
    },
    "ent": {
        "Prime Numbers": "Foundations",
        "The Ring of Integers Modulo n": "Foundations",
        "Quadratic Reciprocity": "Foundations",
        "Public-key Cryptography": "Applications",
        "Continued Fractions": "Applications",
        "Elliptic Curves": "Applications",
    },
    "bogart": {
        "What is Combinatorics?": "Foundations",
        "Distribution Problems": "Foundations",
        "Generating Functions": "Generating Functions",
        "Exponential Generating Functions": "Generating Functions",
        "The Principle of Inclusion and Exclusion": "Advanced Techniques",
        "Mathematical Induction": "Advanced Techniques",
        "Applications of Induction and Recursion in Combinatorics and Graph Theory": "Advanced Techniques",
        "Relations": "Advanced Techniques",
        "Groups acting on sets": "Advanced Techniques",
    },
    "mathematical-reasoning": {
        "Logical Reasoning": "Foundations",
        "Introduction to Writing Proofs in Mathematics": "Proof Techniques",
        "Constructing and Writing Proofs in Mathematics": "Proof Techniques",
        "Mathematical Induction": "Proof Techniques",
        "Set Theory": "Structures",
        "Functions": "Structures",
        "Equivalence Relations": "Structures",
        "Topics in Number Theory": "Structures",
        "Finite and Infinite Sets": "Structures",
    },
    "discrete-mathematics": {
        "Introduction and Preliminaries": "Foundations",
        "Logic and Proofs": "Foundations",
        "Counting": "Combinatorics and Sequences",
        "Sequences": "Combinatorics and Sequences",
        "Graph Theory": "Graph Theory",
        "Discrete Structures Revisited": "Advanced Topics",
        "Additional Topics": "Advanced Topics",
    },
    "exploring-combinatorial-math": {
        "Introduction and Preliminaries": "Foundations",
        "Symbolic Logic and Proofs": "Foundations",
        "Basic Combinatorics": "Combinatorics",
        "Advanced Combinatorics": "Combinatorics",
        "Graph Theory": "Graph Theory",
    },
    "ibl-intro-proof": {
        "Introduction": "Foundations",
        "Mathematics and Logic": "Foundations",
        "Set Theory": "Core Proof Topics",
        "Induction": "Core Proof Topics",
        "Three Famous Theorems": "Core Proof Topics",
        "Relations and Partitions": "Structures",
        "Functions": "Structures",
        "Cardinality": "Structures",
        "Real Numbers and Topology": "Structures",
    },
}


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


def build_napkin_metadata() -> dict:
    """Map filename stem -> (part, chapter_title) from Napkin.tex."""
    src = BASE / "src" / "napkin"
    main_path = src / "Napkin.tex"
    if not main_path.exists():
        return {}

    main = main_path.read_text()
    current_part = None
    mapping = {}

    for line in main.splitlines():
        line = line.strip()
        m = re.match(r"\\part\{(.+?)\}", line)
        if m:
            current_part = m.group(1)
            continue
        m = re.match(r"\\include\{(.+?)\}", line)
        if m:
            rel = m.group(1)
            if "backmatter" in rel:
                continue
            stem = Path(rel).stem
            tex_path = src / (rel + ".tex")
            title = stem.replace("-", " ").title()
            if tex_path.exists():
                content = tex_path.read_text()
                ch = re.search(r"\\chapter\{(.+?)\}", content)
                if ch:
                    title = ch.group(1)
                    # Clean LaTeX from title
                    title = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", title)
                    title = title.replace("\\", "").strip()
            mapping[stem] = (current_part, title)

    return mapping


def build_pretext_metadata(src_dir: Path, chapter_files: list[str]) -> dict:
    """Map filename stem -> chapter_title from PreTeXt chapter files."""
    mapping = {}
    for ch_file in chapter_files:
        ptx_path = src_dir / ch_file
        stem = Path(ch_file).stem.replace("ch_", "").replace("C_", "")
        title = stem.replace("-", " ").title()
        if ptx_path.exists():
            content = ptx_path.read_text()
            # Title may span multiple lines
            m = re.search(r"<title>(.*?)</title>", content, re.DOTALL)
            if m:
                title = m.group(1).strip()
                # Collapse whitespace from multiline
                title = re.sub(r"\s+", " ", title)
                # Strip any XML/math tags
                title = re.sub(r"<m>(.*?)</m>", r"$\1$", title)
                title = re.sub(r"<[^>]+>", "", title)
        mapping[stem] = title
    return mapping


NAPKIN_META = None
PRETEXT_META = {}


def get_napkin_meta():
    global NAPKIN_META
    if NAPKIN_META is None:
        NAPKIN_META = build_napkin_metadata()
    return NAPKIN_META


def get_pretext_meta(book_key):
    if book_key not in PRETEXT_META:
        from extract import PRETEXT_BOOKS
        if book_key in PRETEXT_BOOKS:
            src_dir, files = PRETEXT_BOOKS[book_key]
            PRETEXT_META[book_key] = build_pretext_metadata(src_dir, files)
        else:
            PRETEXT_META[book_key] = {}
    return PRETEXT_META[book_key]


def title_from_md(md_path):
    """Extract chapter title from # header in markdown file."""
    first_line = md_path.read_text().split('\n', 1)[0].strip()
    if first_line.startswith('# '):
        return first_line[2:].strip()
    return None


def resolve_chapter_meta(book_key: str, filename: str, md_path=None) -> dict:
    """Given a book key and md filename, return clean part/chapter metadata."""
    # Extract stem: "05_grp-intro.md" -> "grp-intro"
    stem = Path(filename).stem
    stem = re.sub(r"^\d+_", "", stem)  # strip numeric prefix

    if book_key == "napkin":
        meta = get_napkin_meta()
        if stem in meta:
            part, title = meta[stem]
            return {"part": part or "Front Matter", "chapter": title}
        return {"part": "Front Matter", "chapter": stem.replace("-", " ").title()}

    meta = get_pretext_meta(book_key)
    if stem in meta:
        return {"part": "", "chapter": meta[stem]}

    # Fallback: read title from markdown file's # header
    if md_path and md_path.exists():
        title = title_from_md(md_path)
        if title:
            return {"part": "", "chapter": title}

    return {"part": "", "chapter": stem.replace("-", " ").title()}


def preclean(text: str) -> str:
    """Remove pandoc cross-ref artifacts and other noise before chunking."""
    text = re.sub(r'\[\\?\[.+?\\?\]\]\(#[^)]*\)(?:\{[^}]*\})?', '', text)
    text = re.sub(
        r'\[[^\]]*?\]\(#[^)]*\)\{reference-type="[^"]*"\s+reference="[^"]*"\}', '', text)
    text = re.sub(r'\{reference-type="[^"]*"\s+reference="[^"]*"\}', '', text)
    text = re.sub(r'\[(?:ch|thm|prob|exer|def|sec|ex|lem|cor|rem|prop|fig|tab|eq):[\w_-]+\\?\]', '', text)
    text = re.sub(r'\[@ref:[^\]]+\]', '', text)
    text = re.sub(r'^#{2,4}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r'^(# .+)\n\n# .+$', r'\1', text, count=1, flags=re.MULTILINE)
    return text



ENV_PATTERN = re.compile(
    r'^\*\*('
    r'Theorem|Lemma|Proposition|Corollary|Definition|Example|Remark|'
    r'Conjecture|Axiom|Principle|Convention|Exercise|Investigation|'
    r'Activity|Exploration|Objectives|Worksheet|Assemblage'
    r')(?:\s*\(.*?\))?\.?\*\*',
    re.MULTILINE
)

PROOF_PATTERN = re.compile(r'^\*Proof\.\*', re.MULTILINE)


def parse_sections(text: str) -> list[dict]:
    parts = re.split(r'^(#{2,4}[ \t]+.+)$', text, flags=re.MULTILINE)
    sections = []
    current_header = None
    current_level = 0
    current_body = []

    for part in parts:
        header_match = re.match(r'^(#{2,4})[ \t]+(.+)$', part)
        if header_match:
            if current_body or current_header:
                sections.append({
                    "header": current_header,
                    "level": current_level,
                    "body": '\n'.join(current_body).strip(),
                })
            current_header = header_match.group(2).strip()
            current_level = len(header_match.group(1))
            current_body = []
        else:
            current_body.append(part)

    if current_body or current_header:
        sections.append({
            "header": current_header,
            "level": current_level,
            "body": '\n'.join(current_body).strip(),
        })
    return sections


def split_into_blocks(text: str) -> list[dict]:
    if not text.strip():
        return []

    blocks = []
    pos = 0
    markers = []
    for m in ENV_PATTERN.finditer(text):
        markers.append((m.start(), 'env', m.group(1)))
    for m in PROOF_PATTERN.finditer(text):
        markers.append((m.start(), 'proof', 'Proof'))
    markers.sort(key=lambda x: x[0])

    for i, (start, kind, label) in enumerate(markers):
        if start > pos:
            prose = text[pos:start].strip()
            if prose:
                blocks.append({"type": "prose", "text": prose})
        end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        block_text = text[start:end].strip()
        if block_text:
            blocks.append({"type": kind, "label": label, "text": block_text})
        pos = end

    if pos < len(text):
        trailing = text[pos:].strip()
        if trailing:
            blocks.append({"type": "prose", "text": trailing})

    if not markers:
        stripped = text.strip()
        if stripped:
            blocks.append({"type": "prose", "text": stripped})
    return blocks


def split_at_paragraphs(text: str, max_tokens: int) -> list[str]:
    if estimate_tokens(text) <= max_tokens:
        return [text]
    paragraphs = re.split(r'\n\n+', text)
    pieces = []
    current = []
    current_len = 0
    for para in paragraphs:
        para_tokens = estimate_tokens(para)
        if current_len + para_tokens > max_tokens and current:
            pieces.append('\n\n'.join(current))
            current = [para]
            current_len = para_tokens
        else:
            current.append(para)
            current_len += para_tokens
    if current:
        pieces.append('\n\n'.join(current))
    return pieces



def chunk_chapter(text: str, chapter_meta: dict,
                  min_tokens: int, max_tokens: int) -> list[dict]:
    text = preclean(text)

    # Strip h1 header (metadata comes from source, not the markdown h1)
    body = re.sub(r'^#\s+.+\n*', '', text, count=1).strip()

    sections = parse_sections(body)
    raw_chunks = []

    for section in sections:
        section_header = section["header"] or ""
        blocks = split_into_blocks(section["body"])

        pending = []
        pending_tokens = 0

        def flush():
            nonlocal pending, pending_tokens
            if not pending:
                return
            combined = '\n\n'.join(pending)
            raw_chunks.append(make_chunk(
                combined, chapter_meta, section_header
            ))
            pending = []
            pending_tokens = 0

        for block in blocks:
            block_tokens = estimate_tokens(block["text"])
            if block_tokens > max_tokens:
                flush()
                for piece in split_at_paragraphs(block["text"], max_tokens):
                    raw_chunks.append(make_chunk(
                        piece, chapter_meta, section_header
                    ))
                continue
            if pending_tokens + block_tokens > max_tokens:
                flush()
            pending.append(block["text"])
            pending_tokens += block_tokens

        flush()

    chunks = merge_small_chunks(raw_chunks, min_tokens, max_tokens)
    chunks = [c for c in chunks if c["tokens_est"] >= 20]

    for i, chunk in enumerate(chunks):
        chunk["chunk_id"] = i
    return chunks


def make_chunk(text, chapter_meta, section_header):
    return {
        **chapter_meta,
        "section": section_header,
        "text": text,
        "tokens_est": estimate_tokens(text),
    }


def merge_small_chunks(chunks, min_tokens, max_tokens):
    if len(chunks) <= 1:
        return chunks

    merged = [chunks[0]]
    for chunk in chunks[1:]:
        prev = merged[-1]
        can_merge = (prev["tokens_est"] + chunk["tokens_est"] <= max_tokens)
        same_section = (prev["section"] == chunk["section"])
        prev_tiny = prev["tokens_est"] < min_tokens
        chunk_tiny = chunk["tokens_est"] < min_tokens

        if can_merge and (same_section and (prev_tiny or chunk_tiny)
                          or prev_tiny and prev["tokens_est"] < min_tokens // 2):
            prev["text"] = prev["text"] + '\n\n' + chunk["text"]
            prev["tokens_est"] = estimate_tokens(prev["text"])
            if chunk["tokens_est"] > prev["tokens_est"]:
                prev["section"] = chunk["section"]
        else:
            merged.append(chunk)
    return merged



def process_book(book_key: str, min_tokens: int, max_tokens: int) -> list[dict]:
    book_dir = CHAPTERS_DIR / book_key
    if not book_dir.exists():
        print(f"  SKIP: {book_dir} not found")
        return []

    book_name = BOOKS.get(book_key, book_key)
    subject = BOOK_SUBJECT.get(book_key, "")
    level = BOOK_LEVEL.get(book_key, "")
    part_map = CHAPTER_PARTS.get(book_key, {})
    all_chunks = []

    for md_file in sorted(book_dir.glob("*.md")):
        text = md_file.read_text()
        meta = resolve_chapter_meta(book_key, md_file.name, md_path=md_file)
        # Use part from source metadata (Napkin), or from CHAPTER_PARTS mapping
        part = meta["part"] or part_map.get(meta["chapter"], "")
        chapter_meta = {
            "book": book_name,
            "book_key": book_key,
            "subject": subject,
            "level": level,
            "part": part,
            "chapter": meta["chapter"],
            "source_file": md_file.name,
        }
        chunks = chunk_chapter(text, chapter_meta, min_tokens, max_tokens)
        all_chunks.extend(chunks)

    return all_chunks


def main():
    parser = argparse.ArgumentParser(description="Chunk math textbooks")
    parser.add_argument("--min-tokens", type=int, default=512)
    parser.add_argument("--max-tokens", type=int, default=1536)
    parser.add_argument("--book", type=str, default=None)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    books = [args.book] if args.book else list(BOOKS.keys())
    total_chunks = 0

    for book_key in books:
        print(f"Chunking: {BOOKS.get(book_key, book_key)}")
        chunks = process_book(book_key, args.min_tokens, args.max_tokens)

        out_file = OUT / f"{book_key}.jsonl"
        with open(out_file, 'w') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

        tokens = [c["tokens_est"] for c in chunks]
        if tokens:
            print(f"  {len(chunks)} chunks -> {out_file.name}")
            print(f"  tokens: min={min(tokens)} "
                  f"med={sorted(tokens)[len(tokens)//2]} "
                  f"max={max(tokens)} "
                  f"total={sum(tokens)}")
        total_chunks += len(chunks)

    if not args.book:
        combined = OUT / "all.jsonl"
        with open(combined, 'w') as f:
            for book_key in BOOKS:
                book_file = OUT / f"{book_key}.jsonl"
                if book_file.exists():
                    f.write(book_file.read_text())
        print(f"\nCombined: {total_chunks} chunks -> {combined}")


if __name__ == "__main__":
    main()
