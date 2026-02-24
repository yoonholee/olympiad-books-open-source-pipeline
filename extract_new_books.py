#!/usr/bin/env python3
"""Extract chapters from the 8 new math textbooks into individual .md files.

Reuses helpers from extract_all.py (resolve_includes, ptx_to_md, clean_whitespace).
"""

import os
import re
import subprocess
from pathlib import Path

BASE = Path(os.path.expanduser("~/Downloads/math_textbooks_open"))
OUT = BASE / "chapters"
SRC = BASE / "src"

# Import shared helpers from extract_all
from extract_all import (
    resolve_includes, ptx_to_md, clean_whitespace,
    run, strip_latex_fallback,
)


# ---------------------------------------------------------------------------
# PreTeXt books (reuse existing pipeline)
# ---------------------------------------------------------------------------
def extract_pretext_book(name, src_dir, chapter_files):
    out_dir = OUT / name
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, ch_file in enumerate(chapter_files, 1):
        ptx_path = src_dir / ch_file
        xml_text = resolve_includes(ptx_path)
        if not xml_text.strip():
            print(f"  SKIP (empty): {ch_file}")
            continue
        md = ptx_to_md(xml_text)
        md = clean_whitespace(md)
        stem = Path(ch_file).stem
        # Clean up prefix patterns
        for prefix in ["ch_", "ch-", "C_", "chapter-", "app"]:
            if stem.startswith(prefix):
                stem = stem[len(prefix):]
                break
        out_file = out_dir / f"{i:02d}_{stem}.md"
        out_file.write_text(md)
    print(f"  {name}: {len(chapter_files)} chapters -> {out_dir}")


# ---------------------------------------------------------------------------
# LaTeX books (pandoc)
# ---------------------------------------------------------------------------
def clean_pandoc_generic(text):
    """Clean pandoc markdown artifacts for generic LaTeX books."""
    # Remove fenced div markers
    text = re.sub(r'^:{3,}\s*\w*\s*$', '', text, flags=re.MULTILINE)
    # Remove pandoc span/id artifacts
    text = re.sub(r'\[\]\{[^}]*\}', '', text)
    # Remove {#label} header attributes
    text = re.sub(r'\s*\{#[^}]+\}', '', text)
    # Remove {.class} attributes
    text = re.sub(r'\s*\{\.[^}]+\}', '', text)
    # Remove bare label references [\[label\]](#label){...}
    text = re.sub(
        r'\[\\?\[.+?\\?\]\]\(#[^)]*\)(?:\{[^}]*\})?',
        '', text
    )
    # Remove [label](#label){reference-type=...}
    text = re.sub(
        r'\[[^\]]*?\]\(#[^)]*\)\{reference-type="[^"]*"\s+reference="[^"]*"\}',
        '', text
    )
    # Remaining {reference-type=...}
    text = re.sub(r'\{reference-type="[^"]*"\s+reference="[^"]*"\}', '', text)
    # Double+ spaces
    text = re.sub(r'  +', ' ', text)
    return text


def pandoc_latex_to_md(tex_path, cwd=None, preprocess=None):
    """Convert a LaTeX file to markdown via pandoc."""
    if preprocess:
        content = tex_path.read_text()
        content = preprocess(content)
        tmp = tex_path.parent / f"_tmp_{tex_path.stem}.tex"
        tmp.write_text(content)
        target = tmp
    else:
        target = tex_path
        tmp = None
    try:
        result = run(
            ["pandoc", str(target), "-f", "latex", "-t", "markdown",
             "--wrap=none", "--columns=9999", "--top-level-division=chapter"],
            cwd=str(cwd or tex_path.parent),
        )
        md = result.stdout
        if not md.strip():
            md = strip_latex_fallback(target.read_text())
    finally:
        if tmp:
            tmp.unlink(missing_ok=True)
    md = clean_pandoc_generic(md)
    return md


# ---------------------------------------------------------------------------
# LaTeX preprocessors
# ---------------------------------------------------------------------------
def preprocess_ent(text):
    """Preprocess ENT LaTeX: expand \defn{} and clean bibliography refs."""
    text = re.sub(r'\\defn\{([^}]*)\}', r'\\textbf{\1}', text)
    return text


def preprocess_ra(text):
    r"""Preprocess RA LaTeX: expand \myindex{}, \myquote{}, clean chapter labels."""
    text = re.sub(r'\\myindex\{([^}]*)\}', r'\1', text)
    # \myquote can contain math, so just strip the command and keep the content
    text = re.sub(r'\\myquote\{', '{', text)
    # Strip \label{...} after \chapter{...} and \section{...}
    text = re.sub(r'(\\(?:chapter|section)\{[^}]*\})\s*\\label\{[^}]*\}', r'\1', text)
    # Strip %%%%% comment blocks
    text = re.sub(r'^%+\s*$', '', text, flags=re.MULTILINE)
    return text


def preprocess_openlogic(text):
    """Preprocess Open Logic LaTeX: expand !! macros, custom symbols, strip boilerplate."""
    # Strip subfiles boilerplate
    text = re.sub(r'\\documentclass\[.*?\]\{subfiles\}', '', text)
    text = re.sub(r'\\begin\{document\}', '', text)
    text = re.sub(r'\\end\{document\}', '', text)
    # Strip editorial comments
    text = re.sub(r'\\begin\{editorial\}.*?\\end\{editorial\}', '', text, flags=re.DOTALL)
    # Strip OL chapter/section commands -> LaTeX equivalents
    text = re.sub(r'\\olchapter\{[^}]*\}\{[^}]*\}\{([^}]*)\}', r'\\chapter{\1}', text)
    text = re.sub(r'\\olsection\{[^}]*\}\{[^}]*\}\{([^}]*)\}', r'\\section{\1}', text)
    text = re.sub(r'\\OLEndChapterHook', '', text)
    text = re.sub(r'\\OLEndSectionHook', '', text)
    # !! natural language macros
    # !!^a{term} -> A term (capitalized article)
    text = re.sub(r'!!\^a\{([^}]*)\}', lambda m: 'A ' + m.group(1), text)
    text = re.sub(r'!!\^an\{([^}]*)\}', lambda m: 'An ' + m.group(1), text)
    text = re.sub(r'!!\^the\{([^}]*)\}', lambda m: 'The ' + m.group(1), text)
    # !!^word (no braces) -> Word
    text = re.sub(r'!!\^(\w+)', lambda m: m.group(1).capitalize(), text)
    # !!a{term} -> a term
    text = re.sub(r'!!a\{([^}]*)\}', r'a \1', text)
    text = re.sub(r'!!an\{([^}]*)\}', r'an \1', text)
    text = re.sub(r'!!the\{([^}]*)\}', r'the \1', text)
    # !!{term} -> term (plural handled by text after })
    text = re.sub(r'!!\{([^}]*)\}', r'\1', text)
    # !!word (no braces) -> word
    text = re.sub(r'!!(\w+)', r'\1', text)
    # !A, !B etc. (formula metavariables) -> just A, B (strip the !)
    # (Can't wrap in $ because these also appear inside math environments)
    text = re.sub(r'!([A-Z])', r'\1', text)
    # \iftag{tag}{true}{false} - expand true branch for prv* tags, false for def*
    def expand_iftag(m):
        tag = m.group(1)
        true_br = m.group(2)
        false_br = m.group(3) if m.group(3) else ""
        if tag.startswith("def"):
            return false_br
        return true_br  # prv* and other tags default to true
    # Use brace-aware matching for nested content
    def match_braced(s, pos):
        """Match a {...} group starting at pos, handling nesting. Returns content and end pos."""
        if pos >= len(s) or s[pos] != '{':
            return None, pos
        depth = 1
        i = pos + 1
        while i < len(s) and depth > 0:
            if s[i] == '{':
                depth += 1
            elif s[i] == '}':
                depth -= 1
            i += 1
        return s[pos+1:i-1], i

    def expand_iftag_nested(text):
        result = []
        i = 0
        while i < len(text):
            m = re.match(r'\\(?:iftag|tagitem)', text[i:])
            if m:
                cmd_end = i + m.end()
                tag, pos = match_braced(text, cmd_end)
                if tag is not None:
                    true_br, pos = match_braced(text, pos)
                    false_br, pos = match_braced(text, pos)
                    if tag and tag.startswith("def"):
                        result.append(false_br or "")
                    else:
                        result.append(true_br or "")
                    i = pos
                    continue
            result.append(text[i])
            i += 1
        return ''.join(result)
    text = expand_iftag_nested(text)
    # \ycomma -> ,
    text = re.sub(r'\\ycomma\b', ',', text)
    # \indcase, \indfrm etc. - strip
    text = re.sub(r'\\indcase\{[^}]*\}\{[^}]*\}\{', '', text)
    text = re.sub(r'\\indfrm\b', '', text)
    # \tuple{...} -> (...)
    text = re.sub(r'\\tuple\{([^}]*)\}', r'(\1)', text)
    # \Lang{...} -> ...
    text = re.sub(r'\\Lang\{([^}]*)\}', r'\1', text)
    # \ident -> =
    text = re.sub(r'\\ident\b', r'=', text)
    # \Entails -> \models
    text = re.sub(r'\\Entails\b', r'\\models', text)
    # \pSat{v}{A} -> v \models A
    text = re.sub(r'\\pSat\{([^}]*)\}\{([^}]*)\}', r'\\mathfrak{\1} \\models \2', text)
    # Custom symbol macros
    text = re.sub(r'\\True\b', r'\\top', text)
    text = re.sub(r'\\False\b', r'\\bot', text)
    text = re.sub(r'\\lfalse\b', r'\\bot', text)
    text = re.sub(r'\\ltrue\b', r'\\top', text)
    # Tag system commands - strip
    text = re.sub(r'\\tag(true|false)\{[^}]*\}', '', text)
    text = re.sub(r'\\Frm\[([^\]]*)\]', r'\\mathrm{Frm}(\1)', text)
    text = re.sub(r'\\Frm\b', r'\\mathrm{Frm}', text)
    text = re.sub(r'\\PVar\b', r'\\mathrm{Prop}', text)
    text = re.sub(r'\\lif\b', r'\\rightarrow', text)
    text = re.sub(r'\\liff\b', r'\\leftrightarrow', text)
    text = re.sub(r'\\pAssign\{([^}]*)\}', r'\\mathfrak{\1}', text)
    text = re.sub(r'\\pValue\{([^}]*)\}', r'\\overline{\\mathfrak{\1}}', text)
    text = re.sub(r'\\Struct\{([^}]*)\}', r'\\mathfrak{\1}', text)
    text = re.sub(r'\\Domain\{([^}]*)\}', r'|\\mathfrak{\1}|', text)
    text = re.sub(r'\\Assign\{([^}]*)\}\{([^}]*)\}', r'\1^{\\mathfrak{\2}}', text)
    text = re.sub(r'\\Value\{([^}]*)\}\{([^}]*)\}', r'\\mathrm{Val}_{\\mathfrak{\2}}(\1)', text)
    text = re.sub(r'\\Atom\{([^}]*)\}\{([^}]*)\}', r'\1(\2)', text)
    # \Obj{X} -> X, \Obj X -> X (object language terms)
    text = re.sub(r'\\Obj\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\Obj\s+(\S)', r'\1', text)
    # \Sent[X] -> \mathrm{Sent}(X), \Term[X] -> \mathrm{Term}(X)
    text = re.sub(r'\\Sent\[([^\]]*)\]', r'\\mathrm{Sent}(\1)', text)
    text = re.sub(r'\\Term\[([^\]]*)\]', r'\\mathrm{Term}(\1)', text)
    # Proof system macros
    text = re.sub(r'\\Sat\{([^}]*)\}\{([^}]*)\}', r'\\mathfrak{\1} \\models \2', text)
    text = re.sub(r'\\SatN\{([^}]*)\}\{([^}]*)\}', r'\\mathfrak{\1} \\not\\models \2', text)
    # Strip % Part: / % Chapter: / % Section: comments
    text = re.sub(r'^%\s*(Part|Chapter|Section):.*$', '', text, flags=re.MULTILINE)
    return text


# ---------------------------------------------------------------------------
# 1. AATA - Abstract Algebra: Theory and Applications (PreTeXt)
# ---------------------------------------------------------------------------
def extract_aata():
    extract_pretext_book(
        "aata",
        SRC / "aata" / "src",
        ["sets.xml", "integers.xml", "groups.xml", "cyclic.xml",
         "permute.xml", "cosets.xml", "crypt.xml", "algcodes.xml",
         "isomorph.xml", "normal.xml", "homomorph.xml", "matrix.xml",
         "struct.xml", "actions.xml", "sylow.xml", "rings.xml",
         "poly.xml", "domains.xml", "boolean.xml", "vect.xml",
         "fields.xml", "finite.xml", "galois.xml"],
    )


# ---------------------------------------------------------------------------
# 2. Applied Combinatorics (PreTeXt)
# ---------------------------------------------------------------------------
def extract_applied_combinatorics():
    extract_pretext_book(
        "applied-combinatorics",
        SRC / "applied-combinatorics" / "source",
        ["ch_prologue.ptx", "ch_intro.ptx", "ch_strings.ptx",
         "ch_induction.ptx", "ch_basics.ptx", "ch_graphs.ptx",
         "ch_posets.ptx", "ch_inclusion-exclusion.ptx",
         "ch_genfunction.ptx", "ch_recurrence.ptx",
         "ch_probability.ptx", "ch_probmeth.ptx",
         "ch_graphalgorithms.ptx", "ch_networkflow.ptx",
         "ch_flowapplications.ptx", "ch_polya.ptx",
         "ch_kitchensink.ptx"],
    )


# ---------------------------------------------------------------------------
# 3. Bogart - Combinatorics Through Guided Discovery (PreTeXt/MBX)
# ---------------------------------------------------------------------------
def extract_bogart():
    extract_pretext_book(
        "bogart",
        SRC / "bogart" / "mbx",
        ["ch1-whatis.mbx", "ch2-induction.mbx", "ch3-distribution.mbx",
         "ch4-genfns.mbx", "ch5-inclexcl.mbx", "ch6-groupsonsets.mbx",
         "app1-relations.mbx", "app2-induction.mbx", "app3-expogenfns.mbx"],
    )


# ---------------------------------------------------------------------------
# 4. FCLA - First Course in Linear Algebra (PreTeXt)
# ---------------------------------------------------------------------------
def extract_fcla():
    extract_pretext_book(
        "fcla",
        SRC / "fcla" / "src",
        ["chapter-SLE.xml", "chapter-V.xml", "chapter-M.xml",
         "chapter-VS.xml", "chapter-D.xml", "chapter-E.xml",
         "chapter-LT.xml", "chapter-R.xml"],
    )


# ---------------------------------------------------------------------------
# 5. Elementary Number Theory - William Stein (LaTeX, monolithic)
# ---------------------------------------------------------------------------
def extract_ent():
    out_dir = OUT / "ent"
    out_dir.mkdir(parents=True, exist_ok=True)
    body = (SRC / "ent" / "body.tex").read_text()

    # Split by \chapter{...} or \chapter*{...}
    pattern = re.compile(r'(\\chapter\*?\{[^}]+\})')
    parts = pattern.split(body)

    chapters = []
    for i, part in enumerate(parts):
        m = re.match(r'\\chapter\*?\{(.+?)\}', part)
        if m:
            title = m.group(1)
            # Clean LaTeX from title
            title = re.sub(r'\\em\s+', '', title)
            title = re.sub(r'[{}]', '', title)
            content = parts[i + 1] if i + 1 < len(parts) else ""
            chapters.append((title, content))

    # Skip preface, answers/hints
    skip = {"Preface", "Answers and Hints"}
    ch_num = 0
    written = 0
    for title, content in chapters:
        if title.strip() in skip:
            continue
        ch_num += 1
        # Write temp .tex and pandoc it
        tmp = SRC / "ent" / f"_tmp_ch{ch_num}.tex"
        tex = f"\\chapter{{{title}}}\n{content}"
        tmp.write_text(tex)
        try:
            md = pandoc_latex_to_md(tmp, cwd=SRC / "ent", preprocess=preprocess_ent)
        finally:
            tmp.unlink(missing_ok=True)

        slug = re.sub(r'[^\w\s-]', '', title.lower()).strip()
        slug = re.sub(r'[\s]+', '-', slug)[:50]
        out_file = out_dir / f"{ch_num:02d}_{slug}.md"
        md = f"# {title}\n\n{md}"
        out_file.write_text(clean_whitespace(md))
        written += 1

    print(f"  ent: {written} chapters -> {out_dir}")


# ---------------------------------------------------------------------------
# 6. Basic Analysis - Jiri Lebl (LaTeX, separate chapter files)
# ---------------------------------------------------------------------------
def extract_ra():
    out_dir = OUT / "ra"
    out_dir.mkdir(parents=True, exist_ok=True)

    chapter_files = [
        "ch-vol1-intro.tex", "ch-real-nums.tex", "ch-seq-ser.tex",
        "ch-contfunc.tex", "ch-der.tex", "ch-riemann.tex",
        "ch-seq-funcs.tex", "ch-metric.tex", "ch-several-vars-ders.tex",
        "ch-one-dim-ints-sv.tex", "ch-multivar-int.tex", "ch-approximate.tex",
    ]

    src_dir = SRC / "ra"
    for i, ch_file in enumerate(chapter_files, 1):
        tex_path = src_dir / ch_file
        if not tex_path.exists():
            print(f"  SKIP (missing): {ch_file}")
            continue

        md = pandoc_latex_to_md(tex_path, cwd=src_dir, preprocess=preprocess_ra)
        stem = Path(ch_file).stem.replace("ch-", "")
        out_file = out_dir / f"{i:02d}_{stem}.md"
        out_file.write_text(clean_whitespace(md))

    print(f"  ra: {len(chapter_files)} chapters -> {out_dir}")


# ---------------------------------------------------------------------------
# 7. IBL Intro to Proof - Dana Ernst (LaTeX, many small sections)
# ---------------------------------------------------------------------------
# Group the sections into logical chapters based on the main file structure
IBL_CHAPTERS = {
    "Introduction": ["Introduction"],
    "Mathematics and Logic": [
        "IntroToMath", "TasteNumberTheory", "IntroToLogic",
        "NegatingAndContradiction", "IntroQuantification", "MoreQuantification",
    ],
    "Set Theory": [
        "SetTheory", "Sets", "RussellsParadox", "PowerSets",
        "IndexingSets", "CartesianProducts",
    ],
    "Induction": [
        "Induction", "IntroInduction", "MoreInduction",
        "CompleteInduction", "WellOrderingPrinciple",
    ],
    "Real Numbers and Topology": [
        "RealNumbers", "AxiomsRealNumbers", "Topology",
    ],
    "Three Famous Theorems": [
        "ThreeFamousTheorems", "FundamentalTheoremArithmetic",
        "IrrationalityRoot2", "InfinitudeOfPrimes",
    ],
    "Relations and Partitions": [
        "RelationsPartitions", "Relations", "EquivalenceRelations",
        "Partitions", "ModularArithmetic",
    ],
    "Functions": [
        "Functions", "IntroFunctions", "InjectiveSurjectiveFunctions",
        "CompositionsInverses", "ImagesInverseImages", "ContinuousFunctions",
    ],
    "Cardinality": [
        "Cardinality", "IntroCardinality", "FiniteSets",
        "InfiniteSets", "CountableSets", "UncountableSets",
    ],
}


def extract_ibl_intro_proof():
    out_dir = OUT / "ibl-intro-proof"
    out_dir.mkdir(parents=True, exist_ok=True)
    src_dir = SRC / "IBL-IntroToProof" / "MAAPressVersion"

    for i, (ch_title, sections) in enumerate(IBL_CHAPTERS.items(), 1):
        combined_md = f"# {ch_title}\n\n"
        for sec_name in sections:
            tex_path = src_dir / f"{sec_name}.tex"
            if not tex_path.exists():
                continue
            md = pandoc_latex_to_md(tex_path, cwd=src_dir)
            if md.strip():
                combined_md += md + "\n\n"

        slug = re.sub(r'[^\w\s-]', '', ch_title.lower()).strip()
        slug = re.sub(r'[\s]+', '-', slug)[:50]
        out_file = out_dir / f"{i:02d}_{slug}.md"
        out_file.write_text(clean_whitespace(combined_md))

    print(f"  ibl-intro-proof: {len(IBL_CHAPTERS)} chapters -> {out_dir}")


# ---------------------------------------------------------------------------
# 8. Open Logic Project (LaTeX, modular)
# ---------------------------------------------------------------------------
# Map module dirs to chapter order
OPENLOGIC_MODULES = [
    ("sets-functions-relations", "Sets, Relations, and Functions"),
    ("propositional-logic", "Propositional Logic"),
    ("first-order-logic", "First-Order Logic"),
    ("model-theory", "Model Theory"),
    ("computability", "Computability"),
    ("turing-machines", "Turing Machines"),
    ("incompleteness", "Incompleteness"),
    ("set-theory", "Set Theory"),
    ("second-order-logic", "Second-Order Logic"),
    ("lambda-calculus", "Lambda Calculus"),
    ("normal-modal-logic", "Normal Modal Logic"),
    ("intuitionistic-logic", "Intuitionistic Logic"),
    ("many-valued-logic", "Many-Valued Logic"),
]


def resolve_olimport(text, base_dir):
    """Resolve \\olimport{name} to the content of name.tex in the same directory."""
    def replace(m):
        name = m.group(1)
        path = base_dir / f"{name}.tex"
        if path.exists():
            content = path.read_text()
            # Recursively resolve
            return resolve_olimport(content, path.parent)
        return ""
    return re.sub(r'\\olimport\{([^}]+)\}', replace, text)


def extract_openlogic():
    out_dir = OUT / "openlogic"
    out_dir.mkdir(parents=True, exist_ok=True)
    content_dir = SRC / "OpenLogic" / "content"

    written = 0
    for i, (module_dir, title) in enumerate(OPENLOGIC_MODULES, 1):
        mod_path = content_dir / module_dir
        if not mod_path.exists():
            print(f"  SKIP (missing): {module_dir}")
            continue

        # Collect all .tex files from subdirectories
        combined_tex = ""
        for sub in sorted(mod_path.iterdir()):
            if sub.is_dir():
                ch_tex = sub / f"{sub.name}.tex"
                if ch_tex.exists():
                    content = ch_tex.read_text()
                    content = resolve_olimport(content, sub)
                    combined_tex += content + "\n\n"

        if not combined_tex.strip():
            continue

        # Preprocess, write temp file, pandoc
        combined_tex = preprocess_openlogic(combined_tex)
        tmp = mod_path / "_tmp_combined.tex"
        tmp.write_text(combined_tex)
        try:
            md = pandoc_latex_to_md(tmp, cwd=content_dir)
        finally:
            tmp.unlink(missing_ok=True)

        md = f"# {title}\n\n{md}"
        slug = re.sub(r'[^\w\s-]', '', title.lower()).strip()
        slug = re.sub(r'[\s]+', '-', slug)[:50]
        out_file = out_dir / f"{i:02d}_{slug}.md"
        out_file.write_text(clean_whitespace(md))
        written += 1

    print(f"  openlogic: {written} chapters -> {out_dir}")


# ---------------------------------------------------------------------------
def main():
    print("Extracting new books...\n")

    print("[1/8] Abstract Algebra: Theory and Applications (PreTeXt)")
    extract_aata()

    print("[2/8] Applied Combinatorics (PreTeXt)")
    extract_applied_combinatorics()

    print("[3/8] Combinatorics Through Guided Discovery (PreTeXt/MBX)")
    extract_bogart()

    print("[4/8] First Course in Linear Algebra (PreTeXt)")
    extract_fcla()

    print("[5/8] Elementary Number Theory (LaTeX)")
    extract_ent()

    print("[6/8] Basic Analysis (LaTeX)")
    extract_ra()

    print("[7/8] Intro to Proof via IBL (LaTeX)")
    extract_ibl_intro_proof()

    print("[8/8] Open Logic Project (LaTeX)")
    extract_openlogic()

    print("\nDone! New chapters in:", OUT)
    for d in sorted(OUT.iterdir()):
        if d.is_dir():
            files = list(d.glob("*.md"))
            total = sum(f.stat().st_size for f in files)
            print(f"  {d.name}: {len(files)} files, {total // 1024}KB total")


if __name__ == "__main__":
    main()
