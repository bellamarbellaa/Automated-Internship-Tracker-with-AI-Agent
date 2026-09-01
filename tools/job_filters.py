import re

_MATCHING_WEEKS = {8, 10, 12}
_MATCHING_MONTHS = {3}

_VISA_EXCLUSION_PHRASES = [
    "must be authorized to work",
    "no visa sponsorship",
    "not sponsor",
    "without sponsorship",
    "does not provide sponsorship",
    "must have valid work authorization",
    "unable to sponsor",
    "cannot sponsor",
    "legally authorized to work in the united states",
    "without the need for employer sponsorship",
    "cannot offer employment to",
    "do not accept candidates who require sponsorship",
]

# Handles phrasing where the negation and "sponsorship" are separated by a
# few words, rather than forming one of the fixed phrases above.
_VISA_EXCLUSION_PATTERNS = [
    # "sponsorship for work authorization is not available"
    re.compile(r"sponsorship[^.]{0,60}is not available"),
    # "nor are we able to provide sponsorship opportunities"
    re.compile(r"not able to provide sponsorship"),
    re.compile(r"nor are we able to provide sponsorship"),
]

# Explicit "already completed/hold/graduated" phrasing is always excluded
# outright.
_DEGREE_COMPLETION_EXCLUSION_PHRASES = [
    "must have completed",
    "must hold a completed",
    "already completed a bachelor",
    "already have a bachelor",
    "already hold a bachelor",
    "must have already graduated",
    "must have obtained a degree",
    "must already possess a bachelor",
]

# Compound rule: a posting that mentions a bachelor's/master's degree as a
# qualification, with no current-student signal anywhere in the text, is
# also excluded -- confirmed against a real example (McKinsey's "Associate
# Intern" posting: "a bachelor's degree from a top-tier university" with no
# "pursuing"/"currently enrolled" language anywhere). Postings that mention
# a degree AND a current-student qualifier (the large majority -- "pursuing
# a degree", "expected graduation", "final year", etc.) are correctly left
# alone by this rule.
# Matches straight (') and curly/smart (') apostrophes -- scraped job
# descriptions commonly use the curly form, which a plain "'?" would
# silently fail to match (confirmed against the real McKinsey posting,
# which uses "bachelor's degree" with a curly apostrophe).
# Also matches "fresh graduate(s)" -- a common Indonesian/SEA job-posting
# requirement phrase functionally equivalent to requiring an
# already-completed degree (confirmed against a real posting: RedDoorz's
# "Business Strategy Intern" required "Fresh Graduates in Engineering,
# Statistic or relevant major" with no student qualifier anywhere else in
# the text). The same qualifier check below still protects postings that
# say "for students and fresh graduates" or similar inclusive phrasing.
_DEGREE_MENTION_PATTERN = re.compile(
    r"bachelor['’]?s?\s+degree|master['’]?s?\s+degree|fresh graduate"
)

_CURRENT_STUDENT_PHRASES = [
    "pursuing",
    "currently enrolled",
    "in progress",
    "expected graduation",
    "currently completing",
    "current student",
    "current undergraduate",
    # Broad on purpose: any mention of "student(s)" anywhere in the text is
    # a strong enough signal that current students are eligible -- confirmed
    # this is needed by a real phrasing gap ("open to students and fresh
    # graduates" wasn't caught by the more specific phrases below).
    "student",
    "undergraduate student",
    "final year",
    "penultimate year",
    "rising junior",
    "rising senior",
    "still in school",
    "approaching graduation",
    "graduating in",
    "students and graduates",
    "students or recent graduates",
    "recent graduates or",
    "recent graduates and",
]


# Bonus applied to a posting's CV match score when it's Indonesia-located,
# per user request: they're Jakarta-based and want Indonesia postings
# weighted higher, applied before the >=70% threshold check so borderline
# Indonesia postings get a fair chance to qualify, not just better ranking
# among an already-qualified pool.
INDONESIA_MATCH_BONUS = 10


def apply_indonesia_bonus(match_percent: int, location: str) -> int:
    text = location.lower()
    if "indonesia" in text or "jakarta" in text:
        return min(100, match_percent + INDONESIA_MATCH_BONUS)
    return match_percent


def has_internship_keyword(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    return "intern" in text


def matches_duration(description: str) -> bool:
    text = description.lower()
    if "summer 2027" in text:
        return True

    week_numbers = [int(n) for n in re.findall(r"(\d{1,2})\s*-?\s*weeks?", text)]
    if week_numbers:
        return any(w in _MATCHING_WEEKS for w in week_numbers)

    month_numbers = [int(n) for n in re.findall(r"(\d{1,2})\s*-?\s*months?", text)]
    if month_numbers:
        return any(m in _MATCHING_MONTHS for m in month_numbers)

    return True


def passes_visa_check(description: str) -> bool:
    text = description.lower()
    if any(phrase in text for phrase in _VISA_EXCLUSION_PHRASES):
        return False
    if any(pattern.search(text) for pattern in _VISA_EXCLUSION_PATTERNS):
        return False
    return True


def requires_completed_degree(description: str) -> bool:
    text = description.lower()
    if any(phrase in text for phrase in _DEGREE_COMPLETION_EXCLUSION_PHRASES):
        return True
    if _DEGREE_MENTION_PATTERN.search(text) and not any(
        phrase in text for phrase in _CURRENT_STUDENT_PHRASES
    ):
        return True
    return False
