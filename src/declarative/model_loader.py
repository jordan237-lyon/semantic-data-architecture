"""Load and validate the non-adaptive A2 declaration."""

from pathlib import Path

import copy

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = ROOT / "semantic" / "a2_model.yaml"
ALLOWED_TYPES = {"string", "integer", "decimal", "date", "boolean"}
ALLOWED_TRANSFORMATIONS = {
    "trim", "lowercase", "parse_date", "parse_decimal", "country_dictionary"
}
ALLOWED_AGGREGATIONS = {"first_non_null", "count", "sum", "min", "max"}
ALLOWED_DERIVATIONS = {"concatenate"}


class DeclarativeModelError(ValueError):
    """Raised when the A2 declaration is missing or inconsistent."""


def require_mapping(value, location):
    if not isinstance(value, dict):
        raise DeclarativeModelError(f"{location} doit être un objet YAML.")
    return value


def validate_declarative_model(model):
    model = require_mapping(model, "Le modèle")
    if not model.get("version"):
        raise DeclarativeModelError("Le champ version est obligatoire.")

    architecture = require_mapping(model.get("architecture"), "architecture")
    if architecture.get("level") != "A2" or architecture.get("mode") != "declarative":
        raise DeclarativeModelError("Le modèle doit déclarer le niveau A2 en mode declarative.")
    if architecture.get("automatic_matching") is not False:
        raise DeclarativeModelError("A2 interdit le matching automatique.")
    if architecture.get("confidence_scoring") is not False:
        raise DeclarativeModelError("A2 interdit le score de confiance.")

    canonical = require_mapping(model.get("canonical_model"), "canonical_model")
    attributes = require_mapping(canonical.get("attributes"), "canonical_model.attributes")
    for name, definition in attributes.items():
        definition = require_mapping(definition, f"canonical_model.attributes.{name}")
        if definition.get("type") not in ALLOWED_TYPES:
            raise DeclarativeModelError(f"Type canonique invalide pour {name}.")

    sources = require_mapping(model.get("sources"), "sources")
    if not sources:
        raise DeclarativeModelError("A2 doit déclarer au moins une source.")
    for source_name, source in sources.items():
        location = f"sources.{source_name}"
        source = require_mapping(source, location)
        mappings = require_mapping(source.get("mappings"), f"{location}.mappings")
        identifier = source.get("entity_identifier")
        if identifier not in mappings:
            raise DeclarativeModelError(f"{location}.entity_identifier doit être mappé.")
        for column, mapping in mappings.items():
            mapping = require_mapping(mapping, f"{location}.mappings.{column}")
            if mapping.get("target") not in attributes:
                raise DeclarativeModelError(f"Cible canonique inconnue pour {location}.mappings.{column}.")
            transforms = mapping.get("transformations", [])
            if not isinstance(transforms, list) or not set(transforms) <= ALLOWED_TRANSFORMATIONS:
                raise DeclarativeModelError(f"Transformation invalide pour {location}.mappings.{column}.")

        derived = require_mapping(source.get("derived_attributes", {}), f"{location}.derived_attributes")
        for target, rule in derived.items():
            rule = require_mapping(rule, f"{location}.derived_attributes.{target}")
            if target not in attributes or rule.get("operation") not in ALLOWED_DERIVATIONS:
                raise DeclarativeModelError(f"Dérivation invalide pour {location}.{target}.")
            if not set(rule.get("inputs", [])) <= set(mappings):
                raise DeclarativeModelError(f"Entrée non mappée dans la dérivation {location}.{target}.")

        aggregation = source.get("aggregation")
        if aggregation is not None:
            aggregation = require_mapping(aggregation, f"{location}.aggregation")
            if aggregation.get("group_by") not in mappings:
                raise DeclarativeModelError(f"{location}.aggregation.group_by doit être mappé.")
            rules = require_mapping(aggregation.get("rules"), f"{location}.aggregation.rules")
            if not set(rules) <= set(attributes) or not set(rules.values()) <= ALLOWED_AGGREGATIONS:
                raise DeclarativeModelError(f"Règle d'agrégation invalide dans {location}.")

    resolution = require_mapping(model.get("entity_resolution"), "entity_resolution")
    if resolution.get("method") != "exact":
        raise DeclarativeModelError("A2 supporte uniquement la résolution exacte déclarée.")
    if resolution.get("join_attribute") not in attributes:
        raise DeclarativeModelError("L'attribut de jointure A2 est inconnu.")
    return model


def load_declarative_model(path=DEFAULT_MODEL_PATH):
    path = Path(path)
    if not path.exists():
        raise DeclarativeModelError(f"Modèle déclaratif introuvable : {path}")
    try:
        with path.open(encoding="utf-8") as stream:
            model = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        raise DeclarativeModelError(f"YAML invalide dans {path} : {error}") from error
    if isinstance(model, dict) and "extends" in model:
        base_path = (path.parent / model["extends"]).resolve()
        base = copy.deepcopy(load_declarative_model(base_path))
        overrides = require_mapping(model.get("overrides"), "overrides")
        canonical_override = require_mapping(
            overrides.get("canonical_model", {}), "overrides.canonical_model"
        )
        added_attributes = require_mapping(
            canonical_override.get("add_attributes", {}),
            "overrides.canonical_model.add_attributes",
        )
        canonical_attributes = base["canonical_model"]["attributes"]
        if set(added_attributes) & set(canonical_attributes):
            raise DeclarativeModelError("Ajout d'un attribut canonique déjà déclaré.")
        canonical_attributes.update(copy.deepcopy(added_attributes))
        source_overrides = require_mapping(overrides.get("sources", {}), "overrides.sources")
        for source_name, source_override in source_overrides.items():
            if source_name not in base["sources"]:
                raise DeclarativeModelError(f"Surcharge d'une source inconnue : {source_name}.")
            renames = require_mapping(
                require_mapping(source_override, f"overrides.sources.{source_name}").get("rename_mappings", {}),
                f"overrides.sources.{source_name}.rename_mappings",
            )
            mappings = base["sources"][source_name]["mappings"]
            for old_name, new_name in renames.items():
                if old_name not in mappings or new_name in mappings:
                    raise DeclarativeModelError(
                        f"Renommage de mapping invalide : {source_name}.{old_name} vers {new_name}."
                    )
                mappings[new_name] = mappings.pop(old_name)
            removals = source_override.get("remove_mappings", [])
            if not isinstance(removals, list) or not all(
                isinstance(name, str) for name in removals
            ):
                raise DeclarativeModelError(
                    f"overrides.sources.{source_name}.remove_mappings doit être une liste."
                )
            for column in removals:
                if column not in mappings:
                    raise DeclarativeModelError(
                        f"Suppression d'un mapping inconnu : {source_name}.{column}."
                    )
                del mappings[column]
            additions = require_mapping(
                source_override.get("add_mappings", {}),
                f"overrides.sources.{source_name}.add_mappings",
            )
            if set(additions) & set(mappings):
                raise DeclarativeModelError(
                    f"Ajout d'un mapping déjà déclaré dans {source_name}."
                )
            mappings.update(copy.deepcopy(additions))
            derived = base["sources"][source_name].get("derived_attributes", {})
            derived_removals = source_override.get("remove_derived_attributes", [])
            if not isinstance(derived_removals, list):
                raise DeclarativeModelError(
                    f"overrides.sources.{source_name}.remove_derived_attributes doit être une liste."
                )
            for target in derived_removals:
                if target not in derived:
                    raise DeclarativeModelError(
                        f"Suppression d'une dérivation inconnue : {source_name}.{target}."
                    )
                del derived[target]
            aggregation_override = source_override.get("aggregation")
            if aggregation_override is not None:
                aggregation_override = require_mapping(
                    aggregation_override, f"overrides.sources.{source_name}.aggregation"
                )
                aggregation = require_mapping(
                    base["sources"][source_name].get("aggregation"),
                    f"sources.{source_name}.aggregation",
                )
                rules = aggregation["rules"]
                for target in aggregation_override.get("remove_rules", []):
                    if target not in rules:
                        raise DeclarativeModelError(
                            f"Suppression d'une agrégation inconnue : {source_name}.{target}."
                        )
                    del rules[target]
                added_rules = require_mapping(
                    aggregation_override.get("add_rules", {}),
                    f"overrides.sources.{source_name}.aggregation.add_rules",
                )
                if set(added_rules) & set(rules):
                    raise DeclarativeModelError(
                        f"Ajout d'une agrégation déjà déclarée dans {source_name}."
                    )
                rules.update(added_rules)
        added_sources = require_mapping(overrides.get("add_sources", {}), "overrides.add_sources")
        duplicate_sources = set(base["sources"]) & set(added_sources)
        if duplicate_sources:
            raise DeclarativeModelError(
                "Sources déjà déclarées : " + ", ".join(sorted(duplicate_sources))
            )
        base["sources"].update(copy.deepcopy(added_sources))
        catalog_overrides = require_mapping(
            overrides.get("normalization_catalog", {}),
            "overrides.normalization_catalog",
        )
        for vocabulary_name, additions in catalog_overrides.items():
            catalog = require_mapping(
                base.get("normalization_catalog", {}).get(vocabulary_name),
                f"normalization_catalog.{vocabulary_name}",
            )
            additions = require_mapping(
                additions, f"overrides.normalization_catalog.{vocabulary_name}"
            )
            duplicate_keys = set(catalog) & set(additions)
            if duplicate_keys:
                raise DeclarativeModelError(
                    "Entrées de vocabulaire déjà déclarées : "
                    + ", ".join(sorted(duplicate_keys))
                )
            catalog.update(additions)
        model = base
    return validate_declarative_model(model)
