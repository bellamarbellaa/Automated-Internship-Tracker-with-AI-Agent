from tools.job_filters import has_internship_keyword, matches_duration, passes_visa_check


def test_has_internship_keyword_in_title():
    assert has_internship_keyword("Business Analyst Internship", "") is True


def test_has_internship_keyword_in_description():
    assert has_internship_keyword(
        "Business Analyst", "This is a full-time internship program"
    ) is True


def test_has_internship_keyword_absent():
    assert has_internship_keyword(
        "Senior Business Analyst", "Full-time permanent role"
    ) is False


def test_matches_duration_explicit_week_match():
    assert matches_duration("This is an 8-week summer internship") is True


def test_matches_duration_explicit_week_mismatch():
    assert matches_duration("This is a 16-week internship") is False


def test_matches_duration_month_match():
    assert matches_duration("A 3-month internship program") is True


def test_matches_duration_month_mismatch():
    assert matches_duration("A 6-month internship program") is False


def test_matches_duration_summer_2027_overrides():
    assert matches_duration("Summer 2027 internship, duration TBD") is True


def test_matches_duration_no_info_defaults_true():
    assert matches_duration("Full-time internship, great learning experience") is True


def test_passes_visa_check_no_sponsorship_excluded():
    assert passes_visa_check(
        "We are unable to sponsor work visas for this position"
    ) is False


def test_passes_visa_check_requires_authorization_excluded():
    assert passes_visa_check(
        "Applicants must be authorized to work in the United States"
    ) is False


def test_passes_visa_check_silent_included():
    assert passes_visa_check("Join our team as a summer intern") is True
