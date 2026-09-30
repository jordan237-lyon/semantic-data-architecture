# Application web — contrat fonctionnel v0.1

## Objectif

La version 0.1 fournit un laboratoire web local en lecture seule au-dessus du
moteur scientifique existant. Elle permet de choisir P00 ou S01–S05, de voir
les sources et de profiler leurs colonnes sans modifier les données, les
vérités terrain ou les résultats expérimentaux.

## Périmètre de la première itération

- catalogue P00 et S01–S05 ;
- inventaire des fichiers CSV ;
- nombre de lignes et de colonnes ;
- profilage des noms, types, formats, valeurs absentes et valeurs exemples ;
- API FastAPI en lecture seule ;
- écran Streamlit en lecture seule ;
- espaces de travail préparés mais non encore utilisés.

## Hors périmètre

- import de fichiers utilisateur ;
- écriture du modèle sémantique ;
- validation humaine persistante ;
- lancement du pipeline complet ;
- authentification, base de données et déploiement.

## Contrat de sécurité

Les services de la version 0.1 ne possèdent aucune opération de modification.
Ils lisent les scénarios existants et retournent des représentations
sérialisables. Le démarrage de FastAPI ou Streamlit nécessite une action
explicite distincte.

## Installation future

```bash
source myenv/bin/activate
pip install -r requirements-app.txt
```

Après validation de l'installation, les commandes de démarrage prévues seront :

```bash
uvicorn app.api.main:app --reload
streamlit run app/ui/dashboard.py
```

