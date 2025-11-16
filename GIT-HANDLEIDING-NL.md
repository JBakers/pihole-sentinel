# Git Handleiding (Lokaal)

## Status checken

```bash
git status                    # Huidige status
git branch -a                 # Alle branches (lokaal + remote)
git log --oneline -5          # Laatste 5 commits
```

## Branch wisselen

```bash
git checkout main                                    # Naar main
git checkout claude/project-review-audit-01KcU4...   # Naar claude branch
git checkout -b nieuwe-branch                        # Nieuwe branch maken
```

## Wijzigingen ophalen

```bash
git fetch origin              # Haal updates op (niet mergen)
git pull origin main          # Haal main op en merge
git pull                      # Pull huidige branch
```

## Wijzigingen pushen

```bash
git add .                     # Stage alle wijzigingen
git commit -m "msg"           # Commit
git push                      # Push naar remote
git push -u origin branch     # Push nieuwe branch
```

## Snel overzicht

```bash
git status && git log --oneline -3   # Status + laatste commits
```

---

**Belangrijk:** Claude branches beginnen altijd met `claude/` en eindigen met session ID!
