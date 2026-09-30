# Extension du benchmark : A1, A2 et scénarios sémantiques

## 1. Objet du document

Ce document fixe le contrat expérimental défini avant la campagne. A0–A3 et
S01–S05 sont désormais implémentés et exécutés ; le contrat ci-dessous est
conservé afin de rendre vérifiable que les responsabilités des architectures
n'ont pas été redéfinies après observation des résultats.

### État d'avancement

| Élément | État |
|---|---|
| A0 | Implémenté et testé sur P00–P05 |
| A1 | Implémenté et testé sur P00–P05 |
| A2 | Implémenté et testé sur P00–P05 |
| A3 | Implémenté et testé sur P00–P05 |
| S01–S05 | Générés et exécutés sur A0–A3 |

Les expériences existantes sont renommées de manière homogène :

| Identifiant | Expérience existante |
|---|---|
| P00 | Exécution nominale sur CRM, support et finance |
| P01 | Renommage de `support.mail` |
| P02 | Modification du format des pays |
| P03 | Fusion de `first_name` et `last_name` |
| P04 | Passage à l'échelle 1×, 5× et 10× |
| P05 | Ajout de la source Loyalty |

## 2. Architectures comparées

### A0 — ETL manuel

A0 correspond à la baseline actuelle.

- Sources déclarées explicitement dans le code.
- Mappings de colonnes écrits manuellement.
- Transformations et agrégations impératives en Python.
- Modèle YAML interdit.
- Profilage et matching automatiques interdits.
- Toute évolution exigeant une nouvelle règle est comptabilisée comme une
  adaptation de code.

Artefacts principaux : `src/baseline/transform.py` et
`src/baseline/pipeline.py`.

### A1 — Découverte et métadonnées automatiques

A1 représente une intégration pilotée par les métadonnées techniques, sans
couche sémantique métier.

- Découverte automatique des fichiers CSV.
- Profilage automatique : noms, types, formats, nullité, unicité et
  échantillons.
- Rapprochement fondé sur des heuristiques génériques de noms, types et
  distributions.
- Modèle métier, concepts, synonymes métier et relations YAML interdits.
- Règles propres à un client ou à une source interdites dans le moteur.
- Une ambiguïté non résolue doit être signalée ; elle ne peut pas être corrigée
  silencieusement par une connaissance métier cachée.

Le résultat attendu d'A1 est un ensemble de propositions techniques et une
table unifiée lorsque les métadonnées suffisent. A1 sert à déterminer quelle
partie des gains d'A3 provient simplement de la découverte et du profilage.

L'implémentation se trouve dans `src/metadata/`. Sur P00, elle découvre les
trois sources, profile 19 colonnes et classe 13 rôles techniques ; six colonnes
textuelles restent en revue. La détection des e-mails et des identifiants
répétés permet néanmoins d'obtenir un F1 de matching d'entités de `0.978558`.
Ce résultat ne doit pas être interprété comme une compréhension sémantique des
noms, pays ou relations métier. La campagne P01–P05 conserve un F1 de
`0.978558` pour les relations historiques. A1 découvre également Loyalty sans
adaptation et atteint un F1 CRM–Loyalty de `1.0`. En revanche, P02 augmente de
six à sept le nombre de colonnes en revue : une métadonnée technique seule ne
sait pas reconnaître les noms de pays qui remplacent des codes.

### A2 — Couche sémantique déclarative

A2 représente une architecture guidée par un modèle métier, mais non
adaptative.

L'implémentation A2 se trouve dans `src/declarative/` et sa déclaration dans
`semantic/a2_model.yaml`. Sur P00, ses 19 mappings et 13 transformations
déclaratives produisent 126 entités. Le matching obtient une précision de
`1.0`, un rappel de `0.958015` et un F1 de `0.978558`. La campagne P01–P05
montre que ce F1 est restauré après des adaptations YAML explicites : 1
opération en P01, 7 en P02, 4 en P03, aucune en P04 et 10 en P05. L'ajout de
Loyalty atteint un F1 CRM–Loyalty de `1.0` après déclaration de la source.

- Découverte automatique des sources autorisée.
- Concepts, relations, types, normalisations et attributs canoniques définis en
  YAML.
- Mappings source-vers-canonique déclarés explicitement à l'avance.
- Matching automatique, classement de candidats et score de confiance
  interdits.
- Une colonne absente du catalogue de mappings provoque un état
  `unmapped`, sans proposition automatique.

A2 mesure l'apport de la formalisation métier seule. L'ajout ou la modification
d'un mapping YAML est comptabilisé comme une intervention déclarative.

### A3 — Couche sémantique adaptative

A3 correspond à l'architecture sémantique actuelle enrichie.

- Découverte et profilage automatiques.
- Modèle métier YAML.
- Génération et classement automatique de candidats.
- Score composé sur les noms, types et valeurs.
- Politique `accepted`, `review` ou `rejected` fondée sur le score et la marge.
- Validations humaines explicites et traçables.
- Transformations et agrégations pilotées par le modèle.

Artefacts principaux : `semantic/model.yaml`, `src/semantic/profiler.py`,
`src/semantic/schema_matcher.py`, `src/semantic/transformer.py` et
`src/semantic/pipeline.py`.

## 3. Contraintes communes de comparabilité

Les quatre architectures doivent recevoir exactement les mêmes fichiers pour
chaque scénario. Elles partagent également :

- le même modèle canonique de sortie ;
- la même vérité terrain, jamais utilisée pour produire les mappings ;
- la même règle d'évaluation des entités ;
- les mêmes règles concernant les valeurs absentes ;
- le même environnement Python et la même machine ;
- le même nombre de préchauffages et d'exécutions mesurées ;
- le même ordre alterné des exécutions ;
- les mêmes fichiers de résultats séparés par architecture et scénario.

Une architecture ne peut pas utiliser un artefact interdit par son contrat. En
particulier, A1 ne lit aucun fichier du dossier `semantic/`, tandis qu'A2 ne
peut pas appeler le moteur de matching d'A3.

## 4. Entrées et sorties obligatoires

Chaque exécution doit produire :

- une table client unifiée ;
- les mappings proposés ou appliqués ;
- le statut de chaque colonne : `mapped`, `review`, `rejected` ou `unmapped` ;
- une trace des étapes exécutées ;
- les mesures de performance ;
- les métriques de qualité par scénario ;
- un relevé d'effort distinguant code, YAML et validation humaine.

Arborescence cible :

```text
results/benchmark_v2/
  P00/
    A0/
    A1/
    A2/
    A3/
  S01/
    A0/
    A1/
    A2/
    A3/
  ...
```

## 5. Scénarios sémantiques S01–S05

### S01 — Même nom, sens différent

Une colonne `status` apparaît dans deux sources :

- CRM : état du client (`active`, `inactive`) ;
- support : état du ticket (`open`, `closed`).

La vérité terrain attend deux attributs distincts. Un système qui rapproche les
colonnes uniquement par leur nom commet une erreur sémantique.

### S02 — Noms différents, même sens

La finance remplace `amount` par `gross_amount`, puis une nouvelle source
utilise `turnover_value` pour le même concept financier défini par la vérité
terrain. Le système doit retrouver l'équivalence sans confondre ce montant avec
un revenu déjà agrégé au niveau client.

### S03 — Définitions métier concurrentes

Une source fournit `gross_revenue` et une autre `net_revenue`. Les deux colonnes
sont numériques et proches lexicalement, mais ne sont pas interchangeables. Le
modèle canonique et la vérité terrain doivent distinguer les deux définitions,
leur unité, leur niveau d'agrégation et la prise en compte des taxes.

### S04 — Dérive sémantique temporelle

Avant une date de rupture, `active` signifie « connexion au cours des 90
derniers jours ». Après cette date, il signifie « contrat payant en cours ».
Le nom et le type restent identiques tandis que la définition et la distribution
changent. Le résultat attendu est une détection de dérive ou une revue, pas une
acceptation silencieuse.

### S05 — Conflit entre nom, type et valeurs

Une colonne nommée `customer_id` contient en réalité des identifiants de ticket
ou un mélange d'identifiants clients et tickets. Le nom favorise
`Customer.identifier`, mais les valeurs et le contexte contredisent ce choix.
Le système doit abaisser sa confiance et orienter le mapping vers une revue ou
un rejet.

## 6. Vérité terrain des scénarios

Chaque scénario doit être créé avant l'exécution des architectures et contenir :

- le mapping exact attendu pour chaque colonne ;
- les mappings explicitement incorrects ;
- les entités correspondant réellement ;
- la définition métier textuelle des attributs ambigus ;
- pour S04, la date de rupture et les deux définitions temporelles ;
- la décision attendue pour A3 : acceptation, revue ou rejet.

La vérité terrain sert uniquement à l'évaluation. Elle ne doit être importée par
aucun pipeline ou moteur de matching.

## 7. Métriques

### Qualité des mappings

- Precision, Recall et F1 des correspondances de schéma.
- Accuracy du meilleur candidat.
- Nombre de faux mappings acceptés automatiquement.
- Couverture : proportion de colonnes effectivement mappées.

### Confiance et intervention

- Taux d'acceptation automatique.
- Taux de revue et taux de rejet.
- Precision parmi les mappings acceptés.
- Courbe couverture–risque selon le seuil.
- Brier score lorsque la confiance est interprétée comme une probabilité.
- Expected Calibration Error par intervalles de confiance.
- Nombre de validations humaines nécessaires.

### Effort et performance

- Mappings et règles ajoutés.
- Fichiers Python et fichiers déclaratifs modifiés.
- Temps réel, temps CPU et pic mémoire Python.
- Temps d'intégration humain uniquement s'il est mesuré avec un protocole
  chronométré reproductible.

## 8. Ordre de réalisation

1. Geler ce contrat et les seuils d'A3.
2. Implémenter A1 sans accès au modèle YAML.
3. ~~Tester A1 sur P00–P05.~~
4. ~~Implémenter A2 sans appel au matcher automatique.~~
5. ~~Tester A2 sur P00–P05.~~
6. ~~Construire les vérités terrain S01–S05.~~
7. ~~Exécuter A0–A3 sur S01–S05.~~
8. Mesurer la calibration de confiance d'A3 sur une campagne répétée.
9. ~~Produire la première comparaison consolidée.~~
10. Produire l'analyse statistique multi-graines et multi-volumes.

## 9. Règle d'interprétation

La condition préalable est désormais satisfaite : A1 et A2 ont été implémentés
et exécutés sur les mêmes scénarios. Les conclusions doivent néanmoins
distinguer les gains provenant de la découverte technique, de la formalisation
métier et de l'adaptation automatique, et ne pas confondre revue sûre avec
mapping automatique correct.

## 10. Première synthèse S01–S05

La consolidation est disponible dans
`results/benchmark_v2/semantic_benchmark/`. A0 obtient un score final de `1.00`
avec des règles préparées à l'avance. A2 passe de `0.66` initialement à `1.00`
après quatre adaptations sur S04–S05. A3 obtient `0.80` dès l'état initial,
traite les cinq scénarios sans acceptation silencieuse incorrecte et requiert
quatre revues. A1 obtient `0.26` et accepte 70 erreurs silencieuses dans S05.

Ces valeurs sont descriptives et propres aux scénarios synthétiques présents.
Elles ne constituent pas encore une analyse statistique généralisable.
