"""Calculate the 2025 experimental B-IMD composite, rank, and decile."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.domain_scores import HELD_DOMAINS, IDENTITY_COLUMNS

DEFAULT_DOMAIN_SCORES = Path(
    "data/processed/scores/2025/busan_admin_dong_domain_scores_2025.csv"
)
DEFAULT_SPEC = Path("docs/data/COMPOSITE_INDEX_SPEC_2025.csv")
DEFAULT_OUTPUT = Path("data/processed/scores/2025/busan_admin_dong_imd_2025.csv")
DEFAULT_REPORT = Path("docs/data/manifests/COMPOSITE_INDEX_REPORT_2025.json")
EXPECTED_DOMAINS = {
    "income",
    "employment",
    "education",
    "health",
    "housing_access",
    "living_environment",
}


@dataclass(frozen=True)
class DomainWeight:
    """Executable cross-domain aggregation contract."""

    domain: str
    source_domain: str
    published_weight: float
    scored_model_weight: float
    evidence_status: str
    quality_note: str


def load_weights(path: Path = DEFAULT_SPEC) -> list[DomainWeight]:
    """Read and validate the versioned composite-index contract."""
    frame = pd.read_csv(path)
    required = set(DomainWeight.__dataclass_fields__)
    if set(frame.columns) != required:
        raise ValueError(f"Composite specification columns must be {sorted(required)}")
    if frame["domain"].duplicated().any() or set(frame["domain"]) != EXPECTED_DOMAINS:
        raise ValueError("Composite specification must contain each scored domain exactly once")
    numeric = frame[["published_weight", "scored_model_weight"]].astype(float)
    if not np.isfinite(numeric).all().all() or (numeric <= 0).any().any():
        raise ValueError("Composite weights must be finite and positive")
    if not np.isclose(numeric["scored_model_weight"].sum(), 1.0):
        raise ValueError("Scored-model weights must sum to one")
    expected = numeric["published_weight"] / numeric["published_weight"].sum()
    if not np.allclose(numeric["scored_model_weight"], expected):
        raise ValueError("Scored-model weights must renormalize the published weights")
    return [DomainWeight(**row) for row in frame.to_dict(orient="records")]


def build(
    domain_scores: pd.DataFrame, weights: list[DomainWeight]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build one deterministic composite result row per canonical dong."""
    weight_values = np.array([weight.scored_model_weight for weight in weights], dtype=float)
    if (
        not weights
        or len({weight.domain for weight in weights}) != len(weights)
        or not np.isfinite(weight_values).all()
        or (weight_values <= 0).any()
        or not np.isclose(weight_values.sum(), 1.0)
    ):
        raise ValueError("Composite weights must be unique, positive, finite, and sum to one")
    codes = domain_scores["admin_dong_code"].astype(str)
    if len(domain_scores) != 206 or codes.duplicated().any():
        raise ValueError("Composite scoring requires 206 unique administrative-dong rows")

    expected_columns = {f"{weight.domain}_score_0_100" for weight in weights}
    missing = sorted(expected_columns - set(domain_scores.columns))
    if missing:
        raise ValueError(f"Domain-score input is missing columns: {missing}")
    values = domain_scores[sorted(expected_columns)].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(values).all().all() or ((values < 0) | (values > 100)).any().any():
        raise ValueError("Domain scores must be finite values between 0 and 100")

    output = domain_scores[IDENTITY_COLUMNS + sorted(expected_columns)].copy()
    composite = pd.Series(0.0, index=output.index)
    for weight in weights:
        composite += (
            output[f"{weight.domain}_score_0_100"].astype(float)
            * weight.scored_model_weight
        )
    ordered = output.assign(_score_exact=composite, _code=codes).sort_values(
        ["_score_exact", "_code"], ascending=[False, True], kind="stable"
    )
    ordered["b_imd_rank"] = np.arange(1, len(ordered) + 1)
    ordered["b_imd_decile"] = (
        ((ordered["b_imd_rank"] - 1) * 10 // len(ordered)) + 1
    ).astype(int)
    ordered["b_imd_score_0_100"] = ordered["_score_exact"].round(6)
    result_columns = [
        *IDENTITY_COLUMNS,
        *sorted(expected_columns),
        "b_imd_score_0_100",
        "b_imd_rank",
        "b_imd_decile",
    ]
    output = ordered[result_columns].reset_index(drop=True)

    decile_counts = {
        str(decile): int(count)
        for decile, count in output["b_imd_decile"].value_counts().sort_index().items()
    }
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "record_count": len(output),
        "scored_domains": [weight.domain for weight in weights],
        "held_domains": HELD_DOMAINS,
        "aggregation": "weighted arithmetic mean of 0-100 domain scores",
        "weight_basis": (
            "English Indices of Deprivation 2025 published domain weights, "
            "renormalized across six scored domains"
        ),
        "score_direction": "higher means greater relative deprivation",
        "rank_direction": "rank 1 is most deprived",
        "decile_direction": "decile 1 is most deprived 10 percent",
        "tie_break": "descending score then ascending administrative-dong code",
        "score_summary": {
            "minimum": round(float(output["b_imd_score_0_100"].min()), 6),
            "median": round(float(output["b_imd_score_0_100"].median()), 6),
            "maximum": round(float(output["b_imd_score_0_100"].max()), 6),
        },
        "decile_counts": decile_counts,
    }
    return output, report


def run(
    domain_scores_path: Path = DEFAULT_DOMAIN_SCORES,
    spec_path: Path = DEFAULT_SPEC,
    output_path: Path = DEFAULT_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Read domain scores and write the deterministic composite artifacts."""
    domain_scores = pd.read_csv(domain_scores_path, dtype={"admin_dong_code": str})
    weights = load_weights(spec_path)
    output, report = build(domain_scores, weights)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    report.update(
        {
            "domain_scores_path": domain_scores_path.as_posix(),
            "domain_scores_sha256": sha256_file(domain_scores_path),
            "spec_path": spec_path.as_posix(),
            "spec_sha256": sha256_file(spec_path),
            "output_path": output_path.as_posix(),
            "output_sha256": sha256_file(output_path),
        }
    )
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain-scores", type=Path, default=DEFAULT_DOMAIN_SCORES)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(args.domain_scores, args.spec, args.output, args.report)
    print(
        f"ranked {report['record_count']} administrative dongs into "
        f"{len(report['decile_counts'])} deprivation deciles"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
