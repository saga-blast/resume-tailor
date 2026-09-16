import io
import re
from dataclasses import dataclass

from pypdf import PdfReader

_DOCUMENTCLASS_RE = re.compile(r"\\documentclass(\[[^\]]*\])?\{[^}]*\}\s*\n")
_END_DOCUMENT_RE = re.compile(r"\\end\{document\}")
_XCOLOR_RE = re.compile(r"\\usepackage(\[[^\]]*\])?\{xcolor\}")
_COLOR_RE = re.compile(r"\\usepackage(\[[^\]]*\])?\{color\}")
_SECTION_RE = re.compile(r"\\section\*?\{([^}]*)\}")
_UNESCAPED_SPECIAL_RE = re.compile(r"(?<!\\)([%&#_])")
_BEGIN_DOCUMENT_RE = re.compile(r"\\begin\{document\}")
_IFFALSE_RE = re.compile(r"\\iffalse\b")
_FI_RE = re.compile(r"\\fi\b")


def _body_start(tex_source: str) -> int:
    """Custom macro definitions in the preamble (e.g. \\newcommand{\\resumeSubItem}[1]
    {\\resumeItem{#1}...}) can themselves contain what looks like a bullet
    macro call -- extraction must only look at the actual document body."""
    match = _BEGIN_DOCUMENT_RE.search(tex_source)
    return match.end() if match else 0


def _find_disabled_spans(tex_source: str) -> list[tuple[int, int]]:
    """(start, end) spans of \\iffalse ... \\fi blocks -- TeX never actually
    compiles this content, so bullets found there must be ignored."""
    spans = []
    search_from = 0
    while True:
        start_match = _IFFALSE_RE.search(tex_source, search_from)
        if not start_match:
            break
        end_match = _FI_RE.search(tex_source, start_match.end())
        if not end_match:
            spans.append((start_match.start(), len(tex_source)))
            break
        spans.append((start_match.start(), end_match.end()))
        search_from = end_match.end()
    return spans


def _is_commented(tex_source: str, position: int) -> bool:
    """True if `position` falls after an unescaped % earlier on the same
    line -- LaTeX comments out everything from there to end of line."""
    line_start = tex_source.rfind("\n", 0, position) + 1
    return bool(re.search(r"(?<!\\)%", tex_source[line_start:position]))


def _is_live(tex_source: str, position: int, disabled_spans: list[tuple[int, int]]) -> bool:
    """False if `position` is inside a %-comment or an \\iffalse...\\fi block --
    i.e. text that will never actually appear in the compiled document."""
    if _is_commented(tex_source, position):
        return False
    return not any(start <= position < end for start, end in disabled_spans)


def has_highlight_macro(tex_source: str) -> bool:
    return "\\newcommand{\\hl}" in tex_source or "\\newcommand{\\highlight}" in tex_source


def ensure_highlight_macro(tex_source: str) -> str:
    """Deterministic, not LLM-dependent: an LLM asked to "remember to add a
    highlight macro" will forget sometimes. Scanning for it and injecting a
    fallback in code guarantees \\hl{...} always resolves to something.

    Adapts to what's already loaded rather than blindly adding \\usepackage{xcolor}:
    loading xcolor when the template already has the base `color` package (a
    real resume hit this) raises a LaTeX "Option clash" error, and the base
    `color` package doesn't support xcolor's tint-mixing syntax (yellow!40).
    """
    if has_highlight_macro(tex_source):
        return tex_source

    if _XCOLOR_RE.search(tex_source):
        macro_def = "\\newcommand{\\hl}[1]{\\colorbox{yellow!40}{#1}}\n"
    elif _COLOR_RE.search(tex_source):
        macro_def = "\\newcommand{\\hl}[1]{\\colorbox{yellow}{#1}}\n"
    else:
        macro_def = "\\usepackage{xcolor}\n\\newcommand{\\hl}[1]{\\colorbox{yellow!40}{#1}}\n"

    match = _DOCUMENTCLASS_RE.search(tex_source)
    if match:
        insert_at = match.end()
        return tex_source[:insert_at] + macro_def + tex_source[insert_at:]
    return macro_def + tex_source


def highlight_phrase(text: str, phrase: str) -> str:
    """Wrap every occurrence of `phrase` (case-insensitive, casing preserved) in
    \\hl{...}, skipping spots already wrapped by a longer phrase's highlight."""
    pattern = re.compile(re.escape(phrase), re.IGNORECASE)

    def replacer(match: re.Match) -> str:
        preceding = text[max(0, match.start() - 4) : match.start()]
        if preceding.endswith("\\hl{"):
            return match.group(0)
        return f"\\hl{{{match.group(0)}}}"

    return pattern.sub(replacer, text)


def append_additional_skills_section(tex_source: str, new_skills: list[str]) -> str:
    """Adds confirmed-but-missing skills as their own section rather than trying
    to splice into whatever custom LaTeX macros a given template's existing
    skills section happens to use -- works for any template, no matter how it's
    structured, at the cost of not blending into the original section's exact
    formatting."""
    highlighted = ", ".join(f"\\hl{{{s}}}" for s in new_skills)
    section = f"\n\\section*{{Additional Skills}}\n{highlighted}\n\n"
    match = _END_DOCUMENT_RE.search(tex_source)
    if match:
        insert_at = match.start()
        return tex_source[:insert_at] + section + tex_source[insert_at:]
    return tex_source + section


def resolve_highlight_term(
    requirement_text: str, matched_skill_name: str | None, profile_skill_names: list[str]
) -> str:
    """`matched_skill_name` from the matching step is a human-readable
    justification ("Java experience listed in core stack"), not a literal
    keyword -- useless for exact-substring highlighting. Cross-reference
    against the user's actual profile skill names instead, which are
    guaranteed to exist verbatim in the resume since they were parsed from it;
    prefer the longest match as the more specific/likely-correct one."""
    haystack = f"{requirement_text} {matched_skill_name or ''}".lower()
    candidates = [name for name in profile_skill_names if name.lower() in haystack]
    if candidates:
        return max(candidates, key=len)
    return requirement_text


def generate_tailored_resume(
    base_tex: str, matched_terms: list[str], confirmed_new_skills: list[str]
) -> tuple[str, list[str], list[str]]:
    """Deterministically highlights every matched term that already appears in
    the resume, and appends any confirmed-via-Q&A skill that doesn't. No LLM
    call needed -- by the time this runs, matching has already decided exactly
    what's relevant; this step is plain text search/insert, not judgment.

    Returns (updated_tex, highlighted_terms, added_skills).
    """
    tex = ensure_highlight_macro(base_tex)

    highlighted: list[str] = []
    for term in sorted({t for t in matched_terms if t.strip()}, key=len, reverse=True):
        if term.lower() in tex.lower():
            updated = highlight_phrase(tex, term)
            if updated != tex:
                highlighted.append(term)
            tex = updated

    new_skills = sorted({s for s in confirmed_new_skills if s.strip() and s.lower() not in base_tex.lower()})
    if new_skills:
        tex = append_additional_skills_section(tex, new_skills)

    return tex, highlighted, new_skills


# --- Content rewriting: extract individual bullets/summary as plain text,
# send only those (small, cheap) to the LLM, splice results back by exact
# character offset -- never asking the model to reproduce LaTeX structure it
# could get wrong. ---


@dataclass
class TextBlock:
    outer_start: int  # start of the whole macro call, e.g. "\resumeItem{...}" -- for full removal
    outer_end: int
    inner_start: int  # start/end of just the plain-text content -- for text replacement
    inner_end: int
    text: str


def _find_matching_brace(text: str, open_idx: int) -> int:
    """`text[open_idx]` must be '{'. Returns the index of its matching '}',
    correctly handling nested braces (a naive non-greedy regex can't)."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def extract_bullets(tex_source: str, macro_name: str = "resumeItem") -> list[TextBlock]:
    """Finds every \\resumeItem{...} call (the bullet macro used by this
    template family -- one of the most common LaTeX resume template lines,
    derived from Jake's/sb2nov's templates), unwrapping a single
    \\normalsize{...}/\\small{...} wrapper if present to get the plain text.

    Templates that don't use this macro simply yield no bullets, and the
    rewrite step skips gracefully rather than guessing at unfamiliar structure.
    """
    blocks = []
    body_start = _body_start(tex_source)
    disabled_spans = _find_disabled_spans(tex_source)
    pattern = re.compile(re.escape("\\" + macro_name) + r"\{")
    for m in pattern.finditer(tex_source, body_start):
        if not _is_live(tex_source, m.start(), disabled_spans):
            continue  # commented-out or \iffalse-disabled -- never actually compiles
        open_idx = m.end() - 1
        close_idx = _find_matching_brace(tex_source, open_idx)
        if close_idx == -1:
            continue
        inner = tex_source[open_idx + 1 : close_idx]
        inner_start, inner_end, text = open_idx + 1, close_idx, inner
        wrapper = re.match(r"^\\(normalsize|small|footnotesize)\{", inner)
        if wrapper:
            wrap_open = wrapper.end() - 1
            wrap_close = _find_matching_brace(inner, wrap_open)
            if wrap_close == len(inner) - 1:
                inner_start = open_idx + 1 + wrap_open + 1
                inner_end = open_idx + 1 + wrap_close
                text = inner[wrap_open + 1 : wrap_close]
        blocks.append(
            TextBlock(outer_start=m.start(), outer_end=close_idx + 1, inner_start=inner_start, inner_end=inner_end, text=text)
        )
    return blocks


def extract_summary(tex_source: str) -> TextBlock | None:
    """Finds a \\section{...} whose heading looks like a summary/objective and
    extracts the plain text inside its \\small{...}/\\normalsize{...} wrapper,
    if any. Returns None if no such section/wrapper is found -- summary
    rewriting is skipped rather than guessed at."""
    disabled_spans = _find_disabled_spans(tex_source)
    matches = list(_SECTION_RE.finditer(tex_source, _body_start(tex_source)))
    for i, m in enumerate(matches):
        heading = m.group(1).lower()
        if "summary" not in heading and "objective" not in heading:
            continue
        if not _is_live(tex_source, m.start(), disabled_spans):
            continue
        content_start = m.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(tex_source)
        section_text = tex_source[content_start:content_end]
        wrapper = re.search(r"\\(small|normalsize|footnotesize)\{", section_text)
        if not wrapper:
            return None
        open_idx = wrapper.end() - 1
        close_idx = _find_matching_brace(section_text, open_idx)
        if close_idx == -1:
            return None
        return TextBlock(
            outer_start=content_start + open_idx,
            outer_end=content_start + close_idx + 1,
            inner_start=content_start + open_idx + 1,
            inner_end=content_start + close_idx,
            text=section_text[open_idx + 1 : close_idx],
        )
    return None


def escape_latex_specials(text: str) -> str:
    """Defensive safety net regardless of whether the LLM remembers to do
    this itself: a bare %, &, #, or _ in body text breaks LaTeX compilation,
    and an embedded newline risks leaking a %-commented line back to life or
    creating an unwanted paragraph break inside a single-argument macro."""
    text = text.replace("\r\n", " ").replace("\n", " ")
    return _UNESCAPED_SPECIAL_RE.sub(r"\\\1", text)


def apply_text_rewrites(tex_source: str, rewrites: dict[int, str], blocks: list[TextBlock]) -> str:
    """Replaces each block's inner text with its rewrite, keyed by the block's
    index in `blocks`. Applies from the end of the document backwards so each
    replacement's offset stays valid regardless of how earlier ones change the
    string's length."""
    ordered = sorted(rewrites.items(), key=lambda kv: blocks[kv[0]].inner_start, reverse=True)
    result = tex_source
    for index, new_text in ordered:
        block = blocks[index]
        safe_text = escape_latex_specials(new_text)
        result = result[: block.inner_start] + safe_text + result[block.inner_end :]
    return result


_ITEMIZE_START_RE = re.compile(r"\\(resumeItemListStart|begin\{itemize\})")


def filter_safe_trim_indices(tex_source: str, blocks: list[TextBlock], indices: list[int]) -> list[int]:
    """The trim LLM is told "leave at least one bullet per entry", but it has
    no way to actually check that -- it only sees a flat list of bullet text,
    not which itemize block each one belongs to. Removing every bullet from
    one \\resumeItemListStart...\\resumeItemListEnd (or plain itemize) leaves
    an empty environment, which is a hard LaTeX error ("perhaps a missing
    \\item"), seen in practice. This groups bullets by their enclosing itemize
    block and drops any requested removal that would empty one out entirely,
    regardless of what the LLM suggested -- the same "don't trust the model
    alone" pattern used for preference-memory and highlight-macro handling.
    """
    starts = [m.start() for m in _ITEMIZE_START_RE.finditer(tex_source)]

    def group_of(block: TextBlock) -> int:
        group = -1
        for i, s in enumerate(starts):
            if s <= block.outer_start:
                group = i
            else:
                break
        return group

    group_ids = [group_of(b) for b in blocks]
    group_sizes: dict[int, int] = {}
    for g in group_ids:
        group_sizes[g] = group_sizes.get(g, 0) + 1

    remaining = dict(group_sizes)
    safe: list[int] = []
    for i in sorted(set(indices)):
        if not (0 <= i < len(blocks)):
            continue
        g = group_ids[i]
        if remaining[g] > 1:
            safe.append(i)
            remaining[g] -= 1
    return safe


def remove_bullets(tex_source: str, blocks: list[TextBlock], indices: list[int]) -> str:
    """Deletes the FULL macro call (not just the text) for each given bullet
    index, so trimming for length doesn't leave an empty \\resumeItem{}."""
    result = tex_source
    for index in sorted(set(indices), key=lambda i: blocks[i].outer_start, reverse=True):
        block = blocks[index]
        end = block.outer_end
        while end < len(result) and result[end] in "\n \t":
            end += 1
        result = result[: block.outer_start] + result[end:]
    return result


def count_pdf_pages(pdf_bytes: bytes) -> int:
    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
