import re
from newcitechecker import CitationChecker, CitationValidationException
from typing import Optional

def fix_citation_format(citation: str) -> str:
    orig = citation.strip()

    # Try one clean regex first:
    m = re.match(
        r'^(?P<case>.+?)\s+'              # case name (greedy up to volume)
        r'(?P<vol>\d+)\s+'               # volume
        r'(?P<rep>[A-Za-z\.\']+)\s+'     # reporter
        r'(?P<page>\d+)\s*'              # page
        r'(?P<court>.+?)?\s*'            # court name (optional)
        r'(?P<year>\d{4})\.?$',          # year
        orig
    )
    if m:
        case   = m.group('case').strip()
        vol    = m.group('vol')
        rep    = m.group('rep')
        page   = m.group('page')
        court  = (m.group('court') or '').strip()
        year   = m.group('year')
        # rebuild into exactly “Case, Volume Reporter Page (Court Year)”
        inside = f"{court} {year}".strip()
        return f"{case}, {vol} {rep} {page} ({inside})"

    # fallback: if nothing matched, just hand back the original string
    return orig


class CitationFixError(Exception):
    """Raised when we can’t automatically fix a citation."""
    pass


def auto_fix_citation(
    citation: str,
    provided_quote: Optional[str] = None,
    pincite: Optional[str] = None
) -> str:
    """
    Validate with CitationChecker; if it fails, attempt to fix.
    If the fix works, return the new citation. Otherwise raise CitationFixError.
    """
    checker = CitationChecker()

    # 1) Try validating the original
    try:
        checker.validate_full_citation(citation, provided_quote, pincite)
        return citation
    except CitationValidationException:
        pass

    # 2) Generate a “fixed” version
    fixed = fix_citation_format(citation)
    # if we couldn’t actually change it, give up now
    if fixed == citation:
    # didn’t change anything, so no point re-validating
        raise CitationFixError(f"No changes made; still invalid: {citation}")

    # 3) Re-validate
    try:
        checker.validate_full_citation(fixed, provided_quote, pincite)
        return fixed
    except CitationValidationException as e:
        # If it still doesn’t parse, give up
        raise CitationFixError(
            f"Unable to automatically fix citation.\n"
            f"Original errors: {e}\n"
            f"Tried fix: '{fixed}'"
        )