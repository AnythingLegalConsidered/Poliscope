"""Static keyword dictionary for thematic tagging of parliamentary interventions."""

# Maps tag slug -> list of keywords (case-insensitive matching)
TAGS_DICTIONARY: dict[str, list[str]] = {
    "economie": [
        "budget", "impot", "fiscal", "dette", "economie", "finance",
        "emploi", "chomage", "entreprise", "croissance", "inflation",
    ],
    "securite": [
        "securite", "police", "gendarmerie", "terrorisme", "defense",
        "armee", "militaire", "delinquance", "criminalite",
    ],
    "sante": [
        "sante", "hopital", "medecin", "medicament", "epidemie",
        "vaccination", "soignant", "maladie", "assurance maladie",
    ],
    "education": [
        "education", "ecole", "enseignant", "universite", "etudiant",
        "formation", "pedagogie", "baccalaureat",
    ],
    "environnement": [
        "environnement", "ecologie", "climat", "energie", "renouvelable",
        "pollution", "biodiversite", "carbone",
    ],
    "justice": [
        "justice", "tribunal", "magistrat", "penal", "prison",
        "juridique", "loi", "droit",
    ],
    "immigration": [
        "immigration", "migrant", "asile", "frontiere", "naturalisation",
        "etranger",
    ],
    "logement": [
        "logement", "immobilier", "loyer", "hlm", "hebergement",
        "urbanisme", "construction",
    ],
    "transport": [
        "transport", "sncf", "route", "autoroute", "ferroviaire",
        "aerien", "mobilite",
    ],
    "agriculture": [
        "agriculture", "agricole", "paysan", "elevage", "pac",
        "alimentation", "pesticide",
    ],
    "numerique": [
        "numerique", "internet", "donnees", "cybersecurite",
        "intelligence artificielle", "telecoms", "fibre",
    ],
    "culture": [
        "culture", "patrimoine", "musee", "spectacle", "audiovisuel",
        "artiste", "cinema",
    ],
}

# Maps tag slug -> human-readable display name
TAGS_DISPLAY_NAMES: dict[str, str] = {
    "economie": "Économie",
    "securite": "Sécurité",
    "sante": "Santé",
    "education": "Éducation",
    "environnement": "Environnement",
    "justice": "Justice",
    "immigration": "Immigration",
    "logement": "Logement",
    "transport": "Transport",
    "agriculture": "Agriculture",
    "numerique": "Numérique",
    "culture": "Culture",
}


def tag_content(content: str) -> list[str]:
    """Return tag slugs whose keywords appear in *content* (case-insensitive)."""
    lower = content.lower()
    return [
        slug
        for slug, keywords in TAGS_DICTIONARY.items()
        if any(kw in lower for kw in keywords)
    ]
