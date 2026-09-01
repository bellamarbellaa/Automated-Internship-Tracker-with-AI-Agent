import base64
from email.mime.text import MIMEText

from tools.google_auth import GMAIL_SEND_SCOPE, get_credentials

ROLE_ORDER = ["Business Analyst", "Data Analyst", "Consultant"]


def build_digest_email(postings: list[dict], source_status: dict, to_address: str) -> MIMEText:
    grouped: dict[str, list[dict]] = {role: [] for role in ROLE_ORDER}
    for posting in postings:
        grouped.setdefault(posting.get("role", "Other"), []).append(posting)

    lines = []
    for role in ROLE_ORDER:
        role_postings = grouped.get(role, [])
        if not role_postings:
            continue
        lines.append(f"\n{role} ({len(role_postings)})")
        for p in role_postings:
            lines.append(
                f"- {p['company']} — {p['title']} ({p['location']}, posted {p['posted_date']}, "
                f"match {p['match_percent']}%)\n  {p['url']}"
            )

    lines.append("\n---")
    for source, status in source_status.items():
        if status.get("success"):
            lines.append(f"{source}: ok")
        else:
            lines.append(f"{source}: failed ({status.get('error')})")

    body = "\n".join(lines)
    message = MIMEText(body)
    message["to"] = to_address
    message["subject"] = f"Internship digest — {len(postings)} new posting(s)"
    return message


def send_digest(service, postings: list[dict], source_status: dict, to_address: str) -> None:
    if not postings:
        return

    message = build_digest_email(postings, source_status, to_address)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


if __name__ == "__main__":
    import json
    import os
    import sys

    from dotenv import load_dotenv
    from googleapiclient.discovery import build

    load_dotenv()
    payload = json.load(sys.stdin)
    to_address = os.environ["DIGEST_EMAIL_TO"]

    creds = get_credentials([GMAIL_SEND_SCOPE])
    service = build("gmail", "v1", credentials=creds)

    send_digest(service, payload["postings"], payload["source_status"], to_address)
