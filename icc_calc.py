#!/usr/bin/env python3
"""Dependency-free, balanced-design intraclass correlation coefficients.

Shrout–Fleiss ICC(1,1), ICC(2,1), ICC(3,1) and average-measure variants.
The design effect uses a separately supplied *cluster* ICC; an interrater ICC
must not be substituted for a cluster ICC without justification.
"""
import argparse
import csv
import json
import math
from pathlib import Path


ICC_COLUMNS = ("icc_1_1", "icc_1_k", "icc_2_1", "icc_2_k", "icc_3_1", "icc_3_k")


def _nonnegative(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return number


def _count(value, label):
    number = _nonnegative(value, label)
    if number < 2 or not number.is_integer():
        raise ValueError(f"{label} must be an integer of at least 2")
    return int(number)


def _ratio(numerator, denominator):
    # A zero denominator is an unidentified statistic, not an ICC of zero.
    return None if denominator == 0 else numerator / denominator


def design_effect(cluster_size, cluster_icc):
    """Design effect for equal-size clusters: 1 + (m - 1) * rho."""
    m = float(cluster_size)
    rho = float(cluster_icc)
    if not math.isfinite(m) or m < 1:
        raise ValueError("cluster_size must be a finite number >= 1")
    if not math.isfinite(rho) or not 0 <= rho <= 1:
        raise ValueError("cluster_icc must be between 0 and 1")
    return 1 + (m - 1) * rho


def calculate_metrics(*, ms_between, ms_within, subjects, raters,
                      ms_rater=None, ms_error=None,
                      cluster_size=None, cluster_icc=None):
    """Compute ICCs from balanced ANOVA mean squares.

    ms_between: row/subject mean square (MSR).
    ms_within: within-subject mean square from a one-way model (MSW).
    ms_rater: column/rater mean square (MSC) for a two-way model.
    ms_error: residual/error mean square (MSE) for a two-way model.

    Two-way coefficients require both MSC and MSE. Estimates may be negative.
    Missing/undefined forms are returned as None, never fabricated as zero.
    """
    n, k = _count(subjects, "subjects"), _count(raters, "raters")
    msr = _nonnegative(ms_between, "ms_between")
    msw = _nonnegative(ms_within, "ms_within")
    if (ms_rater is None) != (ms_error is None):
        raise ValueError("ms_rater and ms_error must be supplied together")
    result = {
        "subjects": n, "raters": k,
        "ms_between": msr, "ms_within": msw,
        "ms_rater": None, "ms_error": None,
        "icc_1_1": _ratio(msr - msw, msr + (k - 1) * msw),
        "icc_1_k": _ratio(msr - msw, msr),
        "icc_2_1": None, "icc_2_k": None,
        "icc_3_1": None, "icc_3_k": None,
    }
    if ms_rater is not None:
        msc = _nonnegative(ms_rater, "ms_rater")
        mse = _nonnegative(ms_error, "ms_error")
        result.update(
            ms_rater=msc, ms_error=mse,
            icc_2_1=_ratio(msr - mse, msr + (k - 1) * mse + k * (msc - mse) / n),
            icc_2_k=_ratio(msr - mse, msr + (msc - mse) / n),
            icc_3_1=_ratio(msr - mse, msr + (k - 1) * mse),
            icc_3_k=_ratio(msr - mse, msr),
        )
    if (cluster_size is None) != (cluster_icc is None):
        raise ValueError("cluster_size and cluster_icc must be supplied together")
    result["design_effect"] = (
        design_effect(cluster_size, cluster_icc)
        if cluster_size is not None else None
    )
    return result


def calculate_from_ratings(ratings):
    """Compute all six ICCs from an n-subject by k-rater complete matrix.

    Rows represent subjects; columns represent the *same* raters for all rows.
    An unbalanced matrix, missing data, or nonfinite values is rejected.
    """
    rows = [list(row) for row in ratings]
    n = len(rows)
    if n < 2:
        raise ValueError("At least two subjects are required")
    k = len(rows[0])
    if k < 2 or any(len(row) != k for row in rows):
        raise ValueError("A rectangular matrix with at least two raters is required")
    try:
        rows = [[float(x) for x in row] for row in rows]
    except (TypeError, ValueError) as exc:
        raise ValueError("All ratings must be numeric") from exc
    if any(not math.isfinite(x) for row in rows for x in row):
        raise ValueError("All ratings must be finite")

    grand = sum(sum(row) for row in rows) / (n * k)
    row_means = [sum(row) / k for row in rows]
    col_means = [sum(row[j] for row in rows) / n for j in range(k)]
    ss_rows = k * sum((value - grand) ** 2 for value in row_means)
    ss_columns = n * sum((value - grand) ** 2 for value in col_means)
    ss_total = sum((x - grand) ** 2 for row in rows for x in row)
    ss_within = max(0.0, ss_total - ss_rows)
    ss_error = max(0.0, ss_total - ss_rows - ss_columns)
    result = calculate_metrics(
        ms_between=ss_rows / (n - 1),
        ms_within=ss_within / (n * (k - 1)),
        ms_rater=ss_columns / (k - 1),
        ms_error=ss_error / ((n - 1) * (k - 1)),
        subjects=n, raters=k,
    )
    return result


def process_batch(input_csv, output_csv):
    """Evaluate one ANOVA design per CSV row and write six ICC columns."""
    input_path = Path(input_csv)
    if not input_path.is_file():
        raise FileNotFoundError(f"CSV input file not found: {input_csv}")
    with input_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames or []
        required = {"ms_between", "ms_within", "subjects", "raters"}
        if not required.issubset(fieldnames):
            raise ValueError(f"CSV must contain: {', '.join(sorted(required))}")
        if len(set(fieldnames)) != len(fieldnames):
            raise ValueError("Duplicate CSV columns are not supported")
        output_rows = []
        for lineno, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"CSV row {lineno}: too many columns")
            args = {key: (row.get(key) or None) for key in (
                "ms_between", "ms_within", "ms_rater", "ms_error",
                "subjects", "raters", "cluster_size", "cluster_icc"
            )}
            try:
                result = calculate_metrics(**args)
            except ValueError as exc:
                raise ValueError(f"CSV row {lineno}: {exc}") from exc
            # Neutralize spreadsheet formulas in preserved metadata columns.
            safe = {key: ("'" + val if isinstance(val, str) and
                          val.lstrip().startswith(("=", "+", "-", "@")) and
                          not _is_numeric(val) else val)
                    for key, val in row.items()}
            output_rows.append({**safe, **{key: result[key] for key in
                                          (*ICC_COLUMNS, "design_effect")}})
    output_fields = list(dict.fromkeys([*fieldnames, *ICC_COLUMNS, "design_effect"]))
    destination = Path(output_csv)
    if not destination.parent.is_dir():
        raise ValueError("Output directory does not exist")
    if input_path.resolve() == destination.resolve():
        raise ValueError("Input and output paths must differ")
    with destination.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(output_rows)
    return len(output_rows)


def _is_numeric(value):
    try:
        return math.isfinite(float(value))
    except (ValueError, TypeError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="Balanced-design ICC calculator")
    sub = parser.add_subparsers(dest="command", required=True)
    single = sub.add_parser("single", help="Compute ICCs from ANOVA mean squares")
    for name in ("ms-between", "ms-within", "subjects", "raters"):
        single.add_argument("--" + name, required=True, type=float)
    for name in ("ms-rater", "ms-error", "cluster-size", "cluster-icc"):
        single.add_argument("--" + name, type=float)
    batch = sub.add_parser("batch", help="Process ANOVA summary rows from CSV")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="results.csv")
    args = parser.parse_args(argv)
    try:
        if args.command == "single":
            params = {k: v for k, v in vars(args).items() if k != "command"}
            print(json.dumps(calculate_metrics(**params), indent=2))
        else:
            count = process_batch(args.input, args.output)
            print(f"Processed {count} experiments -> {args.output}")
    except (ValueError, FileNotFoundError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
