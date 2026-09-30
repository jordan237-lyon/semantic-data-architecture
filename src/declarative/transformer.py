"""Generic transformation engine driven exclusively by the A2 YAML model."""

import pandas as pd


class DeclarativeTransformationError(ValueError):
    """Raised when source data does not satisfy its predefined declaration."""


def _country_dictionary(series, model):
    vocabulary = model.get("normalization_catalog", {}).get("country_dictionary", {})
    normalized = {str(key).strip().lower(): value for key, value in vocabulary.items()}

    def replace(value):
        if pd.isna(value):
            return pd.NA
        cleaned = str(value).strip()
        return normalized.get(cleaned.lower(), cleaned)

    return series.map(replace)


def apply_transformations(series, operations, model):
    """Apply only operations explicitly listed in the A2 declaration."""
    result = series.copy()
    for operation in operations:
        if operation == "trim":
            result = result.astype("string").str.strip()
        elif operation == "lowercase":
            result = result.astype("string").str.lower()
        elif operation == "parse_date":
            result = pd.to_datetime(result, errors="coerce").dt.strftime("%Y-%m-%d")
        elif operation == "parse_decimal":
            result = pd.to_numeric(result, errors="coerce")
        elif operation == "country_dictionary":
            result = _country_dictionary(result, model)
        else:
            raise DeclarativeTransformationError(
                f"Transformation A2 non implémentée : {operation}"
            )
    return result.replace({"": pd.NA})


def _first_non_null(series):
    values = series.dropna()
    return values.iloc[0] if not values.empty else pd.NA


def _validate_source_columns(dataframe, source_name, declaration):
    required = set(declaration["mappings"])
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise DeclarativeTransformationError(
            f"Source {source_name} : colonnes déclarées absentes : {', '.join(missing)}"
        )


def build_source_view(dataframe, source_name, model):
    """Build one customer-level view without schema inference or matching."""
    if source_name not in model["sources"]:
        raise DeclarativeTransformationError(f"Source A2 non déclarée : {source_name}")
    declaration = model["sources"][source_name]
    _validate_source_columns(dataframe, source_name, declaration)

    identifier = declaration["entity_identifier"]
    output = pd.DataFrame({"source_identifier": dataframe[identifier]})
    target_columns = {}
    for source_column, mapping in declaration["mappings"].items():
        if mapping.get("use") == "row_identifier":
            continue
        target = mapping["target"]
        values = apply_transformations(
            dataframe[source_column], mapping.get("transformations", []), model
        )
        if target not in target_columns or source_column == identifier:
            target_columns[target] = values
    for target, values in target_columns.items():
        output[target] = values

    for target, rule in declaration.get("derived_attributes", {}).items():
        inputs = rule["inputs"]
        if rule["operation"] == "concatenate":
            separator = rule.get("separator", " ")
            values = dataframe[inputs[0]].fillna("").astype(str)
            for column in inputs[1:]:
                values = values + separator + dataframe[column].fillna("").astype(str)
            output[target] = values.str.replace(r"\s+", " ", regex=True).str.strip().replace("", pd.NA)

    aggregation = declaration.get("aggregation")
    if not aggregation:
        return output

    aggregators = {
        "first_non_null": _first_non_null,
        "count": "count",
        "sum": "sum",
        "min": "min",
        "max": "max",
    }
    named_rules = {
        target: (target, aggregators[operation])
        for target, operation in aggregation["rules"].items()
    }
    return output.groupby("source_identifier", as_index=False, dropna=False).agg(**named_rules)


def merge_source_views(views, model):
    """Outer-join declared customer views on the exact normalized e-mail."""
    join_attribute = model["entity_resolution"]["join_attribute"]
    prepared = []
    for source_name, view in views.items():
        if join_attribute not in view:
            raise DeclarativeTransformationError(
                f"Source {source_name} : attribut de jointure absent : {join_attribute}"
            )
        declaration = model["sources"][source_name]
        identifier_name = f"{source_name}_{declaration['entity_identifier']}"
        renames = {"source_identifier": identifier_name}
        for column in view.columns:
            if column not in {"source_identifier", join_attribute}:
                renames[column] = f"{source_name}_{column}"
        current = view.rename(columns=renames).copy()
        email_column = f"{source_name}_{join_attribute}"
        current = current.rename(columns={join_attribute: email_column})
        current["_match_key"] = current[email_column].astype("object")
        missing = current[email_column].isna()
        current.loc[missing, "_match_key"] = [
            f"__missing__:{source_name}:{index}" for index in current.index[missing]
        ]
        prepared.append((source_name, current, email_column))

    unified = prepared[0][1]
    for _, current, _ in prepared[1:]:
        unified = unified.merge(current, on="_match_key", how="outer")
    email_columns = [email_column for _, _, email_column in prepared]
    unified["email_norm"] = unified[email_columns[0]]
    for email_column in email_columns[1:]:
        unified["email_norm"] = unified["email_norm"].combine_first(unified[email_column])
    return unified.drop(columns=["_match_key", *email_columns])
