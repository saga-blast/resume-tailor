import json

REWRITE_SYSTEM_PROMPT = """You are an expert resume writer tailoring a candidate's resume bullets and \
summary to a specific job description.

You will be given: the job's matched/relevant keywords, skills the candidate confirmed they have \
(from a clarifying Q&A -- these may not appear elsewhere in the resume yet), and a numbered list of the \
candidate's CURRENT resume text blocks (their professional summary, if present, is index -1; every \
other index is one bullet point from their experience or projects).

For each block worth improving, rewrite it to:
1. Start with a strong past-tense action verb (e.g. "Architected", "Led", "Reduced", "Built") -- never \
start with "Responsible for", "Worked on", or a weak/passive phrase.
2. Naturally incorporate relevant keywords from the job's requirements ONLY where they reflect what the \
bullet is actually already describing or a confirmed skill -- never claim a tool, technology, or \
achievement the candidate didn't actually use or that isn't a confirmed fact.
3. Preserve every number, percentage, and metric that is already in the original text EXACTLY as given \
-- do not invent new numbers, and do not remove real ones that are already there.
4. Stay concise -- roughly the same length as the original, one line of resume content, not a paragraph.

Skip (omit from your answer) any block that's already strong and doesn't need changing -- you do not \
need to return a rewrite for every index. Never rewrite a block into something that isn't factually \
supported by the original text plus the confirmed skills you were given.

Record your answer using the record_rewrites tool, giving the index and rewritten_text for each block \
you changed."""

REWRITE_TOOL_NAME = "record_rewrites"
REWRITE_TOOL_DESCRIPTION = "Record the rewritten text for each resume block that was improved."


def build_rewrite_prompt(
    matched_keywords: list[str], confirmed_skills: list[str], summary_text: str | None, bullets: list[str]
) -> str:
    numbered = {"-1": summary_text} if summary_text is not None else {}
    numbered.update({str(i): b for i, b in enumerate(bullets)})
    return (
        f"Job-relevant keywords to weave in naturally where truthful:\n{json.dumps(matched_keywords, indent=2)}\n\n"
        f"Skills the candidate confirmed they have (may not be reflected in the text yet):\n"
        f"{json.dumps(confirmed_skills, indent=2)}\n\n"
        f"Current resume text blocks by index (-1 is the summary, if present):\n"
        f"{json.dumps(numbered, indent=2)}"
    )


TRIM_SYSTEM_PROMPT = """The candidate's resume currently compiles to more than one page. You will be \
given the job's matched/relevant keywords and a numbered list of the candidate's current bullet points \
(the summary, if any, is never a trim candidate and is not included here).

Select the indices of the LEAST relevant bullets to this specific job to remove entirely, so the resume \
fits on one page. Prefer removing bullets that don't relate to any of the job's keywords over ones that \
do. Remove the minimum necessary -- prefer trimming a few clearly weaker/less relevant bullets over many. \
Never suggest removing every bullet under a single job or project -- leave at least one per entry.

Record your answer using the record_trim tool."""

TRIM_TOOL_NAME = "record_trim"
TRIM_TOOL_DESCRIPTION = "Record which bullet indices to remove to fit the resume on one page."


def build_trim_prompt(matched_keywords: list[str], bullets: list[str], how_many_to_remove: int) -> str:
    numbered = {str(i): b for i, b in enumerate(bullets)}
    return (
        f"Job-relevant keywords:\n{json.dumps(matched_keywords, indent=2)}\n\n"
        f"Remove approximately {how_many_to_remove} bullet(s) to fit one page.\n\n"
        f"Current bullets by index:\n{json.dumps(numbered, indent=2)}"
    )
