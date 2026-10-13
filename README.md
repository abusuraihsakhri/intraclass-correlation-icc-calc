# Intraclass Correlation (ICC) Calculator

A browser and Python calculator for **balanced-design intraclass correlation coefficients**, together with a separate **cluster design effect** calculation.

## Features

- Calculate Shrout–Fleiss **ICC(1,1), ICC(1,k), ICC(2,1), ICC(2,k), ICC(3,1), and ICC(3,k)**.
- One-way random, two-way random *absolute agreement*, and two-way mixed *consistency* estimates.
- Paste a complete numeric subject-by-rater matrix, or upload a numeric CSV/TSV, and download a result CSV.
- Compute design effect from **cluster size and a separately specified within-cluster ICC**.
- Python standard-library calculation, ANOVA-summary batch CLI, and FastAPI endpoint (`POST /api/icc`).
- Existing, separate experimental audit CLI/API remains available.

## Use in your browser

The standalone calculator is in [web/index.html](web/index.html). Open it locally or serve the `web/` directory:

```bash
python -m http.server 8001 --directory web
```

Visit `http://localhost:8001/`. Calculations run entirely in JavaScript; no backend or browser-Python runtime is necessary. Modern Chromium, Firefox, and Safari are targeted; automated numerical JavaScript tests run in Node.js.

**Input format:** each line is one subject, each comma/tab-separated value is a rater's measurement. The same raters must score every subject. At least two subjects and two raters are required, and missing values are not supported.

Example:

```csv
Rater A,Rater B
1,2
2,3
3,4
4,5
```

For this dataset, ICC(3,1) is 1 (perfect consistency), whereas ICC(2,1) is approximately 0.769231 because the second rater consistently scores one unit higher.

## Python installation and usage

Python 3.10+:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Compute all six ICC forms using mean squares:

```bash
python icc_calc.py single --subjects 4 --raters 2 \
  --ms-between 3.333333333333 --ms-within 0.5 \
  --ms-rater 2 --ms-error 0
```

`ms_between` is the subject mean square (MSR), `ms_within` the one-way within-subject mean square (MSW), `ms_rater` the rater mean square (MSC), and `ms_error` the two-way error mean square (MSE). If MSC and MSE are omitted, only the one-way ICC(1) forms are estimated. Undefined estimates are returned as `null`, not zero.

Batch processing accepts one ANOVA summary per row:

```bash
python icc_calc.py batch -i sample.csv -o results.csv
```

Required CSV columns: `subjects,raters,ms_between,ms_within`. Optional pairs: `ms_rater,ms_error` and `cluster_size,cluster_icc`. The output includes the six ICC estimates and design effect, where estimable. The installed command `icc-anova` exposes the same interface.

For raw matrices, Python callers can use `from icc_calc import calculate_from_ratings` and pass a rectangular `list[list[float]]`.

## API and legacy audit utilities

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

- `POST /api/icc` with `{"ratings":[[1,2],[2,3],[3,4],[4,5]]}` returns ICC point estimates and mean squares.
- `GET /health` and `GET /metrics` provide basic status.
- The preexisting `/api/audit`, `/api/chat`, and `/api/audit/logs` endpoints remain available.
- Legacy audit commands: `python cli.py audit`, `python cli.py batch`, `python cli.py chat`, and `python cli.py verify-audit`.

The legacy worker thresholds and mock chat responses are **not statistical ICC analyses, diagnostic recommendations, or clinical standards validations**. Do not expose the unauthenticated audit API to an untrusted network. The audit log and its random HMAC key are kept in process memory unless `AUDIT_SECRET_KEY` is provided; neither persistence nor independently trusted storage is implemented. The identifier guard is heuristic, **not a guarantee of PHI deidentification**.

## Statistical assumptions and reporting

ICC form selection depends on model, fixed/random raters, and whether absolute agreement or consistency matters. Results here are **point estimates only**; confidence intervals and significance tests are not implemented. Negative ICC estimates are preserved. Do not substitute an interrater ICC for a study's within-cluster ICC without a justified model. The displayed equal-size-cluster design effect is `1 + (m - 1) × rho`.

Reference: Koo TK, Li MY. *A Guideline of Selecting and Reporting Intraclass Correlation Coefficients for Reliability Research.* J Chiropr Med. 2016;15:155–163. [doi:10.1016/j.jcm.2016.02.012](https://doi.org/10.1016/j.jcm.2016.02.012).

## Privacy, testing, and license

The static browser calculator processes input locally without transmitting ratings to a server or loading external scripts. Avoid patient-identifiable input. CLI/API processing is local to the deployment, subject to the operator's networking and logging configuration.

Tests include Python reference cases, error handling, CSV processing, audit HMAC tampering, and native JavaScript numerical tests:

```bash
python -m pytest -q
node --test web/test_icc.js
```

CI checks Python 3.10–3.12 and Node 22. A separate workflow is provided for GitHub Pages when repository Pages is enabled.

Licensed under [MIT](LICENSE). Maintained by Dr. Abu Suraih Sakhri.
