#!/usr/bin/env python3
"""Extract each chapter from all 5 math textbooks into individual .md files."""

import os
import re
import subprocess
from pathlib import Path

BASE = Path(os.path.expanduser("~/Downloads/math_textbooks_open"))
OUT = BASE / "chapters"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ---------------------------------------------------------------------------
# Common post-processing
# ---------------------------------------------------------------------------
def clean_whitespace(text):
    """Final whitespace cleanup applied to all outputs."""
    # Strip leading whitespace from every line (XML/layout indentation)
    text = '\n'.join(line.strip() for line in text.split('\n'))
    # Collapse 3+ newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Fix list items: "- \n\nFoo" or "-\n\nFoo" -> "- Foo"
    text = re.sub(r'^-\s*\n+', '- ', text, flags=re.MULTILINE)
    # Collapse consecutive blank lines between list items
    text = re.sub(r'(^- .+)\n\n(?=- )', r'\1\n', text, flags=re.MULTILINE)
    # Remove duplicate title: "# Title\n\nTitle\n" -> "# Title\n"
    text = re.sub(r'^(# .+)\n\n\1$', r'\1', text, flags=re.MULTILINE)
    # Also catch near-duplicate where second line has no #
    lines = text.split('\n')
    if len(lines) >= 3 and lines[0].startswith('# '):
        title_text = lines[0][2:].strip()
        if lines[1] == '' and lines[2].strip() == title_text:
            lines = [lines[0]] + lines[3:]
            text = '\n'.join(lines)
    return text.strip() + '\n'


# ---------------------------------------------------------------------------
# 1. Napkin (LaTeX → preprocess → pandoc → cleanup)
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


def preprocess_napkin_tex(text):
    """Preprocess .tex before pandoc: replace custom commands pandoc can't handle."""
    # \vocab{X} -> \textbf{X}  (vocab = bold blue term)
    text = re.sub(r'\\vocab\{([^}]*)\}', r'\\textbf{\1}', text)
    # \prototype{X} -> nothing (it's a marginal note)
    text = re.sub(r'\\prototype\{[^}]*\}', '', text)
    # \ii -> \item
    text = re.sub(r'\\ii\b', r'\\item', text)
    return text


def expand_napkin_macros(text):
    """Expand Napkin-specific LaTeX macros in the markdown output."""
    for macro, expansion in NAPKIN_MACROS.items():
        pattern = re.escape(macro) + r'(?![a-zA-Z])'
        text = re.sub(pattern, expansion.replace('\\', '\\\\'), text)
    # \Zc{n} -> \mathbb{Z}/n\mathbb{Z}
    text = re.sub(r'\\Zc\s*(\w)', r'\\mathbb{Z}/\1\\mathbb{Z}', text)
    text = re.sub(r'\\Zc\{([^}]+)\}', r'\\mathbb{Z}/\1\\mathbb{Z}', text)
    # \Zm{p} -> (\mathbb{Z}/p\mathbb{Z})^\times
    text = re.sub(r'\\Zm\s*(\w)', r'(\\mathbb{Z}/\1\\mathbb{Z})^\\times', text)
    text = re.sub(r'\\Zm\{([^}]+)\}', r'(\\mathbb{Z}/\1\\mathbb{Z})^\\times', text)
    return text


def clean_pandoc_napkin(text):
    """Clean pandoc markdown artifacts from Napkin conversion."""
    # Remove fenced div markers
    text = re.sub(r'^:{3,}\s*\w*\s*$', '', text, flags=re.MULTILINE)
    # Remove pandoc span/id artifacts
    text = re.sub(r'\[\]\{[^}]*\}', '', text)
    # Remove {#ch:... } header attributes
    text = re.sub(r'\s*\{#[^}]+\}', '', text)
    # Expand macros
    text = expand_napkin_macros(text)
    return text


def extract_napkin():
    out_dir = OUT / "napkin"
    out_dir.mkdir(parents=True, exist_ok=True)
    src = BASE / "src" / "napkin"
    main = (src / "Napkin.tex").read_text()

    current_part = None
    ch_num = 0
    entries = []

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
            ch_num += 1
            name = Path(rel).stem
            entries.append((ch_num, name, src / (rel + ".tex"), current_part))

    for ch_num, name, tex_path, part in entries:
        if not tex_path.exists():
            print(f"  SKIP (missing): {tex_path}")
            continue

        # Preprocess: replace custom commands pandoc can't handle
        tex_content = preprocess_napkin_tex(tex_path.read_text())

        # Write to temp file for pandoc
        tmp = tex_path.parent / f"_tmp_{name}.tex"
        tmp.write_text(tex_content)
        try:
            result = run(
                ["pandoc", str(tmp), "-f", "latex", "-t", "markdown",
                 "--wrap=none", "--columns=9999"],
                cwd=str(src),
            )
            md = result.stdout
        finally:
            tmp.unlink(missing_ok=True)

        if not md.strip():
            md = strip_latex_fallback(tex_content)

        md = clean_pandoc_napkin(md)
        part_prefix = f"[{part}] " if part else ""
        header = f"# {part_prefix}{name.replace('-', ' ').title()}\n\n"
        out_file = out_dir / f"{ch_num:02d}_{name}.md"
        out_file.write_text(clean_whitespace(header + md))
    print(f"  Napkin: {len(entries)} chapters -> {out_dir}")


def strip_latex_fallback(text):
    text = re.sub(r"\\begin\{[^}]+\}(\[[^\]]*\])?", "", text)
    text = re.sub(r"\\end\{[^}]+\}", "", text)
    text = re.sub(r"\\[a-zA-Z]+\*?\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?", "", text)
    text = re.sub(r"[{}]", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# 2-4. PreTeXt books
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


def ptx_to_md(xml_text):
    """Convert PreTeXt XML to clean markdown."""
    text = re.sub(r'<\?xml[^?]*\?>', '', xml_text)
    text = re.sub(r'\s+xmlns:[a-z]+="[^"]*"', '', text)

    # Extract chapter title
    title_match = re.search(r'<chapter[^>]*>\s*<title>(.*?)</title>', text, re.DOTALL)
    if not title_match:
        title_match = re.search(r'<title>(.*?)</title>', text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Untitled"
    title = re.sub(r'<m>(.*?)</m>', r'$\1$', title)
    title = re.sub(r'<[^>]+>', '', title)

    # --- Remove non-content elements ---
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

    # --- Math ---
    text = re.sub(r'<m>(.*?)</m>', r'$\1$', text, flags=re.DOTALL)
    text = re.sub(r'<me>(.*?)</me>', r'\n$$\1$$\n', text, flags=re.DOTALL)
    text = re.sub(r'<men>(.*?)</men>', r'\n$$\1$$\n', text, flags=re.DOTALL)
    text = re.sub(r'<md>(.*?)</md>', lambda m: _math_block(m.group(1)), text, flags=re.DOTALL)
    text = re.sub(r'<mdn>(.*?)</mdn>', lambda m: _math_block(m.group(1)), text, flags=re.DOTALL)
    text = re.sub(r'<mrow>(.*?)</mrow>', r'$$\1$$', text, flags=re.DOTALL)

    # --- Structure ---
    text = re.sub(r'<section[^>]*>\s*<title>(.*?)</title>', r'\n## \1\n', text, flags=re.DOTALL)
    text = re.sub(r'</section>', '', text)
    text = re.sub(r'<subsection[^>]*>\s*<title>(.*?)</title>', r'\n### \1\n', text, flags=re.DOTALL)
    text = re.sub(r'</subsection>', '', text)
    text = re.sub(r'<subsubsection[^>]*>\s*<title>(.*?)</title>', r'\n#### \1\n', text, flags=re.DOTALL)
    text = re.sub(r'</subsubsection>', '', text)

    # Named environments with optional title
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
    # Structural wrappers
    for tag in ['statement', 'introduction', 'conclusion', 'task']:
        text = re.sub(rf'<{tag}[^>]*>', '', text)
        text = re.sub(rf'</{tag}>', '', text)

    # --- Inline ---
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

    # --- Cross-references: render as readable text ---
    text = re.sub(r'<xref\s+ref="([^"]*)"[^>]*/>', r'[\1]', text)

    # --- URLs ---
    text = re.sub(r'<url\s+href="([^"]*)"[^>]*/>', r'\1', text)
    text = re.sub(r'<url\s+href="([^"]*)"[^>]*>(.*?)</url>', r'[\2](\1)', text, flags=re.DOTALL)

    # --- Lists ---
    for tag in ['ol', 'ul', 'dl']:
        text = re.sub(rf'<{tag}[^>]*>', '', text)
        text = re.sub(rf'</{tag}>', '', text)
    text = re.sub(r'<li[^>]*>', '\n- ', text)
    text = re.sub(r'</li>', '', text)

    # --- Paragraphs ---
    text = re.sub(r'<p[^>]*>', '\n', text)
    text = re.sub(r'</p>', '\n', text)

    # --- Tables ---
    text = re.sub(r'<tabular[^>]*>', '\n', text)
    text = re.sub(r'</tabular>', '\n', text)
    text = re.sub(r'<row[^>]*>', '', text)
    text = re.sub(r'</row>', '\n', text)
    text = re.sub(r'<cell[^>]*>(.*?)</cell>', r'| \1 ', text, flags=re.DOTALL)
    text = re.sub(r'<col[^>]*/>', '', text)

    # --- Strip all remaining XML tags ---
    text = re.sub(r'<[^>]+>', '', text)

    # --- HTML entities ---
    for entity, char in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                         ('&apos;', "'"), ('&quot;', '"')]:
        text = text.replace(entity, char)

    # --- Fix orphaned cross-references ---
    text = re.sub(r'\bIn\s*,', 'In the previous section,', text)
    text = re.sub(r'\bfrom\s*,', 'from above,', text)

    return f"# {title}\n\n{text}"


def _math_block(inner):
    rows = re.findall(r'<mrow>(.*?)</mrow>', inner, re.DOTALL)
    if rows:
        return '\n$$\n' + '\n'.join(r.strip() for r in rows) + '\n$$\n'
    return f'\n$${inner.strip()}$$\n'


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
        stem = Path(ch_file).stem.replace("ch_", "").replace("C_", "")
        out_file = out_dir / f"{i:02d}_{stem}.md"
        out_file.write_text(md)
    print(f"  {name}: {len(chapter_files)} chapters -> {out_dir}")


# ---------------------------------------------------------------------------
# 5. Book of Proof (PDF only)
# ---------------------------------------------------------------------------
BOOK_OF_PROOF_CHAPTERS = {
    1: "Sets", 2: "Logic", 3: "Counting", 4: "Direct Proof",
    5: "Contrapositive Proof", 6: "Proof by Contradiction",
    7: "Proving Non-Conditional Statements", 8: "Proofs Involving Sets",
    9: "Disproof", 10: "Mathematical Induction", 11: "Relations",
    12: "Functions", 13: "Proofs in Calculus", 14: "Cardinality of Sets",
}


def clean_pdf_text(text, ch_title):
    """Clean pdftotext layout artifacts."""
    # Remove form feeds
    text = text.replace('\f', '\n')

    # Remove page headers/footers
    text = re.sub(
        rf'^\s*\d{{1,3}}\s+{re.escape(ch_title)}\s*$', '', text, flags=re.MULTILINE
    )
    text = re.sub(
        rf'^\s*{re.escape(ch_title)}\s+\d{{1,3}}\s*$', '', text, flags=re.MULTILINE
    )

    # Remove the big centered "CHAPTER N" and title
    text = re.sub(r'^\s*CHAPTER\s+\d+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(rf'^\s*{re.escape(ch_title)}\s*$', '', text, count=2, flags=re.MULTILINE)

    # Fix drop caps: pdftotext renders them as:
    #   "   t is time to prove some theorems. There are various strategies for doing"
    #   "I   this; we now examine the most straightforward approach"
    # Pattern: line1 starts with lowercase (rest of first word after drop cap),
    #          line2 starts with a single uppercase letter + spaces + lowercase continuation
    lines = text.split('\n')
    fixed = []
    i = 0
    while i < len(lines):
        s1 = lines[i].strip()
        if i + 1 < len(lines):
            s2 = lines[i + 1].strip()
            # Pattern: s1 starts with lowercase, s2 starts with single uppercase + spaces + lowercase
            m2 = re.match(r'^([A-Z])\s{2,}(\S.*)$', s2)
            if (s1 and s1[0].islower() and m2):
                capital = m2.group(1)
                rest_of_line2 = m2.group(2)
                # The first word of s1 is the continuation: "t is time..."
                # Prepend the capital: "It is time..."
                merged = capital + s1
                fixed.append(merged)
                # The rest of line2 continues normally
                fixed.append(rest_of_line2)
                i += 2
                continue
        # Also handle "A     ll of mathematics" on a single line
        m = re.match(r'^([A-Z])\s{3,}(\S.*)$', s1)
        if m and m.group(2)[0].islower():
            fixed.append(m.group(1) + m.group(2))
            i += 1
            continue
        fixed.append(lines[i])
        i += 1
    text = '\n'.join(fixed)

    # Fix encoding artifacts from PDF
    text = text.replace('\xa9', '{')  # ©
    text = text.replace('\xaa', '}')  # ª
    text = text.replace('\xa1', '(')  # ¡
    text = text.replace('\xa2', ')')  # ¢

    # Collapse internal multi-spaces to single (layout artifact)
    new_lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped:
            new_lines.append(re.sub(r'  +', ' ', stripped))
        else:
            new_lines.append('')
    text = '\n'.join(new_lines)

    return text


def extract_book_of_proof():
    out_dir = OUT / "book-of-proof"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = BASE / "book-of-proof.pdf"

    result = run(["pdftotext", "-layout", str(pdf), "-"])
    text = result.stdout

    pattern = re.compile(r'^\s*CHAPTER\s+(\d+)\s*$', re.MULTILINE)
    matches = list(pattern.finditer(text))

    if not matches:
        print("  Book of Proof: Could not find chapter headings")
        return

    written = 0
    for idx, match in enumerate(matches):
        ch_num = int(match.group(1))
        if ch_num not in BOOK_OF_PROOF_CHAPTERS:
            continue
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        content = text[start:end]
        title = BOOK_OF_PROOF_CHAPTERS[ch_num]
        content = clean_pdf_text(content, title)
        content = clean_whitespace(content)
        fname = sanitize(title)
        out_file = out_dir / f"{ch_num:02d}_{fname}.md"
        out_file.write_text(f"# Chapter {ch_num}: {title}\n\n{content}\n")
        written += 1
    print(f"  Book of Proof: {written} chapters -> {out_dir}")


def sanitize(s):
    s = s.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s]+', '-', s)
    return s[:60]


# ---------------------------------------------------------------------------
def main():
    print("Extracting chapters...\n")

    print("[1/5] An Infinitely Large Napkin (LaTeX)")
    extract_napkin()

    print("[2/5] Mathematical Reasoning: Writing and Proof (PreTeXt)")
    extract_pretext_book(
        "mathematical-reasoning",
        BASE / "src" / "sundstrom-textbook" / "source",
        ["C_1intro.ptx", "C_2logic.ptx", "C_3proofs.ptx",
         "C_4induction.ptx", "C_5settheory.ptx", "C_6functions.ptx",
         "C_7equivrelations.ptx", "C_8numbertheory.ptx", "C_9topicsinsets.ptx"],
    )

    print("[3/5] Exploring Combinatorial Mathematics (PreTeXt)")
    extract_pretext_book(
        "exploring-combinatorial-math",
        BASE / "src" / "ecm" / "source",
        ["ch_intro.ptx", "ch_basic-combinatorics.ptx",
         "ch_advanced-combinatorics.ptx", "ch_graphtheory.ptx",
         "ch_logic.ptx"],
    )

    print("[4/5] Discrete Mathematics: An Open Introduction (PreTeXt)")
    extract_pretext_book(
        "discrete-mathematics",
        BASE / "src" / "discrete-book" / "source",
        ["ch_intro.ptx", "ch_logic.ptx", "ch_graphtheory.ptx",
         "ch_counting.ptx", "ch_sequences.ptx", "ch_structures.ptx",
         "ch_additionalTopics.ptx"],
    )

    print("[5/5] Book of Proof (PDF)")
    extract_book_of_proof()

    print("\nDone! All chapters in:", OUT)
    for d in sorted(OUT.iterdir()):
        if d.is_dir():
            files = list(d.glob("*.md"))
            total = sum(f.stat().st_size for f in files)
            print(f"  {d.name}: {len(files)} files, {total // 1024}KB total")


if __name__ == "__main__":
    main()
