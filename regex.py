import re
from constants import ALLOWED_REPORTERS

# Build a regex for all allowed reporters, longest-first to avoid prefix collisions
allowed_reporters_regex = r'|'.join(
    sorted(map(re.escape, ALLOWED_REPORTERS), key=len, reverse=True)
)

# 1) Full-form case citations (e.g. Brown v. Bd., 347 U.S. 483 (U.S. 1954))
CITATION_PATTERN = re.compile(
    rf'^(?P<case_name>.+?)\s+'
    r'(?P<volume>\d+)\s+'
    rf'(?P<reporter>({allowed_reporters_regex}))\s+'
    r'(?P<page>\d+)'          # main page
    r'(?:,\s*(?P<pinpoint>\d+(?:-\d+)?))?'  # optional pinpoint
    r'\s*\((?P<court>.+?)\s+(?P<year>\d{4})\)$'
)

# 2) Statutes: federal (U.S.C.) and all states
FEDERAL_STATUTE_PATTERN = re.compile(
    r'^(?P<title>\d+)\s+U\.S\.C\.+\s+§\s*(?P<section>[\d\w\(\)\-/]+)'  
    r'(?:\s*\((?P<extra>.+?)\))?$'
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
    re.compile(r'^[A-Z][^,]+,\s+[^,]+,\s+\d+\s+[A-Za-z\.]+\s+\d+(?:,\s*\d+)?\s*\(\d{4}\)$'),
    re.compile(r'^[A-Z][^,]+,\s+(?:Note|Comment),\s+\d+\s+[A-Za-z\.]+\s+\d+\s*\(\d{4}\)$')
]

# Consolidated core patterns map
PATTERNS = {
    'case':        CITATION_PATTERN,
    'statute':     STATUTE_PATTERNS,
    'court_rule':  COURT_RULE_PATTERNS,
    'book':        BOOK_PATTERNS,
    'article':     ARTICLE_PATTERNS,
}

# Dispatch validators for core types
VALIDATORS = {
    'case':        PATTERNS['case'],
    'statute':     PATTERNS['statute'],
    'court_rule':  PATTERNS['court_rule'],
    'book':        PATTERNS['book'],
    'article':     PATTERNS['article'],
}

# ----- Advanced (less-common) citation types -----
ADVANCED_PATTERNS = {
    # e.g. 'executive_order': EXECUTIVE_ORDER_PATTERN,
    #       'arbitration': ARBITRATION_DECISION_PATTERN,
}
ADVANCED_VALIDATORS = {
    # Mirror ADVANCED_PATTERNS here
}

# ----- Merge core + advanced -----
ALL_PATTERNS   = {**PATTERNS, **ADVANCED_PATTERNS}
ALL_VALIDATORS = {**VALIDATORS, **ADVANCED_VALIDATORS}