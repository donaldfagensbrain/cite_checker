import re
from constants import ALLOWED_REPORTERS
import advancedregex

# Build a regex for all allowed reporters, longest-first to avoid prefix collisions
allowed_reporters_regex = r'|'.join(
    sorted(map(re.escape, ALLOWED_REPORTERS), key=len, reverse=True)
)

# 1) Full-form case citations (e.g. A v. B, C, D & E, 347 U.S. 483 (U.S. 1954))
CITATION_PATTERN = re.compile(
    # capture everything up to the *last* comma before the volume,
    # so internal commas stay inside case_name but the final comma is required
    rf'^(?P<case_name>.+),'         # case_name ends at that comma
    r'(?=\s*\d+\s)'                 # assert that comma is right before volume
    r'\s*(?P<volume>\d+)\s+'        # volume
    rf'(?P<reporter>({allowed_reporters_regex}))\s+'  # reporter
    r'(?P<page>\d+)'                # page
    r'(?:,\s*(?P<pinpoint>\d+(?:-\d+)?))?'  # optional pinpoint
    r'\s*\((?P<court>.+?)\s+(?P<year>\d{4})\)$'  # (Court Year)
)

# 2) Statutes: federal (U.S.C.) and all states
FEDERAL_STATUTE_PATTERN = re.compile(
    # match “U.S.C.” or “U.S.C.A.” then § and section
    r'^(?P<title>\d+)\s+'             # title number
    r'U\.S\.C\.(?:A\.)?\s+'          # U.S.C. or U.S.C.A.
    r'§\s*(?P<section>[\d\w\(\)\-/]+)'# §section
    r'(?:\s*\((?P<extra>.+?)\))?$',   # optional parenthetical
    flags=re.IGNORECASE
)

STATE_STATUTE_PATTERNS = [
    re.compile(
        r'^\d+\s+[A-Za-z\.]+\s+Code\s+§\s*[\d\.\-/]+'  
        r'(?:,\s*et seq\.)?(?:\s*\(.+\))?$'
    )
]
STATUTE_PATTERNS = [FEDERAL_STATUTE_PATTERN] + STATE_STATUTE_PATTERNS

# 3) Court rules
COURT_RULE_PATTERNS = [
    re.compile(r'^(?:Fed\. R\. Civ\. P\.|Fed\. R\. Crim\. P\.)\s+\d+(?:\([^)]+\))?(?:\.\d+)*$'),
    re.compile(r'^[A-Z][a-zA-Z\.]+\sR\.\s(?:Civ\. P\.|Crim\. P\.|App\. P\.)\s+\d+(?:\([^)]+\))?(?:\.\d+)*$'),
    re.compile(r'^(?:Practice Book §\s*\d+-\d+|CPLR\s+\d+\(\d+\))$')
]

# 4) Books & treatises
BOOK_PATTERNS = [
    re.compile(r'^\d+\s+[A-Z][A-Za-z\.\s,&]+§\s*\d+(?:\.\d+)?(?:,\s*n\.\d+)?\s*\(\d{4}\)$'),
    re.compile(r'^[A-Z].+?,\s*\d+\s+[A-Z].+?ed\.+\s*\d{4}$')
]

# 5) Law review & treatise articles
ARTICLE_PATTERNS = [
    re.compile(
        r'^[A-Z][^,]+,\s+[^,]+,\s+\d+\s+[A-Za-z\.]+(?:\s+[A-Za-z\.]+)*\s+\d+(?:,\s*\d+)?\s*\(\d{4}\)$'
    ),
    re.compile(r'^[A-Z][^,]+,\s+(?:Note|Comment),\s+\d+\s+[A-Za-z\.]+\s+\d+\s*\(\d{4}\)$')
]

# Consolidated core patterns map
PATTERNS = {
    # allow newcitechecker to do PATTERNS['citation']
    'citation':      CITATION_PATTERN,
    'case':          CITATION_PATTERN,
    # for validate('statute', …) to accept "12 C.S.C. § 3456"
    'statute':       STATUTE_PATTERNS + [
        re.compile(r'^\d+\s+[A-Za-z\.]+\s+§\s*[\d\w\(\)\-/]+(?:\s*\(.+\))?$')
    ],
    'court_rule':    COURT_RULE_PATTERNS,
    'book':          BOOK_PATTERNS,
    'article':       ARTICLE_PATTERNS,
}

# Dispatch validators for core types
VALIDATORS = {
    'case':        PATTERNS['case'],
    'statute':     PATTERNS['statute'],
    'court_rule':  PATTERNS['court_rule'],
    'book':        PATTERNS['book'],
    'article':     PATTERNS['article'],
}

PATTERNS.update(advancedregex.ADVANCED_PATTERNS)
VALIDATORS.update(advancedregex.ADVANCED_VALIDATORS)
