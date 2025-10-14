# Configuration et constantes

try:
    import dataiku
except Exception:
    import dataiku_stub as dataiku

# Données de configuration
STREAMS = {
    "Résultats globaux des ventes": [
        "Récolte des résultats par sites",
        "Unification des Résultats"
    ],
    "Qualité des données RH": [
        "Contrôles contrats",
        "Gestion des absences"
    ]
}

# Mapping des datasets par contexte (stream, projet, dq_point)
DATASET_MAPPING = {
    ("Résultats globaux des ventes", "Récolte des résultats par sites", "Extraction"): ["ventes_par_site", "produits_vendus"],
    ("Résultats globaux des ventes", "Récolte des résultats par sites", "Transformation"): ["ventes_par_site", "produits_vendus"],
    ("Résultats globaux des ventes", "Récolte des résultats par sites", "Chargement"): ["resultats_consolides"],
    ("Résultats globaux des ventes", "Unification des Résultats", "Extraction"): ["resultats_consolides"],
    ("Résultats globaux des ventes", "Unification des Résultats", "Transformation"): ["resultats_consolides"],
    ("Résultats globaux des ventes", "Unification des Résultats", "Chargement"): ["resultats_consolides"],
    ("Qualité des données RH", "Contrôles contrats", "Extraction"): ["contrats_employes"],
    ("Qualité des données RH", "Contrôles contrats", "Transformation"): ["contrats_employes"],
    ("Qualité des données RH", "Contrôles contrats", "Chargement"): ["contrats_employes"],
    ("Qualité des données RH", "Gestion des absences", "Extraction"): ["absences_employes", "contrats_employes"],
    ("Qualité des données RH", "Gestion des absences", "Transformation"): ["absences_employes"],
    ("Qualité des données RH", "Gestion des absences", "Chargement"): ["absences_employes"],
}

# Client Dataiku
client = dataiku.api_client()
project = client.get_default_project()
