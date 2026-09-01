#!/bin/bash
# Invoked by launchd on a fixed schedule (see
# ~/Library/LaunchAgents/com.marbella.internship-tracker.plist). Runs the
# weekly internship search workflow via a non-interactive Claude Code
# session, since CV matching needs real reasoning, not a plain script.
#
# Scheduled for exactly 3 fixed calendar dates (Sep 7/14/21, 2026) rather
# than an open-ended recurring cron -- this is a portfolio project, not
# meant to run indefinitely. After those 3 dates, this script and the
# launchd job have nothing left to fire on; see the plist for cleanup
# instructions.

set -euo pipefail

PROJECT_DIR="/Users/marbellaelpantja/Documents/Claude Code Agentic Workflow/Internship Search Automation"
LOG_FILE="$PROJECT_DIR/logs/weekly_run_$(date +%Y%m%d_%H%M%S).log"

cd "$PROJECT_DIR"

/Users/marbellaelpantja/.local/bin/claude -p \
  "Read and execute workflows/weekly_internship_search.md end to end, following every step exactly as written. Summarize what you did at the end: how many new postings were added per role, whether the 20-cap was hit, and whether any source failed." \
  --permission-mode bypassPermissions \
  --output-format text \
  > "$LOG_FILE" 2>&1

echo "Run completed. Log: $LOG_FILE"
