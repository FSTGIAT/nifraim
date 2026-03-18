#!/usr/bin/env python3
"""
AI Chat Test Script — Tests context quality and response accuracy.

Usage:
    cd backend
    source venv/bin/activate
    python test_ai_chat.py [--base-url http://localhost:8000] [--email test@test.com] [--password test123]

Outputs a markdown report to stdout.
"""

import argparse
import json
import time
import sys

import httpx


TEST_QUESTIONS = [
    ("מה סך הפרמיות שלי?", "Production totals"),
    ("מה סך הפרמיה מאקסלנס?", "Per-company production"),
    ("כמה לקוחות יש לי בגמל?", "Product type"),
    ("מה סטטוס ההתאמות שלי?", "Comparison overview"),
    ("כמה לקוחות לא משולמים יש לי מהפניקס?", "Unpaid per company"),
    ("מה סך העמלות שהפניקס חייבים לי?", "Commission owed by company"),
    ("מה סך העמלה שקיבלתי מכל חברה?", "Commission breakdown"),
    ("הראה לי את הלקוחות עם הפרמיה הכי גבוהה", "Top clients"),
    ("מי הלקוח עם הצבירה הכי גבוהה?", "Top accumulation"),
    ("מה שיעור העמלה שלי באקסלנס?", "Commission rates"),
    ("אילו לקוחות מהפניקס לא מופיעים בנפרעים?", "Unpaid names by company"),
    ("מה סך ההפקדות בדוח ההיקפים?", "Volume data"),
    ("כמה לקוחות יש לי בסך הכל?", "Basic count"),
    ("מה המצב של ישראל כהן?", "Customer search"),
    ("תן לי סיכום של כל התיק שלי", "Overall summary"),
]


def login(client: httpx.Client, base_url: str, email: str, password: str) -> str:
    """Login and return JWT token."""
    resp = client.post(f"{base_url}/api/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_sources(client: httpx.Client, base_url: str, token: str) -> dict:
    """Get AI data sources."""
    resp = client.get(f"{base_url}/api/ai/sources", headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()


def ask_question(client: httpx.Client, base_url: str, token: str, question: str) -> tuple[str, float]:
    """Send a question via SSE and collect the full response. Returns (response_text, latency_seconds)."""
    start = time.time()
    full_text = ""

    with client.stream(
        "POST",
        f"{base_url}/api/ai/chat",
        json={"question": question, "history": []},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60.0,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            data = json.loads(line[6:])
            if data.get("done"):
                break
            if "text" in data:
                full_text += data["text"]

    latency = time.time() - start
    return full_text.strip(), latency


def main():
    parser = argparse.ArgumentParser(description="AI Chat Test Script")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--email", default="test@test.com", help="Login email")
    parser.add_argument("--password", default="test123", help="Login password")
    parser.add_argument("--context-only", action="store_true", help="Only dump context, don't ask questions")
    args = parser.parse_args()

    client = httpx.Client()

    # Step 1: Login
    print("# AI Chat Test Report\n", file=sys.stderr)
    print("Logging in...", file=sys.stderr)
    try:
        token = login(client, args.base_url, args.email, args.password)
        print(f"Logged in as {args.email}", file=sys.stderr)
    except Exception as e:
        print(f"Login failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Get sources
    print("Fetching data sources...", file=sys.stderr)
    sources = get_sources(client, args.base_url, token)
    print(f"Sources: {json.dumps(sources, ensure_ascii=False, indent=2)}", file=sys.stderr)

    # Step 3: Dump context via a dummy question
    print("\nFetching raw context...", file=sys.stderr)
    try:
        # Use the sources endpoint info — context is built server-side
        # We can test with a minimal question to see what context is built
        context_response, _ = ask_question(client, args.base_url, token, "תן לי סיכום קצר של הנתונים שלי")
        print(f"Context test response length: {len(context_response)} chars", file=sys.stderr)
    except Exception as e:
        print(f"Context fetch failed: {e}", file=sys.stderr)

    if args.context_only:
        print("\n## Context Test Response\n")
        print(context_response)
        return

    # Step 4: Run test questions
    print(f"\nRunning {len(TEST_QUESTIONS)} test questions...\n", file=sys.stderr)

    # Output markdown report
    print("# AI Chat Test Report\n")
    print(f"**Server:** {args.base_url}")
    print(f"**User:** {args.email}")
    print(f"**Sources:** {len(sources.get('sources', []))} data sources")
    for s in sources.get("sources", []):
        print(f"  - {s['type']}: {s.get('label', '')} ({s.get('filename', '')})")
    print()

    total_latency = 0
    results = []

    for i, (question, test_label) in enumerate(TEST_QUESTIONS, 1):
        print(f"  [{i}/{len(TEST_QUESTIONS)}] {test_label}...", file=sys.stderr)
        try:
            response, latency = ask_question(client, args.base_url, token, question)
            total_latency += latency
            results.append((question, test_label, response, latency, None))
        except Exception as e:
            results.append((question, test_label, "", 0, str(e)))
            print(f"    ERROR: {e}", file=sys.stderr)

    # Print results
    print("## Results\n")
    for i, (question, test_label, response, latency, error) in enumerate(results, 1):
        print(f"### Q{i}: {question}")
        print(f"**Test:** {test_label} | **Latency:** {latency:.1f}s\n")
        if error:
            print(f"**ERROR:** {error}\n")
        else:
            print(f"{response}\n")
        print("---\n")

    # Summary
    print("## Summary\n")
    print(f"| Metric | Value |")
    print(f"|--------|-------|")
    print(f"| Total questions | {len(results)} |")
    print(f"| Successful | {sum(1 for _, _, _, _, e in results if e is None)} |")
    print(f"| Failed | {sum(1 for _, _, _, _, e in results if e is not None)} |")
    print(f"| Total latency | {total_latency:.1f}s |")
    print(f"| Avg latency | {total_latency / max(1, len(results)):.1f}s |")

    client.close()


if __name__ == "__main__":
    main()
