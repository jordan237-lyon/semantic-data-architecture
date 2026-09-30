"""Narrative Streamlit interface for the semantic architecture demonstrator."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.scenarios import list_scenarios, list_sources, profile_scenario


SCENARIO_STORIES = {
    "P00": {
        "icon": "🏠", "eyebrow": "SITUATION DE DÉPART",
        "question": "Comment reconnaître un même client dans trois systèmes ?",
        "story": "Le CRM, le support et la finance parlent des mêmes personnes avec des identifiants, des formats et des niveaux de détail différents.",
        "risk": "Créer des doublons ou rapprocher de mauvaises personnes.",
        "goal": "Construire une vue client unifiée et mesurable.",
    },
    "S01": {
        "icon": "🏷️", "eyebrow": "AMBIGUÏTÉ DE VOCABULAIRE",
        "question": "Un même mot peut-il avoir deux sens ?",
        "story": "La colonne status décrit l'état d'un client dans le CRM, mais l'état d'un ticket dans le support.",
        "risk": "Fusionner deux concepts métiers qui n'ont rien d'équivalent.",
        "goal": "Séparer le statut du client du statut du ticket.",
    },
    "S02": {
        "icon": "🔗", "eyebrow": "ÉQUIVALENCE SÉMANTIQUE",
        "question": "Deux noms différents peuvent-ils désigner la même chose ?",
        "story": "gross_amount et turnover_value sont deux noms pour le montant brut d'une transaction.",
        "risk": "Ignorer une correspondance correcte à cause du vocabulaire.",
        "goal": "Retrouver l'équivalence sans confondre transaction et revenu client.",
    },
    "S03": {
        "icon": "⚖️", "eyebrow": "DÉFINITIONS CONCURRENTES",
        "question": "Revenu brut et revenu net sont-ils interchangeables ?",
        "story": "Les deux mesures sont proches et fortement corrélées, mais les taxes et remboursements changent leur sens.",
        "risk": "Comparer ou additionner des mesures comptables incompatibles.",
        "goal": "Conserver les deux définitions et leur granularité client-mois.",
    },
    "S04": {
        "icon": "🕰️", "eyebrow": "DÉRIVE DANS LE TEMPS",
        "question": "Que se passe-t-il quand une colonne change de sens ?",
        "story": "Avant juillet 2025, active signifie une connexion récente. Ensuite, le mot désigne un contrat payant en cours.",
        "risk": "Continuer silencieusement à appliquer l'ancienne définition.",
        "goal": "Détecter la rupture et demander une validation.",
    },
    "S05": {
        "icon": "🧩", "eyebrow": "NOM TROMPEUR",
        "question": "Peut-on faire confiance au nom customer_id ?",
        "story": "La colonne contient 70 % d'identifiants de tickets et seulement 30 % d'identifiants clients.",
        "risk": "Accepter 70 erreurs parce que le nom de colonne semble évident.",
        "goal": "Croiser le nom avec les valeurs et orienter le cas vers une revue.",
    },
}

FRENCH_COLUMNS = {
    "source": "Source", "column": "Colonne", "inferred_type": "Type détecté",
    "detected_format": "Format reconnu", "row_count": "Lignes",
    "non_null_count": "Valeurs présentes", "null_ratio": "Valeurs manquantes",
    "unique_ratio": "Valeurs distinctes", "sample_values": "Exemples",
    "name": "Source", "path": "Emplacement", "column_count": "Colonnes",
}


def inject_theme():
    st.markdown(
        """
        <style>
        :root { --ink:#172033; --muted:#64748b; --brand:#5b4cf0; --brand-soft:#eeecff;
        --green-soft:#e9f8ef; --orange-soft:#fff3df; --red-soft:#ffebeb; --line:#e3e8f2; }
        .stApp { background:radial-gradient(circle at 88% 4%,rgba(91,76,240,.10),transparent 25rem),
        linear-gradient(180deg,#fbfcff 0%,#f7f9fe 100%); color:var(--ink); }
        [data-testid="stSidebar"] { background:linear-gradient(180deg,#17142f 0%,#24204b 100%); }
        [data-testid="stSidebar"] * { color:#f8f7ff; }
        [data-testid="stSidebar"] hr { border-color:rgba(255,255,255,.14); }
        [data-testid="stSidebar"] [data-baseweb="radio"] label { padding:.55rem .65rem; border-radius:.65rem; }
        .block-container { max-width:1180px; padding-top:2.2rem; padding-bottom:4rem; }
        h1,h2,h3 { letter-spacing:-.025em; color:var(--ink); }
        .hero { padding:2.35rem 2.5rem; border-radius:1.4rem;
        background:linear-gradient(125deg,#211b52 0%,#5b4cf0 68%,#776af7 100%); color:white;
        box-shadow:0 18px 45px rgba(48,39,135,.18); margin-bottom:1.5rem; }
        .hero .eyebrow { font-size:.78rem; letter-spacing:.14em; font-weight:700; opacity:.75; }
        .hero h1 { color:white; font-size:2.55rem; line-height:1.08; margin:.45rem 0 .8rem; }
        .hero p { font-size:1.08rem; max-width:760px; opacity:.9; margin:0; }
        .section-kicker { color:var(--brand); font-weight:700; letter-spacing:.1em; font-size:.76rem; }
        .story-card,.info-card,.step-card { height:100%; padding:1.15rem 1.2rem; border:1px solid var(--line);
        border-radius:1rem; background:rgba(255,255,255,.88); box-shadow:0 8px 24px rgba(31,41,90,.06); }
        .story-card h3,.info-card h3,.step-card h3 { margin:.25rem 0 .5rem; font-size:1.05rem; }
        .story-card p,.info-card p,.step-card p { color:var(--muted); margin:0; line-height:1.5; }
        .step-number { display:inline-flex; align-items:center; justify-content:center; width:2rem; height:2rem;
        border-radius:.65rem; color:white; background:var(--brand); font-weight:700; }
        .scenario-banner { padding:1.6rem 1.8rem; border-radius:1.15rem;
        background:linear-gradient(135deg,#fff 0%,var(--brand-soft) 100%); border:1px solid #dedafd; margin-bottom:1rem; }
        .scenario-banner .icon { font-size:2rem; } .scenario-banner h2 { margin:.35rem 0; }
        .scenario-banner p { color:var(--muted); font-size:1.02rem; }
        .explain-box { padding:1rem 1.1rem; border-radius:.85rem; height:100%; }
        .risk { background:var(--red-soft); } .goal { background:var(--green-soft); }
        .explain-box strong { display:block; margin-bottom:.35rem; }
        div[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:.9rem;
        padding:.9rem 1rem; box-shadow:0 5px 16px rgba(31,41,90,.045); }
        div[data-testid="stExpander"] { background:rgba(255,255,255,.8); border:1px solid var(--line); border-radius:.85rem; }
        .status-row { display:flex; gap:.8rem; flex-wrap:wrap; margin:.8rem 0 1.2rem; }
        .status-pill { padding:.42rem .75rem; border-radius:99px; font-size:.86rem; font-weight:650; }
        .accepted { background:var(--green-soft); color:#17603a; }
        .review { background:var(--orange-soft); color:#8a4b00; }
        .rejected { background:var(--red-soft); color:#9b2525; }
        .footer-note { color:var(--muted); text-align:center; padding-top:2.5rem; font-size:.85rem; }
        </style>
        """, unsafe_allow_html=True,
    )


def card(title, text, icon="✦", class_name="info-card"):
    st.markdown(
        f'<div class="{class_name}"><div style="font-size:1.4rem">{icon}</div>'
        f'<h3>{title}</h3><p>{text}</p></div>', unsafe_allow_html=True,
    )


def render_home():
    st.markdown(
        """<div class="hero"><div class="eyebrow">LABORATOIRE DE RECHERCHE · ARCHITECTURE SÉMANTIQUE</div>
        <h1>Vos données parlent-elles vraiment le même langage&nbsp;?</h1>
        <p>Découvrez comment plusieurs systèmes peuvent décrire la même réalité avec des noms,
        formats et définitions différents — et comment une couche sémantique aide à les réunir.</p></div>""",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-kicker">LE PARCOURS</div>', unsafe_allow_html=True)
    st.subheader("De sources isolées à une vision commune")
    steps = [("1","Choisir","Sélectionner une situation expérimentale concrète."),
             ("2","Explorer","Observer ce que contiennent réellement les sources."),
             ("3","Comprendre","Voir pourquoi deux colonnes correspondent — ou non."),
             ("4","Comparer","Mesurer qualité, sécurité et effort d'adaptation.")]
    for column, (number, title, text) in zip(st.columns(4), steps):
        with column:
            st.markdown(f'<div class="step-card"><span class="step-number">{number}</span>'
                        f'<h3>{title}</h3><p>{text}</p></div>', unsafe_allow_html=True)
    st.markdown('<br><div class="section-kicker">LES EXPÉRIENCES</div>', unsafe_allow_html=True)
    st.subheader("Six histoires pour tester le sens des données")
    scenarios = list_scenarios()
    for start in range(0, len(scenarios), 3):
        for column, scenario in zip(st.columns(3), scenarios[start:start + 3]):
            story = SCENARIO_STORIES[scenario.identifier]
            with column:
                card(f"{story['icon']} {scenario.identifier} — {scenario.title}", story["question"], "", "story-card")
    st.markdown('<br><div class="section-kicker">QUATRE NIVEAUX D’ARCHITECTURE</div>', unsafe_allow_html=True)
    st.subheader("De la règle manuelle à l’adaptation sémantique")
    architectures = [("A0","Manuel","Les règles sont écrites à l'avance."),
                     ("A1","Technique","Les formats et distributions sont détectés."),
                     ("A2","Déclaratif","Les mappings métier sont décrits en YAML."),
                     ("A3","Adaptatif","Les candidats sont classés avec un score de confiance.")]
    for column, (code, title, text) in zip(st.columns(4), architectures):
        with column: card(f"{code} · {title}", text, "◈")


def scenario_selector():
    return st.selectbox("Expérience à explorer", list_scenarios(),
                        format_func=lambda item: f"{item.identifier} — {item.title}")


def render_scenario_intro(selected):
    story = SCENARIO_STORIES[selected.identifier]
    st.markdown(f"""<div class="scenario-banner"><div class="section-kicker">{story['eyebrow']}</div>
        <div class="icon">{story['icon']}</div><h2>{selected.identifier} — {selected.title}</h2>
        <p><strong>{story['question']}</strong><br>{story['story']}</p></div>""", unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.markdown(f'<div class="explain-box risk"><strong>⚠️ Risque métier</strong>{story["risk"]}</div>', unsafe_allow_html=True)
    with right:
        st.markdown(f'<div class="explain-box goal"><strong>✓ Résultat recherché</strong>{story["goal"]}</div>', unsafe_allow_html=True)


def render_explorer():
    selected = scenario_selector()
    render_scenario_intro(selected)
    sources = list_sources(selected.identifier)
    metric_columns = st.columns(3)
    metric_columns[0].metric("Sources observées", len(sources))
    metric_columns[1].metric("Lignes disponibles", f"{sum(x.row_count for x in sources):,}".replace(",", " "))
    metric_columns[2].metric("Colonnes à comprendre", sum(x.column_count for x in sources))
    st.markdown('<br><div class="section-kicker">CONTENU DES SOURCES</div>', unsafe_allow_html=True)
    st.subheader("Ce que chaque système apporte")
    for tab, source in zip(st.tabs([x.name.upper() for x in sources]), sources):
        with tab:
            st.write(f"**{source.name.capitalize()}** contient **{source.row_count} lignes** et **{source.column_count} colonnes**.")
            st.dataframe(pd.read_csv(source.path, nrows=5), width="stretch", hide_index=True)
    with st.expander("Afficher l’inventaire technique des fichiers"):
        st.dataframe(pd.DataFrame([x.public_dict() for x in sources]).rename(columns=FRENCH_COLUMNS), width="stretch", hide_index=True)
    st.markdown('<br><div class="section-kicker">ANALYSE DES COLONNES</div>', unsafe_allow_html=True)
    st.subheader("Faire parler la structure des données")
    st.write("Le profilage observe les types, formats et valeurs sans utiliser la vérité terrain. Il précède toute interprétation métier.")
    if st.button("Analyser les colonnes", type="primary"):
        profiles = pd.DataFrame(profile_scenario(selected.identifier))
        profiles["null_ratio"] = (profiles["null_ratio"] * 100).map(lambda value: f"{value:.1f} %")
        profiles["unique_ratio"] = (profiles["unique_ratio"] * 100).map(lambda value: f"{value:.1f} %")
        profiles["detected_format"] = profiles["detected_format"].fillna("Non reconnu")
        profiles["sample_values"] = profiles["sample_values"].map(lambda values: " · ".join(map(str, values[:3])))
        profiles = profiles.rename(columns=FRENCH_COLUMNS)
        visible = ["Source","Colonne","Type détecté","Format reconnu","Valeurs manquantes","Valeurs distinctes","Exemples"]
        st.success(f"Analyse terminée : {len(profiles)} colonnes observées.")
        st.dataframe(profiles[visible], width="stretch", hide_index=True)
        with st.expander("Comment lire ces indicateurs ?"):
            st.markdown("""- **Type détecté** : texte, nombre, date ou booléen.
- **Format reconnu** : structure comme un e-mail, une date ou un code pays.
- **Valeurs manquantes** : part des lignes sans information.
- **Valeurs distinctes** : indice pour reconnaître clés et catégories.""")


def render_understand():
    st.markdown("""<div class="hero"><div class="eyebrow">COMPRENDRE LES DÉCISIONS</div>
    <h1>Un mapping n’est pas qu’une ressemblance de noms.</h1>
    <p>A3 confronte plusieurs indices avant de proposer, accepter ou suspendre une correspondance.</p></div>""", unsafe_allow_html=True)
    explanations = [("① Le nom","Les mots et synonymes sont comparés. Un nom proche est un indice, jamais une preuve."),
                    ("② Le type","Un nombre, une date ou un identifiant doit rester compatible avec l'attribut métier."),
                    ("③ Les valeurs","Formats, unicité et distributions peuvent confirmer ou contredire le nom.")]
    for column, (title, text) in zip(st.columns(3), explanations):
        with column: card(title, text, "")
    st.markdown("""<div class="status-row"><span class="status-pill accepted">✓ Accepté — score et marge suffisants</span>
    <span class="status-pill review">◷ À revoir — doute ou concurrence</span>
    <span class="status-pill rejected">× Rejeté — preuves insuffisantes</span></div>""", unsafe_allow_html=True)
    st.info("La prochaine itération affichera ici les candidats réels, la contribution des scores et la justification de chaque décision.")


def render_compare():
    st.markdown("""<div class="hero"><div class="eyebrow">RÉSULTATS DE LA RECHERCHE</div>
    <h1>Comparer la qualité ne suffit pas.</h1><p>Une architecture utile doit aussi limiter les erreurs silencieuses et rester adaptable.</p></div>""", unsafe_allow_html=True)
    summary_path = ROOT / "results/benchmark_v2/semantic_benchmark/architecture_summary.csv"
    dashboard_path = ROOT / "images/benchmark_v2/semantic_benchmark/semantic_benchmark_dashboard.png"
    if summary_path.exists():
        summary = pd.read_csv(summary_path)
        summary.insert(1, "Approche", summary["architecture"].map({"A0":"Manuel","A1":"Technique","A2":"Déclaratif","A3":"Adaptatif"}))
        summary = summary.rename(columns={"architecture":"Niveau","initial_mean_outcome":"Score initial",
            "final_mean_outcome":"Score final","initial_safe_scenarios":"Scénarios sûrs au départ",
            "final_safe_scenarios":"Scénarios sûrs à la fin","initial_human_reviews":"Revues humaines",
            "silent_wrong_acceptances":"Erreurs silencieuses","post_detection_adaptation_actions":"Adaptations nécessaires"})
        st.dataframe(summary, width="stretch", hide_index=True)
    if dashboard_path.exists(): st.image(str(dashboard_path), caption="Synthèse des scénarios S01 à S05", width="stretch")
    st.warning("Ces résultats proviennent de données synthétiques. Ils démontrent le prototype sans permettre encore une généralisation.")


st.set_page_config(page_title="Semantic Data Architecture", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
inject_theme()
with st.sidebar:
    st.markdown("## ◈ Semantic Lab")
    st.caption("Comprendre, relier, unifier")
    st.divider()
    page = st.radio("Navigation", ["Accueil","Explorer un scénario","Comprendre les mappings","Comparer les résultats"], label_visibility="collapsed")
    st.divider()
    st.caption("Prototype de recherche · v0.1")

if page == "Accueil": render_home()
elif page == "Explorer un scénario": render_explorer()
elif page == "Comprendre les mappings": render_understand()
else: render_compare()

st.markdown('<div class="footer-note">Semantic Data Architecture · Laboratoire expérimental local</div>', unsafe_allow_html=True)
