import re

# ----- Administrative & Agency Patterns -----
ADMIN_CITATION_PATTERNS = [
    re.compile(r'Federal Charge No\.\s*\d{3}-\d{4}-\d{5}'),
    re.compile(r'\d+\s+Fed\.\s+Reg\.\s+\d+'),
    re.compile(r'\d+\s+C\.F\.R\.\s+§\s*\d+[\.\d]*'),
    re.compile(r'(EEOC|OSHA) Enforcement Guidance'),
    re.compile(r'(DOJ|IRS) (Enforcement Manuals|Internal Revenue Manual)'),
    re.compile(r'(DOL|IRS) (Wage and Hour opinion letters|advisory opinions)'),
    re.compile(r'(SEC|FTC) no-action letters'),
    re.compile(r'IRS (Revenue Rulings|Private Letter Rulings)'),
    re.compile(r'(FTC|SEC) (consent decrees|settlement agreements)'),
    re.compile(r"(Agency’s formal enforcement complaints|Agency final orders)"),
    re.compile(r'(DOJ|EEOC) amicus briefs'),
    re.compile(r'(CMS|EPA) (guidance|technical bulletins)'),
    re.compile(r'\bState\b\s+(?:Admin|Reg)\.?\s+Board\b', re.IGNORECASE),
    re.compile(r'\b[A-Z][a-z]+ Admin(?:istrative)? (?:Board|Commission|Agency)\b', re.IGNORECASE)
]

# ----- Regulation Patterns -----
FEDERAL_REGULATION_PATTERN = re.compile(
    r'^(?P<title>\d+)\s+C\.F\.R\.\s+§\s*(?P<section>[\d\.\-]+)$'
)

STATE_REGULATION_PATTERNS = [
    re.compile(
        r'^(?P<state_abbrev>[A-Za-z\.]+)\s+Admin\.\s+Code\s+r\.\s*'
        r'(?P<number>[\d\-\w\. ]+)(?:\s+§\s*(?P<section>[\d\.\-()]+))?$', re.IGNORECASE
    ),
    re.compile(
        r'^(?P<state_abbrev>[A-Za-z\.]+)\s+Admin\.\s+Code,\s+Rule\s+'
        r'(?P<number>[\d\-\w\.\(\)]+)$', re.IGNORECASE
    )
]

# ----- Executive Orders & Proclamations -----
EXECUTIVE_ORDER_PATTERN = re.compile(r'^Exec\. Order No\.\s*\d+.*', re.IGNORECASE)
PROCLAMATION_PATTERN = re.compile(r'^Proclamation No\.\s*\d+.*', re.IGNORECASE)

# ----- Other Agency Citations -----
AGENCY_ADJUDICATION_PATTERN = re.compile(
    r'^[A-Za-z].+?,\s*\d+\s+\w+\.\s+No\.\s*\d+.*', re.IGNORECASE
)
AGENCY_REPORT_PATTERN = re.compile(r'^\d{3,4}\s+[A-Z]{2,5}\.\s+Ann\.\s+Rep\.\s+\d+', re.IGNORECASE)
AG_OPINION_PATTERN = re.compile(r"^\d+\s+Op\.\s+Att'y\s+Gen\.\s+\d+", re.IGNORECASE)
ARBITRATION_DECISION_PATTERN = re.compile(
    r'^.+?No\.\s*\d+\s*\(.+?\)\s*\(.+?Arbs\.\)$', re.IGNORECASE
)

# ----- Exported maps for advanced use -----
ADVANCED_PATTERNS = {
    'admin': ADMIN_CITATION_PATTERNS,
    'federal_regulation': FEDERAL_REGULATION_PATTERN,
    'state_regulation': STATE_REGULATION_PATTERNS,
    'executive_order': EXECUTIVE_ORDER_PATTERN,
    'proclamation': PROCLAMATION_PATTERN,
    'agency_adjudication': AGENCY_ADJUDICATION_PATTERN,
    'agency_report': AGENCY_REPORT_PATTERN,
    'ag_opinion': AG_OPINION_PATTERN,
    'arbitration': ARBITRATION_DECISION_PATTERN,
}

ADVANCED_VALIDATORS = {kind: ADVANCED_PATTERNS[kind] for kind in ADVANCED_PATTERNS}
