# Stand switches: what is real and what is an imitation

The CRM ships twelve `VULN_*` switches (active only with `CRM_MODE=vuln`, never in production — the app refuses
to start). Each has a clean/vuln test pair in `backend/tests/test_vuln_pairs.py`. Not every switch produces a
real exploit chain on its own; the table says which ones are honest demonstrations and which only emit the
*trace* an attack leaves, because the vulnerable consumer is outside the stand.

| Flag | Clean behaviour | Vuln behaviour | Real or imitation |
|---|---|---|---|
| `VULN_SQLI_SEARCH` | ORM parameter | raw string concatenation in `search_by_name` | **real** (SQLite/PostgreSQL) |
| `VULN_IDOR_CUSTOMER` | manager sees own clients (404 otherwise) | any client by id | **real** |
| `VULN_MASS_ASSIGNMENT` | `role` dropped from `PATCH /api/auth/me` | `role` applied | **real** |
| `VULN_PATH_TRAVERSAL_EXPORT` | file name only, inside `EXPORT_DIR` | path joined as given | **real** |
| `VULN_SSRF_WEBHOOK` | webhook host must resolve to a public address, no redirects | any URL fetched, body echoed | **real** |
| `VULN_NO_RATE_LIMIT_LOGIN` | lockout per account and per address | no lockout | **real** |
| `VULN_CSV_INJECTION` | formula prefixes quoted in every cell | cells as typed | **real** in a spreadsheet |
| `VULN_PRICE_TAMPERING` | price from the catalogue | `price_kzt` from the request | **real** |
| `VULN_PAYMENT_SIGNATURE` | HMAC + timestamp required | signature skipped | **real** |
| `VULN_STORED_XSS_NOTES` | body HTML-escaped once by the API; the SPA inserts it as HTML | body returned raw | **real in the stand browser only** — the SPA renders the API string as HTML, so the payload runs where the stand is viewed; the API itself only stores and returns text |
| `VULN_XXE_1C_IMPORT` | defusedxml, DOCTYPE/ENTITY refused after decoding | the parser accepts the document and the endpoint answers 500 "XXE payload accepted" | **imitation** — the stdlib parser does not resolve external entities, no file is read; the signal is the accepted DTD and the error text |
| `VULN_OPEN_REDIRECT` | `next` must be a relative path | `next` reflected in `X-Redirect-To` | **imitation** — the API never issues a 3xx; the SPA decides whether to follow the header |

Rules that apply to every switch:

- a flag is read through `stand_flags.vuln_active()`, which returns `False` unless `CRM_MODE=vuln`;
- `PATCH /api/stand` replaces the whole flag set (there is no "add one flag" call) and is admin-only;
- the simulator records the stand snapshot in every journal row (`stand` field) so a label can be audited later;
- the labels of the training data do not come from these flags: the dataset builder labels from facts visible in
  the event, and the test set is annotated by people who never see the flag state.
