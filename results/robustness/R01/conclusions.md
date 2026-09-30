# R01 — Conclusions de la campagne pilote complète

## Exécution

- 27 jeux de données contrôlés ;
- 108 exécutions A0–A3 ;
- 36 exécutions de calibration sur la graine 11 ;
- 72 exécutions de test sur les graines 22 et 33 ;
- aucune erreur d'exécution.

Les statistiques ci-dessous sont calculées uniquement sur les graines de test.

## Résultats globaux

| Architecture | Score initial moyen | Score final moyen | Sécurité initiale | Erreurs silencieuses initiales | Erreurs silencieuses finales | Revues | Adaptations |
|---|---:|---:|---:|---:|---:|---:|---:|
| A0 | 1,000 | 1,000 | 100,0 % | 0 | 0 | 0 | 12 |
| A1 | 0,389 | 0,389 | 55,6 % | 302 | 302 | 16 | 0 |
| A2 | 0,500 | 1,000 | 33,3 % | 306 | 0 | 0 | 24 |
| A3 | 0,778 | 0,778 | 100,0 % | 0 | 0 | 20 | 0 |

## Lecture scientifique

- **A0** reste exact et sûr parce que les règles sont connues à l'avance. Son
  coût est déplacé vers 42 actions de configuration et 12 actions comptées lors
  des traitements temporels.
- **A1** détecte la dérive S04 à partir de I1 mais ne résout ni les définitions
  métier de S01 ni le conflit d'identifiants S05. Les erreurs silencieuses sont
  dominées par S05.
- **A2** atteint un score final de 1,00 après adaptation. Son état initial est
  cependant le moins sûr : il réutilise des déclarations devenues invalides.
- **A3** ne produit aucune acceptation silencieusement incorrecte. Cette sûreté
  est obtenue au prix de 20 revues et d'une couverture automatique plus faible.

## Effet de l'intensité

- S01 : A3 accepte le cas sans chevauchement I0 et place I1–I2 en revue.
- S04 : A1 ne détecte pas la variation de 5 points en I0 avec un seuil de 10 %,
  mais détecte I1 et I2. A3 utilise la rupture de définition et reste sûr.
- S05 : le score initial d'A1 et d'A2 suit la proportion d'identifiants clients
  (`0,90`, `0,50`, `0,10`). A2 restaure ensuite `1,00`, tandis qu'A3 demande une
  revue pour les trois mélanges.

## Variabilité et limites

Les métriques contrôlées présentent un écart-type nul entre les graines 22 et
33, car les générateurs imposent exactement les proportions et les décisions
évaluées ne dépendent pas des attributs bruités. Cela valide la reproductibilité
technique mais ne démontre pas encore une robustesse statistique réaliste.

Les intervalles de confiance à 95 % sont fournis pour tester la chaîne de calcul,
mais deux graines de test sont insuffisantes pour une interprétation forte. Une
campagne ultérieure devra augmenter le nombre de graines et faire varier le
bruit sur les colonnes effectivement utilisées par les décisions.
