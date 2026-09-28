#!/usr/bin/env python3
"""Fetch and normalize SEC Form D filings for The Private Ledger.

This script is intentionally separate from scripts/build.py. It uses the SEC's
public EDGAR endpoints, requires SEC_USER_AGENT, and caches raw SEC responses
under .cache/sec/ so routine runs remain polite and reproducible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
COMPANIES = ROOT / "content" / "companies"
DATA = ROOT / "content" / "data"
CACHE = ROOT / ".cache" / "sec"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions"
SEC_SEARCH = "https://efts.sec.gov/LATEST/search-index"


class SecClient:
    """Small cached client that stays below the SEC's published rate limit."""

    def __init__(self, user_agent: str, refresh: bool = False) -> None:
        self.user_agent = user_agent
        self.refresh = refresh
        self.last_request = 0.0
        certificate_file = os.environ.get("SSL_CERT_FILE")
        if not certificate_file:
            for candidate in ("/etc/ssl/cert.pem", "/private/etc/ssl/cert.pem"):
                if Path(candidate).exists():
                    certificate_file = candidate
                    break
        self.ssl_context = ssl.create_default_context(cafile=certificate_file)
        CACHE.mkdir(parents=True, exist_ok=True)

    def get(self, url: str) -> bytes:
        suffix = ".json" if ".json" in url else ".xml" if ".xml" in url else ".txt"
        cached = CACHE / (hashlib.sha256(url.encode()).hexdigest() + suffix)
        if cached.exists() and not self.refresh:
            return cached.read_bytes()
        for attempt in range(4):
            delay = max(0.0, 0.20 - (time.monotonic() - self.last_request))
            if delay:
                time.sleep(delay)
            request = Request(url, headers={"User-Agent": self.user_agent})
            self.last_request = time.monotonic()
            try:
                with urlopen(request, timeout=30, context=self.ssl_context) as response:
                    payload = response.read()
                cached.write_bytes(payload)
                return payload
            except HTTPError as error:
                if error.code in (429, 503) and attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise
            except URLError:
                if attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise
        raise RuntimeError("SEC request retries exhausted")

    def json(self, url: str) -> dict[str, Any]:
        return json.loads(self.get(url).decode("utf-8"))


def text(value: Any) -> str:
    return str(value or "").strip()


def local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def find_first(element: ET.Element, names: set[str]) -> str:
    for node in element.iter():
        if local_name(node) in names and text(node.text):
            return text(node.text)
    return ""


def find_node(element: ET.Element, names: set[str]) -> ET.Element | None:
    for node in element.iter():
        if local_name(node) in names:
            return node
    return None


def child_text(element: ET.Element, names: set[str]) -> str:
    for child in element:
        if local_name(child) in names and text(child.text):
            return text(child.text)
    return ""


def money(value: str) -> str:
    value = text(value)
    if not value:
        return "Not disclosed"
    if value.lower() == "indefinite":
        return "Indefinite"
    try:
        return "${:,.0f}".format(float(value.replace(",", "")))
    except ValueError:
        return value


def numeric_money(value: str) -> float | None:
    try:
        return float(re.sub(r"[^0-9.]", "", value))
    except ValueError:
        return None


def truthy(value: str) -> bool:
    return text(value).lower() in {"true", "1", "yes", "y"}


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def looks_like_vehicle(name: str) -> bool:
    return bool(re.search(r"\b(fund|spv|series|vehicle|holdings|capital|partners|feeder)\b", name, re.I))


def parse_people(root: ET.Element) -> list[dict[str, str]]:
    people: list[dict[str, str]] = []
    for node in root.iter():
        if local_name(node) not in {"relatedPersonInfo", "relatedPerson"}:
            continue
        name_node = find_node(node, {"relatedPersonName", "personName", "name"})
        if name_node is None:
            name_node = node
        first = find_first(name_node, {"firstName"})
        middle = find_first(name_node, {"middleName"})
        last = find_first(name_node, {"lastName"})
        name = " ".join(part for part in (first, middle, last) if part) or find_first(node, {"entityName", "name"})
        roles = [text(child.text) for child in node.iter() if local_name(child) in {"relationship", "relationshipType"} and text(child.text)]
        if name:
            people.append({"name": name, "roles": ", ".join(dict.fromkeys(roles)) or "Related person"})
    return people


def parse_security_types(root: ET.Element) -> list[str]:
    labels = {
        "isEquityType": "Equity",
        "isDebtType": "Debt",
        "isOptionToAcquireType": "Option to acquire",
        "isPooledInvestmentFundType": "Pooled investment fund",
        "isOtherType": "Other",
    }
    found = [label for tag, label in labels.items() if truthy(find_first(root, {tag}))]
    other = find_first(root, {"descriptionOfOtherType", "otherTypeDescription"})
    if other and "Other" not in found:
        found.append(other)
    return found or ["Not disclosed"]


def parse_form_d(xml: bytes, company: dict[str, Any], filing: dict[str, str]) -> dict[str, Any]:
    root = ET.fromstring(xml)
    issuer = find_node(root, {"primaryIssuer", "issuer"})
    if issuer is None:
        issuer = root
    filer_name = find_first(issuer, {"entityName", "issuerName", "name"}) or company["name"]
    filer_cik = find_first(issuer, {"cik", "issuerCik"}) or filing["cik"]
    form_type = filing["form"]
    amendment = form_type.upper() == "D/A" or truthy(find_first(root, {"isAmendment"}))
    industry = find_first(root, {"industryGroupType", "industryGroup"}) or "Not disclosed"
    offered = money(find_first(root, {"totalOfferingAmount"}))
    sold = money(find_first(root, {"totalAmountSold"}))
    remaining = money(find_first(root, {"totalRemaining"}))
    investors = find_first(root, {"totalNumberAlreadyInvested", "numberOfInvestors"}) or "Not disclosed"
    filer_type = "fund_or_spv" if looks_like_vehicle(filer_name) else "company"
    return {
        "company_slug": company["slug"],
        "company_name": company["name"],
        "filer_name": filer_name,
        "filer_cik": str(filer_cik).zfill(10),
        "filing_id": filing["accession"],
        "filing_date": filing["filing_date"],
        "form_type": form_type,
        "is_amendment": amendment,
        "date_of_first_sale": find_first(root, {"dateOfFirstSale"}) or "Not disclosed",
        "total_offering_amount": offered,
        "total_amount_sold": sold,
        "total_remaining": remaining,
        "security_types": parse_security_types(root),
        "industry_group": industry,
        "number_of_investors": investors,
        "people": parse_people(root),
        "filing_url": filing["filing_url"],
        "filer_type": filer_type,
    }


def company_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(COMPANIES.glob("*.json")):
        record = json.loads(path.read_text())
        if record.get("status") == "Published":
            record["slug"] = record.get("slug", path.stem)
            records.append(record)
    return records


def all_submissions(client: SecClient, cik: str) -> list[dict[str, str]]:
    data = client.json(f"{SEC_SUBMISSIONS}/CIK{str(cik).zfill(10)}.json")
    groups = [data.get("filings", {}).get("recent", {})]
    for historic in data.get("filings", {}).get("files", []):
        name = historic.get("name")
        if name:
            groups.append(client.json(f"{SEC_SUBMISSIONS}/{name}"))
    filings: list[dict[str, str]] = []
    for group in groups:
        forms = group.get("form", [])
        for index, form in enumerate(forms):
            if form not in {"D", "D/A"}:
                continue
            accession = text(group.get("accessionNumber", [])[index])
            document = text(group.get("primaryDocument", [])[index])
            if not accession:
                continue
            cik_digits = str(cik).lstrip("0") or "0"
            directory = accession.replace("-", "")
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_digits}/{directory}/"
            filings.append({
                "form": form,
                "accession": accession,
                "filing_date": text(group.get("filingDate", [])[index]),
                "primary_document": document,
                "cik": str(cik).zfill(10),
                "filing_url": filing_url + (document or "index.html"),
            })
    return filings


def filing_xml_url(client: SecClient, filing: dict[str, str]) -> str:
    cik_digits = filing["cik"].lstrip("0") or "0"
    directory = filing["accession"].replace("-", "")
    primary = filing.get("primary_document", "")
    if primary.endswith(".xml"):
        # EDGAR submissions may point through an XSL viewer path such as
        # xslFormDX01/primary_doc.xml; the raw filing lives at the directory root.
        return f"{SEC_ARCHIVES}/{cik_digits}/{directory}/{primary.rsplit('/', 1)[-1]}"
    index = client.json(f"{SEC_ARCHIVES}/{cik_digits}/{directory}/index.json")
    items = index.get("directory", {}).get("item", [])
    names = [item.get("name", "") for item in items]
    candidates = [name for name in names if name.lower().endswith(".xml")]
    candidates.sort(key=lambda name: ("primary" not in name.lower(), name.lower()))
    if not candidates:
        raise ValueError("no XML document in filing directory")
    return f"{SEC_ARCHIVES}/{cik_digits}/{directory}/{candidates[0]}"


def latest_amendments(filings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the newest D or D/A for each disclosed offering identity."""
    latest: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for filing in filings:
        key = (filing["company_slug"], filing["filer_cik"], filing["date_of_first_sale"], filing["total_offering_amount"])
        previous = latest.get(key)
        if not previous or filing["filing_date"] > previous["filing_date"]:
            latest[key] = filing
    return sorted(latest.values(), key=lambda item: (item["filing_date"], item["filing_id"]), reverse=True)


def search_candidates(client: SecClient, company: dict[str, Any]) -> dict[str, Any]:
    query = f'"{company["name"]}"'
    url = SEC_SEARCH + "?" + urlencode({"q": query, "forms": "D", "from": 0, "size": 10})
    payload = client.json(url)
    candidates = []
    for hit in payload.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        ciks = source.get("ciks", []) or []
        names = source.get("display_names", []) or []
        candidates.append({
            "ciks": [str(value).zfill(10) for value in ciks],
            "names": names,
            "filing_date": source.get("file_date", ""),
            "form": source.get("form", ""),
            "accession": source.get("adsh", ""),
        })
    return {"slug": company["slug"], "company": company["name"], "query": query, "candidates": candidates}


def fetch_confirmed(client: SecClient, companies: list[dict[str, Any]], log: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for company in companies:
        cik = text(company.get("sec_cik"))
        if not cik:
            continue
        excludes = set(company.get("sec_exclude", []))
        try:
            for filing in all_submissions(client, cik):
                if filing["accession"] in excludes:
                    log.append(f"skipped {company['name']} {filing['accession']} (sec_exclude)")
                    continue
                try:
                    xml = client.get(filing_xml_url(client, filing))
                    result.append(parse_form_d(xml, company, filing))
                    log.append(f"fetched {company['name']} {filing['accession']}")
                except Exception as error:  # one bad filing must not halt the run
                    log.append(f"could not parse {company['name']} {filing['accession']}: {error}")
        except Exception as error:
            log.append(f"could not fetch submissions for {company['name']}: {error}")
    return latest_amendments(result)


def parse_master_index(payload: bytes) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    started = False
    for line in payload.decode("latin-1").splitlines():
        if not started:
            started = line.startswith("-")
            continue
        parts = line.split("|")
        if len(parts) != 5 or parts[2] not in {"D", "D/A"}:
            continue
        accession = re.search(r"(\d{10}-\d{2}-\d{6})", parts[4])
        if accession:
            rows.append({"cik": parts[0].zfill(10), "name": parts[1], "form": parts[2], "filing_date": parts[3], "accession": accession.group(1)})
    return rows


def recent_filings(client: SecClient, companies: list[dict[str, Any]], days: int, log: list[str]) -> list[dict[str, Any]]:
    known = {normalized(company["name"]) for company in companies}
    for company in companies:
        known.update(normalized(name) for name in company.get("sec_names", []))
    discoveries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for offset in range(days):
        day = date.today() - timedelta(days=offset)
        quarter = (day.month - 1) // 3 + 1
        url = f"https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{quarter}/master.{day:%Y%m%d}.idx"
        try:
            filings = parse_master_index(client.get(url))
        except HTTPError as error:
            if error.code == 404:
                continue
            log.append(f"could not fetch index for {day}: {error}")
            continue
        for filing in filings:
            if filing["accession"] in seen or normalized(filing["name"]) in known:
                continue
            seen.add(filing["accession"])
            filing["primary_document"] = ""
            filing["filing_url"] = ""
            try:
                xml_url = filing_xml_url(client, filing)
                xml = client.get(xml_url)
                placeholder = {"slug": "", "name": filing["name"]}
                parsed = parse_form_d(xml, placeholder, filing)
                amount = numeric_money(parsed["total_amount_sold"])
                if amount is not None and amount >= 50_000_000:
                    parsed.pop("company_slug", None)
                    parsed.pop("company_name", None)
                    discoveries.append(parsed)
                    log.append(f"discovered {parsed['filer_name']} {parsed['filing_id']}")
            except Exception as error:
                log.append(f"could not inspect recent filing {filing['accession']}: {error}")
    return sorted(discoveries, key=lambda item: (item["filing_date"], item["total_amount_sold"]), reverse=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch SEC Form D data for The Private Ledger.")
    parser.add_argument("--recent", type=int, metavar="DAYS", help="Discover non-tracked Form D filings from the last DAYS days")
    parser.add_argument("--refresh", action="store_true", help="Ignore cached SEC responses")
    parser.add_argument("--company", action="append", metavar="SLUG", help="Limit a run to one company slug; may be repeated")
    args = parser.parse_args()
    user_agent = text(os.environ.get("SEC_USER_AGENT"))
    if not user_agent or "@" not in user_agent:
        print("SEC_USER_AGENT is required and must include a real contact email. Nothing was fetched.", file=sys.stderr)
        return 2
    companies = company_records()
    if args.company:
        selected=set(args.company)
        companies=[company for company in companies if company['slug'] in selected]
        unknown=selected-{company['slug'] for company in companies}
        if unknown:
            parser.error('Unknown company slug(s): '+', '.join(sorted(unknown)))
    client = SecClient(user_agent, refresh=args.refresh)
    log: list[str] = []
    if args.recent is not None:
        discoveries = recent_filings(client, companies, max(1, args.recent), log)
        write_json(DATA / "form-d-new.json", {"generated_at": date.today().isoformat(), "days": max(1, args.recent), "filings": discoveries})
    else:
        filings = fetch_confirmed(client, companies, log)
        candidates = []
        for company in companies:
            if company.get("sec_cik"):
                continue
            try:
                candidates.append(search_candidates(client, company))
                log.append(f"searched candidates for {company['name']}")
            except Exception as error:
                log.append(f"could not search candidates for {company['name']}: {error}")
        write_json(DATA / "form-d.json", {"generated_at": date.today().isoformat(), "filings": filings})
        write_json(DATA / "sec-cik-candidates.json", {"generated_at": date.today().isoformat(), "candidates": candidates})
    for message in log:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
