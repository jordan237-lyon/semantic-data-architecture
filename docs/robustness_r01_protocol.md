# R01 — Protocole pilote de robustesse multi-graines

## 1. Objectif scientifique

La campagne R01 vérifie si les comportements observés sur S01, S04 et S05
restent stables lorsque les données synthétiques, l'intensité des perturbations
et le bruit varient.

La question principale est :

> Les différences de qualité, de sécurité et d'effort entre A0, A1, A2 et A3
> persistent-elles sur plusieurs réalisations indépendantes ?

R01 ne cherche pas encore à produire une conclusion généralisable. Il s'agit
d'un pilote destiné à valider les générateurs, les métriques et la chaîne
d'analyse statistique avant une campagne plus coûteuse.

## 2. Hypothèses

### H1 — Stabilité

Les tendances observées lors de la première campagne ne dépendent pas d'une
seule réalisation synthétique.

### H2 — Sécurité d'A3

A3 conserve un faible nombre d'acceptations silencieusement incorrectes lorsque
l'ambiguïté ou le bruit augmente, au prix d'une augmentation des revues.

### H3 — Limite d'A1

A1 reste efficace pour les phénomènes purement techniques, mais perd en qualité
lorsque la décision dépend d'une définition métier.

### H4 — Adaptation d'A2

A2 conserve une forte qualité après adaptation explicite, mais son état initial
devient fragile face aux évolutions non déclarées.

### H5 — Coût d'A0

A0 reste exact lorsque toutes les règles sont connues, mais son nombre de règles
et d'adaptations augmente avec les variantes expérimentales.

## 3. Architectures comparées

Les responsabilités d'A0, A1, A2 et A3 restent celles du contrat principal :

- **A0** : ETL et règles manuelles ;
- **A1** : découverte et métadonnées techniques sans modèle métier ;
- **A2** : mappings déclaratifs prédéfinis sans matching automatique ;
- **A3** : modèle sémantique, candidats automatiques et politique de confiance.

Aucune architecture ne peut recevoir une information interdite par son contrat.
La vérité terrain sert uniquement à l'évaluation.

## 4. Scénarios du pilote

### R01-S01 — Même nom, sens différent

Deux colonnes `status` appartiennent à des contextes métier distincts. Le pilote
fait varier le chevauchement entre leurs vocabulaires.

Intensités :

| Niveau | Chevauchement des valeurs |
|---|---:|
| I0 | 0 % |
| I1 | 50 % |
| I2 | 100 % |

La vérité terrain conserve deux attributs distincts pour tous les niveaux.

### R01-S04 — Dérive sémantique temporelle

La colonne `active` conserve son nom et son type, mais change de définition à
une date de rupture.

Intensités :

| Niveau | Variation du taux de `true` |
|---|---:|
| I0 | 5 points |
| I1 | 15 points |
| I2 | 40 points |

Le résultat sûr est une détection ou une revue. Une réutilisation silencieuse
de l'ancienne définition constitue une erreur.

### R01-S05 — Identifiants mélangés

La colonne `customer_id` contient deux classes sémantiques de valeurs.

Intensités :

| Niveau | Identifiants de tickets | Identifiants clients |
|---|---:|---:|
| I0 | 10 % | 90 % |
| I1 | 50 % | 50 % |
| I2 | 90 % | 10 % |

Un mapping unique est considéré comme invalide dès que les deux classes sont
présentes. Le résultat attendu est une séparation explicite ou une revue.

## 5. Graines et volume

Le pilote utilise :

- graines : `11`, `22`, `33` ;
- volume : `100` entités ;
- trois scénarios ;
- trois intensités par scénario ;
- quatre architectures.

Le nombre attendu d'exécutions est donc :

```text
3 graines × 3 scénarios × 3 intensités × 4 architectures = 108 exécutions
```

Les exécutions éventuelles avant et après adaptation doivent être enregistrées
comme deux états d'une même combinaison, et non comme deux tirages indépendants.

## 6. Bruit du pilote

Pour isoler d'abord l'effet de l'intensité sémantique, le pilote conserve un
unique niveau de bruit modéré :

- 5 % de valeurs manquantes sur les attributs non identifiants ;
- 5 % de différences de casse ou d'espaces ;
- aucune suppression de ligne ;
- aucune corruption de la vérité terrain ;
- aucune valeur manquante introduite dans la colonne ambiguë évaluée.

La campagne complète ajoutera des niveaux N0 à N3 après validation du pilote.

## 7. Reproductibilité et isolation

Chaque combinaison possède une clé stable :

```text
{scenario}__{intensity}__seed-{seed}__{architecture}__{state}
```

Exemple :

```text
S05__I1__seed-22__A2__before_adaptation
```

Chaque combinaison doit :

- utiliser son propre dossier de données générées ;
- utiliser son propre dossier de résultats ;
- enregistrer les paramètres exacts ;
- ne jamais modifier `data/raw/` ou les scénarios S01–S05 historiques ;
- être régénérable à partir de la graine et du manifeste ;
- produire les mêmes données et résultats déterministes sur la même version du
  code.

## 8. Séparation calibration et test

La graine `11` constitue l'ensemble de développement et de calibration du
pilote. Elle peut servir à vérifier les générateurs et à corriger une erreur
d'implémentation.

Les graines `22` et `33` constituent l'ensemble de test pilote. Aucun seuil ne
doit être modifié après observation de leurs résultats.

Les seuils A3 restent initialement gelés :

```text
auto_accept_score = 0.85
auto_accept_margin = 0.10
review_score = 0.60
```

Le pilote n'optimise pas encore ces seuils. Il vérifie d'abord leur stabilité.

## 9. Métriques obligatoires

### Qualité

- précision ;
- rappel ;
- F1 ;
- accuracy du meilleur candidat ;
- couverture automatique.

### Sécurité

- acceptations correctes ;
- acceptations incorrectes ;
- erreurs silencieuses ;
- revues ;
- rejets ;
- proportion de scénarios traités de manière sûre.

### Adaptation et intervention

- règles Python ajoutées ;
- déclarations YAML ajoutées ou modifiées ;
- validations humaines ;
- états avant et après adaptation ;
- nombre total d'actions d'adaptation.

### Performance descriptive

- temps réel ;
- temps CPU ;
- pic mémoire Python ;
- nombre de lignes et de colonnes traitées.

Les performances du pilote sont descriptives et ne doivent pas être utilisées
pour une conclusion de passage à l'échelle.

## 10. Agrégation statistique

Pour chaque couple scénario–intensité–architecture, calculer sur les graines de
test :

- moyenne ;
- médiane ;
- écart-type ;
- minimum et maximum ;
- intervalle de confiance à 95 % lorsque le nombre de répétitions le permet.

Avec seulement deux graines de test, les intervalles de confiance du pilote
seront trop instables pour une interprétation forte. Leur calcul sert à valider
la chaîne technique. La campagne complète utilisera au moins dix graines.

## 11. Structure attendue

```text
data/robustness/R01/
  manifests/
  S01/
  S04/
  S05/

results/robustness/R01/
  raw_runs.csv
  scenario_summary.csv
  architecture_summary.csv
  confidence_intervals.json
  calibration/
  plots/
  conclusions.md
```

## 12. Visuels prévus

- score moyen par architecture et intensité ;
- erreurs silencieuses par niveau d'ambiguïté ;
- taux de revue d'A3 ;
- sensibilité à la dérive S04 ;
- décision selon le mélange d'identifiants S05 ;
- variabilité entre graines ;
- synthèse qualité–sécurité–adaptation.

Les visuels seront produits en PNG et copiés dans `images/robustness/R01/`.

## 13. Critères de validation du pilote

Le pilote est considéré comme techniquement valide si :

1. les 27 jeux de données sont reproductibles ;
2. les 108 exécutions reçoivent exactement les mêmes données pour une même
   combinaison scénario–intensité–graine ;
3. aucune architecture ne lit la vérité terrain pendant sa décision ;
4. les métriques peuvent être recalculées depuis les résultats bruts ;
5. les états avant et après adaptation ne sont pas mélangés ;
6. toutes les erreurs d'exécution sont conservées et comptabilisées ;
7. les résultats de test n'entraînent aucune modification des seuils.

## 14. Passage à la campagne complète

La campagne complète sera autorisée uniquement après validation du pilote. Elle
étendra alors :

- les graines à au moins dix réalisations ;
- les volumes à `100`, `1 000` et `10 000` ;
- le bruit aux niveaux N0, N1, N2 et N3 ;
- les intensités intermédiaires ;
- éventuellement S02 et S03 ;
- la calibration formelle des seuils A3.

## 15. Ordre d'implémentation

1. rendre les générateurs S01, S04 et S05 paramétrables ;
2. écrire les tests de déterminisme et d'isolation ;
3. générer uniquement la combinaison de calibration `seed=11` ;
4. inspecter et valider les données générées ;
5. implémenter le lanceur A0–A3 ;
6. exécuter une combinaison complète de bout en bout ;
7. valider les métriques brutes ;
8. exécuter les 108 combinaisons ;
9. agréger et visualiser ;
10. décider du passage à la campagne complète.

