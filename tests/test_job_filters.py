from tools.job_filters import (
    has_internship_keyword,
    matches_duration,
    passes_visa_check,
    requires_completed_degree,
)


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


def test_passes_visa_check_sponsorship_not_available_excluded():
    assert passes_visa_check(
        "Visa sponsorship for work authorization is not available for this "
        "position now or in the future"
    ) is False


def test_passes_visa_check_legally_authorized_us_excluded():
    assert passes_visa_check(
        "Applicants must be legally authorized to work in the United States. "
        "Visa sponsorship is not available for this position."
    ) is False


def test_passes_visa_check_without_employer_sponsorship_excluded():
    assert passes_visa_check(
        "You must be work authorized in the United States on a full-time "
        "basis without the need for employer sponsorship now or in the future."
    ) is False


def test_passes_visa_check_cannot_offer_employment_excluded():
    assert passes_visa_check(
        "We cannot offer employment to F-1 visa holders who require "
        "employer sponsorship in the future."
    ) is False


def test_requires_completed_degree_explicit_already_completed_excluded():
    assert requires_completed_degree(
        "Candidates must have completed a Bachelor's degree prior to starting."
    ) is True


def test_requires_completed_degree_already_hold_excluded():
    assert requires_completed_degree(
        "Applicants must already hold a Bachelor's degree in a related field."
    ) is True


def test_requires_completed_degree_already_graduated_excluded():
    assert requires_completed_degree(
        "You must have already graduated with a relevant degree to apply."
    ) is True


def test_requires_completed_degree_bachelor_mention_with_no_student_qualifier_excluded():
    # Confirmed against a real posting: McKinsey's "Associate Intern" listing
    # mentions "a bachelor's degree from a top-tier university" as a
    # qualification with no "pursuing"/"currently enrolled"/similar language
    # anywhere else in the text -- reads as requiring an already-completed
    # degree, unlike the vast majority of internship postings.
    assert requires_completed_degree(
        "The ideal candidate will have a successful track record of academic "
        "excellence, including a bachelor's degree from a top-tier university."
    ) is True


def test_requires_completed_degree_pursuing_not_excluded():
    assert requires_completed_degree(
        "Currently pursuing a Bachelor's degree with an expected graduation in 2028."
    ) is False


def test_requires_completed_degree_penultimate_year_not_excluded():
    # Real example (JPMorgan Global Corporate Banking Summer Analyst): a
    # posting explicitly for current students, confirmed as a posting that
    # SHOULD be included, not excluded.
    assert requires_completed_degree(
        "Penultimate year Undergraduate/Master's student with outstanding "
        "academic achievement seeking a summer internship. Expected "
        "graduation date of September 2027 through July 2028. If you are "
        "pursuing a Master's Degree, it must be attained within 2 academic "
        "years of your receipt of a Bachelor's Degree."
    ) is False


def test_requires_completed_degree_bare_requirement_with_no_qualifier_excluded():
    # Confirmed direction: "Bachelor's degree ... is required" with no
    # nearby current-student language is now also treated as exclusionary,
    # even though it's phrased as a generic requirement rather than an
    # explicit "already completed" statement.
    assert requires_completed_degree(
        "A Bachelor's degree in finance, accounting, or a related field is required."
    ) is True
