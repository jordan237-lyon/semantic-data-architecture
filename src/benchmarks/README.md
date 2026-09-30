# Code des campagnes versionnées

- `benchmark_v1/campaign.py` référence les moteurs et expériences de V1 ;
- `benchmark_v2/campaign.py` référence A0–A3 et les expériences de V2 ;
- `comparison/build_comparison.py` construit uniquement les comparaisons
  scientifiquement compatibles.

Les moteurs partagés ne sont pas dupliqués : chaque campagne possède un registre
explicite qui indique exactement quels modules elle utilise. Cette organisation
évite que deux copies du même algorithme divergent silencieusement.
