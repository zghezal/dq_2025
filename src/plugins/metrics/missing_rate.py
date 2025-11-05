# src/plugins/metrics/missing_rate.py
from __future__ import annotations

from typing import Optional, List, Union, Tuple
from pydantic import BaseModel, Field
from pyspark.sql import functions as F
from pyspark.sql import types as T
import pandas as pd

from src.plugins.base import BasePlugin, Result, register
from src.plugins.base_models import CommonArgs
from src.plugins.output_schema import OutputSchema, OutputColumn
from src.utils import get_columns_for_dataset

# --- Filtres : chargement + pré-tests ---
from dq.filters.filter_loader import load_filter_by_name
from dq.filters.filter_validator import (
    validate_filter_against_schema,
    build_filter_precheck_tests,
    evaluate_prechecks_and_block,
)

# ----------------------------
# Paramètres du plugin
# ----------------------------

class MissingRateSpecific(BaseModel):
    dataset: str = Field(..., title="Dataset alias")
    column: Optional[Union[str, List[str]]] = Field(
        default=None,
        title="Columns",
        description="Colonne ou liste de colonnes. Si None: toutes les colonnes."
    )
    # Filtres (banque JSON)
    filter: Optional[str] = Field(
        default=None,
        title="Filter name",
        description="Nom du filtre (JSON) à valider/associer"
    )
    stream: Optional[str] = Field(default=None, title="Stream")
    project: Optional[str] = Field(default=None, title="Project")
    zone: Optional[str] = Field(default=None, title="Zone")

class MissingRateParams(CommonArgs):
    id: str = Field(default="missing_rate", title="ID")
    specific: MissingRateSpecific

# ----------------------------
# Helpers internes
# ----------------------------

def _spark_schema_to_map(df) -> dict:
    """Mappe le schéma Spark en types simples (string/int/double/boolean/datetime)."""
    from pyspark.sql import types as T
    m = {}
    for f in df.schema.fields:
        dt = f.dataType
        if isinstance(dt, T.StringType):
            m[f.name] = "string"
        elif isinstance(dt, (T.ByteType, T.ShortType, T.IntegerType, T.LongType)):
            m[f.name] = "int"
        elif isinstance(dt, (T.FloatType, T.DoubleType, T.DecimalType)):
            m[f.name] = "double"
        elif isinstance(dt, T.BooleanType):
            m[f.name] = "boolean"
        elif isinstance(dt, (T.DateType, T.TimestampType)):
            m[f.name] = "datetime"
        else:
            m[f.name] = str(dt)
    return m

def _build_metric_id(
    name: str, *, stream: Optional[str], project: Optional[str], zone: Optional[str],
    dataset: str, column: Optional[str], filter_name: Optional[str]
) -> str:
    parts = [
        (stream or "?"),
        (project or "?"),
        (zone or "?"),
        "metric",
        name,
        dataset,
    ]
    if column:
        parts.append(f"col={column}")
    if filter_name:
        parts.append(f"filter={filter_name}")
    return ".".join(parts)

# ----------------------------
# Plugin
# ----------------------------

@register
class MissingRate(BasePlugin):
    plugin_id = "missing_rate"
    label = "Missing Rate"
    group = "Profiling"
    ParamsModel = MissingRateParams

    @staticmethod
    def _extract_columns_from_params(params: dict) -> Tuple[List[str], Optional[str]]:
        specific = (params or {}).get("specific") or {}
        dataset = params.get("dataset") or specific.get("dataset")

        collected: List[str] = []
        candidates = [
            specific.get("column"),
            specific.get("columns"),
            params.get("column"),
            params.get("columns"),
        ]
        for candidate in candidates:
            if candidate is None:
                continue
            if isinstance(candidate, str):
                collected.append(candidate)
            elif isinstance(candidate, (list, tuple, set)):
                collected.extend([c for c in candidate if c])

        # Deduplicate while preserving order
        seen = set()
        ordered: List[str] = []
        for col in collected:
            if col and col not in seen:
                ordered.append(col)
                seen.add(col)
        return ordered, dataset

    @staticmethod
    def _resolve_column_list(df_columns: List[str], configured: List[str]) -> List[str]:
        if configured:
            df_columns_set = set(df_columns)
            return [c for c in configured if c in df_columns_set]
        return list(df_columns)

    @staticmethod
    def _missing_condition(col_name: str, schema_field: T.StructField):
        base_cond = F.col(col_name).isNull()
        if isinstance(schema_field.dataType, T.StringType):
            trimmed = F.trim(F.col(col_name))
            base_cond = base_cond | (trimmed == "")
        return base_cond

    @classmethod
    def output_schema(cls, params: dict) -> Optional[OutputSchema]:
        """
        Déclare le schéma de sortie pour la métrique Missing Rate.

        Chaque colonne source suivie produit deux colonnes dans le dataset
        virtuel :
          - <col>_missing_rate (float)
          - <col>_missing_number (int)

        La sortie est donc en format "wide" afin d'exposer directement les
        statistiques par colonne. Cette méthode est déterministe et ne réalise
        pas d'I/O : elle décrit simplement la forme des données produites.
        """
        params = params or {}
        specified_cols, dataset = cls._extract_columns_from_params(params)
        candidate_columns = list(specified_cols)

        if not candidate_columns and dataset:
            try:
                candidate_columns = get_columns_for_dataset(dataset)
            except Exception:
                candidate_columns = []

        # Fallback minimal structure if rien n'est détecté
        if not candidate_columns:
            candidate_columns = ["value"]

        schema_columns: List[OutputColumn] = []
        for col in candidate_columns:
            schema_columns.append(OutputColumn(
                name=f"{col}_missing_rate",
                dtype="float",
                nullable=False,
                description=f"Taux de valeurs manquantes pour '{col}'"
            ))
            schema_columns.append(OutputColumn(
                name=f"{col}_missing_number",
                dtype="int",
                nullable=False,
                description=f"Nombre de valeurs manquantes pour '{col}'"
            ))

        return OutputSchema(columns=schema_columns, estimated_row_count=1)

    def run(self, context, **params) -> Result:
        p = self.ParamsModel(**params)
        ds = p.specific.dataset
        col_config = p.specific.column
        flt = p.specific.filter

        # 1) Charger DF tôt (pour connaître le schéma)
        df = context.load(ds)
        df_columns = df.columns
        # Déterminer les colonnes cibles
        configured_cols, _ = self._extract_columns_from_params({
            "specific": {
                "column": col_config,
                "dataset": ds
            }
        })
        target_columns = self._resolve_column_list(df_columns, configured_cols)
        if not target_columns:
            raise ValueError(
                f"Aucune colonne valide trouvée pour la métrique missing_rate sur '{ds}'."
            )

        # 2) Pré-tests techniques du filtre (si fourni)
        prechecks: List[dict] = []
        if flt:
            fdict = load_filter_by_name(
                flt,
                stream=p.specific.stream,
                project=p.specific.project,
                zone=p.specific.zone,
            )
            schema_map = _spark_schema_to_map(df)
            errors = validate_filter_against_schema(fdict, schema_map)
            prechecks = build_filter_precheck_tests(
                flt, fdict, schema_map,
                stream=p.specific.stream or "",
                zone=p.specific.zone or "",
                project=p.specific.project
            )
            verdict = evaluate_prechecks_and_block(prechecks, errors)
            if verdict["blocked"]:
                return Result(
                    passed=False,
                    value=None,
                    message=f"Blocked by invalid filter '{flt}': {verdict['reason']}",
                    meta={
                        "prechecks": prechecks,
                        "status": "Blocked",
                        "stream": p.specific.stream,
                        "project": p.specific.project,
                        "zone": p.specific.zone,
                        "filter_name": flt,
                    },
                )

        # 3) Calcul de la métrique
        #    NB: on ne filtre PAS le DF ici (ton exécution de filtre est gérée ailleurs),
        #    on se contente de valider + tracer. Si tu veux appliquer le filtre réellement,
        #    branche ta fonction d'application de filtre ici, après validation.
        total_rows = df.count()

        if total_rows == 0:
            result_map = {}
            for c in target_columns:
                result_map[f"{c}_missing_rate"] = 0.0
                result_map[f"{c}_missing_number"] = 0
        else:
            agg_alias_map = {}
            agg_exprs = []
            schema_map = {field.name: field for field in df.schema.fields}
            for c in target_columns:
                field = schema_map.get(c)
                if field is None:
                    continue
                cond = self._missing_condition(c, field)
                alias = f"__{c}__missing_number"
                agg_alias_map[c] = alias
                agg_exprs.append(F.sum(F.when(cond, 1).otherwise(0)).alias(alias))

            agg_result = {}
            if agg_exprs:
                agg_row = df.agg(*agg_exprs).collect()[0]
                agg_result = agg_row.asDict(recursive=True)

            result_map = {}
            for c in target_columns:
                alias = agg_alias_map.get(c)
                missing_number = int(agg_result.get(alias, 0)) if alias else 0
                missing_rate = float(missing_number) / total_rows if total_rows else 0.0
                result_map[f"{c}_missing_number"] = missing_number
                result_map[f"{c}_missing_rate"] = missing_rate

        # 4) Stockage pour tests post-métrique (threshold, etc.)
        primary_column = target_columns[0] if target_columns else None
        metric_id = _build_metric_id(
            "missing_rate",
            stream=p.specific.stream,
            project=p.specific.project,
            zone=p.specific.zone,
            dataset=ds,
            column=primary_column,
            filter_name=flt,
        )
        # 5) Résultat
        overall_missing = sum(
            result_map.get(f"{c}_missing_number", 0) for c in target_columns
        )
        total_cells = total_rows * len(target_columns)
        overall_rate = float(overall_missing) / total_cells if total_cells else 0.0

        result_df = pd.DataFrame([result_map]) if result_map else pd.DataFrame()

        if not hasattr(context, "metrics_values"):
            context.metrics_values = {}
        context.metrics_values[metric_id] = overall_rate
        if not hasattr(context, "metrics_details"):
            context.metrics_details = {}
        context.metrics_details[metric_id] = {
            "per_column": result_map.copy(),
            "total_rows": total_rows,
            "overall_rate": overall_rate,
        }

        meta = {
            "prechecks": prechecks,
            "stream": p.specific.stream,
            "project": p.specific.project,
            "zone": p.specific.zone,
            "filter_name": flt,
            "metric_id": metric_id,
            "per_column": result_map,
            "total_rows": total_rows,
        }
        return Result(passed=None, value=overall_rate, dataframe=result_df, message="OK", meta=meta)
