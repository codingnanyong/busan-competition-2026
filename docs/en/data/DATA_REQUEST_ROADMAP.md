# Data Request Roadmap

COD-10 found domains where public data cannot produce a direct measure or complete Busan comparison. Every request below is for non-identifying administrative-dong aggregates, never person-level records.

## Inputs the project owner should prepare

### Access information needed now

| Item | Purpose | Needed by | Safe handling |
|---|---|---|---|
| SGIS consumer key/secret | Verify actual years and coverage for establishment, population, and boundary APIs | Before employment and boundary audit | Store as `SGIS_CONSUMER_KEY` and `SGIS_CONSUMER_SECRET` in local `.env` |
| Public Data Portal service key | Test AED, bus, and air API responses | Before collecting API proxies | Store as `DATA_GO_KR_SERVICE_KEY` in local `.env` |
| Institutional contact route | Send the direct-data requests below | Can run alongside the public-data minimum model | Provide only department name and official email |

Never paste secrets into Slack, Linear, GitHub, documentation, or chat. Public-file auditing and request drafting can continue without them.

### Fixed criteria and decisions still needed

Fixed: the geography is the 206-dong SGIS 2025 version and the data cutoff is 2026-07-31.

1. Whether institutional data and derivatives may be redistributed in deliverables, GitHub, and Docker images
2. Whether non-public data may be used for scoring without submitting the source
3. The maximum acceptable lag where a domain has no current source

## Priority requests

| Priority | Domain | Requested data | Minimum fields | Candidate publisher | Public-data gap |
|---:|---|---|---|---|---|
| 1 | Geography | Same-date Busan administrative codes and boundaries | Date, district code, dong code/name, geometry | Busan City or MOIS | Busan page shows inconsistent 205/206 totals |
| 1 | Income | Dong-level benefits or income bands | Period, dong code, persons/households, denominator, definition | Busan City and district welfare teams | Five districts publish incompatible dates/definitions |
| 1 | Employment | Resident employment, unemployment, or insurance aggregate | Period, dong code, age band, labour-status counts | Busan City and employment agencies | SGIS worker counts are workplace-based proxies |
| 1 | Safety | Crime, crash, and fire counts by type | Period, dong code, type, count, population denominator | Busan Police, Fire HQ, transport agencies | Only maps or partial aggregates were verified |
| 2 | Health | Standardized outcomes and healthcare use | Period, dong code, age/sex denominator, outcome | Public-health and insurance agencies | Facility location is not a health outcome |
| 2 | Education | Adult attainment, dropout, or outcomes | Period, dong code, age band, numerator/denominator | Education and statistics agencies | School location measures access only |
| 2 | Housing | Common-definition vacancy, old housing, and crowding | Date, dong code, dwelling/household denominator, definition | Busan City and housing teams | Two districts use different vacancy definitions |
| 3 | Environment | Citywide flood, heat, and air exposure layers | Period, coordinate/grid, value, quality flag | Busan environment and disaster teams | Flood files are fragmented and station interpolation is required |

## Conditions for a request

- Aggregate or mask small cells under the publisher's disclosure rule.
- Do not request names, addresses, phone numbers, identifiers, or person-level event narratives.
- Request denominator, deduplication rule, date, and administrative-code version.
- Request both calendar-year 2025 and January–July 2026 or a 2026-07-31 snapshot where possible.
- Ask how observed zero, uncollected, private, and not applicable are represented.
- Obtain written permission for source use and publication of aggregates, maps, and index derivatives.
- If unavailable, record the reason and the smallest publishable geography.

## Acceptance

Assign every received source a new stable ID in [DATASET_AUDIT.csv](../../data/DATASET_AUDIT.csv), then record SHA-256, period, geography, mapping rate, missingness, and licence. Institutional origin does not bypass the A/B inclusion gate.

## Sequence

1. COD-11 freezes codes, boundaries, and the population denominator.
2. Once keys exist, verify SGIS and Public Data Portal API responses.
3. Build a reproducible minimum model from eligible B-grade proxies.
4. Replace proxies with requested income, employment, health, and safety direct measures.
5. Promote only versions that pass refresh, drift, and impact review.
