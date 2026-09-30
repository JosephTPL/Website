# SPV tracker: data method

Source: SEC EDGAR Form D and Form D/A filings, the notice a private fund files when it sells securities under Regulation D. Every row in `spvs.csv` comes from a filing on EDGAR; nothing is estimated or taken from secondary sources.

Pulled: 2026-10-01 (latest filing in the file: 2026-09-29).

## How vehicles were found

1. EDGAR full-text search for each company name in Form D filings: Anthropic (121 filings), Anduril (120), Stripe (58), Databricks (47), OpenAI (47), Saronic (29).
2. Every matching filing's `primary_doc.xml` was fetched and parsed (422 filings).
3. Filings were grouped into vehicles by issuer CIK. Linqto files every series under one CIK (1841356), so its series are split using the series label inside each filing ("Linqto Liquidshares LLC - Anthropic - 9").
4. Each row holds the vehicle's latest filing. Form D/A amendments restate cumulative totals, so the latest filing supersedes earlier ones.

## What a row means

- `sold_usd`, `investors`: cumulative figures as of `latest_filed`, as self-reported by the issuer. They are not audited and are updated only when the vehicle files again.
- `offering_usd`: target size. Blank means the filing states "Indefinite".
- `min_investment_usd`: 0 means the filing reports no minimum, not a $0 check.
- `platform`: the administrator named in the filing (for example, Sydecar administers the CGF2021 LLC series).
- `manager`: the first related party identified as manager or general partner. Blank when the filing lists only the administrator's officers.
- `exemption`: 506(b) cannot be generally solicited; 506(c) can be publicly marketed to verified accredited investors.

Form D does not report share price, implied valuation, carry, management fees, or whether a vehicle is still open. The tracker does not show them.

## Known limits

- Discovery is name-based. A vehicle whose EDGAR name does not include the company (e.g. "Series 14 of XYZ Fund LLC") is missed unless the name appears elsewhere in the filing text. Treat counts as a floor.
- The filing does not state what the vehicle holds. A name match is taken to mean the vehicle targets that company.
- Some vehicles may invest through other vehicles (a feeder into a master), so sums across vehicles can double count.
- Figures are as filed. Examples kept as filed: "VM OpenAI 1" reports $2.87M sold with 0 investors; "MW LSVC Anthropic" checks no Rule 506 box.

## Excluded matches

| Search | Issuer | Reason |
|---|---|---|
| Anthropic | Anthropic Capital Fund, LP | Unrelated hedge fund sharing the name |
| OpenAI | OpenAI Startup Fund I, L.P.; OpenAI Startup Fund II, L.P.; OpenAI Startup Fund SPV I–VI, L.P. | OpenAI's own venture fund; invests in other startups |
| OpenAI | Aestas Management Company, LLC | Managed by OpenAI GP, L.L.C.; not a third-party SPV |
| Stripe | Stripe, Inc. | Company's own primary offering |
| Databricks | Databricks, Inc. (both filer names) | Company's own primary offering |
| Saronic | Saronic Technologies, Inc. | Company's own primary offering |
| Stripe | Stripe Milton LLC; Blue Stripe, LLC; Green Stripe Naturals Ltd.; Blue Stripe Software Inc; Parc Productions Ltd Liability Co; OrthoHelix Surgical Design Inc | Unrelated businesses; name match only |

Included after review: Bloom Opportunities Fund series "BVP VIII–XI", which EDGAR previously listed as "Bloom Anduril I–III" and "Anthropic I".

## Refreshing the data

Re-run the same search and keep the same columns. When a vehicle files a new D/A, replace its row with the new `latest_accession`, `latest_form`, `latest_filed` and the restated totals; keep `first_filed`. Add new vehicles as new rows.
