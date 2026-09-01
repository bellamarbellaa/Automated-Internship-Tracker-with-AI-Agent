ROLE_QUERIES = {
    "Business Analyst": [
        "business analyst intern",
        "business analyst intern consulting",
        "business analyst intern banking",
    ],
    "Data Analyst": [
        "data analyst intern",
        "data analyst intern banking",
        "data analyst intern fintech",
    ],
    "Consultant": [
        "consultant intern",
        "consulting intern",
        "consultant intern banking",
    ],
}

# SerpAPI-only: Adzuna has no Indonesia country code (confirmed via its own
# error response, which lists supported ISO codes and "id" is not among
# them). Google Jobs via SerpAPI is location-sensitive to the literal query
# text rather than the "location" param for this case -- verified live that
# "<role> internship jakarta indonesia" reliably surfaces real Jakarta
# postings (PwC, Deloitte, GoTo, SeaBank among them) across all three roles,
# while "location=Jakarta, Indonesia" alone or "magang" (Indonesian for
# "internship") returned zero or irrelevant results.
INDONESIA_QUERIES = {
    "Business Analyst": ["business analyst internship jakarta indonesia"],
    "Data Analyst": ["data analyst internship jakarta indonesia"],
    "Consultant": ["consultant internship jakarta indonesia"],
}
