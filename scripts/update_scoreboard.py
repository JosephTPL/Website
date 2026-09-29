#!/usr/bin/env python3
"""Research and update the weekly private-market scoreboard.

This script never writes partial or unsourced research. It prepares a complete
replacement in memory, validates every qualifying deal, then atomically replaces
content/settings/weekly.json only when the response passes every check.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
WEEKLY_PATH = ROOT / "content" / "settings" / "weekly.json"
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"
VALID_CATEGORIES = {"funding", "valuation", "ipo_filing", "ipo_pricing", "exit"}
IPO_CATEGORIES = {"ipo_filing", "ipo_pricing", "exit"}


class ScoreboardError(RuntimeError):
    """A response was unsafe to publish."""


def completed_week(today: date) -> tuple[date, date]:
    """Return the most recently completed Monday through Sunday period."""
    end = today - timedelta(days=today.weekday() + 1)
    return end - timedelta(days=6), end


def period_text(start: date, end: date) -> str:
    if start.year == end.year and start.month == end.month:
        return f"{start.strftime('%B')} {start.day}\N{EN DASH}{end.day}, {end.year}"
    if start.year == end.year:
        return f"{start.strftime('%B')} {start.day}\N{EN DASH}{end.strftime('%B')} {end.day}, {end.year}"
    return f"{start.strftime('%B')} {start.day}, {start.year}\N{EN DASH}{end.strftime('%B')} {end.day}, {end.year}"


def source_ok(source: object) -> bool:
    return isinstance(source, dict) and isinstance(source.get("label"), str) and source["label"].strip() and isinstance(source.get("url"), str) and re.fullmatch(r"https?://[^\s]+", source["url"].strip()) is not None


def number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScoreboardError(f"{field} must be a numeric USD amount.")
    if value < 0:
        raise ScoreboardError(f"{field} cannot be negative.")
    return float(value)


def parse_model_json(response: dict) -> dict:
    texts = [block.get("text", "") for block in response.get("content", []) if block.get("type") == "text"]
    raw = "\n".join(texts).strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScoreboardError("Anthropic did not return a single valid JSON object.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("deals"), list):
        raise ScoreboardError("Anthropic response is missing the required deals list.")
    return data


def validate_deals(raw_deals: list[object], start: date, end: date) -> list[dict]:
    deals: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in raw_deals:
        if not isinstance(raw, dict):
            raise ScoreboardError("Each deal must be an object.")
        required = ("company", "date", "category", "summary", "sources")
        if any(not raw.get(field) for field in required):
            raise ScoreboardError("Every deal needs company, date, category, summary, and sources.")
        category = str(raw["category"]).strip()
        if category not in VALID_CATEGORIES:
            raise ScoreboardError(f"Unsupported deal category: {category}.")
        try:
            deal_date = datetime.strptime(str(raw["date"]), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ScoreboardError("Every deal date must use YYYY-MM-DD.") from exc
        if not start <= deal_date <= end:
            raise ScoreboardError(f"{raw['company']} falls outside the requested week.")
        sources = raw["sources"]
        if not isinstance(sources, list) or not sources or not all(source_ok(source) for source in sources):
            raise ScoreboardError(f"{raw['company']} is missing a valid direct source URL.")
        private_company = raw.get("private_company")
        if not isinstance(private_company, bool) or not private_company:
            raise ScoreboardError(f"{raw['company']} is not confirmed as a private-company event.")
        amount = raw.get("amount_usd")
        valuation = raw.get("valuation_usd")
        if category == "funding":
            amount = number(amount, "amount_usd")
            if amount < 100_000_000:
                continue
        elif category == "valuation":
            valuation = number(valuation, "valuation_usd")
            if valuation < 1_000_000_000:
                continue
        else:
            amount = None if amount is None else number(amount, "amount_usd")
            valuation = None if valuation is None else number(valuation, "valuation_usd")
        key = (str(raw["company"]).strip().casefold(), deal_date.isoformat(), category)
        if key in seen:
            raise ScoreboardError(f"Duplicate qualifying deal for {raw['company']}.")
        seen.add(key)
        deals.append({
            "company": str(raw["company"]).strip(),
            "date": deal_date.isoformat(),
            "category": category,
            "round_type": str(raw.get("round_type", "")).strip(),
            "amount_usd": amount,
            "valuation_usd": valuation,
            "summary": str(raw["summary"]).strip(),
            "sources": [{"label": source["label"].strip(), "url": source["url"].strip()} for source in sources],
        })
    return deals


def usd(value: float) -> str:
    if value >= 1_000_000_000:
        rendered = f"{value / 1_000_000_000:.2f}".rstrip("0").rstrip(".")
        return f"${rendered}B"
    rendered = f"{value / 1_000_000:.0f}"
    return f"${rendered}M"


def sources_for(deals: list[dict]) -> list[dict]:
    unique: list[dict] = []
    seen: set[str] = set()
    for deal in deals:
        for source in deal["sources"]:
            if source["url"] not in seen:
                seen.add(source["url"])
                unique.append(source)
    return unique


def plural(count: int, singular: str, plural_text: str | None = None) -> str:
    return singular if count == 1 else (plural_text or singular + "s")


def scoreboard_from(deals: list[dict]) -> list[dict]:
    funding = [deal for deal in deals if deal["category"] == "funding"]
    billion_rounds = [deal for deal in funding if deal["amount_usd"] >= 1_000_000_000]
    unicorns = [deal for deal in deals if deal["category"] == "valuation"]
    ipo_events = [deal for deal in deals if deal["category"] in IPO_CATEGORIES]
    raised = sum(deal["amount_usd"] for deal in funding)
    return [
        {"value": usd(raised) if raised else "$0", "label": "Raised in private rounds", "note": f"{len(funding)} disclosed {plural(len(funding), 'round')} of $100M+", "sources": sources_for(funding)},
        {"value": str(len(billion_rounds)), "label": "$1B+ rounds", "note": f"{len(billion_rounds)} private {plural(len(billion_rounds), 'financing')} at $1B+", "sources": sources_for(billion_rounds)},
        {"value": str(len(unicorns)), "label": "New unicorns", "note": f"{len(unicorns)} newly reported $1B+ {plural(len(unicorns), 'valuation')}", "sources": sources_for(unicorns)},
        {"value": str(len(ipo_events)), "label": "IPO filings, pricings & exits", "note": f"{len(ipo_events)} confirmed {plural(len(ipo_events), 'event')}", "sources": sources_for(ipo_events)},
    ]


def prompt(start: date, end: date) -> str:
    return f'''Research qualifying global private-market deals announced from {start.isoformat()} through {end.isoformat()}, inclusive. Use web search and primary company announcements, SEC or exchange filings, Reuters, Bloomberg, Financial Times, or similarly established reporting. Do not use rumors, aggregators, undated claims, targets, or events without a direct URL.

Return JSON only, with this exact top-level schema: {{"deals": [ ... ]}}. Each deal object must contain company, date (YYYY-MM-DD), category, private_company, round_type, amount_usd, valuation_usd, summary, and sources. category must be one of funding, valuation, ipo_filing, ipo_pricing, exit. sources must be a non-empty list of objects with label and direct https URL.

Include only: private-company funding rounds of at least 100000000 USD; newly reported private-company valuations of at least 1000000000 USD; confirmed IPO filings, IPO pricings, or exits involving private companies. For funding, amount_usd is required. For valuation, valuation_usd is required. For IPO categories, use null when an amount or valuation is unavailable. Do not include a deal unless its source supports the specific announced date and claim.'''


def call_anthropic(api_key: str, start: date, end: date) -> dict:
    payload = {
        "model": MODEL,
        "max_tokens": 8000,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": prompt(start, end)}],
    }
    request = Request(API_URL, data=json.dumps(payload).encode(), headers={
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "web-search-2025-03-05",
    }, method="POST")
    try:
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        raise ScoreboardError(f"Anthropic API request failed with HTTP {exc.code}.") from exc
    except (URLError, json.JSONDecodeError) as exc:
        raise ScoreboardError("Anthropic API request did not return valid JSON.") from exc


def write_json(path: Path, payload: dict) -> None:
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        json.dump(payload, temp, indent=2, ensure_ascii=False)
        temp.write("\n")
        temp_path = Path(temp.name)
    temp_path.replace(path)


def pr_body(period: str, deals: list[dict]) -> str:
    lines = [f"## Scoreboard: {period}", "", "Every counted deal has a direct source.", ""]
    if not deals:
        return "\n".join(lines + ["No qualifying, sourced events were found for this period."])
    for deal in deals:
        sources = ", ".join(f"[{source['label']}]({source['url']})" for source in deal["sources"])
        details = deal["round_type"] or deal["category"].replace("_", " ")
        lines.append(f"- **{deal['company']}** ({deal['date']}, {details}): {deal['summary']} Sources: {sources}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", help="Override today's date (YYYY-MM-DD) for a reproducible run.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the proposed weekly JSON without writing it.")
    parser.add_argument("--pr-body", type=Path, help="Write the generated pull-request body to this path.")
    parser.add_argument("--github-output", type=Path, help="Write title and period values for GitHub Actions.")
    args = parser.parse_args()
    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else date.today()
    start, end = completed_week(today)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ScoreboardError("ANTHROPIC_API_KEY is required. The weekly file was not changed.")
    response = call_anthropic(api_key, start, end)
    deals = validate_deals(parse_model_json(response)["deals"], start, end)
    existing = json.loads(WEEKLY_PATH.read_text())
    updated = dict(existing)
    period = period_text(start, end)
    updated["period"] = period
    updated["next_update"] = "Sunday, " + (end + timedelta(days=7)).strftime("%B %-d")
    updated["scoreboard"] = scoreboard_from(deals)
    updated["scoreboard_deals"] = deals
    if args.dry_run:
        print(json.dumps(updated, indent=2, ensure_ascii=False))
    else:
        write_json(WEEKLY_PATH, updated)
    if args.pr_body:
        args.pr_body.write_text(pr_body(period, deals) + "\n")
    if args.github_output:
        with args.github_output.open("a") as output:
            output.write(f"period={period}\npr_title=Scoreboard: {period}\n")
    print(f"Validated {len(deals)} sourced deals for {period}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScoreboardError as exc:
        print(f"Scoreboard update stopped: {exc}", file=sys.stderr)
        raise SystemExit(2)
