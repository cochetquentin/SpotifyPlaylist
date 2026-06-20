## 1. Résumé du projet

Tu veux construire une application qui transforme ta bibliothèque Spotify en playlists très précises par **mood**, **contexte d’écoute** et **proximité avec quelques morceaux de référence**. Le cœur du système n’est pas “créer des playlists Spotify”, mais **représenter chaque chanson sous forme de vecteur + tags + signaux personnels**, puis classer les morceaux selon ce que tu recherches.

Point important : en 2026, il ne faut pas bâtir le projet sur les anciennes Spotify Audio Features. L’endpoint `Get Track's Audio Features` est marqué “Deprecated”, même si la documentation liste encore `danceability`, `energy`, `valence`, `tempo`, etc. ([Spotify for Developers][1]) Spotify indique aussi que son contenu ne doit pas être téléchargé, ni utilisé pour entraîner ou ingérer dans un modèle ML/AI ; l’approche prudente est donc d’utiliser Spotify comme **source d’inventaire et d’export**, puis d’enrichir les morceaux via sources externes, données personnelles, lyrics licenciées ou audio légalement disponible. ([Spotify for Developers][2])

---

## 2. Hypothèses techniques

Hypothèses réalistes pour démarrer :

| Sujet                 | Hypothèse recommandée                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------- |
| Usage initial         | Application personnelle, non commerciale                                                 |
| Nombre de morceaux    | Quelques milliers à quelques dizaines de milliers                                        |
| Source principale     | Spotify pour importer playlists, morceaux, albums, artistes, ISRC si disponible          |
| Intelligence musicale | Construite hors Spotify Audio Features                                                   |
| Audio brut            | Uniquement previews autorisées, fichiers locaux que tu possèdes, ou API tierce autorisée |
| Lyrics                | Optionnelles au début, car juridiquement et techniquement plus fragiles                  |
| ML                    | D’abord scoring simple, puis embeddings, puis feedback personnel                         |
| Export                | Création ou mise à jour de playlists Spotify à la fin du MVP                             |

Spotify Development Mode est devenu plus limité : Premium requis, un Client ID par développeur, cinq utilisateurs autorisés, et accès réduit à certains endpoints. Spotify précise aussi que Development Mode ne doit pas être une base pour scaler un business. ([Spotify for Developers][3]) Pour ton cas personnel, c’est acceptable, mais il faut éviter toute architecture dépendante d’endpoints instables.

---

## 3. Sources de données possibles

| Source                 |                                                                      Utilité |             Facilité |                         Risque | À utiliser quand              |
| ---------------------- | ---------------------------------------------------------------------------: | -------------------: | -----------------------------: | ----------------------------- |
| Spotify API            |   Inventaire, playlists, IDs, artistes, albums, durée, ISRC, export playlist |               Élevée |         Restrictions API / ToS | Dès le MVP                    |
| Spotify Audio Features |                                         Tempo, valence, energy, danceability |    Faible maintenant |                       Déprécié | Ne pas dépendre dessus        |
| Spotify preview_url    |                                                                  Preview 30s |               Faible |           Nullable, deprecated | À ignorer au départ           |
| MusicBrainz            | Métadonnées ouvertes, MBID, ISRC, relations, tags/genres selon disponibilité |              Moyenne |             Matching imparfait | Étape d’enrichissement        |
| Last.fm                |                                     Tags communautaires, playcount, top tags |              Moyenne |                   Tags bruités | Très utile pour mood/style    |
| ListenBrainz           |                          Écosystème MusicBrainz, métadonnées/recommandations |              Moyenne |            Couverture variable | Plus tard                     |
| LRCLIB                 |                     Lyrics synchronisées ou plain lyrics selon disponibilité |              Moyenne |   Vérifier conditions / droits | Expérimental                  |
| Musixmatch / LyricFind |                                               Lyrics plus fiables/licenciées |  Moyenne à difficile |         Souvent payant/licence | Si tu veux un produit sérieux |
| Librosa                |                      BPM, chroma, MFCC, spectral features depuis audio légal |              Moyenne |             Besoin audio légal | Plus tard                     |
| Essentia               |                               Modèles audio open source, tagging, mood/genre |              Moyenne | Licence des modèles à vérifier | V2 audio                      |
| Cyanite / Soundcharts  |                                             Features audio/mood commerciales | Élevée techniquement |          Coût / dépendance API | Si tu veux gagner du temps    |

MusicBrainz fournit une API REST en XML/JSON pour récupérer des métadonnées musicales. ([MusicBrainz][4]) Last.fm `track.getInfo` permet de récupérer des métadonnées par artiste/titre ou MBID, avec `toptags` dans la réponse. ([Last.fm][5]) AcousticBrainz, qui fournissait des caractéristiques acoustiques communautaires, a fonctionné de 2015 à 2022 et doit être considéré comme une source historique, pas comme une dépendance active. ([AcousticBrainz][6])

---

## 4. MVP recommandé

Le MVP ne doit pas essayer d’analyser parfaitement la musique. Il doit répondre à une seule question :

> “Je choisis 5 à 15 morceaux de référence, et l’application me propose les 50 morceaux les plus proches dans ma bibliothèque.”

### MVP fonctionnel minimal

Fonctions :

1. Connexion Spotify.
2. Import des playlists personnelles et morceaux sauvegardés.
3. Normalisation et dédoublonnage.
4. Ajout de tags manuels simples : `sad`, `night`, `drive`, `sing-along`, `calm`, `energetic`, etc.
5. Enrichissement léger via Last.fm / MusicBrainz.
6. Création d’un texte descriptif par morceau.
7. Embedding de ce texte descriptif.
8. Similarité entre les morceaux de référence et toute la bibliothèque.
9. UI pour accepter/refuser les suggestions.
10. Export vers playlist Spotify.

À ne pas mettre dans le MVP : audio ML avancé, clustering automatique complexe, lyrics obligatoires, apprentissage personnalisé profond, modèles audio lourds.

---

## 5. Roadmap étape par étape

### Étape 0 — Cadrage légal et technique

| Élément                     | Détail                                                                                                 |
| --------------------------- | ------------------------------------------------------------------------------------------------------ |
| Objectif                    | Éviter une architecture illégale ou fragile.                                                           |
| À implémenter               | Document interne : quelles données sont stockées, d’où elles viennent, ce qu’on a le droit d’en faire. |
| Données nécessaires         | Spotify Developer Policy, docs API, conditions des APIs externes.                                      |
| Choix techniques            | Fichier `DATA_SOURCES.md` + table `data_source` en DB.                                                 |
| Résultat attendu            | Tu sais quelles features sont “safe”, “expérimentales”, “interdites/à éviter”.                         |
| Vérifications               | Ne jamais télécharger de contenu Spotify ; ne pas entraîner de modèle avec Spotify Content.            |
| Risques                     | Spotify change encore ses endpoints ; ambiguïté autour des embeddings de métadonnées Spotify.          |
| Version minimale acceptable | Une page de règles claires avant de coder l’enrichissement.                                            |

Spotify précise que le contenu Spotify ne peut pas être téléchargé, que les previews ne peuvent pas être un produit autonome, et que le contenu Spotify ne doit pas être utilisé pour entraîner ou ingérer dans un modèle ML/AI. ([Spotify for Developers][2])

---

### Étape 1 — Connexion Spotify et import brut

| Élément             | Détail                                                                                                                           |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Objectif            | Récupérer ta bibliothèque.                                                                                                       |
| À implémenter       | OAuth Spotify, import playlists, playlist items, saved tracks, albums/artists associés.                                          |
| Données nécessaires | `spotify_track_id`, `spotify_uri`, titre, artistes, album, durée, date de sortie, explicit, ISRC si disponible, playlist source. |
| Choix techniques    | Backend TypeScript ou Python ; job async ; pagination ; stockage brut JSON.                                                      |
| Résultat attendu    | Toutes tes musiques Spotify sont visibles dans l’app.                                                                            |
| Vérifications       | Nombre de tracks importées = nombre attendu ; gestion des tracks nulles ; refresh token OK.                                      |
| Risques             | Certaines playlists non possédées/collaboratives peuvent ne pas exposer leur contenu selon les nouvelles règles.                 |
| VMA                 | Importer au moins tes playlists personnelles + morceaux sauvegardés.                                                             |

L’endpoint `Get Current User's Playlists` retourne des résultats paginés, et les playlists ont un champ `items` pointant vers les morceaux. ([Spotify for Developers][7]) Le nouvel endpoint `GET /playlists/{id}/items` est prévu pour récupérer le contenu d’une playlist, mais il est limité aux playlists possédées par l’utilisateur ou où il est collaborateur. ([Spotify for Developers][8])

---

### Étape 2 — Normalisation et dédoublonnage

| Élément             | Détail                                                                                                              |
| ------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Objectif            | Éviter les doublons entre single, album, remaster, compilation.                                                     |
| À implémenter       | Table canonique `tracks`, table `track_sources`, matching par Spotify ID, ISRC, titre normalisé + artistes + durée. |
| Données nécessaires | Spotify ID, ISRC, titre, artistes, durée, album, release date.                                                      |
| Choix techniques    | Règles simples + score de confiance ; pas de ML au début.                                                           |
| Résultat attendu    | Une chanson = une entité canonique, même si elle apparaît dans plusieurs playlists.                                 |
| Vérifications       | Les doublons évidents sont fusionnés ; les versions live/remix restent séparées si nécessaire.                      |
| Risques             | Mauvaise fusion entre version originale, live, remaster ou cover.                                                   |
| VMA                 | Déduplication par Spotify ID + ISRC uniquement.                                                                     |

---

### Étape 3 — Interface de sélection de références

| Élément             | Détail                                                                                  |
| ------------------- | --------------------------------------------------------------------------------------- |
| Objectif            | Pouvoir choisir 5 à 15 morceaux qui définissent un mood.                                |
| À implémenter       | Recherche dans ta bibliothèque, sélection multi-morceaux, création d’un “mood profile”. |
| Données nécessaires | Track canonique, playlist source, favoris utilisateur.                                  |
| Choix techniques    | Frontend simple : Next.js, React, table filtrable.                                      |
| Résultat attendu    | Tu peux créer “night drive”, “sad walk”, “karaoke”, etc. à partir de morceaux exemples. |
| Vérifications       | Tu peux sauvegarder, modifier, supprimer un profil.                                     |
| Risques             | UX trop lourde si recherche lente.                                                      |
| VMA                 | Liste de tracks + checkbox + bouton “Créer profil”.                                     |

---

### Étape 4 — Tags manuels et scoring simple

| Élément             | Détail                                                                                     |
| ------------------- | ------------------------------------------------------------------------------------------ |
| Objectif            | Obtenir une première recommandation sans lyrics ni audio.                                  |
| À implémenter       | Tags utilisateur sur morceaux et moods ; scoring par recouvrement de tags.                 |
| Données nécessaires | Tags manuels, playlists d’origine, artistes, années.                                       |
| Choix techniques    | Score pondéré : tags communs, mêmes artistes, même playlist source, proximité année/durée. |
| Résultat attendu    | Premières playlists plausibles, même si imparfaites.                                       |
| Vérifications       | Sur 20 recommandations, au moins 6 à 10 semblent cohérentes.                               |
| Risques             | Trop dépendant de tes tags manuels.                                                        |
| VMA                 | Score basé sur tags + appartenance aux mêmes playlists.                                    |

Exemple simple :

```text
score = 0.45 * tag_overlap
      + 0.20 * same_source_playlist
      + 0.15 * artist_similarity
      + 0.10 * year_similarity
      + 0.10 * user_favorite_boost
```

---

### Étape 5 — Enrichissement externe léger

| Élément             | Détail                                                                                                    |
| ------------------- | --------------------------------------------------------------------------------------------------------- |
| Objectif            | Ajouter des tags de style/mood sans audio.                                                                |
| À implémenter       | Matching MusicBrainz / Last.fm ; stockage des tags externes avec source et confiance.                     |
| Données nécessaires | Artiste, titre, ISRC, MBID si trouvé.                                                                     |
| Choix techniques    | Job async ; cache ; retries ; matching conservateur.                                                      |
| Résultat attendu    | Beaucoup de morceaux ont des tags comme `pop`, `indie`, `j-rock`, `melancholic`, `female vocalists`, etc. |
| Vérifications       | Taux de matching ; taux de faux positifs ; inspection de 50 morceaux.                                     |
| Risques             | Tags communautaires bruités, incohérents ou trop génériques.                                              |
| VMA                 | Last.fm tags sur les morceaux les plus connus.                                                            |

Last.fm peut retourner des `toptags` pour un morceau, ce qui est très utile pour un système de mood même si les tags sont communautaires et parfois bruités. ([Last.fm][5])

---

### Étape 6 — Embeddings textuels

| Élément             | Détail                                                                                                       |
| ------------------- | ------------------------------------------------------------------------------------------------------------ |
| Objectif            | Passer de tags rigides à une similarité sémantique.                                                          |
| À implémenter       | Générer un texte descriptif par morceau, puis créer un embedding.                                            |
| Données nécessaires | Tags utilisateur, tags externes autorisés, artistes, genres externes, éventuellement résumé lyrics.          |
| Choix techniques    | `pgvector`, Qdrant, Weaviate, Pinecone ; modèle embedding local ou API.                                      |
| Résultat attendu    | Similarité plus souple : “sad night drive” trouve aussi “melancholic synthpop”, pas seulement `sad`.         |
| Vérifications       | Comparer recommandations scoring simple vs embeddings.                                                       |
| Risques             | Attention aux ToS : ne pas ingérer du contenu Spotify dans un modèle si tu veux rester strictement conforme. |
| VMA                 | Embedding uniquement sur tags manuels + tags externes non Spotify.                                           |

Texte descriptif exemple :

```text
Track tags: melancholic, night, synthpop, female vocal, slow tempo.
User tags: sad walk, emotional, late night.
External tags: dream pop, indie pop, electronic.
```

---

### Étape 7 — Similarité par morceaux de référence

| Élément             | Détail                                                                                                           |
| ------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Objectif            | Répondre au cas principal : “voici 10 morceaux, trouve les plus proches”.                                        |
| À implémenter       | Calcul du centroïde vectoriel des morceaux sélectionnés ; ranking par cosine similarity ; filtres anti-doublons. |
| Données nécessaires | Embeddings de tracks, mood profile, exclusions.                                                                  |
| Choix techniques    | Moyenne vectorielle simple ; pondération par morceau préféré ; hybrid score tags + embedding.                    |
| Résultat attendu    | Liste classée de 50 à 200 morceaux candidats.                                                                    |
| Vérifications       | Tester 5 moods réels : triste, marche, voiture, chanter, nuit.                                                   |
| Risques             | Le centroïde écrase les nuances si les morceaux de référence sont trop variés.                                   |
| VMA                 | Moyenne des embeddings + cosine similarity.                                                                      |

Score recommandé pour V1 :

```text
final_score =
  0.60 * embedding_similarity
+ 0.25 * tag_score
+ 0.10 * user_history_score
+ 0.05 * diversity_score
```

---

### Étape 8 — UI de validation

| Élément             | Détail                                                                                                           |
| ------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Objectif            | Transformer le système en outil personnel, pas en algo générique.                                                |
| À implémenter       | Boutons : accepter, refuser, “trop calme”, “trop énergique”, “bon style mauvais mood”, “bon mood mauvais style”. |
| Données nécessaires | Feedback par track et par mood profile.                                                                          |
| Choix techniques    | Table `recommendation_feedback`; recalcul périodique du profil.                                                  |
| Résultat attendu    | Le système apprend tes goûts spécifiques.                                                                        |
| Vérifications       | Après 20 feedbacks, les recommandations suivantes s’améliorent.                                                  |
| Risques             | Trop peu de feedback pour apprendre correctement.                                                                |
| VMA                 | `accepted` / `rejected` seulement.                                                                               |

---

### Étape 9 — Export Spotify

| Élément             | Détail                                                                 |
| ------------------- | ---------------------------------------------------------------------- |
| Objectif            | Créer une vraie playlist Spotify depuis les recommandations.           |
| À implémenter       | Création playlist, ajout de tracks, update si playlist déjà existante. |
| Données nécessaires | `spotify_uri`, playlist target, ordre des morceaux.                    |
| Choix techniques    | Export manuel validé, pas automatique au début.                        |
| Résultat attendu    | Playlist utilisable directement dans Spotify.                          |
| Vérifications       | Les 30 à 100 morceaux exportés correspondent à la preview UI.          |
| Risques             | Duplicats, playlists écrasées par erreur, scopes Spotify.              |
| VMA                 | Créer une nouvelle playlist à chaque export.                           |

Les endpoints actuels incluent `POST /me/playlists` pour créer une playlist et `POST /playlists/{id}/items` pour ajouter des éléments. ([Spotify for Developers][9])

---

### Étape 10 — Lyrics optionnelles

| Élément             | Détail                                                                                   |
| ------------------- | ---------------------------------------------------------------------------------------- |
| Objectif            | Améliorer les moods émotionnels : triste, nostalgique, romantique, colère, introspectif. |
| À implémenter       | Matching lyrics, résumé émotionnel, langue, thèmes, score sing-along.                    |
| Données nécessaires | Lyrics plain ou synchronisées, source, licence/conditions.                               |
| Choix techniques    | LRCLIB pour expérimentation ; fournisseur licencié si produit public.                    |
| Résultat attendu    | Meilleure détection des morceaux émotionnels et à chanter.                               |
| Vérifications       | Taux de lyrics trouvées ; qualité de langue ; erreurs de matching.                       |
| Risques             | Copyright, disponibilité, paroles incorrectes, coût.                                     |
| VMA                 | Ne pas stocker les lyrics complets ; stocker seulement tags dérivés si autorisé.         |

LRCLIB permet de chercher des lyrics avec une signature précise du morceau — titre, artiste, album, durée — et des wrappers existent pour récupérer lyrics synchronisées ou non synchronisées. ([LRCLIB][10]) Pour une application publique, il faudra préférer une source explicitement licenciée.

---

### Étape 11 — Features audio légales

| Élément             | Détail                                                                          |
| ------------------- | ------------------------------------------------------------------------------- |
| Objectif            | Ajouter tempo, énergie, densité, intensité, voix/instrumental, mood audio.      |
| À implémenter       | Pipeline audio seulement pour fichiers locaux possédés ou API tierce autorisée. |
| Données nécessaires | Audio légal, ou identifiants acceptés par fournisseur externe.                  |
| Choix techniques    | Librosa, Essentia, Cyanite, Soundcharts.                                        |
| Résultat attendu    | Meilleur tri pour conduite, marche, sport, calme, nuit.                         |
| Vérifications       | Comparer BPM/énergie estimés avec perception humaine.                           |
| Risques             | Accès audio, coût API, licence modèles.                                         |
| VMA                 | Aucun audio au MVP ; ajouter uniquement plus tard.                              |

Librosa permet d’extraire des features rythmiques comme tempo, tempogram et spectral rhythm patterns depuis un signal audio. ([Librosa][11]) Essentia fournit des modèles pré-entraînés pour des tâches d’analyse audio, mais certains modèles MTG sont sous licence CC BY-NC-SA 4.0 ou licence propriétaire sur demande, donc il faut vérifier la licence selon ton usage. ([Essentia][12]) Cyanite expose des classifieurs BPM, key, mood et genre ; Soundcharts propose aussi des audio features comme energy, valence, danceability, acousticness, instrumentalness, tempo et key. ([Cyanite.ai][13])

---

### Étape 12 — Clustering et visualisation

| Élément             | Détail                                                                                        |
| ------------------- | --------------------------------------------------------------------------------------------- |
| Objectif            | Explorer automatiquement les familles de ta bibliothèque.                                     |
| À implémenter       | Clustering sur embeddings ; visualisation 2D ; renommage manuel des clusters.                 |
| Données nécessaires | Embeddings, tags, feedback.                                                                   |
| Choix techniques    | UMAP + HDBSCAN ; ou KMeans si tu veux nombre fixe de groupes.                                 |
| Résultat attendu    | Découverte de groupes : “sad indie night”, “energetic driving rock”, “soft Japanese ballads”. |
| Vérifications       | Les clusters sont interprétables humainement.                                                 |
| Risques             | Clusters trop abstraits ou instables.                                                         |
| VMA                 | UMAP 2D + sélection manuelle de groupes.                                                      |

---

### Étape 13 — Apprentissage par feedback

| Élément             | Détail                                                                                       |
| ------------------- | -------------------------------------------------------------------------------------------- |
| Objectif            | Chaque mood devient personnel.                                                               |
| À implémenter       | Profil vectoriel positif/négatif ; pondération des features ; réentraînement léger par mood. |
| Données nécessaires | Accept/refuse, raisons de refus, historique d’exports.                                       |
| Choix techniques    | Rocchio feedback, logistic regression, learning-to-rank simple.                              |
| Résultat attendu    | “Night drive” devient ton “night drive”, pas une définition générique.                       |
| Vérifications       | Taux d’acceptation augmente au fil des sessions.                                             |
| Risques             | Surapprentissage si peu de feedback.                                                         |
| VMA                 | Profil positif = moyenne des acceptés ; profil négatif = moyenne des refusés.                |

Formule simple :

```text
mood_vector =
  mean(seed_tracks)
+ 0.7 * mean(accepted_tracks)
- 0.4 * mean(rejected_tracks)
```

---

## 6. Architecture technique proposée

### Architecture simple au départ

```text
Frontend Next.js
   |
Backend API FastAPI ou NestJS
   |
PostgreSQL + pgvector
   |
Jobs async Python
   |
Spotify API / Last.fm / MusicBrainz / Lyrics provider / Audio provider
```

### Modules

| Module                  | Rôle                                                   |
| ----------------------- | ------------------------------------------------------ |
| `spotify-importer`      | OAuth, import playlists, saved tracks, artistes/albums |
| `normalizer`            | Dédoublonnage, canonical track                         |
| `enrichment-worker`     | MusicBrainz, Last.fm, lyrics, audio features           |
| `feature-builder`       | Transforme tags/métadonnées en features exploitables   |
| `embedding-service`     | Génère et stocke les embeddings                        |
| `recommendation-engine` | Similarité, scoring, filtres, diversification          |
| `feedback-service`      | Stocke accept/refuse et ajuste les profils             |
| `playlist-exporter`     | Crée ou met à jour une playlist Spotify                |

### Stack recommandée

| Couche      | Choix simple                        | Alternative                           |
| ----------- | ----------------------------------- | ------------------------------------- |
| Frontend    | Next.js + Tailwind                  | React simple                          |
| Backend     | FastAPI Python                      | NestJS TypeScript                     |
| DB          | PostgreSQL + pgvector               | SQLite au prototype, Qdrant plus tard |
| Jobs        | Celery/RQ/Arq                       | BullMQ si backend TS                  |
| Auth        | Spotify OAuth + session app         | Supabase Auth                         |
| Embeddings  | OpenAI / local sentence-transformer | E5, BGE, MiniLM                       |
| Audio       | Aucun au MVP                        | Librosa / Essentia / API commerciale  |
| Déploiement | Docker Compose                      | Fly.io / Render / Railway             |

---

## 7. Modèle de données initial

### Tables principales

```sql
users
- id
- spotify_user_id
- created_at

spotify_tokens
- user_id
- access_token_encrypted
- refresh_token_encrypted
- expires_at

tracks
- id
- canonical_title
- canonical_artist
- duration_ms
- isrc
- release_year
- explicit
- created_at

track_sources
- id
- track_id
- source              -- spotify, musicbrainz, lastfm, lrclib, manual
- source_track_id
- source_payload_json
- confidence

spotify_tracks
- track_id
- spotify_track_id
- spotify_uri
- spotify_url
- album_name
- artist_names_json
- raw_json

playlists
- id
- spotify_playlist_id
- name
- owner_type
- imported_at

playlist_tracks
- playlist_id
- track_id
- position
- added_at

track_tags
- id
- track_id
- tag
- source              -- manual, lastfm, lyrics_summary, audio_model
- confidence
- created_at

track_features
- track_id
- feature_json
- source
- version

track_embeddings
- track_id
- embedding_model
- embedding_vector
- input_hash
- created_at

mood_profiles
- id
- user_id
- name
- description
- created_at

mood_profile_seeds
- mood_profile_id
- track_id
- weight

recommendation_runs
- id
- mood_profile_id
- params_json
- created_at

recommendation_items
- run_id
- track_id
- score
- rank
- explanation_json

recommendation_feedback
- mood_profile_id
- track_id
- feedback          -- accepted, rejected, neutral
- reason
- created_at
```

### Pourquoi ce modèle est bon

Il sépare :

* la chanson canonique ;
* les sources externes ;
* les tags ;
* les features ;
* les embeddings ;
* le feedback utilisateur.

Donc tu peux changer de fournisseur lyrics ou audio sans casser tout le système.

---

## 8. Stratégie d’enrichissement des morceaux

### Priorité des features

| Feature              |                          Utilité |            Facilité |          Priorité |
| -------------------- | -------------------------------: | ------------------: | ----------------: |
| Playlists d’origine  |        Très utile pour tes goûts |         Très facile |               MVP |
| Tags manuels         |                       Très utile |              Facile |               MVP |
| Last.fm top tags     |                            Utile |               Moyen |              MVP+ |
| MusicBrainz metadata |              Utile pour matching |               Moyen |              MVP+ |
| Année / décennie     |             Utile pour nostalgie |              Facile |               MVP |
| Durée                |         Utile pour ambiance/fond |              Facile |               MVP |
| Lyrics themes        |          Très utile pour émotion |     Moyen/difficile |                V2 |
| Langue des lyrics    |                 Utile pour chant |               Moyen |                V2 |
| BPM                  |      Utile marche/conduite/sport |               Moyen |                V2 |
| Énergie audio        |                       Très utile |  Difficile sans API |             V2/V3 |
| Key / mode           |                Moyennement utile |               Moyen |         Plus tard |
| MFCC / chroma bruts  |    Peu interprétable directement |           Difficile | À éviter au début |
| Cover image          |                   Faible utilité |  Facile mais bruité |           Ignorer |
| Spotify popularity   | Instable/déprécié selon contexte | Facile mais fragile |    Ignorer au MVP |

### Représentation recommandée d’une chanson

Chaque chanson doit avoir trois niveaux :

```text
1. Identité
   titre, artiste, album, ISRC, Spotify URI, durée

2. Descripteurs interprétables
   tags, genres, moods, langue, époque, énergie estimée, chantable, calme, nocturne

3. Vecteurs
   embedding textuel
   éventuellement embedding audio plus tard
   profil personnel issu du feedback
```

---

## 9. Stratégie de similarité / clustering

### Version simple — Tags + scoring

| Aspect        | Détail                                                                    |
| ------------- | ------------------------------------------------------------------------- |
| Principe      | Chaque mood a des tags ; chaque chanson a des tags ; on calcule un score. |
| Avantages     | Facile à comprendre, debug très simple, pas besoin de ML lourd.           |
| Inconvénients | Rigide, dépend de la qualité des tags.                                    |
| À faire       | MVP.                                                                      |

Exemple :

```text
mood = "sad night walk"
tags positifs = sad, melancholic, calm, night, slow, emotional
tags négatifs = party, aggressive, workout, comedy
```

### Version intermédiaire — Embeddings + clustering

| Aspect        | Détail                                                                                  |
| ------------- | --------------------------------------------------------------------------------------- |
| Principe      | Transformer les descriptions de morceaux en vecteurs, puis rechercher les plus proches. |
| Avantages     | Comprend mieux les nuances : “melancholic”, “nostalgic”, “late night”, “bittersweet”.   |
| Inconvénients | Moins explicable, dépend du texte d’entrée.                                             |
| À faire       | Juste après le MVP tags.                                                                |

### Version avancée — Feedback personnel

| Aspect        | Détail                                         |
| ------------- | ---------------------------------------------- |
| Principe      | Chaque accept/refuse ajuste le profil du mood. |
| Avantages     | Devient très personnel.                        |
| Inconvénients | Besoin de feedback, risque d’overfit.          |
| À faire       | Après export playlist + validation UI.         |

---

## 10. Stratégie lyrics

### Recommandation

Ne mets pas les lyrics dans le MVP obligatoire. Ajoute-les en V2 comme enrichissement optionnel.

### Pipeline lyrics prudent

```text
track → match lyrics provider → retrieve lyrics if allowed
      → detect language
      → extract derived tags only
      → store tags + summary + source
      → avoid storing full lyrics unless licence clear
```

### Features lyrics utiles

| Feature lyrics         | Utilité                                              |
| ---------------------- | ---------------------------------------------------- |
| Langue                 | Playlist à chanter, J-pop, anglais/français/japonais |
| Densité vocale         | Sing-along vs fond                                   |
| Thèmes                 | amour, rupture, solitude, fête, nostalgie            |
| Émotion                | triste, colère, espoir, euphorie                     |
| Répétition/refrain     | Chantable                                            |
| Explicitness textuelle | Filtrage contexte                                    |

### À éviter

* Scraper Genius sans vérifier conditions.
* Stocker massivement des lyrics complets sans licence.
* Dépendre d’une source gratuite non garantie.
* Utiliser lyrics Spotify via endpoints privés/non documentés.

---

## 11. Stratégie de validation utilisateur

Le feedback utilisateur est central, car ton concept est personnel.

### Feedback minimal

| Action                 | Interprétation               |
| ---------------------- | ---------------------------- |
| Accepter               | Bon morceau pour ce mood     |
| Refuser                | Mauvais morceau pour ce mood |
| Sauvegarder/exporter   | Signal positif fort          |
| Supprimer après export | Signal négatif fort          |

### Feedback plus riche

| Raison                      | Effet                          |
| --------------------------- | ------------------------------ |
| Trop énergique              | Baisser poids énergie          |
| Trop calme                  | Augmenter énergie minimale     |
| Bon style, mauvais mood     | Garder genre, baisser mood     |
| Bon mood, mauvais style     | Garder mood, baisser genre     |
| Pas assez chantable         | Favoriser lyrics/vocal/refrain |
| Trop connu / trop répétitif | Diversification                |

### Mesure simple

Pour chaque run :

```text
acceptance_rate = accepted / recommended_seen
export_rate = exported / recommended_seen
skip_rate = rejected / recommended_seen
```

Objectif MVP : au moins **40–60 % de recommandations acceptables** sur les 30 premiers résultats pour un mood bien défini.

---

## 12. Évolution vers une version plus avancée

### V1 — MVP solide

* Import Spotify.
* Déduplication.
* Tags manuels.
* Last.fm/MusicBrainz.
* Embeddings textuels.
* Similarité par morceaux de référence.
* Feedback accept/refuse.
* Export playlist.

### V2 — Meilleure compréhension musicale

* Lyrics optionnelles.
* Tags LLM dérivés des lyrics si licence OK.
* BPM/énergie via audio légal ou API tierce.
* Clustering UMAP/HDBSCAN.
* Explications par recommandation.

### V3 — Système personnel intelligent

* Modèle par mood.
* Feedback pondéré.
* Recommandations diversifiées.
* Détection automatique de sous-moods.
* “Je veux une playlist proche de ces 10 morceaux mais plus calme / plus nocturne / plus chantable.”

### V4 — Produit plus large

* Multi-utilisateur.
* Gestion stricte licences.
* Fournisseur audio/lyrics commercial.
* Mode collaboration.
* Mobile app.
* Sync automatique.

---

## 13. Risques techniques

| Risque                                |       Impact | Mitigation                                                                      |
| ------------------------------------- | -----------: | ------------------------------------------------------------------------------- |
| Dépendance Spotify Audio Features     |         Fort | Ne pas les utiliser comme base                                                  |
| Restrictions Spotify Development Mode |   Moyen/fort | App personnelle, scopes minimum, fallback manuel                                |
| Spotify ToS ML/AI                     |         Fort | Ne pas entraîner/ingérer Spotify Content ; utiliser sources externes autorisées |
| Matching MusicBrainz/Last.fm mauvais  |        Moyen | Score de confiance + validation manuelle                                        |
| Lyrics copyright                      |         Fort | Stocker tags dérivés seulement ; fournisseur licencié si public                 |
| Tags trop bruités                     |        Moyen | Pondérer par source + feedback utilisateur                                      |
| Embeddings peu explicables            |        Moyen | Garder tags + explications                                                      |
| Audio features difficiles             |        Moyen | Reporter après MVP                                                              |
| Clustering instable                   | Faible/moyen | Ne pas en faire le cœur produit                                                 |
| UI trop complexe                      |        Moyen | Démarrer avec une table + filtres + feedback simple                             |

---

## 14. Ordre exact d’implémentation

Voici l’ordre que je recommande réellement :

1. Créer repo + Docker Compose + PostgreSQL.
2. Créer modèle DB minimal : users, tracks, spotify_tracks, playlists, playlist_tracks.
3. Implémenter Spotify OAuth.
4. Importer playlists personnelles.
5. Importer playlist items.
6. Importer morceaux sauvegardés.
7. Normaliser et dédupliquer par Spotify ID / ISRC.
8. Créer UI liste de morceaux.
9. Créer UI sélection de 5 à 15 morceaux de référence.
10. Créer `mood_profiles`.
11. Ajouter tags manuels par morceau.
12. Implémenter scoring simple par tags.
13. Afficher recommandations triées.
14. Ajouter feedback accept/refuse.
15. Exporter en playlist Spotify.
16. Ajouter Last.fm tags.
17. Ajouter MusicBrainz matching.
18. Générer descriptions textuelles de morceaux.
19. Générer embeddings.
20. Remplacer scoring simple par score hybride.
21. Ajouter explications de score.
22. Ajouter lyrics optionnelles.
23. Ajouter audio features légales ou API tierce.
24. Ajouter clustering/visualisation.
25. Ajouter apprentissage avancé par mood.

---

## 15. Critères de réussite pour chaque étape

| Étape                  | Critère de réussite                                                          |
| ---------------------- | ---------------------------------------------------------------------------- |
| Spotify import         | 95 % de tes morceaux attendus sont importés.                                 |
| Déduplication          | Les doublons évidents sont fusionnés, sans fusionner remix/live/covers.      |
| Sélection références   | Tu peux créer un mood en moins d’une minute.                                 |
| Tags manuels           | Tu peux corriger rapidement les erreurs de classification.                   |
| Scoring simple         | Les résultats sont compréhensibles même s’ils sont imparfaits.               |
| Enrichissement externe | Au moins 50–70 % des morceaux connus ont des tags externes utiles.           |
| Embeddings             | Les recommandations sont meilleures que le scoring tags seul.                |
| Feedback               | Le taux d’acceptation augmente après plusieurs corrections.                  |
| Export                 | Une playlist Spotify est créée sans doublons et dans le bon ordre.           |
| Lyrics                 | Les tags émotionnels s’améliorent sans dépendre du texte complet.            |
| Audio features         | Les playlists “drive”, “walk”, “energetic”, “calm” deviennent plus précises. |
| Clustering             | Les groupes sont interprétables et renommables manuellement.                 |

### Définition d’un MVP réussi

Le MVP est réussi si tu peux faire ceci :

1. Te connecter à Spotify.
2. Importer ta bibliothèque.
3. Choisir 10 morceaux “sad night walk”.
4. Obtenir 50 recommandations.
5. Accepter/refuser les morceaux proposés.
6. Exporter une playlist Spotify.
7. Répéter pour un autre mood sans modifier le code.

Le bon premier objectif n’est pas “classification musicale parfaite”. C’est : **créer une boucle personnelle de recommandation que tu peux corriger rapidement**. C’est cette boucle — import → références → recommandations → feedback → export — qui rendra le système progressivement intelligent.

[1]: https://developer.spotify.com/documentation/web-api/reference/get-audio-features "Web API Reference | Spotify for Developers"
[2]: https://developer.spotify.com/documentation/web-api/reference/get-track "Web API Reference | Spotify for Developers"
[3]: https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security "Update on Developer Access and Platform Security | Spotify for Developers"
[4]: https://musicbrainz.org/doc/MusicBrainz_API "MusicBrainz API - MusicBrainz"
[5]: https://www.last.fm/api/show/track.getInfo "API Docs | Last.fm"
[6]: https://acousticbrainz.org/ "AcousticBrainz"
[7]: https://developer.spotify.com/documentation/web-api/reference/get-a-list-of-current-users-playlists "Web API Reference | Spotify for Developers"
[8]: https://developer.spotify.com/documentation/web-api/reference/get-playlists-items "Web API Reference | Spotify for Developers"
[9]: https://developer.spotify.com/documentation/web-api/references/changes/february-2026 "Web API Changelog - February 2026 | Spotify for Developers"
[10]: https://lrclib.net/docs?utm_source=chatgpt.com "API Documentation"
[11]: https://librosa.org/doc/latest/feature.html "Feature extraction — librosa 0.11.0 documentation"
[12]: https://essentia.upf.edu/models.html "Essentia models — Essentia 2.1-beta6-dev documentation"
[13]: https://api-docs.cyanite.ai/docs/audio-analysis-v6-classifier/ "Audio Analysis V6 Classifier | Cyanite.ai API Documentation"
