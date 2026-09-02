Automated Internship Tracker with AI Agent

An AI-powered internship automation system built with Claude Code to automate the process of discovering, filtering, and tracking internship opportunities.

Features
1) Automated retrieval — Built an automated workflow using a Claude Code agent that retrieves and processes internship listings from three job platforms through APIs on a weekly basis over one month.
2) CV-based matching — Developed a matching workflow that evaluates opportunities against three tailored CV profiles, allowing internships to be matched based on a multidisciplinary background.
3) Custom filtering — Implemented multiple constraints and filtering criteria, including location, industry, role, and other personal preferences, to identify opportunities that are actually relevant.
4) Google Sheets & Gmail integration — Connected the workflow to Google Sheets and Gmail to automatically organize and display matched opportunities once a week for easier tracking and review.

How it works
The agent pulls internship listings from three job platform APIs on a weekly schedule.
Each listing is evaluated against three tailored CV profiles to find the best fit.
Listings are filtered by location, industry, role, and other personal preferences.
Matched opportunities are written to a Google Sheet and a summary is sent via Gmail once a week.

Tech stack
Python
Claude Code (agent orchestration)
Job platform APIs: Adzuna, SerpApi, Jooble
Google Sheets API
Gmail API
Setup

Setup
Create a .env file in the project root with the following variables (not committed to the repo):

ADZUNA_APP_ID=
ADZUNA_APP_KEY=
SERPAPI_API_KEY=
JOOBLE_API_KEY=
TRACKER_SPREADSHEET_ID=
DIGEST_EMAIL_TO=
