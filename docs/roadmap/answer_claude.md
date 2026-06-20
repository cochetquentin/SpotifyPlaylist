# Roadmap : Application de tri musical Spotify par mood

## 1. Résumé du projet

Tu veux un outil qui apprend tes "moods" à partir de quelques chansons de référence (5-15) et propose les morceaux les plus proches dans ta bibliothèque Spotify. Le cœur technique du projet est de **représenter chaque chanson comme un vecteur** exploitable, sachant que Spotify a fermé l'accès aux `audio features` pour les nouveaux clients API (décision de novembre 2024). Ta vraie contrainte n'est donc pas l'algorithme — c'est l'enrichissement des données.

La bonne nouvelle : tu n'as pas besoin de features audio sophistiquées pour un MVP utile. Des embeddings texte (titre + artiste + genre + tags LLM) suffisent à capturer une grande partie du "mood" perçu, parce que le mood est largement corrélé à l'artiste, au genre et au champ lexical. Tu commences là, et tu ajoutes l'audio seulement si le ressenti ne suffit pas.

## 2. Hypothèses techniques

- Tu as un compte Spotify et tu peux créer une app dans le Developer Dashboard (OAuth Authorization Code Flow).
- Les `audio features` (`/audio-features`), `audio-analysis`, recommandations et 30s previews sont **indisponibles ou non garantis** pour une nouvelle app créée après nov. 2024. On ne s'appuie pas dessus.
- Tu acceptes que l'enrichissement "mood" passe d'abord par du texte + LLM, et que l'audio réel soit une option ultérieure.
- Bibliothèque cible : ordre de grandeur 1 000 à 20 000 morceaux. À cette échelle, **pas besoin de base vectorielle dédiée** — numpy + cosinus en mémoire suffit.
- Usage personnel, mono-utilisateur au départ. Ça simplifie énormément l'auth, le stockage et le scaling.

## 3. Sources de données possibles

| Source | Donne quoi | Facilité | Fiabilité | Verdict MVP |
|---|---|---|---|---|
| **Spotify Web API** | playlists, tracks, artistes, albums, année, popularité, genres (au niveau artiste) | Facile | Stable | **Oui, base** |
| **Tags LLM** (GPT/Claude sur métadonnées) | "sad", "night drive", "energetic"... | Facile | Bonne | **Oui, clé** |
| **Embeddings texte** (OpenAI/sentence-transformers) | vecteur sémantique du morceau | Facile | Bonne | **Oui, clé** |
| **Last.fm API** | tags communautaires ("melancholic", "chill"), similar artists | Facile, gratuit | Bonne | **Oui, fort ROI** |
| **Genius / lyrics** | paroles → thèmes, émotion, langue | Moyen (scraping fragile, ToS) | Moyenne | Phase 2 |
| **MusicBrainz / AcousticBrainz** | BPM, key, mood pré-calculés (open data) | Moyen (matching ISRC) | Variable (couverture inégale) | Phase 2 |
| **Analyse audio locale** (librosa/Essentia sur tes fichiers) | BPM, énergie, timbre réels | Difficile | Excellente | Phase 3, optionnel |

**Le meilleur rapport effort/valeur caché ici : Last.fm.** Ses tags communautaires (gratuits, API stable) sont précisément des descripteurs de mood/genre attachés aux morceaux et artistes. C'est presque un substitut direct aux audio features pour ton cas.

## 4. MVP recommandé

> **Sélectionne 5-15 morceaux de référence → l'app classe toute ta bibliothèque par similarité → tu valides → elle crée une playlist Spotify.**

Stack minimale :
- **Backend** : Python + FastAPI (l'écosystème ML/embeddings est en Python, autant tout y mettre)
- **DB** : SQLite (un seul fichier, zéro config ; tu migreras vers Postgres si besoin)
- **Embeddings** : `sentence-transformers` local (`all-MiniLM-L6-v2`, gratuit) ou OpenAI `text-embedding-3-small`
- **Similarité** : cosinus en mémoire avec numpy
- **Frontend** : au début, **rien** — un script CLI ou un notebook. Tu ajoutes une UI seulement quand le moteur marche.

Représentation d'un morceau dans le MVP = embedding d'une phrase construite par toi :
```
"{titre} par {artiste}. Genres: {genres}. Tags: {tags_lastfm}. Mood: {tags_llm}."
```

## 5. Roadmap étape par étape

Format demandé pour chaque étape : Objectif · Implémenter · Données · Choix techniques · Résultat · Vérifications · Risques · Version minimale.

---

### Étape 0 — Auth Spotify & socle projet

1. **Objectif** : pouvoir s'authentifier et appeler l'API en ton nom.
2. **Implémenter** : OAuth Authorization Code Flow, stockage du refresh token, un client API qui gère le rafraîchissement et le rate-limiting (429 + `Retry-After`).
3. **Données** : `client_id`, `client_secret`, scopes (`playlist-read-private`, `user-library-read`, `playlist-modify-private`).
4. **Choix techniques** : `spotipy` (Python) gère OAuth + retries tout seul. FastAPI pour le callback.
5. **Résultat** : un appel à `/me` retourne ton profil.
6. **Vérifications** : token rafraîchi automatiquement après expiration ; un 429 est géré sans crash.
7. **Risques** : redirect URI mal configurée (cause n°1 d'échec OAuth).
8. **Version minimale** : token en dur dans un `.env`, rafraîchi à la main.

---

### Étape 1 — Import de la bibliothèque

1. **Objectif** : récupérer tous tes morceaux en local.
2. **Implémenter** : pagination sur `/me/tracks` et `/me/playlists` + `/playlists/{id}/tracks` ; déduplication par **ID Spotify** puis par **ISRC** (l'ISRC attrape les doublons remaster/édition).
3. **Données** : track id, ISRC, titre, artiste(s) + leurs ids, album, année, popularité, durée.
4. **Choix techniques** : enrichis les genres via `/artists?ids=` (Spotify ne met les genres que sur l'artiste, pas le track) ; batch par 50.
5. **Résultat** : table `tracks` peuplée.
6. **Vérifications** : nombre de morceaux cohérent ; pas de doublon évident ; genres présents sur la majorité.
7. **Risques** : titres locaux / non disponibles sans ISRC → à marquer, pas à bloquer.
8. **Version minimale** : juste les liked songs, sans les playlists.

---

### Étape 2 — Enrichissement texte (Last.fm + tags LLM)

1. **Objectif** : donner à chaque morceau une description de mood riche.
2. **Implémenter** : pour chaque track, appeler Last.fm `track.getTopTags` (fallback `artist.getTopTags`) ; puis générer 5-10 tags mood via un LLM à partir de `(titre, artiste, genres, tags Last.fm)`.
3. **Données** : tags Last.fm (avec poids), tags LLM.
4. **Choix techniques** : **batch le LLM** (20-50 morceaux par appel, sortie JSON) pour le coût ; cache agressif en DB — un morceau enrichi ne se ré-enrichit jamais.
5. **Résultat** : colonnes `lastfm_tags`, `llm_tags` remplies.
6. **Vérifications** : sur 20 morceaux connus, les tags sont plausibles (pas d'hallucination de genre).
7. **Risques** : coût/latence LLM ; rate limit Last.fm (~5 req/s → throttle).
8. **Version minimale** : Last.fm seul, sans LLM.

---

### Étape 3 — Embeddings & moteur de similarité

1. **Objectif** : le cœur — classer la bibliothèque par proximité à des références.
2. **Implémenter** : construire la phrase descriptive par track → embedding → stocker le vecteur. Fonction `find_similar(refs)` = moyenne (centroïde) des vecteurs de référence, puis cosinus contre tous les autres, tri décroissant.
3. **Données** : un vecteur (≈384 ou 1536 dims) par morceau.
4. **Choix techniques** : `sentence-transformers` local (gratuit, suffisant) ; numpy en mémoire ; stocker les vecteurs en blob ou `.npy`.
5. **Résultat** : top-N morceaux proches d'une sélection.
6. **Vérifications** : **le test qui décide tout** — donne 10 morceaux "tristes", regarde le top 30. Si c'est cohérent, ton MVP marche.
7. **Risques** : embeddings trop dominés par le genre et pas assez par le mood → ajuster la phrase (pondérer les tags mood).
8. **Version minimale** : centroïde + cosinus, sans pondération.

---

### Étape 4 — Création de playlist Spotify

1. **Objectif** : boucler la valeur — sortir une vraie playlist.
2. **Implémenter** : `POST /users/{id}/playlists` puis `POST /playlists/{id}/tracks` (batch 100) à partir de ta sélection validée.
3. **Données** : liste d'URIs validées.
4. **Choix techniques** : playlist privée, nom auto (`Mood: night drive — 2026-06-20`).
5. **Résultat** : playlist visible dans ton Spotify. **Fin du MVP — c'est déjà utilisable au quotidien.**
6. **Vérifications** : ordre et contenu corrects.
7. **Risques** : morceaux non disponibles dans ta région.
8. **Version minimale** : créer la playlist, ajout manuel des tracks.

---

### Étape 5 — Validation utilisateur (accept/refuse)

1. **Objectif** : transformer un classement en sélection affinée.
2. **Implémenter** : UI minimale (liste proposée, boutons ✓/✗) ; stocker le feedback par mood.
3. **Choix techniques** : maintenant une vraie UI vaut le coup — React, ou plus simple Streamlit/Gradio pour rester en Python.
4. **Résultat** : tu construis une playlist en quelques clics.
5. **Vérifications** : le feedback persiste et est rattaché au bon mood.
6. **Risques** : sur-ingénierie de l'UI — reste minimal.
7. **Version minimale** : tableur CSV où tu mets ✓/✗.

---

### Étape 6 — Apprentissage du feedback (profils de mood)

1. **Objectif** : chaque mood devient un profil vectoriel personnel qui s'améliore.
2. **Implémenter** : profil = centroïde des ✓ **moins** une fraction du centroïde des ✗ (Rocchio). Optionnel : petit classifieur logistique par mood quand tu as assez de feedback.
3. **Données** : historique accept/refuse par mood.
4. **Choix techniques** : Rocchio d'abord (3 lignes, robuste) ; régression logistique seulement si Rocchio plafonne.
5. **Résultat** : les propositions s'améliorent à chaque session.
6. **Vérifications** : un mood entraîné bat la sélection brute de l'étape 3 sur un échantillon test.
7. **Risques** : sur-apprentissage avec peu de feedback → garder l'influence des ✗ faible.
8. **Version minimale** : recalcul du centroïde avec seulement les ✓.

---

### Étape 7 (optionnelle) — Clustering exploratoire

1. **Objectif** : découvrir des moods que tu n'avais pas nommés.
2. **Implémenter** : UMAP (réduction 2D) + HDBSCAN sur les embeddings ; visualisation ; tu nommes les clusters intéressants.
3. **Choix techniques** : HDBSCAN (pas besoin de fixer le nombre de clusters, gère le bruit) > KMeans.
4. **Résultat** : carte de ta bibliothèque, clusters comme points de départ de nouveaux moods.
5. **Risques** : clusters ininterprétables — c'est exploratoire, pas critique.
6. **Version minimale** : KMeans + liste des morceaux par cluster.

---

### Étape 8 (optionnelle) — Audio réel

À n'ouvrir **que si** le texte ne suffit pas à distinguer certains moods (typiquement "énergique" vs "calme" pour un même artiste). Options par ordre de difficulté : tags Last.fm de tempo → lookup AcousticBrainz/MusicBrainz via ISRC → analyse `librosa`/Essentia sur **tes propres fichiers légaux** uniquement. Jamais de téléchargement non autorisé.

## 6. Architecture technique proposée

```
┌─────────────┐   OAuth    ┌──────────────────────────┐
│  Spotify    │◄──────────►│  FastAPI (Python)        │
│  Web API    │            │                          │
└─────────────┘            │  • import job            │
┌─────────────┐            │  • enrichment pipeline   │
│  Last.fm    │◄──────────►│  • embedding service     │
└─────────────┘            │  • similarity engine     │
┌─────────────┐            │  • feedback / profils    │
│  LLM API    │◄──────────►│                          │
└─────────────┘            └────────┬─────────────────┘
                                    │
                            ┌───────▼────────┐   ┌──────────────┐
                            │  SQLite        │   │ UI (Streamlit│
                            │  + vecteurs    │   │  puis React) │
                            └────────────────┘   └──────────────┘
```

Principe directeur : **pipeline en étapes idempotentes et caché**. Import → enrich → embed → score sont des passes séparées, chacune sautant ce qui est déjà fait. Tu peux relancer n'importe quelle étape sans tout recalculer, ce qui est vital quand l'enrichissement coûte du temps et de l'argent.

## 7. Modèle de données initial

```sql
tracks(
  id PK, spotify_id, isrc, title, artist, artist_id,
  album, year, popularity, duration_ms,
  genres,            -- JSON, depuis l'artiste
  lastfm_tags,       -- JSON [{tag, weight}]
  llm_tags,          -- JSON ["sad","night drive",...]
  embed_text,        -- la phrase descriptive construite
  embedding,         -- BLOB / ref .npy
  enriched_at, embedded_at
)

moods(id PK, name, description, profile_vector BLOB, updated_at)

feedback(id PK, mood_id FK, track_id FK, decision, created_at)
-- decision ∈ {accept, reject}
```

## 8. Stratégie d'enrichissement des morceaux

Ordre par ROI décroissant : **(1) genres Spotify** quasi gratuits → **(2) tags Last.fm** gratuits, stables, très "mood" → **(3) tags LLM** pour combler les trous et homogénéiser le vocabulaire mood → **(4) lyrics** seulement si tu vises des moods lexicaux ("à chanter", "très émotionnelles") → **(5) audio** en dernier recours.

Règles : cache tout en DB, n'enrichis jamais deux fois, batch les appels LLM, throttle Last.fm, et traite chaque source comme **best-effort** (un morceau sans tags Last.fm doit quand même avoir un embedding via ses métadonnées).

## 9. Stratégie de similarité / clustering

- **MVP** : centroïde des références + cosinus. Simple, interprétable, sans entraînement. Suffit dans 80 % des cas.
- **Intermédiaire** : clustering HDBSCAN pour explorer, pas pour recommander.
- **Avancé** : profil de mood appris par Rocchio (centroïde ✓ − λ·centroïde ✗), puis éventuellement logistic regression par mood.

Avantages/inconvénients : le **centroïde** est instantané et transparent mais ne capte pas un mood "multimodal" (deux sous-styles dans le même mood) — dans ce cas, garde les k plus proches de **chaque** référence plutôt que du centroïde. Le **clustering** révèle des structures mais ne répond pas directement à "trouve-moi des morceaux comme ceux-ci". L'**apprentissage par feedback** colle le mieux à ton goût mais demande des données et risque le sur-apprentissage si tu pousses trop tôt.

## 10. Stratégie lyrics

Reste prudent : récupérer des paroles complètes via scraping viole souvent les ToS (Genius, Musixmatch) et c'est fragile. Pour le MVP, **ignore les lyrics**. En phase 2, si tu y tiens : utilise une API officielle quand elle existe, et n'extrais que des **features dérivées** (langue, émotion dominante, thèmes, "chantabilité") via LLM plutôt que de stocker le texte intégral — tu obtiens le signal utile sans reproduire l'œuvre.

## 11. Stratégie de validation utilisateur

Trois niveaux : (a) **passive** — tu acceptes/refuses dans la liste proposée ; (b) **persistée** — chaque décision est rattachée à un mood ; (c) **active** — le système re-propose en évitant ce que tu as déjà refusé. Garde l'UI minimale au début (Streamlit/Gradio génèrent une interface ✓/✗ en quelques dizaines de lignes), passe à React seulement si l'usage s'installe.

## 12. Évolution vers une version plus avancée

Dans l'ordre, une fois le MVP éprouvé : profils Rocchio → re-ranking par feedback → clustering exploratoire → enrichissement audio sélectif → multi-vecteurs (un embedding texte + un embedding audio concaténés ou pondérés) → éventuellement classifieur par mood. **Ne saute jamais une marche** : chaque ajout doit prouver qu'il bat la version précédente sur un échantillon test, sinon il ne reste pas.

## 13. Risques techniques

Le principal est la **dépendance aux audio features Spotify** — neutralisé en ne s'en servant pas. Ensuite : instabilité du scraping lyrics (→ évité au MVP), coût/latence LLM (→ batch + cache), rate limits Spotify et Last.fm (→ backoff), **embeddings dominés par le genre** plutôt que le mood (→ pondérer les tags mood dans la phrase), et le piège classique de la **sur-ingénierie ML précoce** (→ centroïde + cosinus avant tout le reste).

## 14. Ordre exact d'implémentation

0 Auth → 1 Import → 2 Enrichissement (Last.fm puis LLM) → 3 Embeddings + similarité → 4 Création playlist **[MVP fini, utilisable]** → 5 Validation ✓/✗ → 6 Profils appris (Rocchio) → 7 Clustering *(optionnel)* → 8 Audio *(optionnel)*.

## 15. Critères de réussite par étape

| Étape | Critère de réussite |
|---|---|
| 0 Auth | `/me` répond, token auto-rafraîchi |
| 1 Import | bibliothèque complète, dédupliquée par ISRC, genres présents |
| 2 Enrichissement | tags plausibles sur 20 morceaux vérifiés à la main |
| 3 Similarité | top-30 cohérent pour 10 références d'un même mood |
| 4 Playlist | playlist correcte créée dans Spotify |
| 5 Validation | sélection en quelques clics, feedback persisté |
| 6 Profils | mood entraîné > sélection brute sur échantillon test |
| 7 Clustering | au moins un cluster nommable et utile |
| 8 Audio | sépare deux moods que le texte confondait |

---

Le point que je veux vraiment souligner : **ton MVP s'arrête à l'étape 4 et il est déjà bon.** Tout le reste est de l'amélioration marginale. La seule étape qui peut invalider l'approche est la 3 — si la similarité texte ne "sent" pas le mood, tout le reste est inutile. Donc dès que tu as importé ne serait-ce que 200 morceaux enrichis, fais le test de l'étape 3 avant de coder quoi que ce soit d'autre. C'est ton go/no-go.

Veux-tu que je détaille en code une étape précise (l'OAuth, le pipeline d'enrichissement, ou le moteur de similarité) pour démarrer ?