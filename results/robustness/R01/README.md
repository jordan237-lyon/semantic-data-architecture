# Résultats R01

Ce dossier contient la campagne pilote complète R01. Les résultats des
campagnes précédentes restent dans leurs dossiers versionnés.

## État de la campagne

- 27 jeux de données ;
- 108 exécutions terminées ;
- 0 échec ;
- 36 exécutions de calibration (`seed-11`) ;
- 72 exécutions de test (`seed-22` et `seed-33`).

## Fichiers principaux

- `raw_runs.csv` : une ligne par exécution architecture–dataset ;
- `scenario_summary.csv` : statistiques par scénario, intensité et architecture ;
- `architecture_summary.csv` : synthèse globale des graines de test ;
- `confidence_intervals.json` : intervalles diagnostiques à 95 % ;
- `campaign_summary.json` : contrôle du nombre d'exécutions ;
- `runs/` : résultat JSON isolé de chacune des 108 exécutions ;
- `conclusions.md` : interprétation et limites ;
- `plots/full_campaign/` : graphiques PNG de synthèse.

Les agrégats scientifiques excluent la graine de calibration 11.
