# Comparaison Benchmark V1 / Benchmark V2

## Résultat directement comparable

Sur le cas nominal P00, toutes les approches mesurées produisent la même qualité
de matching d'entités : précision `1,000`, rappel `0,958015` et F1 `0,978558`.
V2 ne démontre donc pas une amélioration de la qualité nominale.

## Ce que V2 ajoute

| Élément | Benchmark V1 | Benchmark V2 |
|---|---:|---:|
| Architectures distinguées | 2 | 4 |
| Scénarios structurels P00–P05 | 6 | 6 |
| Scénarios sémantiques S01–S05 | 0 | 5 |
| Ambiguïtés métier mesurées | Non | Oui |
| Erreurs silencieuses mesurées | Partiellement | Explicitement |
| Décisions de revue humaine | Cas ponctuels | Mesure systématique |

Sur S01–S05, qui n'existent que dans V2 :

| Architecture | Résultat initial moyen | Résultat final moyen | Scénarios initialement sûrs | Erreurs initiales silencieuses | Revues humaines |
|---|---:|---:|---:|---:|---:|
| A0 | 1,00 | 1,00 | 5/5 | 0 | 0 |
| A1 | 0,26 | 0,26 | 4/5 | 70 | 7 |
| A2 | 0,66 | 1,00 | 3/5 | 71 | 0 |
| A3 | 0,80 | 0,80 | 5/5 | 0 | 4 |

Le résultat A3 plus faible ne signifie pas nécessairement un échec : une revue
sûre peut recevoir un score inférieur à une acceptation automatique tout en
empêchant une erreur silencieuse.

## Limite de comparaison

Le F1 d'entités de V1 et le score normalisé des scénarios sémantiques de V2 ne
mesurent pas le même objet. Ils sont donc présentés séparément et ne doivent pas
être soustraits ou agrégés.
