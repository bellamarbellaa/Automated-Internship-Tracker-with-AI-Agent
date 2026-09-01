# Weekly Internship Search

## Objective

Find new Business Analyst / Data Analyst / Consultant internship postings
matching the user's criteria, add genuinely new ones to the Google Sheet
tracker, and email a digest if anything new was found.

## Required inputs

- `.env` populated with `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `SERPAPI_API_KEY`,
  `TRACKER_SPREADSHEET_ID`, `DIGEST_EMAIL_TO`.
- `credentials.json` (Desktop OAuth client) and `token.json` present.
- `reference/cv_business.txt`, `reference/cv_data.txt`, `reference/cv_consulting.txt`.

## Steps

1. For each role in ["Business Analyst", "Data Analyst", "Consultant"], run:
   ```bash
   python tools/search_adzuna.py --role "<role>"
   python tools/search_serpapi_jobs.py --role "<role>"
   ```
   Each prints a JSON object: `{"source": ..., "success": ..., "error": ...,
   "postings": [...]}`. Record `success`/`error` per source for the digest
   footer later. If a source fails, proceed with whatever the other source
   returned — don't abort the run.

2. Merge all postings from both sources across all three roles into one
   list. Deduplicate this merged list by `url` (a posting can appear in
   both sources).

3. Filter out postings whose `url` is already in the sheet. Run:
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
   urls = get_existing_urls(service, os.environ['TRACKER_SPREADSHEET_ID'])
   print(json.dumps(sorted(urls)))
   "
   ```
   Drop any merged posting whose `url` is in this set.

4. For each remaining posting, read the CV matching its `role`:
   - Business Analyst → `reference/cv_business.txt`
   - Data Analyst → `reference/cv_data.txt`
   - Consultant → `reference/cv_consulting.txt`

   Estimate a skills/qualifications match percentage (0-100) between the
   CV and the posting's title + description. This is a judgment call — use
   your own reasoning, not a script. Add the result as `"match_percent"`
   on the posting dict. Drop any posting scoring below 70.

5. Pipe the surviving postings (as a JSON array, each with `match_percent`
   added) to the tracker sheet tool:
   ```bash
   echo '<json array>' | python tools/update_tracker_sheet.py
   ```
   This prints back the JSON array of postings that were actually appended
   (it dedups again internally in case of a race between steps 3 and 5).

6. If the array from step 5 is non-empty, send the digest:
   ```bash
   echo '{"postings": <appended array>, "source_status": <status dict from step 1>}' \
     | python tools/send_digest_email.py
   ```
   If the array is empty, skip this step — no email on a quiet week.

7. Summarize what happened in your final response: how many new postings
   were added per role, and whether any source failed this run.

## Handling recurring problems (WAT self-improvement loop)

- If a source consistently returns 0 postings or errors, investigate (check
  API docs, rate limits, key validity) and fix the relevant tool, then
  document the fix here.
- If CV matching feels systematically too strict or too lenient after a
  few runs, note it here and adjust the 70% threshold or matching approach
  by agreement with the user — don't silently change it.
- If the duration/visa keyword heuristics in `tools/job_filters.py` are
  letting through or excluding things they shouldn't, update the heuristics
  and document the change and why here.
