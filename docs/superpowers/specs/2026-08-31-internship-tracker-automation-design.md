# Internship Tracker Automation — Design

Date: 2026-08-31
Status: Approved (pending implementation plan)

## Purpose

A weekly automation, built on the WAT (Workflows, Agents, Tools) framework
defined in `WAT Claude.md`, that:

1. Searches free job APIs for new internship postings matching specific
   criteria.
2. Appends genuinely new postings to a Google Sheet that doubles as an
   application tracker.
3. Emails a digest of what's new, only when there's something to report.

Runs automatically every week via a scheduled cloud agent — no laptop
required.

## Search Criteria

- **Roles** (exact set, no others): Business Analyst, Data Analyst,
  Consultant.
- **Industry**: not a hard filter. Search broadly, but bias queries toward
  Consulting, Banking, and Fintech (e.g. combine each role with those
  industry terms in some queries, plus general role-only queries).
- **Internship requirement** (hard filter): the posting must have
  "internship" or "intern" in its title or job description. Full-time
  postings are excluded even if otherwise matching.
- **Timing**: Summer 2027 internships, or any 2027 posting that states (or
  reasonably implies) a full-time internship of 8, 10, or 12 weeks.
  Postings with no duration info get a lighter-touch judgment call rather
  than auto-exclusion, since many postings omit exact week counts.
- **CV match** (hard filter, ≥70%): the posting must score at least 70%
  against the user's CV for that role on skills/qualifications fit (see
  "CV Matching" below).
- **Location/visa** (soft filter, not by country): user is based in
  Jakarta, Indonesia and open to roles anywhere, with higher realistic odds
  in Indonesia, other Asian countries, and the US (per their US-accredited
  institution background) than Europe/Australia — this is not used to
  exclude postings, only as a tiebreaker/priming consideration. The one
  hard exclusion: if a posting explicitly requires existing work
  authorization or does not sponsor visas for its country, exclude it. If
  a posting says nothing about visa/work authorization, include it (benefit
  of the doubt — sponsorship may still be possible). Indonesia has no hard
  exclusion of its own — Adzuna simply doesn't support Indonesia as a
  search country (confirmed via its own API error response), so coverage
  there comes from SerpAPI's Indonesia-targeted queries instead (see
  Sources below).
- **Completed-degree requirement** (hard filter): a posting that mentions
  a bachelor's/master's degree as a qualification with no current-student
  signal anywhere in the text (no "pursuing", "currently enrolled", "final
  year", "expected graduation", etc.) is excluded — it reads as requiring
  an already-completed degree, which the user (an undergraduate) doesn't
  have. Confirmed against two real examples: McKinsey's "Associate Intern"
  posting (bare "a bachelor's degree from a top-tier university", no
  qualifier — excluded) vs. a JPMorgan Summer Analyst posting ("penultimate
  year", "expected graduation... 2028", "pursuing a Master's Degree" — not
  excluded). Explicit phrasing ("must have already completed/graduated") is
  always excluded outright, degree-mention-without-qualifier is the
  broader compound rule.
- **Weekly cap**: at most 20 postings added per week, highest CV match
  score first, across all three roles combined (not per-role).
- **Cost constraint**: free sources/tools only, no paid services anywhere
  in the pipeline. Up to 8 distinct sources total (currently using 2).

## Sources (Layer 3 tools)

Both already have free-tier API keys provisioned by the user, to be stored
in `.env`:

- **Adzuna API** (`tools/search_adzuna.py`) — free tier, aggregates listings
  across many boards including Indeed-sourced postings.
- **SerpAPI Google Jobs endpoint** (`tools/search_serpapi_jobs.py`) — free
  tier (~100 searches/month), surfaces Google Jobs cards including
  LinkedIn/Indeed postings without directly scraping those sites. Also runs
  Indonesia-targeted queries (`"<role> internship jakarta indonesia"`,
  `tools/role_queries.py`'s `INDONESIA_QUERIES`) — verified live to
  reliably surface real Jakarta postings (PwC, Deloitte, GoTo, SeaBank)
  across all three roles, unlike SerpAPI's `location` parameter alone or
  the Indonesian word "magang", both of which returned nothing useful.

Each search tool:
- Takes role + industry-bias query terms as input.
- Calls its respective API.
- Filters results against the internship requirement and 2027 timing.
- Returns a normalized list of postings: `title, company, location, url,
  posted_date, source, role, description`. `description` is carried through
  so the agent's CV-matching step (below) has actual job content to score
  against, not just the title.
- On API failure (bad key, rate limit, timeout): logs the error and returns
  an empty list with a failure flag, rather than raising and aborting the
  whole run.

Room to add up to 6 more sources later (e.g. Greenhouse/Lever for specific
target firms) without changing the rest of the pipeline — out of scope for
this iteration; explicitly deferred by the user.

## CV Matching (Layer 2 — Agent reasoning)

The user provided 3 role-tailored CVs as PDFs, stored as extracted plain
text in `reference/` (gitignored, personal documents): `cv_consulting.txt`,
`cv_data.txt`, `cv_business.txt`. Text form was chosen over keeping raw
PDFs so the agent can read them directly on every scheduled run without a
PDF-parsing step each time; content is unchanged from the source PDFs.

Matching skills/experience to a job description is a judgment call, not a
deterministic computation — per the WAT principle that probabilistic
reasoning belongs at the Agent layer, this is done by the agent (Claude)
at run time, not a Python tool:

- After dedup (new postings only, to avoid rescoring what's already been
  judged), the agent reads the CV matching the posting's role (Consultant
  → `cv_consulting.txt`, Business Analyst → `cv_business.txt`, Data
  Analyst → `cv_data.txt`) and estimates a skills/qualifications match
  percentage against the posting.
- Only postings scoring ≥70% are kept; the rest are dropped before ever
  reaching the sheet.
- This avoids needing a paid embeddings/LLM API for scoring — it's part of
  the same scheduled agent run already happening.

## Google Sheet — Tracker

**One tab per week**, named after the Monday that starts that week (e.g.
"31 Aug") — `tools/setup_tracker_sheet.py`'s `current_week_tab_name()`
computes it, `ensure_week_tab()` creates the tab with headers if it
doesn't already exist (idempotent, safe to call on a same-week re-run).
Every tab has the same columns:

| Date Found | Title | Company | Location | Source | Posted Date | URL | Match % | Status |
|---|---|---|---|---|---|---|---|---|

- `tools/update_tracker_sheet.py` reads all existing URLs from **the
  current week's tab only** into a set, filters incoming normalized
  postings against it, and appends only genuinely new rows with
  `Status = New` — including the `Match %` the agent assigned during CV
  matching.
- **Dedup is scoped to the current week's tab, not across all weeks** —
  explicit user decision. A still-open posting can legitimately reappear
  in a later week's tab; the tracker does not try to remember postings
  from prior weeks.
- **Dedup key**: normalized job URL — trailing slash/whitespace trimmed,
  and volatile tracking query parameters (`se`, `utm_source`, `utm_medium`,
  `utm_campaign`) stripped. The `se` param specifically was found to
  rotate on every Adzuna API call for the same listing (confirmed via two
  live searches minutes apart returning the same job with only `se`
  differing) — without stripping it, the same still-open posting would
  look "new" indefinitely and duplicate. Dedup also applies within a
  single incoming batch, not just against the sheet, since the same job
  can surface twice in one run via two query variants.
- **Weekly cap**: `update_tracker_sheet.py` sorts candidates by
  `match_percent` descending and appends only enough to fill this week's
  tab up to 20 total rows (accounting for rows already present from an
  earlier same-week run).
- The automation only ever appends rows — it never edits `Status` on
  existing rows. The user hand-edits `Status` (e.g. `Applied`, `Interview`,
  `Rejected`, `Offer`) to use the same sheet as their application tracker.

## Email Digest

`tools/send_digest_email.py`, sent via Gmail API to
belbel.bella00@gmail.com.

- Sent **only if** new rows were added that week — a quiet week produces no
  email.
- Content: postings grouped by role (Business Analyst / Data Analyst /
  Consultant), each entry showing Company, Title, Location, Posted Date,
  and link.
- Footer: which sources ran successfully, and which (if any) failed that
  week, so partial coverage is visible rather than silent.

## Orchestration (Layer 1 + 2)

`workflows/weekly_internship_search.md` is the SOP: defines the search
criteria above, which tools to call in what order, how to merge results
across sources before dedup, and how to handle a source failing (proceed
with whatever succeeded, note the failure).

The agent (Claude, at run time):
1. Reads the workflow.
2. Computes this week's tab name and ensures it exists
   (`current_week_tab_name()` + `ensure_week_tab()`).
3. Calls `search_adzuna.py` and `search_serpapi_jobs.py` (the latter
   automatically covers Indonesia too).
4. Merges normalized results from both, handling either source failing
   gracefully.
5. Filters out postings already in this week's tab (by URL) using the
   existing URL set from `update_tracker_sheet.py`, so only genuinely new
   postings reach CV matching.
6. For each remaining posting, reads the matching CV and scores it;
   drops anything below 70%, and applies the completed-degree hard filter
   during the same read-through for cases the deterministic filter misses.
7. Passes the surviving postings (with Match %) to
   `update_tracker_sheet.py` to append to this week's tab — which also
   enforces the 20-per-week cap automatically.
8. If any new rows were appended, calls `send_digest_email.py` with just
   the new rows.
9. Per the WAT self-improvement loop: if a source's filtering proves too
   noisy/strict or a recurring failure shows up, the agent updates the
   relevant tool and documents the change in the workflow doc.

## Scheduling

A Claude Code scheduled cloud agent (weekly cron, e.g. Monday 8am) runs a
prompt instructing the agent to execute
`workflows/weekly_internship_search.md` end to end. No local machine
required to be on.

## Google OAuth

User has a Desktop-type OAuth client (`credentials.json`) already
configured — no redirect URI registration needed, uses the loopback flow.
Used for both Sheets and Gmail API access; `token.json` is generated on
first auth and gitignored thereafter.

## Out of Scope (this iteration)

- Application-status tracking automation (e.g. parsing confirmation
  emails) — the Status column is manual for now.
- Additional sources beyond Adzuna + SerpAPI (Greenhouse/Lever for named
  target firms) — deferred, room left in the design to add later.
- Any paid service or API.
- Automated CV updates/versioning — the 3 CVs are static reference inputs
  the user maintains manually.
