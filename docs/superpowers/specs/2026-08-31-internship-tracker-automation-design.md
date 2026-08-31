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
- **Timing**: Summer 2027 internships, or any 2027 posting that offers a
  ~3-month full-time internship.
- **Cost constraint**: free sources/tools only, no paid services anywhere
  in the pipeline. Up to 8 distinct sources total (currently using 2).

## Sources (Layer 3 tools)

Both already have free-tier API keys provisioned by the user, to be stored
in `.env`:

- **Adzuna API** (`tools/search_adzuna.py`) — free tier, aggregates listings
  across many boards including Indeed-sourced postings.
- **SerpAPI Google Jobs endpoint** (`tools/search_serpapi_jobs.py`) — free
  tier (~100 searches/month), surfaces Google Jobs cards including
  LinkedIn/Indeed postings without directly scraping those sites.

Each search tool:
- Takes role + industry-bias query terms as input.
- Calls its respective API.
- Filters results against the internship requirement and 2027 timing.
- Returns a normalized list of postings: `title, company, location, url,
  posted_date, source`.
- On API failure (bad key, rate limit, timeout): logs the error and returns
  an empty list with a failure flag, rather than raising and aborting the
  whole run.

Room to add up to 6 more sources later (e.g. Greenhouse/Lever for specific
target firms) without changing the rest of the pipeline — out of scope for
this iteration; explicitly deferred by the user.

## Google Sheet — Tracker

One tab, "Internship Tracker", columns:

| Date Found | Title | Company | Location | Source | Posted Date | URL | Status |
|---|---|---|---|---|---|---|---|

- `tools/update_tracker_sheet.py` reads all existing URLs from the sheet
  into a set, filters incoming normalized postings against it, and appends
  only genuinely new rows with `Status = New`.
- **Dedup key**: normalized job URL. Fallback if a source provides no
  stable URL: lowercased `company + title + posted_date`.
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
2. Calls `search_adzuna.py` and `search_serpapi_jobs.py`.
3. Merges normalized results from both, handling either source failing
   gracefully.
4. Passes merged results to `update_tracker_sheet.py`.
5. If any new rows were appended, calls `send_digest_email.py` with just
   the new rows.
6. Per the WAT self-improvement loop: if a source's filtering proves too
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
