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
]


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
    return not any(phrase in text for phrase in _VISA_EXCLUSION_PHRASES)
