import copy
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = ROOT / "semantic" / "model.yaml"

ALLOWED_TYPES = {"string", "integer", "decimal", "date", "boolean"}
ALLOWED_CARDINALITIES = {
    "one_to_one",
    "one_to_many",
    "many_to_one",
    "many_to_many",
}
ALLOWED_AGGREGATIONS = {"count", "sum", "min", "max", "average"}


class SemanticModelError(ValueError):
    """Raised when the semantic model is missing or inconsistent."""


def _require_mapping(value, location):
    if not isinstance(value, dict):
        raise SemanticModelError(f"{location} doit être un objet YAML.")
    return value


def _split_attribute_reference(reference, location):
    if not isinstance(reference, str) or reference.count(".") != 1:
        raise SemanticModelError(
            f"{location} doit utiliser le format Concept.attribut."
        )
    return reference.split(".", 1)


def _validate_attribute_reference(reference, concepts, location):
    concept_name, attribute_name = _split_attribute_reference(reference, location)
    if concept_name not in concepts:
        raise SemanticModelError(
            f"{location} référence le concept inconnu {concept_name}."
        )
    attributes = concepts[concept_name].get("attributes", {})
    if attribute_name not in attributes:
        raise SemanticModelError(
            f"{location} référence l'attribut inconnu {reference}."
        )


def _temporal_ranges_are_disjoint(left, right):
    """Allow a shared alias only when ISO-like validity ranges cannot overlap."""
    left_end, right_start = left.get("valid_to"), right.get("valid_from")
    right_end, left_start = right.get("valid_to"), left.get("valid_from")
    return bool(
        (left_end is not None and right_start is not None and str(left_end) < str(right_start))
        or (right_end is not None and left_start is not None and str(right_end) < str(left_start))
    )
def validate_semantic_model(model):
    model = _require_mapping(model, "Le modèle")
    if not model.get("version"):
        raise SemanticModelError("Le champ version est obligatoire.")

    concepts = _require_mapping(model.get("concepts"), "concepts")
    required_concepts = {"Customer", "SupportTicket", "Transaction"}
    missing_concepts = required_concepts - set(concepts)
    if missing_concepts:
        raise SemanticModelError(
            "Concepts obligatoires absents : " + ", ".join(sorted(missing_concepts))
        )

    canonical_entity = model.get("canonical_entity")
    if canonical_entity not in concepts:
        raise SemanticModelError(
            f"L'entité canonique {canonical_entity!r} n'existe pas."
        )

    matching_policy = _require_mapping(
        model.get("matching_policy"), "matching_policy"
    )
    weights = _require_mapping(
        matching_policy.get("weights"), "matching_policy.weights"
    )
    if set(weights) != {"name", "type", "value"} or not all(
        isinstance(weight, (int, float)) and 0 <= weight <= 1
        for weight in weights.values()
    ):
        raise SemanticModelError(
            "Les poids name, type et value doivent être compris entre 0 et 1."
        )
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise SemanticModelError("La somme des poids de matching doit être égale à 1.")

    thresholds = _require_mapping(
        matching_policy.get("thresholds"), "matching_policy.thresholds"
    )
    required_thresholds = {
        "auto_accept_score",
        "auto_accept_margin",
        "review_score",
    }
    if set(thresholds) != required_thresholds or not all(
        isinstance(threshold, (int, float)) and 0 <= threshold <= 1
        for threshold in thresholds.values()
    ):
        raise SemanticModelError(
            "Les seuils de matching doivent être compris entre 0 et 1."
        )
    if thresholds["review_score"] > thresholds["auto_accept_score"]:
        raise SemanticModelError(
            "review_score ne peut pas dépasser auto_accept_score."
        )

    for concept_name, concept in concepts.items():
        concept = _require_mapping(concept, f"concepts.{concept_name}")
        attributes = _require_mapping(
            concept.get("attributes"), f"concepts.{concept_name}.attributes"
        )
        aliases = {}
        for attribute_name, attribute in attributes.items():
            attribute = _require_mapping(
                attribute, f"concepts.{concept_name}.attributes.{attribute_name}"
            )
            attribute_type = attribute.get("type")
            if attribute_type not in ALLOWED_TYPES:
                raise SemanticModelError(
                    f"Type invalide pour {concept_name}.{attribute_name} : "
                    f"{attribute_type!r}."
                )
            synonyms = attribute.get("synonyms", [])
            if not isinstance(synonyms, list) or not all(
                isinstance(item, str) and item for item in synonyms
            ):
                raise SemanticModelError(
                    f"Les synonymes de {concept_name}.{attribute_name} "
                    "doivent être une liste de chaînes."
                )
            for synonym in synonyms:
                normalized_synonym = synonym.strip().lower()
                previous = aliases.get(normalized_synonym)
                if (
                    previous
                    and previous != attribute_name
                    and not _temporal_ranges_are_disjoint(attributes[previous], attribute)
                ):
                    raise SemanticModelError(
                        f"Synonyme ambigu {synonym!r} dans {concept_name} : "
                        f"{previous} et {attribute_name}."
                    )
                aliases[normalized_synonym] = attribute_name
            reference = attribute.get("references")
            if reference is not None:
                _validate_attribute_reference(
                    reference,
                    concepts,
                    f"concepts.{concept_name}.attributes.{attribute_name}.references",
                )

    relations = model.get("relations", [])
    if not isinstance(relations, list):
        raise SemanticModelError("relations doit être une liste.")
    relation_names = set()
    for index, relation in enumerate(relations):
        relation = _require_mapping(relation, f"relations[{index}]")
        name = relation.get("name")
        if not name or name in relation_names:
            raise SemanticModelError(
                f"Le nom de relations[{index}] est absent ou dupliqué."
            )
        relation_names.add(name)
        for endpoint in ("source", "target"):
            if relation.get(endpoint) not in concepts:
                raise SemanticModelError(
                    f"relations[{index}].{endpoint} référence un concept inconnu."
                )
        for endpoint in ("source_attribute", "target_attribute"):
            _validate_attribute_reference(
                relation.get(endpoint), concepts, f"relations[{index}].{endpoint}"
            )
        if relation.get("cardinality") not in ALLOWED_CARDINALITIES:
            raise SemanticModelError(
                f"Cardinalité invalide dans relations[{index}]."
            )

    derived_attributes = _require_mapping(
        model.get("derived_attributes", {}), "derived_attributes"
    )
    for target, rule in derived_attributes.items():
        _validate_attribute_reference(target, concepts, f"derived_attributes.{target}")
        rule = _require_mapping(rule, f"derived_attributes.{target}")
        _validate_attribute_reference(
            rule.get("source"), concepts, f"derived_attributes.{target}.source"
        )
        if rule.get("aggregation") not in ALLOWED_AGGREGATIONS:
            raise SemanticModelError(
                f"Agrégation invalide pour derived_attributes.{target}."
            )

    return model


def load_semantic_model(path=DEFAULT_MODEL_PATH):
    path = Path(path)
    if not path.exists():
        raise SemanticModelError(f"Modèle sémantique introuvable : {path}")
    try:
        with path.open(encoding="utf-8") as stream:
            model = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        raise SemanticModelError(f"YAML invalide dans {path} : {error}") from error
    if isinstance(model, dict) and "extends" in model:
        base_path = (path.parent / model["extends"]).resolve()
        base = copy.deepcopy(load_semantic_model(base_path))
        overrides = _require_mapping(model.get("overrides"), "overrides")
        concept_overrides = _require_mapping(
            overrides.get("concepts", {}), "overrides.concepts"
        )
        for concept_name, concept_override in concept_overrides.items():
            if concept_name not in base["concepts"]:
                raise SemanticModelError(f"Surcharge d'un concept inconnu : {concept_name}.")
            additions = _require_mapping(
                _require_mapping(
                    concept_override, f"overrides.concepts.{concept_name}"
                ).get("add_attributes", {}),
                f"overrides.concepts.{concept_name}.add_attributes",
            )
            attributes = base["concepts"][concept_name]["attributes"]
            if set(additions) & set(attributes):
                raise SemanticModelError(
                    f"Ajout d'un attribut déjà déclaré dans {concept_name}."
                )
            attributes.update(copy.deepcopy(additions))
            synonym_extensions = _require_mapping(
                concept_override.get("extend_synonyms", {}),
                f"overrides.concepts.{concept_name}.extend_synonyms",
            )
            for attribute_name, synonyms in synonym_extensions.items():
                if attribute_name not in attributes:
                    raise SemanticModelError(
                        f"Extension de synonymes pour un attribut inconnu : {concept_name}.{attribute_name}."
                    )
                if not isinstance(synonyms, list) or not all(
                    isinstance(synonym, str) and synonym for synonym in synonyms
                ):
                    raise SemanticModelError(
                        f"Synonymes invalides pour {concept_name}.{attribute_name}."
                    )
                attributes[attribute_name].setdefault("synonyms", []).extend(synonyms)
        added_concepts = _require_mapping(
            overrides.get("add_concepts", {}), "overrides.add_concepts"
        )
        if set(added_concepts) & set(base["concepts"]):
            raise SemanticModelError("Ajout d'un concept déjà déclaré.")
        base["concepts"].update(copy.deepcopy(added_concepts))
        added_relations = overrides.get("add_relations", [])
        if not isinstance(added_relations, list):
            raise SemanticModelError("overrides.add_relations doit être une liste.")
        base.setdefault("relations", []).extend(copy.deepcopy(added_relations))
        model = base
    return validate_semantic_model(model)
