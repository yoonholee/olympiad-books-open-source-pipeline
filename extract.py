#!/usr/bin/env python3
"""Extract all 12 math textbooks into individual markdown chapter files.

Handles two source formats:
  - PreTeXt XML (7 books): custom XML-to-markdown converter
  - LaTeX (5 books): pandoc with per-book preprocessors
"""

import os
import re
import subprocess
from pathlib import Path

BASE = Path(os.path.expanduser("~/Downloads/math_textbooks_open"))
OUT = BASE / "chapters"
SRC = BASE / "src"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def clean_whitespace(text):
    """Final whitespace cleanup applied to all outputs."""
    text = '\n'.join(line.strip() for line in text.split('\n'))
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'^-\s*\n+', '- ', text, flags=re.MULTILINE)
    text = re.sub(r'(^- .+)\n\n(?=- )', r'\1\n', text, flags=re.MULTILINE)
    text = re.sub(r'^(# .+)\n\n\1$', r'\1', text, flags=re.MULTILINE)
    lines = text.split('\n')
    if len(lines) >= 3 and lines[0].startswith('# '):
        title_text = lines[0][2:].strip()
        if lines[1] == '' and lines[2].strip() == title_text:
            lines = [lines[0]] + lines[3:]
            text = '\n'.join(lines)
    return text.strip() + '\n'


def strip_latex_fallback(text):
    """Last-resort LaTeX stripping when pandoc fails."""
    text = re.sub(r"\\begin\{[^}]+\}(\[[^\]]*\])?", "", text)
    text = re.sub(r"\\end\{[^}]+\}", "", text)
    text = re.sub(r"\\[a-zA-Z]+\*?\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?", "", text)
    text = re.sub(r"[{}]", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# PreTeXt pipeline
# ---------------------------------------------------------------------------
def resolve_includes(ptx_path):
    if not ptx_path.exists():
        return ""
    text = ptx_path.read_text()

    def replace_include(m):
        inc_path = ptx_path.parent / m.group(1)
        return resolve_includes(inc_path) if inc_path.exists() else ""

    text = re.sub(r'<xi:include\s+href="([^"]+)"\s*/?\s*>', replace_include, text)
    return text


def _math_block(inner):
    rows = re.findall(r'<mrow>(.*?)</mrow>', inner, re.DOTALL)
    if rows:
        return '\n$$\n' + '\n'.join(r.strip() for r in rows) + '\n$$\n'
    return f'\n$${inner.strip()}$$\n'


def ptx_to_md(xml_text):
    """Convert PreTeXt XML to clean markdown."""
    text = re.sub(r'<\?xml[^?]*\?>', '', xml_text)
    text = re.sub(r'\s+xmlns:[a-z]+="[^"]*"', '', text)

    title_match = re.search(r'<chapter[^>]*>\s*<title>(.*?)</title>', text, re.DOTALL)
    if not title_match:
        title_match = re.search(r'<title>(.*?)</title>', text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Untitled"
    title = re.sub(r'<m>(.*?)</m>', r'$\1$', title)
    title = re.sub(r'<[^>]+>', '', title)

    # Remove non-content elements
    text = re.sub(r'<idx>.*?</idx>', '', text, flags=re.DOTALL)
    text = re.sub(r'<notation>.*?</notation>', '', text, flags=re.DOTALL)
    text = re.sub(r'<image[^>]*/>', '', text)
    text = re.sub(r'<image[^>]*>.*?</image>', '[figure]', text, flags=re.DOTALL)
    text = re.sub(r'<latex-image>.*?</latex-image>', '[figure]', text, flags=re.DOTALL)
    text = re.sub(r'<asymptote>.*?</asymptote>', '[figure]', text, flags=re.DOTALL)
    text = re.sub(r'<sage>.*?</sage>', '[code block]', text, flags=re.DOTALL)
    text = re.sub(r'<interactive[^>]*>.*?</interactive>', '', text, flags=re.DOTALL)
    text = re.sub(r'<video[^>]*/>', '', text)
    text = re.sub(r'<hint>.*?</hint>', '', text, flags=re.DOTALL)
    text = re.sub(r'<answer>.*?</answer>', '', text, flags=re.DOTALL)
    text = re.sub(r'<solution>.*?</solution>', '', text, flags=re.DOTALL)
    text = re.sub(r'<figure[^>]*>', '', text)
    text = re.sub(r'</figure>', '', text)
    text = re.sub(r'<caption>(.*?)</caption>', r'*Figure: \1*', text, flags=re.DOTALL)
    text = re.sub(r'<sidebyside[^>]*>', '', text)
    text = re.sub(r'</sidebyside>', '', text)
    text = re.sub(r'<table[^>]*>', '', text)
    text = re.sub(r'</table>', '', text)

    # Math
    text = re.sub(r'<m>(.*?)</m>', r'$\1$', text, flags=re.DOTALL)
    text = re.sub(r'<me>(.*?)</me>', r'\n$$\1$$\n', text, flags=re.DOTALL)
    text = re.sub(r'<men>(.*?)</men>', r'\n$$\1$$\n', text, flags=re.DOTALL)
    text = re.sub(r'<md>(.*?)</md>', lambda m: _math_block(m.group(1)), text, flags=re.DOTALL)
    text = re.sub(r'<mdn>(.*?)</mdn>', lambda m: _math_block(m.group(1)), text, flags=re.DOTALL)
    text = re.sub(r'<mrow>(.*?)</mrow>', r'$$\1$$', text, flags=re.DOTALL)

    # Structure
    text = re.sub(r'<section[^>]*>\s*<title>(.*?)</title>', r'\n## \1\n', text, flags=re.DOTALL)
    text = re.sub(r'</section>', '', text)
    text = re.sub(r'<subsection[^>]*>\s*<title>(.*?)</title>', r'\n### \1\n', text, flags=re.DOTALL)
    text = re.sub(r'</subsection>', '', text)
    text = re.sub(r'<subsubsection[^>]*>\s*<title>(.*?)</title>', r'\n#### \1\n', text, flags=re.DOTALL)
    text = re.sub(r'</subsubsection>', '', text)

    # Named environments
    named_envs = ['theorem', 'lemma', 'proposition', 'corollary', 'definition',
                  'example', 'remark', 'conjecture', 'axiom', 'principle',
                  'convention', 'observation', 'fact', 'note', 'investigation',
                  'activity', 'exploration', 'assemblage', 'objectives',
                  'worksheet', 'exercise']
    for env in named_envs:
        text = re.sub(
            rf'<{env}[^>]*>\s*<title>(.*?)</title>',
            rf'\n**{env.title()} (\1).**\n',
            text, flags=re.DOTALL
        )
        text = re.sub(f'<{env}[^>]*>', f'\n**{env.title()}.**\n', text)
        text = re.sub(f'</{env}>', '', text)
    text = re.sub(r'<proof[^>]*>', '\n*Proof.*\n', text)
    text = re.sub(r'</proof>', '', text)
    for tag in ['statement', 'introduction', 'conclusion', 'task']:
        text = re.sub(rf'<{tag}[^>]*>', '', text)
        text = re.sub(rf'</{tag}>', '', text)

    # Inline
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<term>(.*?)</term>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<q>(.*?)</q>', r'"\1"', text, flags=re.DOTALL)
    text = re.sub(r'<sq>(.*?)</sq>', r"'\1'", text, flags=re.DOTALL)
    text = re.sub(r'<c>(.*?)</c>', r'`\1`', text, flags=re.DOTALL)
    text = re.sub(r'<alert>(.*?)</alert>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<foreign>(.*?)</foreign>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<pubtitle>(.*?)</pubtitle>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<articletitle>(.*?)</articletitle>', r'"\1"', text, flags=re.DOTALL)
    text = re.sub(r'<fillin[^/]*/>', '___', text)
    text = re.sub(r'<xref\s+ref="([^"]*)"[^>]*/>', r'[\1]', text)
    text = re.sub(r'<url\s+href="([^"]*)"[^>]*/>', r'\1', text)
    text = re.sub(r'<url\s+href="([^"]*)"[^>]*>(.*?)</url>', r'[\2](\1)', text, flags=re.DOTALL)

    # Lists
    for tag in ['ol', 'ul', 'dl']:
        text = re.sub(rf'<{tag}[^>]*>', '', text)
        text = re.sub(rf'</{tag}>', '', text)
    text = re.sub(r'<li[^>]*>', '\n- ', text)
    text = re.sub(r'</li>', '', text)

    # Paragraphs / tables
    text = re.sub(r'<p[^>]*>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<tabular[^>]*>', '\n', text)
    text = re.sub(r'</tabular>', '\n', text)
    text = re.sub(r'<row[^>]*>', '', text)
    text = re.sub(r'</row>', '\n', text)
    text = re.sub(r'<cell[^>]*>(.*?)</cell>', r'| \1 ', text, flags=re.DOTALL)
    text = re.sub(r'<col[^>]*/>', '', text)

    # Strip remaining XML tags and fix entities
    text = re.sub(r'<[^>]+>', '', text)
    for entity, char in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                         ('&apos;', "'"), ('&quot;', '"')]:
        text = text.replace(entity, char)

    # Fix orphaned cross-references
    text = re.sub(r'\bIn\s*,', 'In the previous section,', text)
    text = re.sub(r'\bfrom\s*,', 'from above,', text)

    return f"# {title}\n\n{text}"


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
        for prefix in ["ch_", "ch-", "C_", "chapter-", "app"]:
            if stem.startswith(prefix):
                stem = stem[len(prefix):]
                break
        out_file = out_dir / f"{i:02d}_{stem}.md"
        out_file.write_text(md)
    print(f"  {name}: {len(chapter_files)} chapters -> {out_dir}")


# ---------------------------------------------------------------------------
# LaTeX/Pandoc pipeline
# ---------------------------------------------------------------------------
def clean_pandoc(text):
    """Clean common pandoc markdown artifacts."""
    text = re.sub(r'^:{3,}\s*\w*\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[\]\{[^}]*\}', '', text)
    text = re.sub(r'\s*\{#[^}]+\}', '', text)
    text = re.sub(r'\s*\{\.[^}]+\}', '', text)
    text = re.sub(
        r'\[\\?\[.+?\\?\]\]\(#[^)]*\)(?:\{[^}]*\})?', '', text)
    text = re.sub(
        r'\[[^\]]*?\]\(#[^)]*\)\{reference-type="[^"]*"\s+reference="[^"]*"\}',
        '', text)
    text = re.sub(r'\{reference-type="[^"]*"\s+reference="[^"]*"\}', '', text)
    text = re.sub(r'  +', ' ', text)
    return text


def pandoc_latex_to_md(tex_path, cwd=None, preprocess=None, postprocess=None):
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
    md = clean_pandoc(md)
    if postprocess:
        md = postprocess(md)
    return md


# ---------------------------------------------------------------------------
# Napkin (LaTeX)
# ---------------------------------------------------------------------------
NAPKIN_MACROS = {
    r'\ZZ': r'\mathbb{Z}', r'\QQ': r'\mathbb{Q}', r'\RR': r'\mathbb{R}',
    r'\CC': r'\mathbb{C}', r'\FF': r'\mathbb{F}', r'\NN': r'\mathbb{N}',
    r'\EE': r'\mathbb{E}', r'\TT': r'\mathbb{T}',
    r'\inv': r'^{-1}', r'\defeq': r':=',
    r'\eps': r'\varepsilon', r'\half': r'\frac{1}{2}',
    r'\id': r'\mathrm{id}', r'\ol': r'\overline', r'\ul': r'\underline',
    r'\wt': r'\widetilde', r'\wh': r'\widehat',
    r'\OO': r'\mathcal{O}', r'\VV': r'\mathcal{V}',
    r'\SA': r'\mathscr{A}', r'\SB': r'\mathscr{B}',
    r'\SC': r'\mathscr{C}', r'\SF': r'\mathscr{F}',
    r'\SG': r'\mathscr{G}', r'\SH': r'\mathscr{H}',
    r'\kg': r'\mathfrak{g}', r'\kh': r'\mathfrak{h}',
    r'\kn': r'\mathfrak{n}', r'\ka': r'\mathfrak{a}',
    r'\kb': r'\mathfrak{b}', r'\kp': r'\mathfrak{p}',
    r'\kq': r'\mathfrak{q}', r'\km': r'\mathfrak{m}',
    r'\kP': r'\mathfrak{P}', r'\kQ': r'\mathfrak{Q}',
    r'\kf': r'\mathfrak{f}',
    r'\On': r'\mathrm{On}', r'\Mat': r'\mathrm{Mat}',
    r'\CH': r'\mathsf{CH}', r'\ZFC': r'\mathsf{ZFC}',
    r'\PP': r'\mathcal{P}', r'\Po': r'\mathbb{P}',
    r'\AA': r'\mathcal{A}', r'\BB': r'\mathcal{B}',
    r'\op': r'^{\mathrm{op}}', r'\ab': r'^{\mathrm{ab}}',
    r'\Frob': r'\mathrm{Frob}', r'\Cl': r'\mathrm{Cl}',
    r'\liff': r'\leftrightarrow', r'\lthen': r'\rightarrow',
    r'\surjto': r'\twoheadrightarrow', r'\injto': r'\hookrightarrow',
    r'\triv': r'\mathrm{triv}',
    r'\normalin': r'\trianglelefteq',
}


def preprocess_napkin(text):
    text = re.sub(r'\\vocab\{([^}]*)\}', r'\\textbf{\1}', text)
    text = re.sub(r'\\prototype\{[^}]*\}', '', text)
    text = re.sub(r'\\ii\b', r'\\item', text)
    return text


def expand_napkin_macros(text):
    for macro, expansion in NAPKIN_MACROS.items():
        pattern = re.escape(macro) + r'(?![a-zA-Z])'
        text = re.sub(pattern, expansion.replace('\\', '\\\\'), text)
    text = re.sub(r'\\Zc\s*(\w)', r'\\mathbb{Z}/\1\\mathbb{Z}', text)
    text = re.sub(r'\\Zc\{([^}]+)\}', r'\\mathbb{Z}/\1\\mathbb{Z}', text)
    text = re.sub(r'\\Zm\s*(\w)', r'(\\mathbb{Z}/\1\\mathbb{Z})^\\times', text)
    text = re.sub(r'\\Zm\{([^}]+)\}', r'(\\mathbb{Z}/\1\\mathbb{Z})^\\times', text)
    return text


def extract_napkin():
    out_dir = OUT / "napkin"
    out_dir.mkdir(parents=True, exist_ok=True)
    src = SRC / "napkin"
    main = (src / "Napkin.tex").read_text()

    ch_num = 0
    entries = []
    for line in main.splitlines():
        line = line.strip()
        m = re.match(r"\\include\{(.+?)\}", line)
        if m:
            rel = m.group(1)
            if "backmatter" in rel:
                continue
            ch_num += 1
            name = Path(rel).stem
            entries.append((ch_num, name, src / (rel + ".tex")))

    for ch_num, name, tex_path in entries:
        if not tex_path.exists():
            continue
        md = pandoc_latex_to_md(
            tex_path, cwd=str(src),
            preprocess=preprocess_napkin,
            postprocess=expand_napkin_macros,
        )
        out_file = out_dir / f"{ch_num:02d}_{name}.md"
        out_file.write_text(clean_whitespace(md))
    print(f"  napkin: {len(entries)} chapters -> {out_dir}")


# ---------------------------------------------------------------------------
# ENT (LaTeX)
# ---------------------------------------------------------------------------
def preprocess_ent(text):
    text = re.sub(r'\\defn\{([^}]*)\}', r'\\textbf{\1}', text)
    return text


def extract_ent():
    out_dir = OUT / "ent"
    out_dir.mkdir(parents=True, exist_ok=True)
    body = (SRC / "ent" / "body.tex").read_text()

    pattern = re.compile(r'(\\chapter\*?\{[^}]+\})')
    parts = pattern.split(body)

    chapters = []
    for i, part in enumerate(parts):
        m = re.match(r'\\chapter\*?\{(.+?)\}', part)
        if m:
            title = m.group(1)
            title = re.sub(r'\\em\s+', '', title)
            title = re.sub(r'[{}]', '', title)
            content = parts[i + 1] if i + 1 < len(parts) else ""
            chapters.append((title, content))

    skip = {"Preface", "Answers and Hints"}
    ch_num = 0
    for title, content in chapters:
        if title.strip() in skip:
            continue
        ch_num += 1
        tmp = SRC / "ent" / f"_tmp_ch{ch_num}.tex"
        tmp.write_text(f"\\chapter{{{title}}}\n{content}")
        try:
            md = pandoc_latex_to_md(tmp, cwd=SRC / "ent", preprocess=preprocess_ent)
        finally:
            tmp.unlink(missing_ok=True)

        slug = re.sub(r'[^\w\s-]', '', title.lower()).strip()
        slug = re.sub(r'[\s]+', '-', slug)[:50]
        out_file = out_dir / f"{ch_num:02d}_{slug}.md"
        out_file.write_text(clean_whitespace(f"# {title}\n\n{md}"))

    print(f"  ent: {ch_num} chapters -> {out_dir}")


# ---------------------------------------------------------------------------
# Basic Analysis (LaTeX)
# ---------------------------------------------------------------------------
def preprocess_ra(text):
    r"""Expand \myindex{}, strip \myquote{}, clean labels and comment blocks."""
    text = re.sub(r'\\myindex\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\myquote\{', '{', text)
    text = re.sub(r'(\\(?:chapter|section)\{[^}]*\})\s*\\label\{[^}]*\}', r'\1', text)
    text = re.sub(r'^%+\s*$', '', text, flags=re.MULTILINE)
    return text


RA_CHAPTERS = [
    "ch-vol1-intro.tex", "ch-real-nums.tex", "ch-seq-ser.tex",
    "ch-contfunc.tex", "ch-der.tex", "ch-riemann.tex",
    "ch-seq-funcs.tex", "ch-metric.tex", "ch-several-vars-ders.tex",
    "ch-one-dim-ints-sv.tex", "ch-multivar-int.tex", "ch-approximate.tex",
]


def extract_ra():
    out_dir = OUT / "ra"
    out_dir.mkdir(parents=True, exist_ok=True)
    src_dir = SRC / "ra"
    for i, ch_file in enumerate(RA_CHAPTERS, 1):
        tex_path = src_dir / ch_file
        if not tex_path.exists():
            print(f"  SKIP (missing): {ch_file}")
            continue
        md = pandoc_latex_to_md(tex_path, cwd=src_dir, preprocess=preprocess_ra)
        stem = Path(ch_file).stem.replace("ch-", "")
        out_file = out_dir / f"{i:02d}_{stem}.md"
        out_file.write_text(clean_whitespace(md))
    print(f"  ra: {len(RA_CHAPTERS)} chapters -> {out_dir}")


# ---------------------------------------------------------------------------
# IBL Intro to Proof (LaTeX)
# ---------------------------------------------------------------------------
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
# Open Logic (LaTeX)
# ---------------------------------------------------------------------------
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
    """Resolve \\olimport{name} to file contents, recursively."""
    def replace(m):
        name = m.group(1)
        path = base_dir / f"{name}.tex"
        if path.exists():
            return resolve_olimport(path.read_text(), path.parent)
        return ""
    return re.sub(r'\\olimport\{([^}]+)\}', replace, text)


def _match_braced(s, pos):
    """Match a {...} group at pos, handling nesting. Returns (content, end_pos)."""
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


def preprocess_openlogic(text):
    """Expand Open Logic's custom macro system."""
    # Strip subfiles boilerplate
    text = re.sub(r'\\documentclass\[.*?\]\{subfiles\}', '', text)
    text = re.sub(r'\\begin\{document\}', '', text)
    text = re.sub(r'\\end\{document\}', '', text)
    text = re.sub(r'\\begin\{editorial\}.*?\\end\{editorial\}', '', text, flags=re.DOTALL)

    # OL chapter/section -> standard LaTeX
    text = re.sub(r'\\olchapter\{[^}]*\}\{[^}]*\}\{([^}]*)\}', r'\\chapter{\1}', text)
    text = re.sub(r'\\olsection\{[^}]*\}\{[^}]*\}\{([^}]*)\}', r'\\section{\1}', text)
    text = re.sub(r'\\OLEndChapterHook', '', text)
    text = re.sub(r'\\OLEndSectionHook', '', text)

    # !! natural language macros (order matters: capitalized before lowercase)
    text = re.sub(r'!!\^a\{([^}]*)\}', lambda m: 'A ' + m.group(1), text)
    text = re.sub(r'!!\^an\{([^}]*)\}', lambda m: 'An ' + m.group(1), text)
    text = re.sub(r'!!\^the\{([^}]*)\}', lambda m: 'The ' + m.group(1), text)
    text = re.sub(r'!!\^(\w+)', lambda m: m.group(1).capitalize(), text)
    text = re.sub(r'!!a\{([^}]*)\}', r'a \1', text)
    text = re.sub(r'!!an\{([^}]*)\}', r'an \1', text)
    text = re.sub(r'!!the\{([^}]*)\}', r'the \1', text)
    text = re.sub(r'!!\{([^}]*)\}', r'\1', text)
    text = re.sub(r'!!(\w+)', r'\1', text)
    text = re.sub(r'!([A-Z])', r'\1', text)

    # \iftag / \tagitem: brace-aware expansion (prv* -> true branch, def* -> false)
    def expand_conditionals(text):
        result = []
        i = 0
        while i < len(text):
            m = re.match(r'\\(?:iftag|tagitem)', text[i:])
            if m:
                cmd_end = i + m.end()
                tag, pos = _match_braced(text, cmd_end)
                if tag is not None:
                    true_br, pos = _match_braced(text, pos)
                    false_br, pos = _match_braced(text, pos)
                    result.append((false_br or "") if tag.startswith("def") else (true_br or ""))
                    i = pos
                    continue
            result.append(text[i])
            i += 1
        return ''.join(result)
    text = expand_conditionals(text)

    # Misc macros
    text = re.sub(r'\\ycomma\b', ',', text)
    text = re.sub(r'\\indcase\{[^}]*\}\{[^}]*\}\{', '', text)
    text = re.sub(r'\\indfrm\b', '', text)
    text = re.sub(r'\\tuple\{([^}]*)\}', r'(\1)', text)
    text = re.sub(r'\\Lang\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\ident\b', r'=', text)

    # Logic/model theory symbols
    text = re.sub(r'\\Entails\b', r'\\models', text)
    text = re.sub(r'\\pSat\{([^}]*)\}\{([^}]*)\}', r'\\mathfrak{\1} \\models \2', text)
    text = re.sub(r'\\Sat\{([^}]*)\}\{([^}]*)\}', r'\\mathfrak{\1} \\models \2', text)
    text = re.sub(r'\\SatN\{([^}]*)\}\{([^}]*)\}', r'\\mathfrak{\1} \\not\\models \2', text)
    text = re.sub(r'\\True\b', r'\\top', text)
    text = re.sub(r'\\False\b', r'\\bot', text)
    text = re.sub(r'\\lfalse\b', r'\\bot', text)
    text = re.sub(r'\\ltrue\b', r'\\top', text)
    text = re.sub(r'\\lif\b', r'\\rightarrow', text)
    text = re.sub(r'\\liff\b', r'\\leftrightarrow', text)

    # Structural/formatting macros
    text = re.sub(r'\\tag(true|false)\{[^}]*\}', '', text)
    text = re.sub(r'\\Frm\[([^\]]*)\]', r'\\mathrm{Frm}(\1)', text)
    text = re.sub(r'\\Frm\b', r'\\mathrm{Frm}', text)
    text = re.sub(r'\\PVar\b', r'\\mathrm{Prop}', text)
    text = re.sub(r'\\pAssign\{([^}]*)\}', r'\\mathfrak{\1}', text)
    text = re.sub(r'\\pValue\{([^}]*)\}', r'\\overline{\\mathfrak{\1}}', text)
    text = re.sub(r'\\Struct\{([^}]*)\}', r'\\mathfrak{\1}', text)
    text = re.sub(r'\\Domain\{([^}]*)\}', r'|\\mathfrak{\1}|', text)
    text = re.sub(r'\\Assign\{([^}]*)\}\{([^}]*)\}', r'\1^{\\mathfrak{\2}}', text)
    text = re.sub(r'\\Value\{([^}]*)\}\{([^}]*)\}', r'\\mathrm{Val}_{\\mathfrak{\2}}(\1)', text)
    text = re.sub(r'\\Atom\{([^}]*)\}\{([^}]*)\}', r'\1(\2)', text)
    text = re.sub(r'\\Obj\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\Obj\s+(\S)', r'\1', text)
    text = re.sub(r'\\Sent\[([^\]]*)\]', r'\\mathrm{Sent}(\1)', text)
    text = re.sub(r'\\Term\[([^\]]*)\]', r'\\mathrm{Term}(\1)', text)

    # Strip LaTeX comments
    text = re.sub(r'^%\s*(Part|Chapter|Section):.*$', '', text, flags=re.MULTILINE)
    return text


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

        combined_tex = preprocess_openlogic(combined_tex)
        tmp = mod_path / "_tmp_combined.tex"
        tmp.write_text(combined_tex)
        try:
            md = pandoc_latex_to_md(tmp, cwd=content_dir)
        finally:
            tmp.unlink(missing_ok=True)

        slug = re.sub(r'[^\w\s-]', '', title.lower()).strip()
        slug = re.sub(r'[\s]+', '-', slug)[:50]
        out_file = out_dir / f"{i:02d}_{slug}.md"
        out_file.write_text(clean_whitespace(f"# {title}\n\n{md}"))
        written += 1
    print(f"  openlogic: {written} chapters -> {out_dir}")


# ---------------------------------------------------------------------------
# PreTeXt book configs
# ---------------------------------------------------------------------------
PRETEXT_BOOKS = {
    "mathematical-reasoning": (
        SRC / "sundstrom-textbook" / "source",
        ["C_1intro.ptx", "C_2logic.ptx", "C_3proofs.ptx",
         "C_4induction.ptx", "C_5settheory.ptx", "C_6functions.ptx",
         "C_7equivrelations.ptx", "C_8numbertheory.ptx", "C_9topicsinsets.ptx"],
    ),
    "exploring-combinatorial-math": (
        SRC / "ecm" / "source",
        ["ch_intro.ptx", "ch_basic-combinatorics.ptx",
         "ch_advanced-combinatorics.ptx", "ch_graphtheory.ptx",
         "ch_logic.ptx"],
    ),
    "discrete-mathematics": (
        SRC / "discrete-book" / "source",
        ["ch_intro.ptx", "ch_logic.ptx", "ch_graphtheory.ptx",
         "ch_counting.ptx", "ch_sequences.ptx", "ch_structures.ptx",
         "ch_additionalTopics.ptx"],
    ),
    "aata": (
        SRC / "aata" / "src",
        ["sets.xml", "integers.xml", "groups.xml", "cyclic.xml",
         "permute.xml", "cosets.xml", "crypt.xml", "algcodes.xml",
         "isomorph.xml", "normal.xml", "homomorph.xml", "matrix.xml",
         "struct.xml", "actions.xml", "sylow.xml", "rings.xml",
         "poly.xml", "domains.xml", "boolean.xml", "vect.xml",
         "fields.xml", "finite.xml", "galois.xml"],
    ),
    "applied-combinatorics": (
        SRC / "applied-combinatorics" / "source",
        ["ch_prologue.ptx", "ch_intro.ptx", "ch_strings.ptx",
         "ch_induction.ptx", "ch_basics.ptx", "ch_graphs.ptx",
         "ch_posets.ptx", "ch_inclusion-exclusion.ptx",
         "ch_genfunction.ptx", "ch_recurrence.ptx",
         "ch_probability.ptx", "ch_probmeth.ptx",
         "ch_graphalgorithms.ptx", "ch_networkflow.ptx",
         "ch_flowapplications.ptx", "ch_polya.ptx",
         "ch_kitchensink.ptx"],
    ),
    "bogart": (
        SRC / "bogart" / "mbx",
        ["ch1-whatis.mbx", "ch2-induction.mbx", "ch3-distribution.mbx",
         "ch4-genfns.mbx", "ch5-inclexcl.mbx", "ch6-groupsonsets.mbx",
         "app1-relations.mbx", "app2-induction.mbx", "app3-expogenfns.mbx"],
    ),
    "fcla": (
        SRC / "fcla" / "src",
        ["chapter-SLE.xml", "chapter-V.xml", "chapter-M.xml",
         "chapter-VS.xml", "chapter-D.xml", "chapter-E.xml",
         "chapter-LT.xml", "chapter-R.xml"],
    ),
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Extracting all books...\n")

    # PreTeXt books
    for name, (src_dir, files) in PRETEXT_BOOKS.items():
        print(f"  [{name}]")
        extract_pretext_book(name, src_dir, files)

    # LaTeX books
    for name, func in [
        ("napkin", extract_napkin),
        ("ent", extract_ent),
        ("ra", extract_ra),
        ("ibl-intro-proof", extract_ibl_intro_proof),
        ("openlogic", extract_openlogic),
    ]:
        print(f"  [{name}]")
        func()

    print("\nDone!")
    for d in sorted(OUT.iterdir()):
        if d.is_dir():
            files = list(d.glob("*.md"))
            total = sum(f.stat().st_size for f in files)
            print(f"  {d.name}: {len(files)} files, {total // 1024}KB")


if __name__ == "__main__":
    main()
