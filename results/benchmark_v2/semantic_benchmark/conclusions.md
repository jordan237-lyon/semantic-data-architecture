# Conclusions du benchmark sémantique S01–S05

## Résultat principal

Aucune architecture ne domine sur toutes les dimensions. A0 et A2 atteignent une qualité finale parfaite lorsque les règles nécessaires sont fournies. Leur faiblesse apparaît lors des changements non anticipés : A2 accepte silencieusement une ancienne définition dans S04 et un identifiant mal nommé dans S05 avant adaptation.

A1 couvre correctement la découverte technique et peut signaler une dérive de distribution, mais ne résout pas les ambiguïtés métier. Dans S05, l'absence de contrôle sémantique conduit à 70 erreurs silencieuses.

A3 obtient le meilleur compromis de sécurité sans adaptation post-détection : il automatise S02 et S03, et dirige S01, S04 et S05 vers une revue lorsque la marge ou le contexte ne permettent pas une acceptation sûre. Sa contrepartie est une couverture automatique plus faible et la nécessité de maintenir le modèle et les politiques sémantiques.

## Limites d'interprétation

- Les scores consolidés combinent des tâches différentes ; ils servent à résumer, pas à remplacer les métriques détaillées.
- Les scénarios sont synthétiques et de taille limitée.
- Les déclarations et politiques spécifiques aux scénarios constituent elles-mêmes un coût de préparation, même lorsqu'aucune adaptation post-détection n'est comptée.
- Les temps d'exécution ne sont pas interprétables comme un benchmark de performance à cette échelle.
- Une campagne répétée sur plusieurs graines, volumes et niveaux de bruit est nécessaire avant toute généralisation.
