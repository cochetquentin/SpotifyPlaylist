# Roadmap officielle — SpotifyPlaylist

> Application de tri automatique de musique Spotify en playlists thématiques par mood/contexte, basée sur des chansons de référence.

---

## Vision produit

L'utilisateur sélectionne 5 à 15 chansons de référence qui définissent un mood ou un contexte (ex. : "travail deep focus", "running", "soirée chill"). L'application analyse sa bibliothèque Spotify et génère automatiquement une playlist avec les titres les plus similaires, sans dépendre de l'API Audio Features de Spotify (dépréciée).

---

## Contraintes techniques non-négociables

| Contrainte | Raison |
|------------|--------|
| Pas d'API Spotify Audio Features | Dépréciée depuis novembre 2024 |
| Respect des ToS Spotify | Pas de scraping, pas de redistribution de données audio |
| Mode Développement Spotify | Limite à 25 utilisateurs, pas de quota étendu sans review |
| Données personnelles | Ne stocker que ce qui est nécessaire (RGPD-friendly) |

---

## Stack technique retenue

| Couche | Technologie | Justification |
|--------|-------------|---------------|
| Backend | Python 3.11+ / FastAPI | Async natif, typage fort, ecosystem ML |
| Base de données | SQLite (MVP) → PostgreSQL + pgvector (V2) | SQLite suffit pour débuter, pgvector pour la recherche vectorielle à l'échelle |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | Local, gratuit, 384 dimensions, rapide |
| Tags musicaux | Last.fm API (gratuit) | Tags communautaires riches, pas de ToS restrictif |
| Paroles | LRCLIB API (gratuit) | Open source, pas de limite stricte |
| Métadonnées | MusicBrainz API (gratuit) | Genre, artiste, date de sortie |
| Tagging LLM | OpenAI API ou Ollama (local) | Génération de tags mood/énergie/contexte |
| Gestion dépendances | `uv` | Rapide, reproductible |
| Frontend V1 | CLI (rich/typer) | Démarrage rapide, pas de frontend à maintenir |
| Frontend V2 | React + Vite | Simple, moderne, séparation claire |

---

## Flux de travail Git

```
main (protégée — aucun push direct)
  └── feat/etape1-fondation
  └── feat/etape2-import
  └── feat/etape3-enrichissement
  ...
```

### Règles

- **`main` est protégée** : aucun commit direct, pas de force-push
- **Chaque étape = une branche** : `feat/etapeN-nom`
- **PR obligatoire** avec description claire avant merge sur `main`
- **Tag Git** à chaque étape validée : `v0.1`, `v0.2`, etc.
- **Merge uniquement** quand tous les critères de validation sont cochés

---

## Vue d'ensemble des étapes

```
Étape 1 : Fondation          → git, env, Spotify OAuth, CI GitHub Actions, skill /handle-codex-review
Étape 2 : Import données     → tracks, playlists, normalisation
Étape 3 : Enrichissement     → Last.fm tags + LLM mood tagging
Étape 4 : Embeddings         → vecteurs, stockage, similarité cosinus
Étape 5 : Algorithme         → centroïde, scoring hybride, export playlist
Étape 6 : Interface          → CLI/web pour sélectionner références et valider
Étape 7 : Feedback           → Rocchio, ajustement des poids, historique
Étape 8 : Avancé             → clustering UMAP/HDBSCAN, sources audio alternatives
```

---

## Étape 1 : Fondation

### Objectif

Mettre en place l'infrastructure de base : dépôt Git configuré, environnement Python reproductible, authentification Spotify fonctionnelle, premier endpoint de santé, pipeline CI GitHub Actions et skill Claude `/handle-codex-review` pour automatiser les cycles de review.

### Tâches

#### Git & environnement
- [ ] Initialiser le dépôt Git avec `.gitignore` adapté Python
- [ ] Configurer la protection de branche `main` sur GitHub (no direct push, PR required)
- [ ] Initialiser le projet Python avec `uv` (`pyproject.toml`)
- [ ] Configurer les variables d'environnement (`.env` + `python-dotenv`)
- [ ] Documenter la procédure d'installation dans `README.md`

#### Application
- [ ] Créer l'application FastAPI avec un endpoint `GET /health`
- [ ] Implémenter le flux OAuth 2.0 Spotify (Authorization Code Flow)
- [ ] Stocker les tokens dans un fichier local chiffré (pas en clair)
- [ ] Créer un endpoint `GET /me` qui retourne le profil Spotify connecté
- [ ] Écrire un test d'intégration minimal (auth → /me)

#### GitHub Actions CI
- [ ] Créer `.github/workflows/ci.yml` avec les jobs suivants (déclenchés sur PR et push `main`) :
  - **Python / Lint** : `uv run ruff check .`
  - **Python / Format** : `uv run ruff format --check .`
  - **Python / Tests** : `uv run pytest --cov=. --cov-fail-under=80 tests/`
  - **Python / Security** : `uv run pip-audit`
  - **Smoke test** : build Docker + `curl /health` (optionnel si Dockerfile présent)
- [ ] Configurer `concurrency` pour annuler les runs redondants sur la même branche
- [ ] Ajouter `dependabot.yml` pour les mises à jour automatiques des actions GitHub

#### Skill Claude — `/handle-codex-review`
- [ ] Copier le fichier de commande dans `.claude/commands/handle-codex-review.md`
- [ ] Créer les scripts shell dans `.claude/scripts/codex-review/` :
  - `pr-info.sh` — récupère repo, PR, state, title, branch via `gh`
  - `anti-loop-check.sh <REPO> <PR>` — détecte les boucles de review
  - `get-comments.sh <REPO> <PR> <T_TRIGGER>` — récupère et classe les remarques Codex
  - `dirty-files.sh` — snapshot de l'état du working tree avant modifications
  - `post-skipped.sh <PR>` — poste les corrections ignorées sur la PR (stdin Markdown)
  - `trigger.sh <PR>` — poste le commentaire de relance de Codex

### Stack / APIs utilisées

- Spotify API : `accounts.spotify.com/authorize`, `/api/token`, `/v1/me`
- `httpx`, `fastapi`, `uvicorn`, `python-dotenv`
- `ruff` (lint + format), `pytest`, `pytest-cov`, `pip-audit`
- GitHub Actions : `actions/checkout@v6`, `actions/setup-python@v6`, `astral-sh/setup-uv@v7`
- `gh` CLI (pour les scripts codex-review)

### Critères de validation

- [ ] `uv run uvicorn app.main:app` démarre sans erreur
- [ ] `GET /health` retourne `{"status": "ok"}`
- [ ] Le flux OAuth complet fonctionne dans un navigateur
- [ ] `GET /me` retourne le nom d'utilisateur Spotify
- [ ] Les tokens sont rafraîchis automatiquement (refresh token flow)
- [ ] Aucun secret n'est commité dans Git (vérification `.gitignore`)
- [ ] La CI passe au vert sur la PR de cette étape (lint + format + tests + security)
- [ ] `/handle-codex-review` s'exécute sans erreur sur une PR de test

### Définition de Done

PR mergée sur `main`, tag `v0.1`, README à jour. La CI est verte, la branche `main` est protégée, et le skill `/handle-codex-review` est opérationnel dans `.claude/`.

### Branche Git

`feat/etape1-fondation`

---

## Étape 2 : Import des données

### Objectif

Récupérer la bibliothèque complète de l'utilisateur (titres sauvegardés + playlists), la normaliser et la stocker localement avec gestion des doublons.

### Tâches

- [ ] Créer le schéma de base de données SQLite (voir schéma ci-dessous)
- [ ] Implémenter la pagination complète de `GET /v1/me/tracks` (liked songs)
- [ ] Implémenter la pagination complète de `GET /v1/playlists` + tracks par playlist
- [ ] Normaliser et dédupliquer par `track_id` Spotify
- [ ] Stocker : `track_id`, `title`, `artist`, `album`, `release_year`, `duration_ms`, `popularity`
- [ ] Endpoint `POST /import` pour déclencher l'import
- [ ] Endpoint `GET /library/stats` (nombre de tracks, playlists, dernière sync)
- [ ] Gestion des erreurs API Spotify (rate limit, retry avec backoff exponentiel)
- [ ] Mode incrémental : ne ré-importer que les nouveaux titres si la lib existe déjà

### Schéma SQLite (MVP)

```sql
CREATE TABLE tracks (
    id TEXT PRIMARY KEY,              -- Spotify track ID
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT,
    release_year INTEGER,
    duration_ms INTEGER,
    popularity INTEGER,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE playlists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT,
    synced_at TIMESTAMP
);

CREATE TABLE playlist_tracks (
    playlist_id TEXT,
    track_id TEXT,
    position INTEGER,
    PRIMARY KEY (playlist_id, track_id),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);
```

### Stack / APIs utilisées

- Spotify API : `/v1/me/tracks`, `/v1/me/playlists`, `/v1/playlists/{id}/tracks`
- `sqlalchemy` (ORM léger) ou `sqlite3` brut
- `tenacity` pour le retry/backoff

### Critères de validation

- [ ] Import de 500+ tracks sans erreur
- [ ] Pas de doublons en base après import
- [ ] `GET /library/stats` retourne des chiffres cohérents
- [ ] Un second import incrémental n'insère que les nouveaux titres
- [ ] Le rate limit Spotify est géré proprement (pas de 429 non traité)

### Définition de Done

PR mergée sur `main`, tag `v0.2`. La bibliothèque complète est importée et interrogeable en SQL.

### Branche Git

`feat/etape2-import`

---

## Étape 3 : Enrichissement des métadonnées

### Objectif

Enrichir chaque track avec des tags musicaux (genre, mood, énergie, contexte) en combinant Last.fm et un LLM, avec stratégie de fallback si une source est indisponible.

### Tâches

- [ ] Intégrer Last.fm API : récupérer les top tags par `artist + title`
- [ ] Normaliser et filtrer les tags Last.fm (garder les 10 plus pertinents)
- [ ] Implémenter le tagging LLM : prompt structuré → JSON avec `mood`, `energy`, `context`, `tempo_feel`, `instruments`
- [ ] Stratégie de fallback : Last.fm seul si LLM indisponible, tags vides si les deux échouent
- [ ] Étendre le schéma DB avec une table `track_tags`
- [ ] Intégrer LRCLIB : récupérer les paroles si disponibles (optionnel, enrichit le contexte LLM)
- [ ] Endpoint `POST /enrich` (asynchrone, avec progression)
- [ ] Endpoint `GET /tracks/{id}/tags` pour inspecter les tags d'un titre
- [ ] Mise en cache : ne ré-enrichir que les tracks sans tags

### Schéma additionnel

```sql
CREATE TABLE track_tags (
    track_id TEXT,
    source TEXT,         -- 'lastfm', 'llm', 'manual'
    tag TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    PRIMARY KEY (track_id, source, tag),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);

CREATE TABLE track_enrichment (
    track_id TEXT PRIMARY KEY,
    mood TEXT,           -- ex: 'melancholic', 'energetic', 'peaceful'
    energy REAL,         -- 0.0 à 1.0
    context TEXT,        -- ex: 'workout', 'focus', 'party'
    tempo_feel TEXT,     -- 'slow', 'medium', 'fast'
    enriched_at TIMESTAMP,
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);
```

### Prompt LLM (template)

```
Tu es un expert en musique. Analyse ce titre et retourne un JSON strict.
Titre: "{title}" — Artiste: "{artist}" — Album: "{album}" ({year})
Tags Last.fm: {lastfm_tags}
{lyrics_excerpt_if_available}

Retourne UNIQUEMENT ce JSON (pas de texte autour) :
{
  "mood": "un seul mot en anglais",
  "energy": 0.0 à 1.0,
  "context": "workout|focus|party|chill|sleep|commute|social",
  "tempo_feel": "slow|medium|fast",
  "instruments": ["guitar", "piano", ...]
}
```

### Critères de validation

- [ ] 90%+ des tracks ont au moins des tags Last.fm ou LLM
- [ ] Le fallback fonctionne si Last.fm rate limit ou LLM down
- [ ] Les champs JSON LLM sont validés (pas de valeur hors plage)
- [ ] `GET /tracks/{id}/tags` retourne des données cohérentes
- [ ] L'enrichissement de 100 tracks prend moins de 5 minutes

### Définition de Done

PR mergée sur `main`, tag `v0.3`. Chaque track a un profil de tags exploitable pour la similarité.

### Branche Git

`feat/etape3-enrichissement`

---

## Étape 4 : Embeddings et similarité

### Objectif

Transformer chaque track en vecteur numérique à partir de ses métadonnées enrichies, stocker ces vecteurs et implémenter la recherche par similarité cosinus.

### Tâches

- [ ] Installer `sentence-transformers` (modèle `all-MiniLM-L6-v2`)
- [ ] Construire la représentation textuelle de chaque track pour l'embedding
- [ ] Générer et stocker les embeddings (384 dimensions) pour chaque track
- [ ] Implémenter la recherche des K voisins les plus proches (cosinus)
- [ ] Endpoint `POST /embeddings/generate` (batch asynchrone)
- [ ] Endpoint `GET /tracks/{id}/similar?k=10` pour tester la similarité
- [ ] Vérifier la cohérence : des tracks similaires musicalement doivent ressortir proches

### Représentation textuelle pour embedding

```python
def build_track_text(track: Track, tags: TrackEnrichment) -> str:
    return (
        f"Title: {track.title}. "
        f"Artist: {track.artist}. "
        f"Album: {track.album}. "
        f"Mood: {tags.mood}. "
        f"Energy: {tags.energy}. "
        f"Context: {tags.context}. "
        f"Tags: {', '.join(track.lastfm_tags[:5])}."
    )
```

### Schéma additionnel

```sql
CREATE TABLE track_embeddings (
    track_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,    -- numpy array sérialisé (float32, 384 dims)
    model_version TEXT,
    generated_at TIMESTAMP,
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);
```

### Critères de validation

- [ ] 95%+ des tracks ont un embedding généré
- [ ] `GET /tracks/{id}/similar?k=5` retourne des résultats musicalement cohérents (test manuel sur 10 tracks variés)
- [ ] La génération de 1000 embeddings prend moins de 2 minutes
- [ ] Les embeddings sont persistés et ne sont pas recalculés à chaque requête

### Définition de Done

PR mergée sur `main`, tag `v0.4`. La similarité cosinus fonctionne et les résultats sont musicalement sensés.

### Branche Git

`feat/etape4-embeddings`

---

## Étape 5 : Algorithme de playlist

### Objectif

À partir de 5 à 15 chansons de référence, calculer un centroïde, scorer toute la bibliothèque via un scoring hybride et générer une playlist exportable sur Spotify.

### Tâches

- [ ] Implémenter le calcul de centroïde (moyenne des embeddings de référence)
- [ ] Implémenter le scoring hybride : `score = 0.7 * cosine_sim + 0.3 * tag_overlap`
- [ ] Filtrer les références elles-mêmes du résultat
- [ ] Paramètre `n` : nombre de tracks à inclure dans la playlist (défaut : 30)
- [ ] Endpoint `POST /playlist/preview` : reçoit les IDs de référence, retourne les N meilleurs candidats
- [ ] Endpoint `POST /playlist/export` : crée la playlist sur Spotify via l'API
- [ ] Endpoint `GET /playlist/{id}/stats` : distribution des scores, breakdown par tag

### Algorithme de scoring

```python
def hybrid_score(
    candidate_embedding: np.ndarray,
    centroid: np.ndarray,
    candidate_tags: set[str],
    reference_tags: set[str],
    w_embedding: float = 0.7,
    w_tags: float = 0.3,
) -> float:
    cosine = cosine_similarity(candidate_embedding, centroid)
    tag_overlap = len(candidate_tags & reference_tags) / max(len(reference_tags), 1)
    return w_embedding * cosine + w_tags * tag_overlap
```

### Critères de validation

- [ ] `POST /playlist/preview` répond en moins de 3 secondes pour une bibliothèque de 1000 tracks
- [ ] Les 30 premiers résultats sont musicalement cohérents avec les références (évaluation subjective sur 5 essais)
- [ ] L'export Spotify crée bien la playlist dans le compte de l'utilisateur
- [ ] Les références ne figurent pas dans les résultats
- [ ] Le taux d'acceptation subjectif (tracks qu'on garderait) dépasse 40%

### Définition de Done

PR mergée sur `main`, tag `v0.5`. La fonctionnalité core est opérationnelle de bout en bout.

### Branche Git

`feat/etape5-algorithme`

---

## Étape 6 : Interface utilisateur

### Objectif

Fournir une interface utilisable (CLI d'abord, puis web optionnel) pour sélectionner les références, prévisualiser la playlist, valider/rejeter des tracks et lancer l'export.

### Tâches

#### CLI (obligatoire)
- [ ] `spotify-playlist init` — authentification Spotify
- [ ] `spotify-playlist import` — import de la bibliothèque
- [ ] `spotify-playlist enrich` — enrichissement des métadonnées
- [ ] `spotify-playlist create --refs "titre1, titre2..."` — génération interactive
- [ ] Affichage de la prévisualisation avec `rich` (tableau coloré, scores visibles)
- [ ] Validation interactive : approuver/rejeter des tracks avant export
- [ ] `spotify-playlist export --name "Ma Playlist"` — export vers Spotify

#### Web (optionnel V2)
- [ ] Interface React simple : sélection des références par recherche, prévisualisation, validation

### Critères de validation

- [ ] Un utilisateur non-technique peut créer une playlist en suivant uniquement le README
- [ ] La CLI affiche une progression claire pendant l'import et l'enrichissement
- [ ] La prévisualisation est lisible (titre, artiste, score, tags principaux)
- [ ] L'export confirme visuellement le succès avec le lien Spotify

### Définition de Done

PR mergée sur `main`, tag `v0.6`. Demo complète possible de bout en bout via CLI.

### Branche Git

`feat/etape6-interface`

---

## Étape 7 : Feedback et apprentissage

### Objectif

Enregistrer les validations/rejets de l'utilisateur et ajuster les poids de l'algorithme via Rocchio pour que les suggestions s'améliorent au fil du temps.

### Tâches

- [ ] Stocker les feedback utilisateur (track_id, action: accept/reject, session_id)
- [ ] Implémenter l'algorithme Rocchio pour ajuster le centroïde
- [ ] Ajuster les poids `w_embedding` et `w_tags` selon le profil utilisateur
- [ ] Endpoint `POST /feedback` : enregistrer un feedback
- [ ] Endpoint `GET /feedback/stats` : voir les tendances (quels tags sont sur/sous-représentés dans les rejects)
- [ ] Ré-ordonner la playlist après feedback sans relancer tout l'algorithme
- [ ] Historique des playlists générées avec leurs scores de satisfaction

### Algorithme Rocchio (simplifié)

```python
def rocchio_update(
    centroid: np.ndarray,
    accepted: list[np.ndarray],
    rejected: list[np.ndarray],
    alpha: float = 1.0,   # poids centroïde original
    beta: float = 0.8,    # poids positifs
    gamma: float = 0.2,   # pénalité négatifs
) -> np.ndarray:
    pos = np.mean(accepted, axis=0) if accepted else np.zeros_like(centroid)
    neg = np.mean(rejected, axis=0) if rejected else np.zeros_like(centroid)
    return alpha * centroid + beta * pos - gamma * neg
```

### Schéma additionnel

```sql
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    track_id TEXT,
    action TEXT CHECK(action IN ('accept', 'reject')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE playlist_sessions (
    id TEXT PRIMARY KEY,
    reference_ids TEXT,    -- JSON array
    generated_at TIMESTAMP,
    exported_at TIMESTAMP,
    satisfaction_score REAL  -- 0-1, calculé a posteriori
);
```

### Critères de validation

- [ ] Après 20+ feedbacks, le taux d'acceptation dépasse 60%
- [ ] Les rejets récurrents influencent visiblement les futures suggestions
- [ ] `GET /feedback/stats` montre des tendances exploitables
- [ ] Le système fonctionne sans feedback (dégradation gracieuse)

### Définition de Done

PR mergée sur `main`, tag `v0.7`. L'application apprend des préférences de l'utilisateur.

### Branche Git

`feat/etape7-feedback`

---

## Étape 8 : Fonctions avancées

### Objectif

Ajouter des capacités avancées d'exploration musicale : clustering automatique de la bibliothèque, détection de groupes thématiques et intégration de sources audio alternatives.

### Tâches

#### Clustering
- [ ] Installer `umap-learn`, `hdbscan`
- [ ] Réduire les embeddings à 2D avec UMAP pour visualisation
- [ ] Appliquer HDBSCAN pour détecter des clusters naturels dans la bibliothèque
- [ ] Nommer automatiquement chaque cluster via les tags dominants
- [ ] Endpoint `GET /library/clusters` : retourner les clusters avec leurs tracks et tags
- [ ] Visualisation optionnelle : scatter plot des clusters (matplotlib/plotly)

#### Sources audio alternatives
- [ ] Explorer l'API AcousticBrainz (archivée mais données disponibles) pour BPM/clé
- [ ] Intégrer les données de MusicBrainz pour affiner les genres
- [ ] Pondérer optionnellement les features audio dans le scoring si disponibles

#### Améliorations algorithmiques
- [ ] Support multi-centroïde : une playlist qui fusionne plusieurs moods
- [ ] Exclusion par artiste (éviter 5 tracks du même artiste dans une playlist)
- [ ] Diversité forcée : paramètre `diversity` qui pénalise la répétition d'artiste/album

### Critères de validation

- [ ] Les clusters détectés sont musicalement cohérents (évaluation sur 5 clusters)
- [ ] `GET /library/clusters` répond en moins de 30 secondes pour 2000 tracks
- [ ] La diversification évite les artistes sur-représentés (max 2 tracks par artiste par défaut)

### Définition de Done

PR mergée sur `main`, tag `v0.8`. L'application offre une exploration autonome de la bibliothèque.

### Branche Git

`feat/etape8-avance`

---

## Sources de données et limites

| Source | Usage | Limite | Gratuit |
|--------|-------|--------|---------|
| Spotify API | Auth, import library, export playlist | Rate limit, Mode Dev = 25 users | Oui |
| Last.fm API | Tags musicaux communautaires | 5 req/s | Oui (clé API) |
| LRCLIB | Paroles (contexte LLM) | Pas de limite officielle | Oui |
| MusicBrainz | Genre, métadonnées enrichies | 1 req/s | Oui |
| OpenAI API | Tagging LLM | Payant à l'usage | Non |
| Ollama (local) | Tagging LLM alternatif | Ressources machine | Oui |
| sentence-transformers | Embeddings locaux | CPU/GPU machine | Oui |

---

## Indicateurs de succès globaux

| Métrique | Cible MVP (v0.5) | Cible V2 (v0.7+) |
|----------|-----------------|-----------------|
| Taux d'acceptation subjectif | > 40% | > 60% |
| Temps de génération playlist (1000 tracks) | < 5s | < 2s |
| Couverture enrichissement | > 80% des tracks | > 95% |
| Satisfaction utilisateur (1-5) | ≥ 3.5 | ≥ 4.0 |

---

## Évolution des versions

```
v0.1  Fondation (auth Spotify)
v0.2  Import bibliothèque
v0.3  Enrichissement tags
v0.4  Embeddings + similarité
v0.5  ★ MVP — Génération playlist de bout en bout
v0.6  Interface CLI complète
v0.7  Feedback + apprentissage
v0.8  Clustering + sources avancées
v1.0  Interface web + multi-utilisateurs
```

---

*Roadmap synthétisée à partir des propositions de Claude, ChatGPT, DeepSeek, Gemini et Grok — juin 2026.*
