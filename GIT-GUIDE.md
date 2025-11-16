# Git Handleiding (Lokaal)

**Versie:** 1.0.0
**Laatst bijgewerkt:** 2025-11-16
**Project:** Pi-hole Sentinel

Quick reference voor lokale Git operaties.

---

## Status checken

```bash
git status                    # Huidige status
git branch -a                 # Alle branches (lokaal + remote)
git log --oneline -5          # Laatste 5 commits
```

---

## Branch wisselen

```bash
git checkout main                                    # Naar main
git checkout claude/project-review-audit-01KcU4...  # Naar claude branch
git checkout -b nieuwe-branch                        # Nieuwe branch maken
```

---

## Wijzigingen ophalen

```bash
git fetch origin              # Haal updates op (niet mergen)
git pull origin main          # Haal main op en merge
git pull                      # Pull huidige branch
```

---

## Wijzigingen pushen

```bash
git add .                     # Stage alle wijzigingen
git commit -m "msg"           # Commit
git push                      # Push naar remote
git push -u origin branch     # Push nieuwe branch
```

---

## Snel overzicht

```bash
git status && git log --oneline -3    # Status + laatste commits
```

---

## Belangrijk

⚠️ **Claude branches beginnen altijd met `claude/` en eindigen met session ID!**

Voorbeeld: `claude/project-review-audit-01KcU4Da3NQyemv38xvUv4sF`

---

## Veelgebruikte Combinaties

```bash
# Check status en recent werk
git status
git log --oneline -5

# Update van remote
git fetch origin
git checkout main
git pull origin main

# Nieuwe feature branch
git checkout main
git pull origin main
git checkout -b feature/nieuwe-feature

# Commit en push
git add .
git commit -m "type: beschrijving"
git push -u origin branch-naam

# Terug naar claude branch
git checkout claude/project-review-audit-01KcU4Da3NQyemv38xvUv4sF
```

---

## Commit Types (zie CLAUDE.md)

- `feat` - Nieuwe feature
- `fix` - Bug fix
- `docs` - Documentatie
- `style` - Formatting
- `refactor` - Code refactoring
- `test` - Tests
- `chore` - Build/tooling
- `security` - Security fixes

---

**Zie ook:** `CLAUDE.md` voor volledige commit regels en versioning
