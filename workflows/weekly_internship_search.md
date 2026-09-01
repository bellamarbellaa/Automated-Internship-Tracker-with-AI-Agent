# Weekly Internship Search

## Objective

Find new Business Analyst / Data Analyst / Consultant internship postings
matching the user's criteria, add genuinely new ones to this week's tab in
the Google Sheet tracker (capped at 20, highest CV match first), and email
a digest if anything new was found.

## Required inputs

- `.env` populated with `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `SERPAPI_API_KEY`,
  `TRACKER_SPREADSHEET_ID`, `DIGEST_EMAIL_TO`.
- `credentials.json` (Desktop OAuth client) and `token.json` present.
- `reference/cv_business.txt`, `reference/cv_data.txt`, `reference/cv_consulting.txt`.

## Steps

1. Compute this week's tab name and make sure it exists:
   ```bash
   python -c "
   import os
   from dotenv import load_dotenv
   from googleapiclient.discovery import build
   from tools.google_auth import get_credentials, SHEETS_SCOPE
   from tools.setup_tracker_sheet import current_week_tab_name, ensure_week_tab
   load_dotenv()
   creds = get_credentials([SHEETS_SCOPE])
   service = build('sheets', 'v4', credentials=creds)
   tab = current_week_tab_name()
   ensure_week_tab(service, os.environ['TRACKER_SPREADSHEET_ID'], tab)
   print(tab)
   "
   ```
   The tab is named after the Monday that starts the current week (e.g.
   "31 Aug"). `ensure_week_tab` is idempotent — if the tab already exists
   (e.g. a same-week re-run), it does nothing. Keep this tab name — every
   later step needs it.

2. For each role in ["Business Analyst", "Data Analyst", "Consultant"], run:
   ```bash
   python -m tools.search_adzuna --role "<role>"
   python -m tools.search_serpapi_jobs --role "<role>"
   ```
   Each prints a JSON object: `{"source": ..., "success": ..., "error": ...,
   "postings": [...]}`. Record `success`/`error` per source for the digest
   footer later. If a source fails, proceed with whatever the other source
   returned — don't abort the run.

   `search_serpapi_jobs` automatically includes Indonesia-targeted queries
   (`tools.role_queries.INDONESIA_QUERIES`) alongside the general ones —
   Adzuna has no Indonesia country code (confirmed via its own API error
   response), so Indonesia coverage comes from SerpAPI only.

3. Merge all postings from both sources across all three roles into one
   list. Deduplicate this merged list by `url` (a posting can appear in
   both sources).

4. Filter out postings whose `url` is already in **this week's tab** (not
   other weeks' tabs — dedup is scoped per-week, so a still-open posting
   can legitimately resurface in a later week). Run:
   ```bash
   python -c "
   import json, os, sys
   from dotenv import load_dotenv
   from googleapiclient.discovery import build
   from tools.google_auth import get_credentials, SHEETS_SCOPE
   from tools.update_tracker_sheet import get_existing_urls
   load_dotenv()
   creds = get_credentials([SHEETS_SCOPE])
   service = build('sheets', 'v4', credentials=creds)
   urls = get_existing_urls(service, os.environ['TRACKER_SPREADSHEET_ID'], '<TAB_NAME>')
   print(json.dumps(sorted(urls)))
   "
   ```
   Drop any merged posting whose `url` is in this set.

5. For each remaining posting, read the CV matching its `role`:
   - Business Analyst → `reference/cv_business.txt`
   - Data Analyst → `reference/cv_data.txt`
   - Consultant → `reference/cv_consulting.txt`

   Estimate a skills/qualifications match percentage (0-100) between the
   CV and the posting's title + description. This is a judgment call — use
   your own reasoning, not a script. Then apply
   `tools.job_filters.apply_indonesia_bonus(match_percent, location)` to
   the raw score — it adds +10 (capped at 100) for Indonesia-located
   postings, applied *before* the threshold check below so a borderline
   Indonesia posting gets a fair chance to qualify, not just better
   ranking among an already-qualified pool. Add the boosted result as
   `"match_percent"` on the posting dict. Drop any posting scoring below
   70 after the bonus.

   While reading each full description, also watch for things the
   deterministic filters can miss or only partially catch:
   - **Stale postings.** A posting can carry an explicit start/end date
     from a past year (e.g. "Expected Start/End Date: October 2020 -
     December 2020") even though it surfaced in a search for 2027 roles —
     `matches_duration` only checks week/month counts and the literal
     phrase "summer 2027", so it won't catch this. Drop postings with an
     explicit past-year date, regardless of match score.
   - **Visa/sponsorship or degree-completion language the filters don't
     catch.** `passes_visa_check` and `requires_completed_degree` run
     first and catch most cases, but phrasing evolves — if you read a
     full description that clearly violates either hard rule without
     matching the filter's known phrases, drop the posting yourself and
     consider adding the new phrasing to `tools/job_filters.py` afterward,
     per the self-improvement loop below. Watch specifically for curly
     apostrophes (’) in scraped text — a plain `'` in a phrase or regex
     can silently fail to match them (this happened once already, see
     commit history on `job_filters.py`).

   Note: you do not need to enforce the 20-per-week cap yourself —
   `update_tracker_sheet.py` sorts by `match_percent` and truncates to
   whatever headroom remains in this week's tab automatically.

6. Pipe the surviving postings (as a JSON array, each with `match_percent`
   added) to the tracker sheet tool, passing this week's tab name:
   ```bash
   echo '<json array>' | python -c "
   import json, os, sys
   from dotenv import load_dotenv
   from googleapiclient.discovery import build
   from tools.google_auth import get_credentials, SHEETS_SCOPE
   from tools.update_tracker_sheet import append_postings
   load_dotenv()
   postings = json.load(sys.stdin)
   creds = get_credentials([SHEETS_SCOPE])
   service = build('sheets', 'v4', credentials=creds)
   appended = append_postings(service, os.environ['TRACKER_SPREADSHEET_ID'], postings, '<TAB_NAME>')
   json.dump(appended, sys.stdout)
   "
   ```
   This prints back the JSON array of postings that were actually appended
   (it dedups again internally in case of a race between steps 4 and 6,
   and applies the 20-per-week cap).

7. If the array from step 6 is non-empty, send the digest:
   ```bash
   echo '{"postings": <appended array>, "source_status": <status dict from step 2>}' \
     | python -m tools.send_digest_email
   ```
   If the array is empty, skip this step — no email on a quiet week.

8. Summarize what happened in your final response: how many new postings
   were added per role, whether the 20-cap was hit, and whether any source
   failed this run.

## Handling recurring problems (WAT self-improvement loop)

- If a source consistently returns 0 postings or errors, investigate (check
  API docs, rate limits, key validity) and fix the relevant tool, then
  document the fix here.
- If CV matching feels systematically too strict or too lenient after a
  few runs, note it here and adjust the 70% threshold or matching approach
  by agreement with the user — don't silently change it.
- If the duration/visa/degree-completion keyword heuristics in
  `tools/job_filters.py` are letting through or excluding things they
  shouldn't, update the heuristics and document the change and why here.
- If the 20-per-week cap is consistently binding (i.e. more than 20 strong
  matches show up most weeks) and the user wants a higher cap, that's a
  one-line change to `WEEKLY_CAP` in `tools/update_tracker_sheet.py`.
