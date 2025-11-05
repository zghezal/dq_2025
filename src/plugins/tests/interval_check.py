from __future__ import annotations

from typing import Optional, List, Dict, Tuple

import pandas as pd
from pydantic import BaseModel, Field, ConfigDict

from src.core.ui_meta import UIMeta
from src.plugins.base import BasePlugin, Result, register
from src.plugins.base_models import CommonArgs


class IntervalColumnRule(BaseModel):
    """Rule overriding bounds for one or several columns."""

    model_config = ConfigDict(extra="allow")

    columns: List[str] = Field(
        ..., title="Columns", description="Columns impacted by this rule"
    )
    lower: Optional[float] = Field(
        default=None,
        title="Lower bound (>=)",
        description="Override minimum value for these columns.",
    )
    upper: Optional[float] = Field(
        default=None,
        title="Upper bound (<=)",
        description="Override maximum value for these columns.",
    )

    def resolved_bounds(self) -> Tuple[Optional[float], Optional[float]]:
        """Return the effective lower/upper bounds, including legacy aliases."""
        lower_value = self.lower
        if lower_value is None:
            lower_value = getattr(self, "lower_value", None)
        upper_value = self.upper
        if upper_value is None:
            upper_value = getattr(self, "upper_value", None)
        return lower_value, upper_value


class IntervalSpecific(BaseModel):
    """Specific parameters for the Interval Check test."""

    target_mode: str = Field(
        default="metric_value",
        title="Target source",
        json_schema_extra={
            "ui_meta": UIMeta(
                group="specific",
                widget="select",
                choices_source="enums",
                enum_values=["metric_value", "dataset_columns"],
                help="Choose whether to control a computed metric value or raw dataset columns.",
            )
        },
    )

    metric_id: str = Field(
        default="",
        title="Metric ID",
        json_schema_extra={
            "ui_meta": UIMeta(
                group="specific",
                widget="select",
                choices_source="metrics",
                help="Metric identifier to validate when using metric mode.",
            )
        },
    )

    database: str = Field(
        default="",
        title="Dataset or virtual dataset",
        json_schema_extra={
            "ui_meta": UIMeta(
                group="specific",
                widget="select",
                choices_source="databases_and_metrics",
                help="Dataset or virtual dataset to load when checking columns.",
            )
        },
    )

    columns: list[str] = Field(
        default_factory=list,
        title="Columns",
        json_schema_extra={
            "ui_meta": UIMeta(
                group="specific",
                widget="multi-select",
                choices_source="columns_for_database",
                help="Numeric columns to evaluate when checking dataset columns.",
            )
        },
    )

    lower_enabled: bool = Field(
        default=False,
        title="Enable lower bound",
        json_schema_extra={
            "ui_meta": UIMeta(
                group="specific",
                widget="checkbox",
                help="Enable lower bound (>=).",
            )
        },
    )

    lower_value: Optional[float] = Field(
        default=None,
        title="Lower bound value",
        json_schema_extra={
            "ui_meta": UIMeta(
                group="specific",
                widget="number",
                placeholder="Ex: 0",
                help="Numeric value for the lower bound (>=).",
            )
        },
    )

    upper_enabled: bool = Field(
        default=False,
        title="Enable upper bound",
        json_schema_extra={
            "ui_meta": UIMeta(
                group="specific",
                widget="checkbox",
                help="Enable upper bound (<=).",
            )
        },
    )

    upper_value: Optional[float] = Field(
        default=None,
        title="Upper bound value",
        json_schema_extra={
            "ui_meta": UIMeta(
                group="specific",
                widget="number",
                placeholder="Ex: 100",
                help="Numeric value for the upper bound (<=).",
            )
        },
    )

    column_rules: List[IntervalColumnRule] = Field(
        default_factory=list,
        title="Column rules",
        description="Optional overrides per column or group.",
    )


class IntervalCheckParams(CommonArgs):
    """Full parameter model for the Interval Check test."""

    specific: IntervalSpecific


@register
class IntervalCheck(BasePlugin):
    plugin_id = "test.interval_check"
    label = "Interval Check"
    group = "Validation"
    ParamsModel = IntervalCheckParams

    def run(self, context, **params) -> Result:
        spec = self.ParamsModel(**params).specific
        mode = (spec.target_mode or "").strip() or "metric_value"

        lower = spec.lower_value if spec.lower_enabled else None
        upper = spec.upper_value if spec.upper_enabled else None
        rules_with_bounds = [
            rule
            for rule in (spec.column_rules or [])
            if rule and any(bound is not None for bound in rule.resolved_bounds())
        ]
        if lower is None and upper is None and not rules_with_bounds:
            return Result(
                passed=False,
                value=None,
                message="Define at least one bound (min or max).",
                meta={"mode": mode},
            )

        if mode not in {"metric_value", "dataset_columns"}:
            return Result(
                passed=False,
                value=None,
                message=f"Unsupported target mode '{spec.target_mode}'.",
                meta={"mode": spec.target_mode},
            )

        if mode == "metric_value":
            return self._check_metric_value(context, spec, lower, upper, mode)
        return self._check_dataset_columns(context, spec, lower, upper, mode)

    def _check_metric_value(
        self,
        context,
        spec: IntervalSpecific,
        lower: Optional[float],
        upper: Optional[float],
        mode: str,
    ) -> Result:
        metric_id = (spec.metric_id or "").strip()
        if not metric_id:
            return Result(
                passed=False,
                value=None,
                message="Metric ID is required when using metric mode.",
                meta={"mode": mode},
            )

        value = getattr(context, "metrics_values", {}).get(metric_id)
        if isinstance(value, dict):
            for key in ("value", "overall", "overall_rate"):
                if key in value and value[key] is not None:
                    value = value[key]
                    break
        if value is None:
            details = getattr(context, "metrics_details", {})
            if isinstance(details, dict):
                detail_entry = details.get(metric_id)
                if isinstance(detail_entry, dict):
                    value = detail_entry.get("overall_rate") or detail_entry.get("value")
        if value is None:
            return Result(
                passed=False,
                value=None,
                message=f"Metric '{metric_id}' not found or not computed.",
                meta={"mode": mode, "metric_id": metric_id},
            )

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return Result(
                passed=False,
                value=None,
                message=f"Non numeric value for metric '{metric_id}': {value}.",
                meta={"mode": mode, "metric_id": metric_id},
            )

        failures = []
        if lower is not None and numeric_value < lower:
            failures.append(f"{numeric_value} < min {lower}")
        if upper is not None and numeric_value > upper:
            failures.append(f"{numeric_value} > max {upper}")

        return Result(
            passed=not failures,
            value=numeric_value,
            message="; ".join(failures) if failures else "OK",
            meta={
                "mode": mode,
                "metric_id": metric_id,
                "bounds": {"lower": lower, "upper": upper},
            },
        )

    def _check_dataset_columns(
        self,
        context,
        spec: IntervalSpecific,
        lower: Optional[float],
        upper: Optional[float],
        mode: str,
    ) -> Result:
        database = (spec.database or "").strip()
        selected_columns = [col for col in (spec.columns or []) if col]
        rules = spec.column_rules or []

        column_bounds: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
        for rule in rules:
            if not isinstance(rule, IntervalColumnRule):
                continue
            rule_columns = [c for c in (rule.columns or []) if c]
            if not rule_columns:
                continue
            override_lower, override_upper = rule.resolved_bounds()
            for col_name in rule_columns:
                column_bounds[col_name] = (override_lower, override_upper)

        effective_columns: List[str] = list(selected_columns)
        for col_name in column_bounds.keys():
            if col_name not in effective_columns:
                effective_columns.append(col_name)

        if not database:
            return Result(
                passed=False,
                value=None,
                message="Select a dataset or virtual dataset to evaluate.",
                meta={"mode": mode},
            )
        if not selected_columns and not column_bounds:
            return Result(
                passed=False,
                value=None,
                message="Select at least one column or define column_rules to evaluate.",
                meta={"mode": mode, "database": database},
            )

        df = context.load(database)

        total_checked = 0
        total_violations = 0
        missing_columns: list[str] = []
        non_numeric_columns: list[str] = []
        violations_detail: dict[str, dict[str, int]] = {}
        applied_bounds: Dict[str, Dict[str, Optional[float]]] = {}
        skipped_columns: list[str] = []

        for col in effective_columns:
            if col not in df.columns:
                missing_columns.append(col)
                continue

            numeric_series = pd.to_numeric(df[col], errors="coerce").dropna()
            if numeric_series.empty:
                non_numeric_columns.append(col)
                continue

            total_checked += int(numeric_series.size)

            overrides = column_bounds.get(col)
            effective_lower = overrides[0] if overrides else lower
            effective_upper = overrides[1] if overrides else upper

            if effective_lower is None and effective_upper is None:
                skipped_columns.append(col)
                continue

            applied_bounds[col] = {"lower": effective_lower, "upper": effective_upper}

            mask = pd.Series(False, index=numeric_series.index, dtype=bool)
            if effective_lower is not None:
                mask |= numeric_series < effective_lower
            if effective_upper is not None:
                mask |= numeric_series > effective_upper

            violations = int(mask.sum())
            if violations:
                total_violations += violations
                violations_detail[col] = {
                    "violations": violations,
                    "total": int(numeric_series.size),
                }

        passed = (
            total_violations == 0
            and not missing_columns
            and not non_numeric_columns
        )

        messages: list[str] = []
        if missing_columns:
            messages.append(
                "Missing columns: " + ", ".join(sorted(set(missing_columns)))
            )
        if total_violations:
            detail_parts = [
                f"{info['violations']}/{info['total']} out of bounds in '{col}'"
                for col, info in sorted(violations_detail.items())
            ]
            messages.append("; ".join(detail_parts))
        if non_numeric_columns:
            messages.append(
                "Columns without numeric values: " + ", ".join(sorted(set(non_numeric_columns)))
            )
        if skipped_columns:
            messages.append(
                "No bounds configured for: " + ", ".join(sorted(set(skipped_columns)))
            )
        if not messages:
            messages.append(
                f"All values ({total_checked}) respect the configured bounds."
            )

        return Result(
            passed=passed,
            value=total_violations,
            message="; ".join(messages),
            meta={
                "mode": mode,
                "database": database,
                "columns": selected_columns,
                "bounds": {
                    "lower": lower,
                    "upper": upper,
                    "per_column": applied_bounds,
                },
                "column_rules": [
                    rule.model_dump(exclude_unset=True) for rule in rules
                ] if rules else [],
                "violations": violations_detail,
                "missing_columns": missing_columns,
                "non_numeric_columns": non_numeric_columns,
                "skipped_columns": skipped_columns,
            },
        )
