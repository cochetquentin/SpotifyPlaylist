# handle-codex-review

Automatise le cycle de review Codex ↔ Claude Code sur la PR courante.
La logique shell est déléguée aux scripts dans `.claude/scripts/codex-review/`.

---

## Phase 1 — Info PR

```bash
bash .claude/scripts/codex-review/pr-info.sh
```

Extraire `repo`, `pr`, `state`, `title`, `branch` depuis le JSON retourné.
Si `state != "OPEN"` → arrêter : "PR fermée ou mergée."

---

## Phase 2 — Anti-boucle

```bash
bash .claude/scripts/codex-review/anti-loop-check.sh <REPO> <PR>
```

- exit 1 → afficher la raison et arrêter.
- exit 0 → mémoriser `T_TRIGGER` (valeur après `T_TRIGGER=` dans la sortie).

---

## Phase 3 — Remarques Codex

```bash
bash .claude/scripts/codex-review/get-comments.sh <REPO> <PR> <T_TRIGGER>
```

Classer les remarques par priorité :
1. Reviews formelles `state=CHANGES_REQUESTED`
2. Commentaires inline (type=inline, file+line disponibles)
3. Commentaires généraux

Si aucune remarque → afficher "Aucune remarque Codex sur cette PR." et arrêter.

Sinon, **afficher un résumé des points à traiter** avant toute modification.

---

## Phase 4 — Snapshot + corrections

```bash
bash .claude/scripts/codex-review/dirty-files.sh
```

Mémoriser `dirty[]` et `new[]` (état du working tree avant toute modification).

Pour chaque remarque (dans l'ordre de priorité) :

1. Lire le fichier concerné pour comprendre le contexte actuel.
2. **Évaluer** : la remarque est-elle valide ? Déjà corrigée dans un commit précédent ?
3. Si le fichier est dans `dirty[]` **ou** `new[]` → **ignorer** (évite de mélanger avec des modifications locales préexistantes, trackées ou non).
4. Si **valide** → appliquer, noter `[APPLIQUÉ] fichier:ligne — description`.
5. Si **invalide / non applicable** → ignorer, noter `[IGNORÉ] description — raison courte`.

Ne pas modifier les tests pour forcer le coverage — corriger le code de production.

---

## Phase 5 — Tests

```bash
node_modules/.bin/vitest run
```

- **Succès** → continuer.
- **Échec** → diagnostiquer, corriger, relancer (max 2 tentatives).
  Si toujours KO : rollback des fichiers trackés modifiés dans ce cycle (`git checkout -- <fichiers>`)
  et suppression des fichiers non-trackés créés (`rm`), sans toucher `dirty[]` ni `new[]`.

---

## Phase 6 — Commit & push

Si des modifications ont été appliquées :

```bash
git add <fichiers modifiés spécifiquement>
git commit -m "fix: appliquer corrections Codex — {résumé 1 ligne}"
git push
```

Si **aucune modification** → exécuter quand même Phase 7 (rapport ignorées si applicable),
puis afficher le résumé final avec `@Codex review relancé : NON (aucun changement)` et arrêter.

---

## Phase 7 — Rapport des corrections ignorées

Si des remarques ont été ignorées, construire le tableau Markdown directement et le passer via stdin :

```bash
bash .claude/scripts/codex-review/post-skipped.sh <PR> << 'MARKDOWN'
## Corrections Codex ignorées

| Remarque | Raison |
|----------|--------|
| [type] fichier:ligne — description | raison courte |
MARKDOWN
```

Le script poste le contenu reçu sur stdin. Sans ignorées → ne rien poster.

---

## Phase 8 — Relancer Codex

Re-vérifier l'anti-boucle avant de poster (le statut peut avoir changé pendant les phases 4-7) :

```bash
bash .claude/scripts/codex-review/anti-loop-check.sh <REPO> <PR>
```

- exit 1 → ne pas relancer, afficher la raison.
- exit 0 → poster le trigger :

```bash
bash .claude/scripts/codex-review/trigger.sh <PR>
```

---

## Résumé de sortie

```
## /handle-codex-review — Résultat

PR : #{PR} — {title}
Branche : {branch}

Remarques Codex : N trouvées
Corrections : X appliquées, Y ignorées
Tests : PASS | FAIL (coverage : Z%)
Commit : {sha} — "{message}"
Push : OK | SKIPPED

@Codex review relancé : OUI / NON (raison si NON)
```