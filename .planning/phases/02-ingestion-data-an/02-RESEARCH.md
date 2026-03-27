# Phase 2: Ingestion des donnees AN - Research

**Researched:** 2026-03-27
**Domain:** French National Assembly open data APIs, Python data ingestion, PostgreSQL
**Confidence:** MEDIUM (APIs verified but XML schema details require runtime validation)

## Summary

L'ingestion des donnees de l'Assemblee Nationale repose sur **deux sources complementaires** :

1. **data.assemblee-nationale.fr** -- source officielle, fournit les deputes (JSON/XML zips) et les comptes rendus de seance (XML brut "Syseron" en zip). Pas de vraie REST API : ce sont des fichiers statiques telechargeables. Les comptes rendus sont un seul gros zip XML (~10MB+) contenant toutes les seances de la legislature.

2. **nosdeputes.fr** (Regards Citoyens) -- API REST riche avec JSON/XML/CSV. Fournit deputes, seances, interventions avec des endpoints clairs et paginables. C'est la **source recommandee** pour les interventions car elle structure deja les donnees en seances/interventions avec des IDs stables.

**Strategie recommandee :** Utiliser nosdeputes.fr comme source principale (API REST, donnees structurees, photos), et data.assemblee-nationale.fr en fallback/complement pour les donnees manquantes. Les scripts Python se connectent directement a la meme base PostgreSQL que l'app Nuxt via `DATABASE_URL`.

**Primary recommendation:** Utiliser l'API nosdeputes.fr en JSON pour les deputes et interventions, psycopg (v3) pour la DB, et un dictionnaire de mots-cles statique pour le tagging thematique.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| psycopg | 3.x (psycopg[binary]) | PostgreSQL adapter | Moderne, context managers, parameterized queries, remplace psycopg2 |
| httpx | 0.27+ | HTTP client | Async-ready, timeout config, retry-friendly, meilleur que requests |
| python-dotenv | 1.x | Env vars (.env) | Lit le meme .env que Nuxt |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lxml | 5.x | XML parsing | Si parsing du syseron.xml.zip d'AN officiel |
| slugify (python-slugify) | 8.x | Slug generation | Pour generer les slugs des tags |
| tqdm | 4.x | Progress bars | Feedback visuel pendant l'ingestion |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | requests plus simple mais pas async, moins configurable pour timeouts/retries |
| psycopg 3 | psycopg2 | psycopg2 plus repandu mais en maintenance-only, pas de nouvelles features |
| lxml | xml.etree.ElementTree | ElementTree inclus dans stdlib mais moins performant pour gros XML |

**Installation:**
```bash
pip install psycopg[binary] httpx python-dotenv python-slugify tqdm lxml
```

**requirements.txt:**
```
psycopg[binary]>=3.1
httpx>=0.27
python-dotenv>=1.0
python-slugify>=8.0
tqdm>=4.60
lxml>=5.0
```

## Data Sources Analysis

### Source 1: nosdeputes.fr API (RECOMMENDED - Primary)

**Confidence: HIGH** (endpoints verified, JSON structure confirmed)

#### Deputies
- **URL:** `https://www.nosdeputes.fr/deputes/json`
- **Format:** JSON array of deputy objects
- **Key fields:** `id`, `nom`, `nom_de_famille`, `prenom`, `sexe`, `slug`, `groupe_sigle`, `num_deptmt`, `nom_circo`, `num_circo`, `id_an`, `url_an`, `mandat_debut`, `mandat_fin`, `profession`, `twitter`, `sites_web`, `emails`
- **Photo URL:** `https://www.nosdeputes.fr/depute/photo/{slug}/120` (hauteur configurable)
- **Note:** Au 2026-03-27, `/deputes/enmandat/json` retourne un tableau vide (probablement lié a la transition de legislature). Utiliser `/deputes/json` qui liste tous les deputes de la legislature courante.

#### Seances (sessions)
- **URL pattern:** Acces en 2 etapes :
  1. Rechercher les seances : `https://www.nosdeputes.fr/seances/json`
  2. Interventions d'une seance : `https://www.nosdeputes.fr/seance/{id}/json`
- **Pagination:** `?page=N`, 50 resultats par defaut, max 500
- **Filtres:** `?commission=1` ou `?hemicycle=1`

#### Interventions
- **Acces via seance:** `https://www.nosdeputes.fr/seance/{id}/json`
- **Recherche:** `https://www.nosdeputes.fr/recherche/{query}?format=json&object_name=Intervention`
- **Filtre par date:** `&date=20250101,20250131`

#### Limites connues
- Pas de rate limit documente (utiliser 1-2 req/sec par politesse)
- La legislature courante (17e, depuis juillet 2024) peut avoir des donnees incompletes
- Les seances anciennes redirigent vers des sous-domaines (ex: `2017-2022.nosdeputes.fr`)

### Source 2: data.assemblee-nationale.fr (Complement/Fallback)

**Confidence: MEDIUM** (URLs verifiees, structure XML non documentee en detail)

#### Deputies (JSON zip)
- **URL:** `https://data.assemblee-nationale.fr/static/openData/repository/17/amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip`
- **CSV simple:** `https://data.assemblee-nationale.fr/static/openData/repository/17/amo/deputes_actifs_csv_opendata/liste_deputes_libre_office.csv`
- **Format:** ZIP contenant du JSON/XML, fichiers conçus pour chargement DB en un seul pass
- **Mise a jour:** Quotidienne

#### Debats (XML Syseron)
- **URL:** `https://data.assemblee-nationale.fr/static/openData/repository/17/vp/syceronbrut/syseron.xml.zip`
- **Format:** ZIP contenant XML (format SyceronBrut)
- **Taille:** > 10MB, contient TOUTES les seances de la legislature
- **Structure XML connue (tags):** `CompteRendu`, `dateSeance`/`DateSeance`, probablement `intervention`, `orateur`
- **Mise a jour:** Quotidienne (MD5 change daily)

#### Debats via DILA (data.gouv.fr)
- **URL:** `https://echanges.dila.gouv.fr/OPENDATA/Debats/AN/`
- **Format:** Fichiers `.taz` (tar.gz) par seance, nommes `AN_YYYYNNN.taz`
- **Schema XSD:** Disponible dans `Schema-documentation/schemas-debats-V2.0.zip`
- **Volume 2025:** ~142 fichiers, de 30KB a 3.7MB chacun
- **Mise a jour:** Hebdomadaire (mais parfois en retard)

### Photos des deputes
| Source | URL Pattern | Qualite |
|--------|-------------|---------|
| nosdeputes.fr | `https://www.nosdeputes.fr/depute/photo/{slug}/{height}` | Bonne, hauteur configurable |
| AN officielle | `https://www.assemblee-nationale.fr/dyn/deputes/{id_an}` (page profil) | Officielle mais pas d'URL directe d'image |

**Recommandation:** Utiliser nosdeputes.fr pour les photos, URL directe et configurable.

## Architecture Patterns

### Recommended Project Structure
```
scripts/
├── requirements.txt          # Dependencies Python
├── .env                      # Symlink ou copie du .env racine
├── config.py                 # DB URL, API base URLs, constants
├── db.py                     # Connection pool psycopg, helpers upsert
├── ingest_deputies.py        # Script: import des deputes
├── ingest_debates.py         # Script: import seances + interventions
├── tag_interventions.py      # Script: tagging thematique
├── run_all.py                # Orchestrateur: execute tout dans l'ordre
├── tags_dictionary.py        # Dictionnaire mots-cles -> tags
└── utils.py                  # Helpers: slugify, rate limiting, logging
```

### Pattern 1: Incremental Ingestion via officialId/unique constraint
**What:** Chaque record a un `official_id` unique. Avant insert, verifier existence. Utiliser `INSERT ... ON CONFLICT (official_id) DO UPDATE` (upsert).
**When to use:** Toujours -- c'est le pattern de base pour l'ingestion incrementale.
**Example:**
```python
# Upsert pattern with psycopg 3
def upsert_deputy(conn, deputy_data):
    conn.execute("""
        INSERT INTO deputies (official_id, first_name, last_name, full_name,
                              political_group, photo_url, constituency, is_active)
        VALUES (%(official_id)s, %(first_name)s, %(last_name)s, %(full_name)s,
                %(political_group)s, %(photo_url)s, %(constituency)s, %(is_active)s)
        ON CONFLICT (official_id) DO UPDATE SET
            political_group = EXCLUDED.political_group,
            photo_url = EXCLUDED.photo_url,
            is_active = EXCLUDED.is_active,
            updated_at = NOW()
    """, deputy_data)
```

### Pattern 2: DB Connection from shared .env
**What:** Lire DATABASE_URL depuis le meme .env que Nuxt.
**Example:**
```python
import os
from dotenv import load_dotenv
import psycopg

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DATABASE_URL = os.getenv('DATABASE_URL')

def get_connection():
    return psycopg.connect(DATABASE_URL)

# Context manager usage
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM deputies")
        print(cur.fetchone())
```

### Pattern 3: Paginated API Fetch
**What:** Parcourir les pages d'une API avec backoff.
**Example:**
```python
import httpx
import time

BASE_URL = "https://www.nosdeputes.fr"

def fetch_all_pages(path, params=None):
    """Fetch all pages from nosdeputes.fr API."""
    all_results = []
    page = 1
    while True:
        url = f"{BASE_URL}/{path}/json"
        p = {**(params or {}), "page": page}
        resp = httpx.get(url, params=p, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if not data or (isinstance(data, dict) and not any(data.values())):
            break

        all_results.append(data)
        page += 1
        time.sleep(1)  # Rate limiting par politesse

    return all_results
```

### Pattern 4: Keyword-Based Tagging
**What:** Dictionnaire statique de mots-cles mappes a des tags thematiques. Pas de NLP lourd.
**When to use:** Pour le tagging initial. Evolutif vers du NLP plus tard si besoin.
**Example:**
```python
TAGS_DICTIONARY = {
    "economie": ["budget", "impot", "fiscal", "dette", "economie", "finance",
                  "emploi", "chomage", "entreprise", "croissance", "inflation"],
    "securite": ["securite", "police", "gendarmerie", "terrorisme", "defense",
                 "armee", "militaire", "delinquance", "criminalite"],
    "sante": ["sante", "hopital", "medecin", "medicament", "epidemie",
              "vaccination", "soignant", "maladie", "assurance maladie"],
    "education": ["education", "ecole", "enseignant", "universite", "etudiant",
                  "formation", "pedagogie", "baccalaureat"],
    "environnement": ["environnement", "ecologie", "climat", "energie",
                      "renouvelable", "pollution", "biodiversite", "carbone"],
    "justice": ["justice", "tribunal", "magistrat", "penal", "prison",
                "juridique", "loi", "droit"],
    "immigration": ["immigration", "migrant", "asile", "frontiere",
                    "naturalisation", "etranger"],
    "logement": ["logement", "immobilier", "loyer", "hlm", "hebergement",
                 "urbanisme", "construction"],
    "transport": ["transport", "sncf", "route", "autoroute", "ferroviaire",
                  "aerien", "mobilite"],
    "agriculture": ["agriculture", "agricole", "paysan", "elevage",
                    "pac", "alimentation", "pesticide"],
    "numerique": ["numerique", "internet", "donnees", "cybersecurite",
                  "intelligence artificielle", "telecoms", "fibre"],
    "culture": ["culture", "patrimoine", "musee", "spectacle", "audiovisuel",
                "artiste", "cinema"],
}

def tag_intervention(content: str) -> list[str]:
    """Return list of tag slugs matching the content."""
    content_lower = content.lower()
    matched_tags = []
    for tag_slug, keywords in TAGS_DICTIONARY.items():
        if any(kw in content_lower for kw in keywords):
            matched_tags.append(tag_slug)
    return matched_tags
```

### Anti-Patterns to Avoid
- **Telecharger tout a chaque run:** Toujours verifier ce qui existe deja en DB (incrementalite via `official_id`)
- **Parser le gros syseron.xml.zip en memoire:** Utiliser SAX/iterparse pour les gros XML, jamais DOM complet
- **Hardcoder les credentials:** Toujours utiliser .env / DATABASE_URL
- **Ignorer les erreurs HTTP:** Toujours retry avec backoff, logger les erreurs sans crasher le pipeline entier
- **Un seul script monolithique:** Separer deputes / debats / tagging pour pouvoir relancer individuellement

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PostgreSQL adapter | Raw socket/SQL builder | psycopg 3 | Parameterized queries, connection pooling, context managers |
| HTTP client with retries | urllib + manual retry logic | httpx (+ tenacity si besoin) | Timeout config, connection pooling, retry patterns |
| Slug generation | `re.sub(r'[^a-z]', '-', name.lower())` | python-slugify | Gere les accents, caracteres speciaux, unicode |
| Progress bars | `print(f"{i}/{total}")` | tqdm | ETA, speed, nested bars, zero effort |
| XML parsing performant | xml.etree + full load | lxml iterparse / SAX | Memoire constante pour fichiers > 100MB |

**Key insight:** Le pipeline d'ingestion est un ETL classique. Les librairies standard Python gèrent parfaitement ce cas. Ne pas ajouter de framework ETL (Airflow, Prefect) -- c'est overkill pour un run periodique lance manuellement.

## Common Pitfalls

### Pitfall 1: nosdeputes.fr legislature routing
**What goes wrong:** Les URLs de l'ancienne legislature redirigent (302) vers des sous-domaines (ex: `2017-2022.nosdeputes.fr`), et la legislature courante peut ne pas avoir de donnees sur certains endpoints.
**Why it happens:** nosdeputes.fr heberge chaque legislature sur un sous-domaine different.
**How to avoid:** Toujours specifier la legislature dans l'URL si necessaire. Gerer les redirects HTTP. Tester les endpoints avant de coder le parsing.
**Warning signs:** Reponse vide `{}` ou `{"deputes":[]}`, HTTP 302.

### Pitfall 2: Encoding XML/accents français
**What goes wrong:** Caracteres corrompus dans les noms de deputes ou textes d'interventions.
**Why it happens:** Mix d'encodages (UTF-8, Latin-1, Windows-1252) dans les sources officielles.
**How to avoid:** Toujours decoder en UTF-8. Si erreur, essayer `latin-1`. lxml gere l'encoding automatiquement si declare dans le XML header.
**Warning signs:** Caracteres `Ã©` au lieu de `e` avec accent.

### Pitfall 3: Matching deputes entre sources
**What goes wrong:** Un depute de nosdeputes.fr ne matche pas avec la DB car nom legerement different.
**Why it happens:** Noms composes, particules (de, Le), accents, tirets.
**How to avoid:** Utiliser `id_an` (identifiant AN officiel) comme cle de jointure plutot que le nom. Le champ `official_id` dans la DB doit etre l'`id_an` de nosdeputes.fr ou l'UID AN officiel.
**Warning signs:** Deputes orphelins dans la table interventions (deputyId NULL).

### Pitfall 4: Volume de donnees sous-estime
**What goes wrong:** Le script tourne pendant des heures ou timeout.
**Why it happens:** La 17e legislature (depuis juillet 2024) a deja des centaines de seances et des dizaines de milliers d'interventions.
**How to avoid:** Ingerer par batch (ex: par mois). Logger le progres. Utiliser des transactions par seance (pas par intervention). Limiter le scope initial (ex: 6 derniers mois).
**Warning signs:** Script qui semble "bloque" sans output.

### Pitfall 5: ON CONFLICT avec colonnes identity
**What goes wrong:** `INSERT ... ON CONFLICT DO UPDATE` echoue sur les colonnes `GENERATED ALWAYS AS IDENTITY`.
**Why it happens:** PostgreSQL refuse d'ecrire dans une colonne identity meme dans le SET.
**How to avoid:** Ne jamais inclure la colonne `id` dans l'INSERT ou l'UPDATE. Utiliser `official_id` comme constraint unique.
**Warning signs:** Erreur `cannot insert a non-DEFAULT value into column "id"`.

## Code Examples

### Complete Deputy Ingestion Flow
```python
#!/usr/bin/env python3
"""Ingest deputies from nosdeputes.fr into PostgreSQL."""
import os
import httpx
import psycopg
from dotenv import load_dotenv
from slugify import slugify

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DATABASE_URL = os.getenv('DATABASE_URL')
NOSDEPUTES_BASE = "https://www.nosdeputes.fr"

def fetch_deputies():
    """Fetch all deputies from nosdeputes.fr."""
    resp = httpx.get(f"{NOSDEPUTES_BASE}/deputes/json", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return [d["depute"] for d in data.get("deputes", [])]

def map_deputy(raw):
    """Map nosdeputes.fr deputy to DB schema."""
    slug = raw.get("slug", "")
    return {
        "official_id": str(raw.get("id_an", raw.get("id", ""))),
        "first_name": raw.get("prenom", ""),
        "last_name": raw.get("nom_de_famille", ""),
        "full_name": raw.get("nom", ""),
        "political_group": raw.get("groupe_sigle"),
        "photo_url": f"{NOSDEPUTES_BASE}/depute/photo/{slug}/120" if slug else None,
        "constituency": f"{raw.get('nom_circo', '')} ({raw.get('num_circo', '')})",
        "is_active": raw.get("mandat_fin") is None or raw.get("mandat_fin") == "",
    }

def upsert_deputies(conn, deputies):
    """Upsert deputies into PostgreSQL."""
    for dep in deputies:
        conn.execute("""
            INSERT INTO deputies (official_id, first_name, last_name, full_name,
                                  political_group, photo_url, constituency, is_active)
            VALUES (%(official_id)s, %(first_name)s, %(last_name)s, %(full_name)s,
                    %(political_group)s, %(photo_url)s, %(constituency)s, %(is_active)s)
            ON CONFLICT (official_id) DO UPDATE SET
                political_group = EXCLUDED.political_group,
                photo_url = EXCLUDED.photo_url,
                constituency = EXCLUDED.constituency,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """, dep)

if __name__ == "__main__":
    raw_deputies = fetch_deputies()
    mapped = [map_deputy(d) for d in raw_deputies]

    with psycopg.connect(DATABASE_URL) as conn:
        upsert_deputies(conn, mapped)
        conn.commit()

    print(f"Ingested {len(mapped)} deputies.")
```

### Intervention Tagging SQL Pattern
```sql
-- Insert tag if not exists, return id
INSERT INTO tags (name, slug)
VALUES ('Economie', 'economie')
ON CONFLICT (slug) DO NOTHING;

-- Link intervention to tag
INSERT INTO intervention_tags (intervention_id, tag_id)
SELECT %(intervention_id)s, id FROM tags WHERE slug = %(tag_slug)s
ON CONFLICT DO NOTHING;
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| psycopg2 | psycopg 3 | 2021+ (stable 2023) | Context managers, modern Python, async support |
| requests | httpx | 2023+ mainstream | Async-ready, better timeout/retry config |
| Full DOM XML parsing | SAX / iterparse | Always best for large files | Memory: O(1) vs O(n) |
| NLP keyword extraction (spaCy, RAKE) | Simple keyword dictionary | Pragmatic choice for v1 | Zero dependency, fast, good enough for categories |

**Deprecated/outdated:**
- `anpy` (Python client for AN): Scrapes HTML, pas maintenu activement, fragile. Ne pas utiliser.
- psycopg2: Toujours fonctionnel mais en maintenance-only, pas de nouvelles features.

## Open Questions

1. **Structure exacte du XML Syseron**
   - What we know: Tags `CompteRendu`, `dateSeance`/`DateSeance` confirmes. Schema XSD disponible.
   - What's unclear: Noms exacts des tags pour interventions et orateurs dans le format Syseron.
   - Recommendation: Telecharger le syseron.xml.zip au debut de la phase, explorer la structure avec un script. Si trop complexe, rester sur nosdeputes.fr uniquement.

2. **Disponibilite des donnees 17e legislature sur nosdeputes.fr**
   - What we know: `/deputes/json` retourne des deputes. `/deputes/enmandat/json` retourne vide.
   - What's unclear: Completude des seances/interventions pour la 17e legislature.
   - Recommendation: Tester les endpoints seances au debut de la phase. Si insuffisant, utiliser DILA/data.assemblee-nationale.fr.

3. **Rate limits nosdeputes.fr**
   - What we know: Pas de rate limit documente.
   - What's unclear: Seuil exact avant blocage.
   - Recommendation: 1 requete/seconde par defaut. Ajouter un sleep configurable.

4. **Mapping speakerName pour les non-deputes**
   - What we know: Certains intervenants sont des ministres, president de seance, etc. Pas dans la table deputies.
   - What's unclear: Comment les identifier dans l'API nosdeputes.fr.
   - Recommendation: `deputyId` nullable (deja le cas dans le schema). `speakerName` et `speakerRole` couvrent ce cas.

## Sources

### Primary (HIGH confidence)
- [nosdeputes.fr API documentation](https://github.com/regardscitoyens/nosdeputes.fr/blob/master/doc/api.md) -- endpoints, formats, pagination
- [data.assemblee-nationale.fr](https://data.assemblee-nationale.fr/acteurs/deputes-en-exercice) -- download URLs for deputies JSON/CSV
- [data.assemblee-nationale.fr debats](https://data.assemblee-nationale.fr/travaux-parlementaires/debats) -- syseron.xml.zip URL
- [nosdeputes.fr /deputes/json](https://www.nosdeputes.fr/deputes/json) -- JSON structure verified (field names confirmed)

### Secondary (MEDIUM confidence)
- [Assemblee-nationale/opendata_snippets](https://github.com/Assemblee-nationale/opendata_snippets) -- official AN code examples for XML parsing
- [data.gouv.fr debats dataset](https://www.data.gouv.fr/datasets/comptes-rendus-des-debats-de-l-assemblee-nationale) -- DILA XML files, schema docs
- [DILA file server](https://echanges.dila.gouv.fr/OPENDATA/Debats/AN/) -- .taz file listing for 2025

### Tertiary (LOW confidence)
- [anpy GitHub](https://github.com/regardscitoyens/anpy) -- Python client, not recommended (HTML scraping, fragile)
- XML Syseron tag structure -- inferred from opendata_snippets, needs runtime validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- psycopg3 + httpx are well-documented, verified
- Data sources (nosdeputes.fr): HIGH -- endpoints verified, JSON structure confirmed
- Data sources (AN officiel): MEDIUM -- URLs confirmed, XML structure partially documented
- Architecture patterns: HIGH -- standard Python ETL patterns
- Tagging approach: MEDIUM -- keyword-based is pragmatic but thresholds need tuning
- Pitfalls: HIGH -- documented from real API behavior observed during research

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (30 days -- APIs stables, legislature ongoing)
