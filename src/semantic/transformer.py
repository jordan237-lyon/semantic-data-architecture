from collections import defaultdict

import pandas as pd


def apply_normalizations(series, operations, model):
    result = series.copy()
    for operation in operations:
        if operation == "trim":
            result = result.astype("string").str.strip()
        elif operation == "lowercase":
            result = result.astype("string").str.lower()
        elif operation == "collapse_spaces":
            result = result.astype("string").str.replace(r"\s+", " ", regex=True)
        elif operation == "title_case":
            result = result.astype("string").str.title()
        elif operation == "country_code_to_name":
            vocabulary = model.get("normalization_catalog", {}).get(operation, {})
            result = result.map(vocabulary).fillna(result)
        else:
            raise ValueError(f"Normalisation sémantique inconnue : {operation}")
    return result.replace({"": pd.NA})


def _columns_by_attribute(source_columns, mappings):
    grouped = defaultdict(list)
    for column in source_columns:
        semantic_attribute = mappings.get(column)
        if semantic_attribute:
            grouped[semantic_attribute].append(column)
    return grouped


def _materialize_attribute(dataframe, columns, definition, model):
    composition = definition.get("composition")
    if composition and composition.get("strategy") == "concatenate":
        configured = [
            column
            for column in composition.get("source_fields", [])
            if column in columns and column in dataframe
        ]
        if len(configured) > 1:
            separator = composition.get("separator", " ")
            series = dataframe[configured[0]].fillna("").astype(str)
            for column in configured[1:]:
                series = series + separator + dataframe[column].fillna("").astype(str)
        else:
            series = dataframe[columns].bfill(axis=1).iloc[:, 0]
    else:
        series = dataframe[columns].bfill(axis=1).iloc[:, 0]
    return apply_normalizations(series, definition.get("normalization", []), model)


def build_customer_view(dataframe, source_concept, mappings, model):
    """Transform one source into a customer-level view using semantic metadata."""
    grouped_columns = _columns_by_attribute(dataframe.columns, mappings)
    customer_attributes = model["concepts"]["Customer"]["attributes"]

    if source_concept == "Customer":
        identifier_column = grouped_columns["Customer.identifier"][0]
        output = pd.DataFrame({"source_identifier": dataframe[identifier_column]})
        for attribute_name, definition in customer_attributes.items():
            reference = f"Customer.{attribute_name}"
            if attribute_name == "identifier" or reference not in grouped_columns:
                continue
            output[attribute_name] = _materialize_attribute(
                dataframe, grouped_columns[reference], definition, model
            )
        return output

    relation = next(
        relation
        for relation in model["relations"]
        if relation["source"] == "Customer" and relation["target"] == source_concept
    )
    reference_attribute = relation["target_attribute"]
    reference_column = grouped_columns[reference_attribute][0]
    working = pd.DataFrame({"source_identifier": dataframe[reference_column]})
    aggregation = {}

    for attribute_name, definition in customer_attributes.items():
        reference = f"Customer.{attribute_name}"
        if reference in grouped_columns and attribute_name != "identifier":
            working[attribute_name] = _materialize_attribute(
                dataframe, grouped_columns[reference], definition, model
            )
            aggregation[attribute_name] = "first"

    for target, rule in model.get("derived_attributes", {}).items():
        source_attribute = rule["source"]
        if not source_attribute.startswith(f"{source_concept}."):
            continue
        source_column = grouped_columns[source_attribute][0]
        target_name = target.split(".", 1)[1]
        working[target_name] = dataframe[source_column]
        aggregation[target_name] = rule["aggregation"]

    return working.groupby("source_identifier", as_index=False).agg(aggregation)


def merge_customer_views(crm, support, finance, additional_views=None):
    """Outer-join customer views without ever matching missing emails."""
    source_specs = [
        (
            crm,
            "crm",
            {
                "source_identifier": "crm_client_id",
                "full_name": "crm_full_name",
                "country": "crm_country",
            },
        ),
        (
            support,
            "support",
            {
                "source_identifier": "support_customer_ref",
                "full_name": "support_full_name",
                "country": "support_country",
            },
        ),
        (
            finance,
            "finance",
            {
                "source_identifier": "finance_account_id",
                "full_name": "finance_full_name",
                "country": "finance_country",
            },
        ),
    ]
    for source, dataframe in (additional_views or {}).items():
        source_specs.append(
            (
                dataframe,
                source,
                {
                    "source_identifier": f"{source}_identifier",
                    "full_name": f"{source}_full_name",
                    "country": f"{source}_country",
                    "created_at": f"{source}_created_at",
                },
            )
        )
    prepared = []
    for dataframe, source, renames in source_specs:
        current = dataframe.rename(columns=renames).copy()
        email_column = f"{source}_email"
        current = current.rename(columns={"email": email_column})
        current["match_key"] = current[email_column].astype("object")
        missing = current[email_column].isna()
        current.loc[missing, "match_key"] = [
            f"__missing__:{source}:{index}" for index in current.index[missing]
        ]
        prepared.append(current)

    unified = prepared[0]
    for current in prepared[1:]:
        unified = unified.merge(current, on="match_key", how="outer")
    email_columns = [f"{source}_email" for _, source, _ in source_specs]
    unified["email_norm"] = unified[email_columns[0]]
    for email_column in email_columns[1:]:
        unified["email_norm"] = unified["email_norm"].combine_first(
            unified[email_column]
        )
    unified = unified.drop(columns=["match_key", *email_columns])

    preferred_order = [
        "crm_client_id",
        "crm_full_name",
        "email_norm",
        "crm_country",
        "created_at",
        "support_customer_ref",
        "support_full_name",
        "support_country",
        "ticket_count",
        "finance_account_id",
        "finance_full_name",
        "finance_country",
        "revenue",
    ]
    for source in (additional_views or {}):
        preferred_order.extend(
            [
                f"{source}_identifier",
                f"{source}_full_name",
                f"{source}_country",
                f"{source}_created_at",
            ]
        )
    return unified[[column for column in preferred_order if column in unified]]
