# Roadmap détaillée pour l'application de tri automatique de musiques Spotify

---

## 1. Résumé du projet

L'objectif est de créer une application capable de trier automatiquement vos musiques Spotify en playlists ultra-spécifiques selon le mood, le contexte d'écoute et le style. Le cœur du système repose sur la capacité à représenter chaque chanson par des données exploitables (métadonnées, embeddings textuels, éventuellement features audio alternatives) et à comparer ces représentations pour trouver des similarités.

Le problème principal est que Spotify a récemment retiré l'accès aux `audio features` comme `danceability`, `energy`, `valence` pour les nouveaux projets via son API Web officielle . Il faut donc une architecture qui contourne cette limitation tout en restant légale.

## 2. Hypothèses techniques

- **Backend** : Python (Flask/FastAPI) pour la flexibilité et l'écosystème ML
- **Base de données** : SQLite d'abord, puis PostgreSQL
- **Cache** : Redis optionnel pour les appels API Spotify
- **Stockage des embeddings** : Vecteurs stockés en base avec extension pgvector (PostgreSQL)
- **Frontend** : Interface web minimale (HTML + JavaScript) pour la V1
- **Authentification** : OAuth 2.0 Spotify

## 3. Sources de données possibles

### 🟢 Faciles et légales (à utiliser en priorité)

| Source | Données obtenues | Accès |
|--------|------------------|-------|
| **Spotify Web API** | Playlists, morceaux, artistes, albums, popularité, genres | OAuth 2.0  |
| **Spotify Extended Audio Features API** | danceability, energy, valence, tempo, key, etc. | API payante (RapidAPI)  |
| **LLM (OpenAI/Gemini)** | Tags de mood, analyse de contexte, descriptions | API payante  |

### 🟡 Moyennement difficiles (à considérer)

| Source | Données obtenues | Accès |
|--------|------------------|-------|
| **Paroles (Lyrics)** | Texte des chansons | API non officielles (risque DMCA)  |
| **Embeddings texte** | Représentation vectorielle des titres/artistes/genres | Modèles open source (all-MiniLM-L6-v2)  |

### 🔴 Difficiles ou risquées (à ignorer en V1)

| Source | Problème |
|--------|----------|
| Analyse audio directe | Nécessite les fichiers musicaux (téléchargement illégal) |
| Spotify Audio Features officielle | **Dépréciée** depuis novembre 2024  |
| Lyrics officielles Spotify | Nécessite un compte Premium + API mobile non officielle |

## 4. MVP recommandé

Le Minimum Viable Product doit permettre de :

1. Se connecter à Spotify et récupérer toutes vos playlists et morceaux
2. Enrichir chaque morceau avec :
   - Ses métadonnées (titre, artiste, album, année, genres, popularité)
   - Ses features audio via l'API Extended Features (substitut Spotify)
   - Ses embeddings textuels (via un modèle comme SentenceTransformer)
3. Sélectionner 5 à 15 morceaux de référence pour un mood donné
4. Comparer tous les autres morceaux par similarité cosine
5. Retourner les 20-50 morceaux les plus proches
6. Afficher la playlist proposée avec possibilité d'ajuster

## 5. Roadmap étape par étape

---

### Étape 0 : Mise en place de l'environnement

**Objectif** : Préparer la base technique du projet

**Implémentation** :
- Créer un projet Python avec environnement virtuel
- Configurer les dépendances : `spotipy`, `fastapi`, `sqlalchemy`, `sentence-transformers`, `numpy`, `scikit-learn`
- Créer un compte Spotify Developer et enregistrer une application
- Configurer les variables d'environnement pour les clés API

**Données nécessaires** : Aucune

**Choix techniques** :
- Python 3.10+
- Spotipy comme wrapper Spotify
- FastAPI pour l'API

**Résultat attendu** : Un projet fonctionnel avec les dépendances installées

**Vérifications** :
- [ ] `pip install` réussi
- [ ] Application Spotify créée avec Client ID et Secret

**Risques** : Aucun

**Version minimale acceptable** : Code qui s'exécute sans erreur

---

### Étape 1 : Connexion Spotify et récupération des données

**Objectif** : Authentifier l'utilisateur et récupérer toutes ses playlists et morceaux

**Implémentation** :
- Mettre en place le flux OAuth 2.0 Spotify
- Récupérer la liste des playlists de l'utilisateur
- Récupérer tous les morceaux de chaque playlist (avec pagination)
- Normaliser les morceaux pour éviter les doublons (déduplication par URI Spotify)
- Stocker les données dans une base locale (SQLite)

**Données nécessaires** : Token d'accès Spotify

**Choix techniques** :
- Spotipy pour OAuth et appels API
- SQLAlchemy pour le modèle de données
- Pagination gérée automatiquement par Spotipy

**Résultat attendu** : Base locale contenant toutes vos playlists et morceaux (dédupliqués)

**Vérifications** :
- [ ] Connexion OAuth fonctionnelle
- [ ] Récupération d'au moins 100 morceaux
- [ ] Absence de doublons dans la base

**Risques** : Limites de rate limiting Spotify (gérer avec des retries)

**Version minimale acceptable** : Afficher le nombre de playlists et morceaux récupérés

---

### Étape 2 : Enrichissement des métadonnées

**Objectif** : Ajouter des informations contextuelles à chaque morceau

**Implémentation** :
- Pour chaque morceau, récupérer les détails artiste/album
- Récupérer les genres associés aux artistes
- Stocker : année de sortie, popularité, genres, etc.
- Ajouter un champ `artist_genres` pour le texte enrichi

**Données nécessaires** : Playlists et morceaux (Étape 1)

**Choix techniques** :
- Appels Spotify API par lot pour optimiser (`artists` avec plusieurs IDs)
- Mise à jour des enregistrements en base

**Résultat attendu** : Tous les morceaux ont des métadonnées complètes (titre, artiste(s), album, année, genres, popularité)

**Vérifications** :
- [ ] Chaque morceau a au moins un genre associé (même "unknown")
- [ ] Année de sortie présente pour > 90% des morceaux

**Risques** : Certains artistes n'ont pas de genre renseigné

**Version minimale acceptable** : Champs remplis partiellement

---

### Étape 3 : Récupération des features audio alternatives

**Objectif** : Obtenir les caractéristiques audio (energy, valence, tempo, etc.) pour chaque morceau

**Implémentation** :
- S'inscrire sur RapidAPI pour utiliser Spotify Extended Audio Features API 
- Pour chaque morceau, appeler l'API avec son ID Spotify
- Stocker les features : `danceability`, `energy`, `key`, `loudness`, `mode`, `speechiness`, `acousticness`, `instrumentalness`, `liveness`, `valence`, `tempo`
- Gérer les erreurs et les retries

**Données nécessaires** : Liste des IDs Spotify des morceaux

**Choix techniques** :
- RapidAPI avec le endpoint audio-features
- Stockage des features dans la base (colonnes dédiées)
- Batch processing pour éviter les appels trop fréquents

**Résultat attendu** : Chaque morceau a des features audio numériques exploitables

**Vérifications** :
- [ ] Au moins 10 morceaux ont des features audio
- [ ] Les valeurs sont dans les ranges attendues (0-1 pour la plupart)
- [ ] Tempo > 0

**Risques** : API payante à partir d'un certain volume, dépendance externe

**Version minimale acceptable** : Features récupérées pour les morceaux les plus récents d'abord

---

### Étape 4 : Génération des embeddings textuels

**Objectif** : Représenter chaque chanson par un vecteur numérique à partir de son titre, artiste(s) et genres

**Implémentation** :
- Créer un texte composite par morceau : `"{titre} par {artiste} - genres: {genres}"`
- Utiliser un modèle SentenceTransformer (ex: `all-MiniLM-L6-v2`) pour générer un embedding de 384 dimensions 
- Stocker les embeddings dans la base (en tant que BLOB ou vecteur pgvector)

**Données nécessaires** : Métadonnées enrichies (Étape 2)

**Choix techniques** :
- `sentence-transformers` library
- Batch processing pour éviter de saturer la mémoire
- Cache des embeddings pour ne pas régénérer

**Résultat attendu** : Chaque morceau a un vecteur embedding qui capture sémantiquement son identité

**Vérifications** :
- [ ] Embeddings générés pour > 90% des morceaux
- [ ] Dimension de l'embedding constante
- [ ] Temps de génération raisonnable (< 1s par morceau)

**Risques** : Modèle de 90 Mo à télécharger, consommation mémoire

**Version minimale acceptable** : Embeddings pour les 100 premiers morceaux seulement

---

### Étape 5 : Tags LLM (optionnel mais recommandé)

**Objectif** : Ajouter des tags de mood par chanson via un LLM

**Implémentation** :
- Pour chaque chanson (ou par lot), envoyer le titre + artiste à un LLM (OpenAI ou Gemini) 
- Prompt : *"Quels sont les 3 moods principaux de cette chanson parmi : triste, joyeux, énergique, calme, nostalgique, romantique, mélancolique, euphorique, introspectif ? Réponds en un seul mot."*
- Stocker les tags dans un champ texte

**Données nécessaires** : Métadonnées (Étape 2)

**Choix techniques** :
- API OpenAI ou Gemini (via `openai` ou `google-generativeai`)
- Mode "fallback" : si une API ne fonctionne pas, utiliser l'autre
- Batch avec limite de tokens

**Résultat attendu** : Tags de mood pour les morceaux les plus importants

**Vérifications** :
- [ ] Tags générés pour au moins 20 morceaux
- [ ] Qualité des tags cohérente avec le contenu

**Risques** : Coût API, latence, qualité variable selon le modèle

**Version minimale acceptable** : Seulement pour les morceaux de référence (5-15)

---

### Étape 6 : Implémentation du scoring par similarité

**Objectif** : Comparer des morceaux de référence avec tout le catalogue

**Implémentation** :
- Fonction qui prend une liste d'IDs de morceaux de référence
- Calcule l'embedding moyen des références
- Calcule la similarité cosine entre cet embedding moyen et tous les autres morceaux
- Retourne les N morceaux les plus proches

**Données nécessaires** : Embeddings (Étape 4), tags si disponibles

**Choix techniques** :
- NumPy pour les calculs vectoriels
- Similarité cosine de scikit-learn
- Pondération possible : embedding (70%) + features audio (30%)

**Résultat attendu** : Une fonction qui retourne une playlist classée par similarité

**Vérifications** :
- [ ] La similarité retourne des valeurs entre -1 et 1
- [ ] Les morceaux de référence sont en tête de liste
- [ ] Les résultats semblent pertinents visuellement

**Risques** : Résultats non pertinents si les embeddings sont mauvais

**Version minimale acceptable** : Comparaison basée uniquement sur les métadonnées textuelles

---

### Étape 7 : Interface utilisateur et création de playlists

**Objectif** : Permettre à l'utilisateur de sélectionner des références et visualiser les résultats

**Implémentation** :
- Interface web simple avec :
  - Recherche/sélection de morceaux de référence
  - Bouton "Générer la playlist"
  - Affichage des résultats classés
  - Possibilité d'accepter/rejeter chaque morceau proposé
  - Bouton "Créer la playlist Spotify" pour exporter
- Utiliser l'API Spotify pour créer la playlist dans le compte de l'utilisateur

**Données nécessaires** : Tout le pipeline des étapes précédentes

**Choix techniques** :
- Frontend : HTML + JavaScript (ou React/Vue si besoin)
- Backend : FastAPI avec endpoints REST
- Création de playlist : `spotify.user_playlist_create()`

**Résultat attendu** : Application web fonctionnelle où l'utilisateur peut :
1. Sélectionner 5-15 morceaux de référence
2. Lancer la génération
3. Voir la playlist proposée
4. L'ajuster manuellement
5. L'exporter vers Spotify

**Vérifications** :
- [ ] Sélection de référence fonctionnelle
- [ ] Génération en < 5 secondes pour 500 morceaux
- [ ] Export Spotify réussi

**Risques** : Performance avec un grand catalogue

**Version minimale acceptable** : Interface en ligne de commande

---

### Étape 8 : Feedback utilisateur et amélioration

**Objectif** : Apprendre des préférences de l'utilisateur pour affiner les recommandations

**Implémentation** :
- Stocker les feedbacks : "accepté" / "rejeté" pour chaque proposition
- Pour chaque mood, construire un profil vectoriel moyen à partir des morceaux acceptés
- Pondérer les embeddings en fonction des feedbacks (renforcement positif)
- Option : affiner avec un petit modèle ML (Multilayer Perceptron) 

**Données nécessaires** : Historique des feedbacks utilisateur

**Choix techniques** :
- Stockage des feedbacks en base
- Mise à jour des profils en temps réel ou par batch
- Possibilité de ré-entraînement périodique

**Résultat attendu** : Les recommandations s'améliorent avec l'usage

**Vérifications** :
- [ ] Les feedbacks sont stockés
- [ ] Un morceau rejeté n'apparaît pas dans les prochaines recommandations pour ce mood
- [ ] Amélioration mesurable sur 10 utilisations

**Risques** : Surcharge cognitive pour l'utilisateur

**Version minimale acceptable** : Ignorer les feedbacks (système statique)

---

## 6. Architecture technique proposée

```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend Web                          │
│                  (HTML + JavaScript)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────────────┐
│                   API Backend (FastAPI)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Endpoints : /auth, /playlists, /tracks, /generate  │   │
│  │             /feedback, /export                       │   │
│  └──────────────────────────────────────────────────────┘   │
└──┬──────────────┬──────────────┬──────────────┬────────────┘
   │              │              │              │
   ▼              ▼              ▼              ▼
┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────┐
│ SQLite  │ │ Embedding│ │ Spotify  │ │ Extended Audio  │
│ /       │ │ Generator│ │ Web API  │ │ Features API    │
│PostgreSQ│ │(Sentence │ │(Spotipy) │ │ (RapidAPI)      │
│L        │ │Transform)│ │          │ │                 │
└─────────┘ └──────────┘ └──────────┘ └─────────────────┘
```

## 7. Modèle de données initial

```sql
-- Table principale des morceaux
CREATE TABLE tracks (
    id TEXT PRIMARY KEY,           -- Spotify URI
    name TEXT NOT NULL,
    artists TEXT NOT NULL,          -- JSON array
    album TEXT,
    release_year INTEGER,
    popularity INTEGER,
    genres TEXT,                    -- JSON array
    duration_ms INTEGER,
    
    -- Features audio (API Extended)
    danceability REAL,
    energy REAL,
    key INTEGER,
    loudness REAL,
    mode INTEGER,
    speechiness REAL,
    acousticness REAL,
    instrumentalness REAL,
    liveness REAL,
    valence REAL,
    tempo REAL,
    
    -- Embedding (stocké en BLOB ou via pgvector)
    embedding BLOB,
    
    -- Tags LLM
    mood_tags TEXT,                 -- JSON array
    
    -- Métadonnées
    last_sync DATETIME
);

-- Playlists
CREATE TABLE playlists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    owner TEXT,
    snapshot_id TEXT
);

-- Relation playlist ↔ morceaux
CREATE TABLE playlist_tracks (
    playlist_id TEXT,
    track_id TEXT,
    added_at DATETIME,
    PRIMARY KEY (playlist_id, track_id)
);

-- Feedback utilisateur
CREATE TABLE user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mood_query TEXT,                -- Identifiant du mood
    track_id TEXT,
    reference_track_ids TEXT,       -- IDs des références utilisées
    feedback INTEGER,               -- 1 = accepté, -1 = rejeté
    created_at DATETIME
);
```

## 8. Stratégie d'enrichissement des morceaux

### Niveau 1 (core) - Obligatoire
- Métadonnées : titre, artiste(s), album, année, genres, popularité
- Embedding textuel : via all-MiniLM-L6-v2 

### Niveau 2 (recommandé) - Améliore significativement
- Features audio alternatives : energy, valence, tempo, danceability, etc. 
- Tags LLM pour le mood (OpenAI ou Gemini) 

### Niveau 3 (optionnel) - Peaufinage
- Lyrics (si accessibles) 
- Embedding des paroles

### Niveau 4 (à long terme) - Avancé
- User feedback personnalisé
- Profils de mood vectoriels

## 9. Stratégie de similarité / clustering

### Version simple (recommandée pour MVP)
**Approche :** Scalarisation + similarité cosine

1. **Embedding principal** : Vectorisation du texte composite (poids 70%)
2. **Features audio** : Vecteur normalisé des features (poids 30%)
3. **Vecteur composite** : Concaténation pondérée des deux
4. **Similarité** : Cosine entre le vecteur moyen des références et chaque morceau

```python
def compute_similarity(reference_track_ids, all_tracks):
    # Vecteur moyen des références
    ref_embedding = mean([tracks[id].embedding for id in reference_track_ids])
    ref_features = mean([tracks[id].audio_features for id in reference_track_ids])
    
    # Vecteur composite
    ref_vector = 0.7 * ref_embedding + 0.3 * ref_features
    
    # Cosine similarity avec tous les morceaux
    results = []
    for track in all_tracks:
        track_vector = 0.7 * track.embedding + 0.3 * track.audio_features
        score = cosine_similarity(ref_vector, track_vector)
        results.append((track.id, score))
    
    return sorted(results, key=lambda x: x[1], reverse=True)
```

### Version intermédiaire (après MVP)
**Approche :** Clustering par mood

- Utiliser HDBSCAN ou K-Means sur les embeddings 
- Visualiser les clusters (PCA/t-SNE) pour identifier des groupes naturels
- Associer un mood à chaque cluster
- Sélectionner des références = naviguer dans le cluster

### Version avancée (feedback + ML)
- MLP (Multilayer Perceptron) entraîné sur les feedbacks utilisateur 
- Apprentissage des préférences de l'utilisateur par mood
- Vecteur de profil personnalisé évolutif

## 10. Stratégie lyrics

### Statut : Optionnel, à implémenter en dernier

**Pourquoi c'est compliqué :**
- L'API officielle Spotify pour les lyrics est réservée aux comptes Premium 
- Les APIs alternatives sont instables et risquent un DMCA
- Intégrer des paroles nécessite un embedding supplémentaire

**Approche recommandée :**
1. Utiliser l'API Spotify Mobile Lyrics **uniquement avec un compte Premium** 
2. Ou utiliser une API externe de lyrics (musixmatch, genius) avec leurs propres limitations
3. Si des paroles sont disponibles, les passer dans SentenceTransformer pour un embedding de paroles additionnel
4. Le pondérer à 20% dans la similarité finale

**Risques :** Dépendance à des APIs tierces, légalité incertaine, coût

**Recommandation :** **Ignorer les lyrics dans le MVP**. Le titre + artiste + genre + features audio donnent déjà une très bonne base.

## 11. Stratégie de validation utilisateur

**Phases de validation :**

### Phase 1 (MVP) - Validation manuelle
- L'utilisateur voit la playlist proposée
- Peut accepter/rejeter chaque morceau
- Les rejets ne sont pas stockés (pas de mémoire)

### Phase 2 - Feedback mémorisé
- Les acceptations/rejets sont stockés en base
- Un profil utilisateur par mood est construit
- Les morceaux rejetés sont pondérés négativement

### Phase 3 - Apprentissage actif
- L'utilisateur peut noter les morceaux de 1 à 5
- Un modèle ML (MLP) s'entraîne sur les évaluations 
- Les recommandations deviennent personnalisées

## 12. Évolution vers une version plus avancée

### Post-MVP (3-6 mois)
- [ ] Interface de visualisation des clusters
- [ ] Mode "exploration" : découverte de morceaux inconnus
- [ ] Amélioration des performances (passer à PostgreSQL + pgvector)
- [ ] Support des playlists collaboratives

### Version 2 (6-12 mois)
- [ ] Profils de mood multiples et combinables
- [ ] Analyse de l'historique d'écoute
- [ ] Détection automatique des nouveaux morceaux
- [ ] API publique pour intégrations tierces

### Version 3 (12+ mois)
- [ ] Modèle personnalisé entraîné sur vos données
- [ ] Recommandation en temps réel (streaming)
- [ ] Intégration avec d'autres plateformes (Apple Music, Deezer)
- [ ] Fonctionnalités sociales (partage de playlists, mood boards)

## 13. Risques techniques

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| API Extended Features payante | Coût | Élevée | Limiter les appels, faire du cache, mode dégradé |
| Dépréciation d'une API tierce | Bloquant | Moyenne | Prévoir un système de fallback (features basiques uniquement) |
| Performance avec > 10k morceaux | Ralentissement | Élevée | Optimiser avec des batchs, utiliser pgvector |
| Qualité des embeddings médiocre | Résultats non pertinents | Moyenne | Utiliser le modèle le plus récent, enrichir le texte |
| Coût LLM pour les tags | Dépenses | Faible | Faire des batchs, limiter aux morceaux de référence |
| Spotify rate limiting | Bloquant | Élevée | Implémenter des retries exponentiels, batch requests |

## 14. Ordre exact d'implémentation

1. **Semaine 1** : Étape 0 (Environnement) + Étape 1 (Connexion Spotify)
2. **Semaine 2** : Étape 2 (Métadonnées) + Étape 3 (Features audio alternatives)
3. **Semaine 3** : Étape 4 (Embeddings textuels) + Validation sur 100 morceaux
4. **Semaine 4** : Étape 5 (Tags LLM) - optionnel, uniquement pour test
5. **Semaine 5** : Étape 6 (Scoring par similarité) + Tests de pertinence
6. **Semaine 6** : Étape 7 (Interface utilisateur) + Création de playlists
7. **Semaine 7** : Intégration complète + Tests utilisateur
8. **Semaine 8** : Étape 8 (Feedback) + Déploiement MVP

## 15. Critères de réussite pour chaque étape

### Étape 0 : Environnement
- ✅ `python app.py` démarre sans erreur

### Étape 1 : Connexion Spotify
- ✅ Redirection OAuth réussie
- ✅ > 50 morceaux récupérés
- ✅ Base de données avec au moins 3 tables créées

### Étape 2 : Métadonnées
- ✅ Chaque morceau a un champ `artist_genres` non vide
- ✅ 90% des morceaux ont une année de sortie

### Étape 3 : Features audio
- ✅ Au moins 100 morceaux avec `energy` et `valence`
- ✅ Valeurs cohérentes avec le genre (ex: metal = energy élevée)

### Étape 4 : Embeddings
- ✅ Embedding généré pour > 50 morceaux
- ✅ Similarité entre "Bohemian Rhapsody" et "Somebody to Love" > 0.7
- ✅ Similarité entre "Bohemian Rhapsody" et "Baby Shark" < 0.3

### Étape 5 : Tags LLM
- ✅ Tags cohérents pour 20 morceaux testés manuellement

### Étape 6 : Scoring
- ✅ Les morceaux de référence sont en top 5 des résultats
- ✅ Playlist générée en < 5 secondes pour 500 morceaux

### Étape 7 : Interface
- ✅ Sélection de références intuitive
- ✅ Export Spotify réussi
- ✅ Feedback utilisateur (accept/reject) fonctionnel

### Étape 8 : Feedback
- ✅ Les rejets influencent les futures recommandations
- ✅ Amélioration mesurable sur 5 itérations avec les mêmes références

---

## Conclusion

Cette roadmap vous permet de construire l'application de tri automatique de musiques Spotify de manière progressive, en commençant par un MVP solide basé sur des embeddings textuels et des features audio alternatives. La solution contourne intelligemment la dépréciation des Audio Features Spotify tout en restant légale et maintenable.

**Points clés à retenir :**
1. L'API Extended Features sur RapidAPI est votre meilleure option pour les features audio 
2. Les embeddings avec SentenceTransformer donnent une base de similarité très fiable 
3. Les LLM peuvent enrichir avec des tags de mood mais ne sont pas indispensables en V1 
4. L'architecture modulaire permet d'ajouter facilement le feedback utilisateur plus tard

**Première action concrète :** Créez un compte Spotify Developer, enregistrez une application, et installez Spotipy. Commencez par récupérer vos playlists et leurs morceaux.