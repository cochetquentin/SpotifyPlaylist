# SpotifyPlaylist

Tri automatique de musique Spotify en playlists thématiques par mood/contexte, basé sur des chansons de référence.

> Voir [docs/roadmap/ROADMAP.md](docs/roadmap/ROADMAP.md) pour la feuille de route complète.

---

## Prérequis

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — gestionnaire de dépendances
- Un compte Spotify + une application créée sur le [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

## Installation

```bash
# 1. Cloner le dépôt
git clone <url-du-repo>
cd SpotifyPlaylist

# 2. Installer les dépendances
uv sync --locked

# 3. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos credentials Spotify
```

## Configuration Spotify

1. Aller sur le [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Créer une nouvelle application
3. Dans les paramètres de l'application, ajouter l'URI de redirection : `http://localhost:8000/auth/callback`
4. Copier le `Client ID` et le `Client Secret` dans votre fichier `.env`

## Démarrage

```bash
uv run uvicorn app.main:app --reload
```

L'API est disponible sur `http://localhost:8000`.

Documentation interactive : `http://localhost:8000/docs`

## Authentification Spotify

1. Ouvrir `http://localhost:8000/auth/login` dans un navigateur
2. Autoriser l'application sur la page Spotify
3. Vous serez redirigé vers `/auth/callback` — la page confirmera le succès
4. Les tokens sont stockés localement dans `.tokens.json` (gitignored, chmod 600)

## Endpoints disponibles (Étape 1)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Santé de l'application |
| `GET` | `/auth/login` | Lancer le flux OAuth Spotify |
| `GET` | `/auth/callback` | Callback OAuth (usage interne) |
| `GET` | `/auth/logout` | Supprimer les tokens locaux |
| `GET` | `/me` | Profil Spotify de l'utilisateur connecté |

## Tests

```bash
# Lancer tous les tests avec coverage
uv run pytest --cov=app tests/ -v

# Lint
uv run ruff check .

# Format
uv run ruff format --check .
```

## Flux Git

```
main (protégée — push direct interdit)
  └── feat/etape1-fondation  ← branche courante
  └── feat/etape2-import
  ...
```

### Configurer la protection de `main` sur GitHub

Après le premier push :

1. Aller dans `Settings > Branches > Add branch ruleset`
2. Cibler la branche `main`
3. Activer :
   - **Require a pull request before merging**
   - **Require status checks to pass** (sélectionner les jobs CI)
   - **Do not allow bypassing the above settings**

## Skill Claude — `/handle-codex-review`

Le skill `.claude/commands/handle-codex-review.md` automatise le cycle de review Codex ↔ Claude Code.

```bash
# Dans Claude Code, sur une PR ouverte :
/handle-codex-review
```

Voir le fichier de commande pour le détail des phases.
