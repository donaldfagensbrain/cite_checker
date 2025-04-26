import re
import difflib
from typing import Any, Dict, Optional, Tuple, Literal, List
from dataclasses import dataclass
from constants import (
    MONTH_ABBREVIATIONS,
    JOURNAL_ABBREVIATIONS,
    ALLOWED_REPORTERS,
    COURT_REPORTER_MAPPING,
    STATE_COURT_REPORTER_MAPPING,
    VALID_CITATION_SIGNALS,
    CITATION_SIGNALS_ORDERED,
    WORD_ABBREVIATIONS)

from regex import PATTERNS, VALIDATORS


@dataclass(frozen=True)
class ShortKey:
    kind: str
    volume: str
    reporter: str
    pin: Optional[str]
    parallels: Tuple[Tuple[str, str, str], ...]


@dataclass
class CitationError:
    message: str
    start: int          # character offset of the citation in the doc
    end: int            # character offset end
    field: Optional[str]  # e.g. 'year', 'parentheses', etc.


class CitationValidationException(Exception):
    def __init__(self, errors: List[CitationError]):
        # join just the human‐readable messages for the .args
        super().__init__("\n".join(err.message for err in errors))
        self.errors = errors


# Pre-compile: match full month names only inside a parenthetical ending in a 4-digit year
_month_pattern = re.compile(
    r'\b(' + '|'.join(MONTH_ABBREVIATIONS.keys()) + r')'
    r'(?=[^)]*\b\d{4}\))'
)

def abbreviate_months_in_citation(text: str) -> str:
    """
    Replace full month names with their §4-600 abbreviations,
    but only when they appear in a parenthesis that ends with a 4-digit year.
    """
    return _month_pattern.sub(lambda m: MONTH_ABBREVIATIONS[m.group(1)], text)


# Pre-compile: match journal names only when followed by volume/reporter/page
_journal_pattern = re.compile(
    r'\b(' + '|'.join(map(re.escape, JOURNAL_ABBREVIATIONS.keys())) + r')'
    r'(?=\s+\d+\s+[A-Za-z\.]+\s+\d+)',
    re.IGNORECASE
)

def abbreviate_journals_in_citation(text: str) -> str:
    """
    Replace any of the §4-700 journal full names with their
    abbreviations—but only when they appear in a citation.
    """
    def _repl(m):
        # normalize to title case so it always keys correctly
        key = m.group(1).title()
        return JOURNAL_ABBREVIATIONS[key]
    return _journal_pattern.sub(_repl, text)


def abbreviate_case_name(name: str) -> str:
    """
    Replace party-name words with their §4-100 abbreviations.
    Only matches whole words (e.g. “Justice” → “Just.”).
    """
    def _replace(m: re.Match) -> str:
        w = m.group(0)
        return WORD_ABBREVIATIONS.get(w, w)
    return re.sub(r'\b[A-Za-z][A-Za-z\'\.]*\b', _replace, name)

def omit_words_in_case_name(name: str) -> str:
    """
    Apply §4-300 omissions to a case name.
    """
    # 1) Drop leading “The ”
    name = re.sub(r'^(The)\s+', '', name, flags=re.IGNORECASE)
    # 2) Keep only before first comma
    name = name.split(',', 1)[0].strip()
    # 3) On each side of “ v. ”, keep only first party
    if ' v. ' in name:
        left, right = name.split(' v. ', 1)
        right = right.split(',', 1)[0]
        name = f"{left} v. {right}"
    # 4) “In re” → keep only up to comma
    if name.lower().startswith('in re'):
        name = name.split(',', 1)[0]
    # 5) Collapse multiple “ ex rel.” to one, then normalize “United States of America”
    #parts = re.split(r'\s+ex rel\.', name, flags=re.IGNORECASE)
    #if len(parts) > 1:
        #name = parts[0] + ' ex rel.'
        # collapse "United States of America" → "United States"
        #name = re.sub(
            #r'United States of America',
            #'United States',
            #name,
           # flags=re.IGNORECASE
        #).strip()
        #return name
    # 6) Drop Trustee/Executor/Admin descriptors
    name = re.sub(r'\b(Trustee|Executor|Administrator|Administratrix)\b.*', '', name, flags=re.IGNORECASE).strip()
    # 7) Drop “State of ”
    name = re.sub(r'\bState of\s+', 'State ', name, flags=re.IGNORECASE)
    # 8) Drop “City of ” not at start
    name = re.sub(r'(?<!^)\bCity of\s+', '', name, flags=re.IGNORECASE)
    # 9) Drop other locational phrases
    name = re.sub(r'\b(of|County|Township|Village|District)\s+[A-Za-z ]+', '', name, flags=re.IGNORECASE)
    # 10) “United States of America” → “United States”
    name = re.sub(r'United States of America', 'United States', name, flags=re.IGNORECASE)
    # 11) Keep only last name for individuals
    def _last(p: str) -> str:
        ps = p.split()
        return ps[-1] if len(ps) > 1 else p
    if ' v. ' in name:
        a, b = name.split(' v. ')
        name = f"{_last(a)} v. {_last(b)}"
    else:
        name = _last(name)
    # 12) If Co./Corp. present, drop Inc./Ltd./etc.
    if re.search(r'\b(Co|Corp|Ass\'n)\b', name):
        name = re.sub(r'\b(Inc|Ltd|N\.A\.|F\.S\.B\.),?\s*', '', name)
    return name.strip()

def map_federal_court_level(court_str: str) -> Optional[str]:
    if not court_str:
        return None
    cs = court_str.lower()
    if "supreme" in cs:
        return "Supreme Court"
    if "ct. cl." in cs:
        return "Court of Federal Claims"
    if "t.c." in cs:
        return "Tax Court"
    if "cir" in cs:
        return "Court of Appeals"
    if "f.r.d." in cs or "district" in cs:
        return "District Courts"
    if "m.j." in cs:
        return "Military Service"
    if "vet. app." in cs:
        return "Veterans' Appeals"
    return "Unknown"

def map_state_court_level(citation_components: Dict[str, Any]) -> Optional[str]:
    rep = citation_components.get("reporter", "")
    if rep.startswith("Cal. App."):
        return "California Appellate"
    if rep.startswith("Cal. Rptr."):
        return "California"
    if rep in {"N.Y.2d", "N.Y.3d"}:
        return "New York Appellate"
    if rep in {"N.Y.", "N.Y.S."}:
        return "New York"
    for st, reps in STATE_COURT_REPORTER_MAPPING.items():
        if rep in reps:
            return st
    return None

def validate_reporter_for_court(citation_components: Dict[str, Any]) -> bool:
    court_str = citation_components.get("court", "")
    reporter  = citation_components.get("reporter")
    fed_level = map_federal_court_level(court_str)
    if fed_level and fed_level != "Unknown":
        allowed = COURT_REPORTER_MAPPING.get(fed_level)
        if allowed and reporter not in allowed:
            raise ValueError(f"Reporter '{reporter}' not valid for federal {fed_level}. Allowed: {allowed}")
        return True
    st_level = map_state_court_level(citation_components)
    if st_level:
        allowed = STATE_COURT_REPORTER_MAPPING.get(st_level)
        if allowed and reporter not in allowed:
            raise ValueError(f"Reporter '{reporter}' not valid for {st_level}. Allowed: {allowed}")
    return True

# ----- Main CitationChecker Class -----
class CitationChecker:
    def __init__(self):
        """Store parsed full‐form citations as {volume_reporter_page: components}."""
        self.full_citations: Dict[str, Dict[str, Any]] = {}
        self.last_short_key = None  

    def validate(self, kind: str, citation: str) -> bool:
        """
        Dispatch to the appropriate regex‐based validator from VALIDATORS.
        Raises ValueError if no match.
        """
        validator = VALIDATORS.get(kind)
        if validator is None:
            raise ValueError(f"No validator found for kind '{kind}'")

        # If it's a list of patterns, try each one
        if isinstance(validator, list):
            for pat in validator:
                if pat.match(citation):
                    return True
        else:
            if validator.match(citation):
                return True

        raise ValueError(f"Invalid {kind} citation format")

    def process_document(self, text: str) -> Dict[str, Dict[str, Any]]:
        """
        Scan `text` for full‐form citations using CITATION_PATTERN,
        parse them into components, and store in self.full_citations.
        """
        self.full_citations.clear()

        # split on semicolons so we catch multiple citations in one string
        for segment in re.split(r';\s*', text):
            for m in PATTERNS['citation'].finditer(segment):
                comps = m.groupdict()
                key = f"{comps['volume']}_{comps['reporter']}_{comps['page']}"
                self.full_citations[key] = comps

        return self.full_citations

    @staticmethod
    def normalize_abbrev_spacing_and_periods(citation: str) -> str:
        """
        §4-810 & §4-820:
        1) Collapse spaces in single‐letter sequences: "D. C." → "D.C."
        2) Ensure multi‐letter words end in a period, except:
           • ALL‐CAP initialisms (EEOC)
           • apostrophe‐contraction forms (Eng’g)
        """
        # 1) D. C. → D.C.
        citation = re.sub(r'\b([A-Z])\.\s+([A-Z])\.', r'\1.\2.', citation)

        # 2) Add trailing period to 2+ letter words (unless ALL‐CAP or contains apostrophe)
        def _add_dot(m: re.Match) -> str:
            term = m.group(1)
            if term.isupper() and len(term) > 1:
                return term
            if "’" in term:
                return term
            return term + "."

        citation = re.sub(
            r'(?<![\.\"’])\b([A-Za-z]{2,})\b(?!\.)',
            _add_dot,
            citation
        )
        return citation
    

    def format_quote(self, quote: str, citation_str: str) -> str:
        """
        Apply §6-100 Principles 1–4:
        - If <50 words, wrap in “…” and normalize embedded quotes.
        - If ≥50 words or special emphasis requested, indent as a block.
        - Always follow immediately with citation_str.
        """
        words = quote.split()
        # normalize quote marks: strip any existing curly quotes
        quote = quote.replace('“', '"').replace('”', '"')
        # convert any straight double‐quotes inside to straight single‐quotes
        quote = quote.replace('"', "'")
        # Principle 4: internal omissions shown as spaced ellipses
        quote = re.sub(r'\.{3,}', ' . . . ', quote)

        if len(words) < 50:
            # inline: if it starts lowercase, bracket‐capitalize that first letter
            if quote and quote[0].islower():
                quote = f"[{quote[0].upper()}]{quote[1:]}"
            return f'“{quote}” {citation_str}'
        else:
            # block quote: leave text intact and indent each line with a single space
            indented = "\n".join(" " + line for line in quote.splitlines())
            return f"{indented}\n{citation_str}"
    
    def _apply_signal_formatting(self, text: str, style: str = "italic") -> str:
        """
        § 6-300 — italicize (or underline) introductory signals *only* when
        they open a citation clause or citation sentence.
        """
        opener = r'(^|[.;]\s+)'  # start of string OR just after . or ;
        tag = (lambda x: f"<i>{x}</i>") if style == "italic" else (lambda x: f"__{x}__")
        def wrap(m: re.Match) -> str:
            prefix, signal = m.groups()
            # the trailing space is consumed by the regex \s, so we add it back
            return prefix + tag(signal) + " "

        for sig in CITATION_SIGNALS_ORDERED:
            pattern = rf"{opener}({re.escape(sig)})\s"
            text = re.sub(pattern, wrap, text, flags=re.IGNORECASE)
        return text

    def format_citation(self, comps: Dict[str, Any], style: str = "italic") -> str:
        """
        Assemble a full citation string from parsed components and
        wrap the following elements in italics (or underlining if you
        prefer):
          - case_name
          - book titles (if you ever parse them)
          - journal‐article titles
          - introductory signals (See, cf., etc.) when used in citation sentences
          - explanatory history phrases (e.g. “aff’d, 5 F.3d 123 (2d Cir. 1990)”)
          - attribution phrases (e.g. “as quoted in”)
          - cross-refs: id., supra, infra
        """

        # 1) build the raw string:
        s = f"{comps['case_name']} {comps['volume']} {comps['reporter']} {comps['page']}"
        if comps.get('pinpoint'):
            s += f", {comps['pinpoint']}"
        s += f" ({comps['court']} {comps['year']})"

        # 2) wrap comps['case_name'] in <i>…</i> (or __…__ if underlining)
        if style == "italic":
            s = s.replace(comps['case_name'], f"<i>{comps['case_name']}</i>")
        else:  # underline
            s = s.replace(comps['case_name'], f"__{comps['case_name']}__")

        # 3) likewise for id./supra/infra:
        for x in ("id.", "supra", "infra"):
            pattern = rf"\b{x}\b"
            replacement = f"<i>{x}</i>" if style == "italic" else f"__{x}__"
            s = re.sub(pattern, replacement, s)

        for phrase in ("aff’d", "overruled by", "as quoted in"):
            pattern = rf"(?i)\b{re.escape(phrase)}\b"
            def repl(m):
                txt = m.group(0)
                return f"<i>{txt}</i>" if style == "italic" else f"__{txt}__"
            s = re.sub(pattern, repl, s)

        return self._apply_signal_formatting(s, style)


    def format_short_citation(self,
                              full_comps: Dict[str, Any],
                              kind: Literal['case','statute','reg','book','article']) -> str:
        """
        §6-500 Short‐form based on the kind of source,
        with automatic Id./supra when in same discussion.
        """
        # Build a ShortKey for this work + pinpoint
        pin = full_comps.get('pinpoint') or full_comps.get('page') or full_comps.get('section')
        parallels = tuple(sorted(
            [(p['volume'], p['reporter'], p['page'])
             for p in full_comps.get('parallel', [])]
        ))
        key = ShortKey(
            kind=kind,
            volume=full_comps.get('volume'),
            reporter=full_comps.get('reporter') or full_comps.get('code') or full_comps.get('title'),
            pin=pin,
            parallels=parallels
        )

        # 1) If same work as last time → Id. at pin
        if self.last_short_key == key:
            if pin:
                return f"Id. at {pin}."
            else:
                return "Id."

        # 2) Otherwise build the explicit short form
        if kind == 'case':
            name = full_comps['case_name'].split()[0]  # first party
            vol, rep, page = full_comps['volume'], full_comps['reporter'], full_comps['page']
            short = f"{name}, {vol} {rep} at {page}"
            parallels = full_comps.get('parallel')
            if parallels:
                extra_parts = [
                    f"{p['volume']} {p['reporter']} at {p['page']}"
                    for p in parallels
                ]
                short += ', ' + ', '.join(extra_parts)

        elif kind == 'statute':
            code    = full_comps.get('code', '').strip()
            section = full_comps['section']
            if code:
                short = f"{code} § {section}"
            else:
                short = f"§ {section}"

        elif kind == 'reg':
            title   = full_comps.get('title')
            section = full_comps['section']
            if title:
                short = f"{title} C.F.R. § {section}"
            else:
                short = f"§ {section}"

        elif kind == 'book':
            author   = full_comps.get('author')
            pinpoint = full_comps.get('pinpoint')
            if author:
                short = f"{author}, supra"
                if pinpoint:
                    short += f" at {pinpoint}"
            else:
                short = "Id."

        elif kind == 'article':
            author   = full_comps.get('author')
            pinpoint = full_comps.get('pinpoint') or full_comps.get('page')
            if author:
                short = f"{author}, supra"
                if pinpoint:
                    short += f" at {pinpoint}"
            else:
                short = "Id."

        else:
            raise ValueError("Unsupported short form kind")

        # 3) Save this key for the next call
        self.last_short_key = key
        # ensure trailing period on every short‐form
        if not short.endswith('.'):
            short += '.'
        return short

    def _collect_format_errors(self, citation: str) -> List[CitationError]:
        """
        Gather simple formatting violations:
        - missing parentheses/comma
        - missing volume/reporter/page
        - malformed parenthetical contents
        """
        errors: List[CitationError] = []
        # 1) Parentheses
        if '(' not in citation or ')' not in citation:
            errors.append(
                CitationError(
                    message="Missing parentheses around court and year (…)",
                    start=0,
                    end=len(citation),
                    field="parentheses"
                )
            )

        # 2) Comma before parenthetical
        prefix = citation.split('(', 1)[0]
        if ',' not in prefix:
            errors.append(
                CitationError(
                    message="Missing comma before the parenthetical containing court and year.",
                    start=0,
                    end=len(prefix),
                    field="comma"
                )
            )

        # 3) Volume/Reporter/Page
        if not re.search(r"\d+\s+[A-Za-z\.']+\s+\d+", prefix):
            errors.append(
                CitationError(
                    message="Missing volume, reporter, or page (e.g., ‘123 U.S. 456’).",
                    start=0,
                    end=len(prefix),
                    field="volume_reporter_page"
                )
            )

        # 4) Parenthetical contents
        if '(' in citation and ')' in citation:
            inner = citation[citation.find('(')+1 : citation.rfind(')')]
            parts = inner.rsplit(' ', 1)
            if len(parts) != 2:
                errors.append(
                    CitationError(
                        message="Parenthetical must be of the form ‘(Court Year)’.",
                        start=citation.find('('),
                        end=citation.rfind(')')+1,
                        field="parenthetical_contents"
                    )
                )
            else:
                court_part, year_part = parts

                # 5) Year format
                if not (year_part.isdigit() and len(year_part) == 4):
                    errors.append(
                        CitationError(
                            message=f"Invalid year ‘{year_part}’; expected four digits.",
                            start=citation.rfind(' ')+1,
                            end=citation.rfind(')'),
                            field="year"
                        )
                    )

                # 6) Court name
                if not court_part.strip():
                    errors.append(
                        CitationError(
                            message="Missing court name before the year inside parentheses.",
                            start=citation.find('(')+1,
                            end=citation.find(' '),
                            field="court"
                        )
                    )

        # 7) Final structure check
        if not errors and not PATTERNS['citation'].match(citation):
            errors.append(
                CitationError(
                    message="Citation structure invalid. Expected: CaseName Volume Reporter Page (Court Year).",
                    start=0,
                    end=len(citation),
                    field="overall"
                )
            )
        return errors


    def validate_full_citation(
        self,
        citation: str,
        provided_quote: Optional[str] = None,
        pincite: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
        """
        1) Abbreviate months/journals inside `citation`
        2) Accumulate any format violations (parentheses, comma, vol/reporter/page, parenthetical contents)
        3) Parse via CITATION_PATTERN
        4) Verify reporter + court level
        5) Fetch case data (+ optional pincite check)
        6) Verify provided quote
        7) Omit/abbreviate case name (§4-300 & §4-100)
        8) Normalize abbrev spacing/periods (§4-810/820)
        9) Format the final string with italics/underlining rules

        Returns a 3-tuple: (parsed_components, case_data, formatted_string).
        """
        # — Preprocess —
        citation = abbreviate_months_in_citation(citation)
        citation = abbreviate_journals_in_citation(citation)

        errors = self._collect_format_errors(citation)
        if errors:
            raise CitationValidationException(errors)

        # — Parse —
        m = PATTERNS['citation'].match(citation)
        if m is None:
            raise CitationValidationException([
                CitationError(
                    message=f"Unable to parse citation: {citation}",
                    start=0,
                    end=len(citation),
                    field="parse"
                )
            ])
        comps = m.groupdict()

        # — Reporter + Court Level —
        if comps['reporter'] not in ALLOWED_REPORTERS:
            raise ValueError(f"Reporter '{comps['reporter']}' not allowed")
        validate_reporter_for_court(comps)

        # — Fetch + Pincite Check —
        # only do the DB lookup & error if a pincite was actually passed in
        if pincite is not None:
            data = self.fetch_case_data(
                comps['volume'], comps['reporter'], comps['page'], pincite
            )
            if not data:
                raise ValueError("Citation not found or pincite incorrect")
        else:
            data = {}

        # — Quote Verification —
        if provided_quote:
            cleaned = self._remove_signals(provided_quote)
            if not self._check_quote(cleaned, data.get('text', "")):
                raise ValueError("Provided quote does not match source text")

        # — Case-Name Omission & Abbreviation —
        # — Normalize spacing/periods on the case name, but do NOT abbreviate —
        # — Case-Name Cleanup — strip any trailing comma, then normalize spacing/periods
        comps['case_name'] = comps['case_name'].rstrip(',')

        # — Formatting —
        formatted = self.format_citation(comps)
        return comps, data, formatted



    def _remove_signals(self, txt: str) -> str:
        sigs = sorted([re.escape(s.strip('*')) for s in VALID_CITATION_SIGNALS], key=len, reverse=True)
        pat = r'\*(' + '|'.join(sigs) + r')\*'
        return re.sub(pat, '', txt, flags=re.IGNORECASE).strip()

    def _check_quote(self, prov: str, orig: str) -> bool:
        sm = difflib.SequenceMatcher(None, prov, orig)
        thresh = 0.3 if len(prov) < 50 else 0.6
        return sm.ratio() > thresh

    def fetch_case_data(
        self,
        vol: str,
        rep: str,
        page: str,
        pincite: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Placeholder synthetic DB lookup. Raises ValueError if pincite is out of range.
        """
        db = {
            "291_U.S._193": {"text": "Brown v. Board opinion text here...", "valid_pin_range": (190, 210)},
            "347_U.S._483": {"text": "Brown v. Board decision text...", "valid_pin_range": (480, 500)}
        }
        key = f"{vol}_{rep}_{page}"
        rec = db.get(key)
        if rec and pincite:
            try:
                if '-' in pincite:
                    start, end = map(int, pincite.split('-'))
                    low, high = rec["valid_pin_range"]
                    if not (low <= start <= high and low <= end <= high):
                        raise ValueError(f"Pincite range {pincite} outside {low}-{high}")
                else:
                    val = int(pincite)
                    low, high = rec["valid_pin_range"]
                    if not (low <= val <= high):
                        raise ValueError(f"Pincite {val} outside {low}-{high}")
            except Exception as e:
                raise ValueError(str(e))
        return rec

    def validate_short_citation(self, short: str, full: str) -> bool:
        sf = short.split(',')[0].strip()
        if sf not in full:
            raise ValueError("Short citation does not match full citation context")
        return True

    def resolve_short_citation(self, short: str) -> Dict[str, Any]:
        for key, grp in self.full_citations.items():
            if grp['volume'] in short and grp['reporter'] in short:
                return grp
        raise KeyError(f"No matching full citation for short form: '{short}'")
