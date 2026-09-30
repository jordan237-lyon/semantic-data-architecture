# Semantic Data Architecture — Research Lab

Application locale et protocole expérimental consacrés à l'intégration adaptative
de sources de données hétérogènes. Le projet compare quatre niveaux
d'architecture, de l'ETL manuel à la décision sémantique avec score de confiance.

## Démonstration locale

### Prérequis

- Python 3.9 ou supérieur ;
- Git ;
- un terminal ouvert à la racine du projet.

### Installation

```bash
git clone https://github.com/jordan237-lyon/semantic-data-architecture.git
cd semantic-data-architecture

python3 -m venv myenv
source myenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-app.txt
```

Sous Windows PowerShell, l'activation s'effectue avec :

```powershell
myenv\Scripts\Activate.ps1
```

### Lancer l'interface Streamlit

```bash
python -m streamlit run app/ui/dashboard.py
```

Ouvrir ensuite <http://localhost:8501>. L'application permet d'explorer P00 et
S01–S05, de comprendre les sources, de profiler leurs colonnes et de consulter
la comparaison A0–A3.

### Lancer l'API locale — optionnel

Dans un second terminal, avec l'environnement activé :

```bash
python -m uvicorn app.api.main:app --reload
```

- API : <http://localhost:8000>
- documentation interactive : <http://localhost:8000/docs>
- vérification : <http://localhost:8000/health>

### Vérifier le projet

```bash
python -m pytest -q
```

La version actuelle comporte 89 tests automatisés. Les données et résultats de
recherche nécessaires à la démonstration sont inclus dans le dépôt.

## Première version de l'application

La version `v0.1.0` est un laboratoire en lecture seule. Elle ne modifie ni les
données, ni les vérités terrain, ni les résultats expérimentaux.

- page d'accueil narrative ;
- catalogue des scénarios P00 et S01–S05 ;
- aperçu et profilage des sources ;
- explication pédagogique du mapping sémantique ;
- comparaison des architectures A0, A1, A2 et A3 ;
- API FastAPI en lecture seule.

Le périmètre détaillé est décrit dans
[`docs/application_v01.md`](docs/application_v01.md).

## L'histoire racontée par les données

Tout commence avec un client, par exemple **Jean Martin**. Dans le CRM, il est
connu sous l'identifiant `CRM0021`. Lorsqu'il contacte le support, il devient
`SUP-0021` et son nom apparaît en majuscules. Côté finance, il porte encore un
autre identifiant, `ACC0021`, son e-mail est écrit en majuscules et son pays est
réduit au code `IT`. Il s'agit pourtant toujours de la même personne.

Ce POC met en scène cette réalité fréquente des systèmes d'information : trois
sources décrivent les mêmes clients, mais chacune possède son propre vocabulaire
et ses propres conventions. Le CRM contient **120 clients**, le support
**495 tickets associés à 90 clients observables**, et la finance **250
transactions associées à 100 comptes**. Les e-mails peuvent comporter des
majuscules ou des espaces, les noms changer de format et les pays être
représentés par un nom ou un code.

Le pipeline joue alors le rôle de traducteur. Il agrège d'abord les tickets et
les transactions au niveau client, harmonise les noms, les e-mails et les pays,
puis rapproche les enregistrements grâce à l'adresse e-mail normalisée. Cette
première version repose sur **19 correspondances de schéma** et **9 règles de
transformation** écrites manuellement : elle constitue le point de départ à
dépasser avec une approche d'intégration assistée par la sémantique.

## Composition du projet

### Documentation et dépendances

- **`README.md`** : présente le problème étudié, le rôle des données, la
  structure du projet et la procédure d'exécution.
- **`requirements.txt`** : déclare les bibliothèques Python nécessaires.
  `pandas` sert à lire, transformer et fusionner les données ; `pytest` sert à
  exécuter les tests automatisés.

### Données sources — `data/raw/`

Ces trois fichiers CSV simulent des applications indépendantes qui ne se sont
pas accordées sur un modèle de données commun.

- **`crm.csv`** : référentiel commercial de 120 clients. Chaque ligne contient
  l'identifiant CRM (`client_id`), le prénom, le nom, l'e-mail, le pays et la
  date de création du client. Il constitue la source principale du pipeline.
- **`support.csv`** : historique synthétique dont chaque ligne représente un
  ticket. Il contient `ticket_id`, la référence du client, ses attributs et la
  date du ticket. Plusieurs lignes peuvent donc appartenir au même client.
- **`finance.csv`** : historique dont chaque ligne représente une transaction.
  Il contient `transaction_id`, le compte concerné, les attributs du client, le
  montant (`amount`) et la date. Plusieurs transactions peuvent appartenir au
  même compte.

### Données de génération — `data/seed/`

- **`support_customers.csv`** : copie de la source support agrégée initiale. Son
  champ `ticket_count` détermine combien de tickets doivent être générés.
- **`finance_accounts.csv`** : copie de la source financière agrégée initiale.
  Son champ `revenue` est réparti entre plusieurs transactions sans modifier le
  total de chaque compte.
- **`scripts/introduce_granularity.py`** : transforme ces deux tables agrégées
  en sources événementielles reproductibles et actualise la présence des
  clients support dans la vérité terrain.

### Vérité terrain — `data/ground_truth/`

Ces fichiers décrivent la réponse attendue. Ils ne servent pas à construire la
fusion de référence, mais permettront de mesurer objectivement les résultats
des différentes approches.

- **`schema_mapping.csv`** : indique l'attribut sémantique porté par chaque
  colonne. Par exemple, `email`, `mail` et `contact_email` correspondent à
  `Customer.email`. Pour les clés étrangères événementielles, la colonne
  `references` précise aussi l'attribut visé : `customer_ref` appartient à
  `SupportTicket`, mais référence `Customer.identifier`.
- **`entity_mapping.csv`** : indique quels identifiants CRM, support et finance
  désignent une même personne. L'identifiant neutre `canonical_customer_id`
  représente le client réel attendu ; une cellule vide signifie que ce client
  n'existe pas dans la source concernée.

### Code de transformation — `src/`

- **`src/baseline/transform.py`** : contient les règles de préparation propres
  à chaque source. Le fichier normalise les e-mails, harmonise la casse des
  noms, recompose les noms séparés du CRM et traduit les codes pays de la
  finance. Il compte aussi les tickets par client et additionne les transactions
  par compte avant de retourner des colonnes homogènes.
- **`src/baseline/pipeline.py`** : orchestre tout le traitement. Il charge les
  trois CSV, appelle les fonctions de transformation, réalise deux jointures
  externes sur l'e-mail normalisé, écrit la table unifiée, puis enregistre les
  métriques d'exécution.
- **`src/evaluation/metrics.py`** : fournit les fonctions `precision`, `recall`
  et `f1_score`. Elles serviront à comparer les correspondances produites par
  un pipeline avec celles de la vérité terrain.
- **Les fichiers `__init__.py`** : déclarent les dossiers comme des modules
  Python afin de permettre des imports tels que
  `from src.baseline.transform import prepare_crm`.

### Résultats produits

- **`data/output/unified_customer_baseline.csv`** : table finale générée par le
  pipeline. Une ligne rassemble, lorsque le rapprochement est possible, les
  identifiants et attributs CRM, support et finance d'un même client. La jointure
  externe conserve aussi les enregistrements présents dans une seule source.
- **`results/baseline/baseline_metrics.json`** : résumé mesurable d'une exécution : temps
  de traitement, nombre de règles manuelles, dimensions de la table finale et
  nombre de lignes support/finance rattachées par e-mail.

### Tests

- **`tests/test_metrics.py`** : vérifie sur de petits exemples connus que les
  calculs de précision, de rappel et de score F1 renvoient les bonnes valeurs.

Les dossiers **`__pycache__/`** et les fichiers `.pyc` sont créés
automatiquement par Python pour accélérer le chargement des modules. Ils ne
contiennent ni logique métier ni données du projet.

## Reproduire les expériences

```bash
python3 -m venv myenv
source myenv/bin/activate
python -m pip install -r requirements-app.txt
python scripts/introduce_granularity.py
python -m src.baseline.pipeline
python -m src.evaluation.evaluate_baseline
python -m src.semantic.schema_matcher
python -m src.semantic.pipeline
python -m src.evaluation.benchmark
python -m src.evaluation.visualize_comparison
python -m pytest -q
```

Expected outputs:

- `data/output/unified_customer_baseline.csv`
- `results/baseline/baseline_metrics.json`
- `results/baseline/baseline_evaluation.json`
- `results/baseline/baseline_matching_errors.csv`
- `results/baseline/baseline_evaluation_plot.svg`
- `results/baseline/plots/`
- `results/semantic/`

## Évaluation de la baseline

L'évaluation compare les paires d'identifiants produites par la jointure sur
l'e-mail avec `data/ground_truth/entity_mapping.csv`. Elle calcule la précision,
le rappel et le score F1 séparément pour les relations CRM-support,
CRM-finance et support-finance, puis calcule un résultat global. Le fichier des
erreurs détaille chaque faux positif et chaque faux négatif afin de permettre
une analyse qualitative. Le graphique SVG facilite la comparaison visuelle des
scores entre les relations.

Pour produire les visuels détaillés :

```bash
python -m src.evaluation.visualize_baseline
```

Le tableau de bord rassemble les résultats essentiels. Les trois autres
graphiques présentent séparément les scores de qualité, les volumes de
correspondances et la matrice expliquant les neuf faux positifs provoqués par
les e-mails absents.

## Couche sémantique minimale

Le fichier `semantic/model.yaml` rend la connaissance métier explicite et
indépendante du pipeline. Il définit les concepts `Customer`, `SupportTicket`
et `Transaction`, leurs attributs, synonymes, types, normalisations et
relations. Il exprime également les agrégations permettant de compter les
tickets et de sommer les transactions au niveau client.

Les colonnes relationnelles conservent leurs deux dimensions sémantiques. Par
exemple, `support.customer_ref` est décrit comme
`SupportTicket.customer_reference` tout en référençant `Customer.identifier`.
Cette distinction sépare le rôle structurel de la colonne de l'entité métier
qu'elle permet de retrouver.

Le chargeur `src/semantic/model_loader.py` vérifie la structure du YAML, les
types, les références entre concepts, les cardinalités, les agrégations et les
synonymes ambigus. À ce stade, le modèle est déclaratif : le futur moteur de
matching l'utilisera pour analyser automatiquement les schémas.

## Matching automatique des schémas

Le module `src/semantic/profiler.py` analyse chaque colonne des sources : type
probable, format détecté, taux de valeurs absentes, unicité et échantillons. Le
module `src/semantic/schema_matcher.py` compare ensuite ce profil aux attributs
du modèle YAML selon la pondération suivante : 50 % pour le nom, 20 % pour le
type et 30 % pour les valeurs.

Le moteur conserve le meilleur attribut, le second candidat et leur écart de
score. Il produit les fichiers suivants :

- `results/semantic/schema_profiles.json`
- `results/semantic/semantic_schema_matches.csv`
- `results/semantic/semantic_schema_decisions.csv`
- `results/semantic/schema_review_queue.csv`
- `results/semantic/schema_confidence_metrics.json`

Pour lancer l'analyse :

```bash
python -m src.semantic.schema_matcher
```

La politique de confiance est déclarée dans le YAML. Un mapping est accepté si
son score atteint `0.85` avec une marge minimale de `0.10`, envoyé en validation
si son score atteint au moins `0.60`, puis rejeté sous ce seuil. Les résultats
sont séparés entre `results/baseline/` et `results/semantic/`, tandis que les
graphiques de la baseline sont regroupés dans `results/baseline/plots/`.

Les visualisations sémantiques sont générées avec :

```bash
python -m src.semantic.visualize_schema_matching
```

Elles sont enregistrées dans `results/semantic/plots/` : tableau de bord des
décisions, graphique score-marge, décomposition des composantes du score et
schéma du parcours complet du moteur.

## Pipeline sémantique

Le fichier `semantic/human_validations.yaml` conserve les décisions humaines
nécessaires pour les mappings ambigus. Le module `src/semantic/pipeline.py`
enchaîne le profilage, le matching de schéma, la politique de confiance, les
validations, les transformations déclarées dans le YAML, les agrégations et le
matching des entités.

Contrairement à la baseline, les e-mails absents reçoivent des clés techniques
distinctes et ne peuvent jamais provoquer un rapprochement. Les résultats sont
enregistrés dans :

- `data/output/unified_customer_semantic.csv`
- `results/semantic/pipeline/semantic_pipeline_metrics.json`
- `results/semantic/pipeline/semantic_evaluation.json`
- `results/semantic/pipeline/semantic_matching_errors.csv`
- `results/semantic/pipeline/execution_trace.json`

## Benchmark comparatif

Le module `src/evaluation/benchmark.py` exécute chaque pipeline cinq fois pour
le préchauffage, puis trente fois pour la mesure. L'ordre d'exécution alterne
afin de limiter le biais temporel. Il mesure le temps réel, le temps CPU et le
pic des allocations mémoire Python avec `tracemalloc`.

Les résultats bruts, les statistiques agrégées, la qualité et l'effort sont
rangés dans `results/comparison/`. Les graphiques peuvent être régénérés avec :

```bash
python -m src.evaluation.visualize_comparison
```

Le coût initial de construction du modèle sémantique est séparé de l'effort
nécessaire pour intégrer une source. Les nombres d'artefacts et de décisions ne
sont pas présentés comme des heures de travail.

## Perturbations

Le premier scénario renomme uniquement `support.mail` en
`support.customer_email_address` dans une copie isolée des sources. Les données
de référence ne sont jamais modifiées. Pour générer et exécuter P01 :

```bash
python -m src.evaluation.perturbations
```

Les données du scénario sont rangées dans
`data/perturbations/p01_renamed_column/` et ses résultats dans
`results/perturbations/p01_renamed_column/`.

La validation humaine de `support.customer_email_address` est conservée dans
`data/perturbations/p01_renamed_column/human_validations.yaml`. Elle est propre
au scénario et n'ajoute aucun synonyme au modèle sémantique global.

Les visuels du scénario sont régénérés avec :

```bash
python -m src.evaluation.visualize_perturbation
```

Ils présentent le résultat avant adaptation, la différence entre panne
technique et validation métier, ainsi que la décomposition du score ayant
conduit le nouveau champ en revue humaine.

Le deuxième scénario modifie uniquement le format des valeurs de
`finance.country_code` : les codes (`FR`, `IT`, etc.) deviennent des libellés
minuscules (`france`, `italy`, etc.). Il vérifie séparément le succès technique,
la qualité du matching d'entités et la conformité des pays au format canonique.

```bash
python -m src.evaluation.perturbation_p02
python -m src.evaluation.visualize_p02
```

Les artefacts sont isolés dans `data/perturbations/p02_country_format/` et
`results/perturbations/p02_country_format/`.

L'état à 0 % de conformité est conservé dans `before_adaptation/`. Après
adaptation, la baseline ajoute une normalisation impérative dans Python, tandis
que l'approche sémantique étend le vocabulaire YAML avec les sept libellés en
minuscules. Le visuel P02 compare directement les deux états.

Le troisième scénario réalise une évolution structurelle du CRM : les colonnes
`first_name` et `last_name` sont remplacées par `customer_name`. Il permet de
vérifier si chaque architecture dépend de la structure physique historique ou
si elle peut retrouver directement le concept `Customer.full_name`.

```bash
python -m src.evaluation.perturbation_p03
python -m src.evaluation.visualize_p03
```

Les données et résultats de P03 sont isolés dans les dossiers
`data/perturbations/p03_merged_name_columns/` et
`results/perturbations/p03_merged_name_columns/`.

L'état avant adaptation est conservé dans `before_adaptation/`. Pour accepter
le schéma fusionné, la baseline ajoute une branche Python et passe à onze règles
manuelles. L'approche sémantique reconnaît automatiquement `customer_name`
comme `Customer.full_name` sans modification ni validation supplémentaire.

## Test de passage à l'échelle

Le module `src/evaluation/scale_experiment.py` construit trois jeux isolés de
taille 1×, 5× et 10×. Les blocs répliqués reçoivent des identifiants et des
e-mails uniques ; les valeurs absentes sont conservées. Pour chaque volume, les
deux pipelines sont préchauffés puis mesurés cinq fois avec alternance de
l'ordre d'exécution. Le protocole relève le temps médian, le pic mémoire Python,
le volume de sortie et les scores de qualité.

```bash
python -m src.evaluation.scale_experiment
python -m src.evaluation.visualize_scale
```

Les données générées sont rangées dans `data/scale/`, et les mesures dans
`results/scale/`. Le tableau de bord est également fourni en PNG afin de pouvoir
l'ouvrir directement dans un éditeur qui affiche les SVG comme du texte XML.

Les premières mesures, conservées dans `results/scale/before_null_fix/`, ont
montré une chute du F1 de la baseline lorsque les e-mails absents se
multipliaient. La correction ajoute une douzième règle manuelle : chaque e-mail
absent reçoit une clé technique distincte et ne peut donc plus être rapproché
d'un autre e-mail absent.

## Ajout d'une quatrième source

Le scénario `loyalty` ajoute 80 membres décrits par cinq colonnes inconnues des
pipelines initiaux : `member_id`, `display_name`, `email_address`, `market` et
`joined_on`. La vérité terrain étendue relie chaque membre à son client CRM.

```bash
python -m src.evaluation.new_source_experiment
python -m src.evaluation.visualize_new_source
```

Avant adaptation, les deux orchestrations ignorent le nouveau fichier et leur
couverture est donc nulle. Exécuté séparément, le matcher sémantique propose le
bon candidat pour quatre colonnes sur cinq : une est acceptée automatiquement
et quatre sont orientées vers une revue humaine. Les artefacts sont conservés
dans `results/new_source/loyalty/before_adaptation/`.

Après adaptation, la baseline ajoute cinq mappings, cinq règles et la prise en
charge explicite de `loyalty.csv`. L'architecture sémantique découvre désormais
les CSV présents, fusionne génériquement les nouvelles vues `Customer` et
ajoute quatre synonymes au modèle YAML. Les cinq colonnes Loyalty sont alors
acceptées automatiquement, sans validation humaine. Les deux approches
retrouvent les 80 correspondances CRM–Loyalty avec une précision et un rappel
de 1,0. Les résultats finaux sont dans
`results/new_source/loyalty/after_adaptation/`.

```bash
python -m src.evaluation.visualize_new_source_after
```

## Synthèse expérimentale

La synthèse finale est générée avec :

```bash
python -m src.evaluation.final_synthesis
```

Après correction du traitement des e-mails absents, les deux approches
atteignent un F1 nominal de `0.978558`. La baseline reste la plus performante :
son temps médian est de `0.0314 s`, contre `0.1634 s` pour la sémantique, soit
un facteur d'environ `5.21`. Le pic médian des allocations Python est de
`0.52 Mo` pour la baseline et `0.72 Mo` pour la sémantique.

Le bénéfice principal de la sémantique apparaît dans l'adaptation. P01 est
transformé en validation métier plutôt qu'en panne, P03 est absorbé
automatiquement et la quatrième source obtient cinq mappings automatiques après
enrichissement du vocabulaire. P02 rappelle toutefois que la sémantique ne
supprime pas tout effort : une représentation métier inconnue doit être ajoutée
au YAML. La découverte générique de nouvelles sources a également nécessité
une évolution initiale du code d'orchestration.

Les conclusions doivent rester limitées au périmètre du POC : données
synthétiques, domaine unique, matching exact par e-mail, une seule machine et
mesure de l'effort en artefacts plutôt qu'en heures humaines. Le rapport JSON,
la matrice CSV et le dashboard PNG sont regroupés dans `results/final/`.

## Benchmark étendu : A0–A3 et scénarios sémantiques S01–S05

La seconde campagne expérimentale est terminée. Elle complète P00–P05 avec des
cas où la difficulté ne vient plus seulement du format ou de la structure, mais
du sens des données. Les quatre niveaux comparés sont : A0, ETL manuel ; A1,
découverte et métadonnées techniques ; A2, mappings sémantiques déclaratifs ;
et A3, matching adaptatif avec score de confiance.

Le contrat expérimental, fixé avant l'exécution, est conservé dans
[`docs/benchmark_extension_a1_a2_semantic_scenarios.md`](docs/benchmark_extension_a1_a2_semantic_scenarios.md).

La première implémentation A1 est disponible dans `src/metadata/`. Elle utilise
uniquement la découverte des CSV, les types, formats, taux de nullité et taux
d'unicité. Elle ne lit aucun artefact du dossier `semantic/`.

```bash
python -m src.metadata.pipeline
```

Sur P00, A1 découvre les trois sources et atteint un F1 d'entités de `0.978558`
grâce aux e-mails détectés automatiquement. Treize colonnes reçoivent un rôle
technique et six textes restent en revue. Les résultats sont enregistrés dans
`results/benchmark_v2/P00/A1/`. La campagne P01–P05 se lance avec :

```bash
python -m src.metadata.campaign
```

Elle conserve un F1 de `0.978558` sur les relations historiques, teste les
échelles 1×, 5× et 10× et découvre automatiquement Loyalty avec un F1
CRM–Loyalty de `1.0`.

A2 est disponible dans `src/declarative/`. Il exécute exclusivement les
mappings et transformations prédéfinis dans `semantic/a2_model.yaml`, sans
matcher automatique ni score de confiance :

```bash
python -m src.declarative.pipeline
python -m src.declarative.visualize
```

Sur P00, A2 produit 126 entités avec une précision de `1.0`, un rappel de
`0.958015` et un F1 de `0.978558`. La campagne P01–P05 est également terminée :
A2 restaure la même qualité après des adaptations YAML explicites et intègre
Loyalty avec un F1 CRM–Loyalty de `1.0`. La synthèse se trouve dans
`results/benchmark_v2/a2_campaign_summary.csv`.

Les visuels A1/P00 sont générés au format PNG avec :

```bash
python -m src.metadata.visualize
python -m src.metadata.visualize_campaign
```

Le tableau de bord résume le pipeline et ses scores. La carte des colonnes
montre les rôles techniques détectés et met en évidence les six textes qui
restent sans interprétation métier.

### Ce que racontent les scénarios S01–S05

- **S01 — même nom, sens différent** : `status` décrit un client dans le CRM et
  un ticket dans le support. A0 et A2 appliquent les distinctions préparées ;
  A1 et A3 orientent les deux colonnes vers une revue. A3 retrouve les bons
  candidats, mais sa marge de confiance reste insuffisante pour les accepter.
- **S02 — noms différents, même sens** : `gross_amount` et `turnover_value`
  désignent tous deux le montant d'une transaction. A0, A2 et A3 obtiennent un
  F1 de `1.0`. A1 reconnaît des mesures numériques sans pouvoir prouver leur
  équivalence métier.
- **S03 — définitions concurrentes** : le revenu brut et le revenu net sont
  fortement corrélés (`0.997861`), mais non interchangeables. A0, A2 et A3 les
  distinguent correctement ; A1 demande deux validations.
- **S04 — dérive temporelle** : `active` passe de « connexion dans les 90
  derniers jours » à « contrat payant en cours » le `2025-07-01`. A2 réutilise
  silencieusement l'ancien sens avant adaptation. A1 et A3 détectent un risque
  et déclenchent une revue.
- **S05 — nom contredit par les valeurs** : `customer_id` contient 70 %
  d'identifiants de tickets et 30 % d'identifiants clients. A1 et A2 avant
  adaptation n'obtiennent qu'un F1 de `0.30` et produisent 70 erreurs
  silencieuses. La faible marge d'A3 (`0.009`) empêche l'acceptation automatique.

Les scénarios peuvent être régénérés et exécutés séparément avec :

```bash
python -c "from src.evaluation.semantic_scenarios import generate_s01, generate_s02, generate_s03, generate_s04, generate_s05; [f() for f in (generate_s01, generate_s02, generate_s03, generate_s04, generate_s05)]"
python -m src.evaluation.s01_benchmark
python -m src.evaluation.s02_benchmark
python -m src.evaluation.s03_benchmark
python -m src.evaluation.s04_benchmark
python -m src.evaluation.s05_benchmark
python -m src.evaluation.consolidate_semantic_benchmark
python -m src.evaluation.visualize_semantic_benchmark
```

### Résultats consolidés

Le score ci-dessous est une normalisation documentée : F1 de mapping pour
S01–S03, gestion sûre de la dérive pour S04, puis F1 par valeur ou revue sûre
pour S05. Il facilite la lecture globale, mais ne remplace pas les métriques
détaillées de chaque scénario.

| Architecture | Score initial | Score final | Scénarios sûrs au départ | Erreurs silencieuses | Revues initiales |
|---|---:|---:|---:|---:|---:|
| A0 | 1.00 | 1.00 | 5/5 | 0 | 0 |
| A1 | 0.26 | 0.26 | 4/5 | 70 | 7 |
| A2 | 0.66 | 1.00 | 3/5 | 71 | 0 |
| A3 | 0.80 | 0.80 | 5/5 | 0 | 4 |

A0 atteint la qualité maximale parce que ses règles sont fournies à l'avance.
A2 atteint également `1.00`, mais après quatre adaptations post-détection sur
S04 et S05. A3 offre le meilleur compromis initial entre automatisation et
sécurité : il accepte les équivalences suffisamment nettes et bloque les cas
ambigus. Cette sécurité réduit toutefois sa couverture automatique et suppose
la maintenance d'un modèle et de politiques sémantiques.

Les artefacts consolidés sont regroupés dans
`results/benchmark_v2/semantic_benchmark/` : résultats détaillés par scénario,
résumé par architecture, conclusions et dashboard PNG.

### Limites scientifiques

Les données sont synthétiques, limitées à un domaine et à une machine. Les
scores agrégés combinent plusieurs types de tâches. Les configurations propres
aux scénarios représentent elles-mêmes un coût de préparation, même lorsqu'une
architecture ne nécessite aucune adaptation après détection. Enfin, les temps
d'exécution observés sur ces petits volumes ne constituent pas un benchmark de
performance généralisable. Une campagne multi-graines, multi-volumes et avec
plusieurs niveaux de bruit reste nécessaire.

## Rôle scientifique

Ce projet compare désormais quatre niveaux d'intégration sur les mêmes données :
manuel, technique, déclaratif et adaptatif. Il sert à étudier non seulement la
qualité finale, mais aussi le risque d'acceptation silencieuse, la couverture
automatique et l'effort nécessaire lors d'une évolution non anticipée.

## Séparation des benchmarks V1 et V2

Les deux campagnes disposent maintenant d'espaces indépendants :

- `results/benchmark_v1/` rassemble la baseline, le premier pipeline
  sémantique, P01–P05, les essais d'échelle et la synthèse historique ;
- `results/benchmark_v2/` contient les architectures A0–A3 ainsi que les
  scénarios structurels P00–P05 et sémantiques S01–S05 ;
- `results/benchmark_comparison/` contient uniquement les métriques qui peuvent
  être comparées sans mélanger des tâches différentes.

Sur P00, V1 baseline, V1 sémantique, V2/A1 et V2/A2 obtiennent tous un F1
nominal de `0.978558`. L'apport observé de V2 est donc principalement
méthodologique : quatre architectures isolées et cinq scénarios supplémentaires
d'ambiguïté ou de dérive sémantique. Le rapport détaillé est disponible dans
[`results/benchmark_comparison/README.md`](results/benchmark_comparison/README.md).

## Campagne de robustesse R01

La campagne R01 vérifie la stabilité des conclusions sur plusieurs graines et
intensités. Elle porte sur S01, S04 et S05 avec trois graines, trois niveaux de
difficulté et 100 entités. Les 108 exécutions A0–A3 sont terminées sans échec.

Le protocole est gelé avant implémentation dans
[`docs/robustness_r01_protocol.md`](docs/robustness_r01_protocol.md). Il précise
les hypothèses, la séparation calibration/test, les métriques, l'isolation des
données et les critères autorisant le passage à une campagne plus large.

Les résultats et limites sont présentés dans
[`results/robustness/R01/conclusions.md`](results/robustness/R01/conclusions.md).
