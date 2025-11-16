# Handleiding Claude Code Gesprekken

**Versie:** 1.0.0
**Laatst bijgewerkt:** 2025-11-16
**Project:** Pi-hole Sentinel

---

## Bij het SLUITEN van een gesprek

```
Gesprek sluiten. Huidige status:
- Branch: claude/[session-id]
- Laatste commit: [korte beschrijving]
- Todo: [wat er nog moet gebeuren]
- Notities: [belangrijke context voor volgende sessie]
```

**Voorbeeld:**
```
Gesprek sluiten. Huidige status:
- Branch: claude/project-review-audit-01KcU4Da3NQyemv38xvUv4sF
- Laatste commit: fix: improved VIP detection retry logic
- Todo: Test failover scenario, update documentation
- Notities: VIP timeout verhoogd naar 500ms, retry 3x toegevoegd
```

---

## Bij het STARTEN van een nieuw gesprek

```
Nieuw gesprek. Context:
- Werk verder op branch: claude/[session-id]
- Vorige sessie: [wat er gedaan is]
- Nu doen: [wat er moet gebeuren]
- Let op: [belangrijke waarschuwingen/context]
```

**Voorbeeld:**
```
Nieuw gesprek. Context:
- Werk verder op branch: claude/project-review-audit-01KcU4Da3NQyemv38xvUv4sF
- Vorige sessie: VIP detection retry logic toegevoegd
- Nu doen: Failover scenario testen en documentatie updaten
- Let op: VERSION en CHANGELOG.md moeten nog gebumpt worden
```

---

## Tips

- **Houd het kort en zakelijk** - Claude Code leest CLAUDE.md automatisch
- **Geen duplicate informatie** - Wat in CLAUDE.md staat hoef je niet te herhalen
- **Focus op continuïteit** - Wat heeft de volgende sessie nodig?
- **Specifieke context** - Vermeld edge cases, workarounds, tijdelijke oplossingen

---

## Waarom deze format?

- ✅ **Geen geheugen tussen sessies** - Claude Code heeft geen context van vorige gesprekken
- ✅ **Snelle orientatie** - Nieuwe sessie weet meteen waar te beginnen
- ✅ **Voorkomt werk duplication** - Duidelijk wat al gedaan is
- ✅ **Reduceert fouten** - Belangrijke waarschuwingen worden niet vergeten

---

**Zie ook:** `CLAUDE.md` voor volledige project regels en conventies
