# T47 — 24-Hour Sanity Checklist

**Phase 11 · Defense Prep · Estimated time: 3 h the day before · Owner: everyone**

---

## 🎯 What you are doing
The final countdown. A single checklist covering everything you need to arrive at the defense with.

## ✅ How to know you are done
- Every box ticked.
- You sleep 8 hours.

---

## 📝 The Checklist

### 24 hours before

- [ ] `python scripts/pre_defense_check.py` prints all green.
- [ ] `python scripts/strip_internal.py --go` → any `internal/` content removed from the thesis repo.
- [ ] Commit + push to GitHub. Tag release `v1.0`.
- [ ] Upload final `thesis/main.pdf` to the BracU submission portal.
- [ ] Final Turnitin report saved as PDF, shared with the team.
- [ ] Poster printed A1, matte, rolled safely in a poster tube.
- [ ] USB stick contains: `thesis/main.pdf`, `slides/defense.pdf`, `paper/ieee.pdf`, `webapp/` offline-ready. Back it up to a second USB.
- [ ] A **portable demo** is rehearsed: Streamlit app starts offline, uses a pre-cached video.
- [ ] `docs/DEFENSE_QA.md` printed for each team member.
- [ ] Ollama tested running locally with the laptop you will bring.
- [ ] Charger + adapter + HDMI cable + clicker packed.
- [ ] Supervisor informed of session time.

### 4 hours before

- [ ] Eat a real meal.
- [ ] Run through the first 3 slides silently in your head.
- [ ] Walk to the venue early.

### 10 min before

- [ ] Project connected, slides up on a Test Slide (not the title — you want to keep that hidden).
- [ ] Demo laptop Wi-Fi disabled → run offline demo to avoid network flakes.

### In the room

- [ ] Hydrate, breathe, smile.
- [ ] Present. Trust the rehearsal.

---

## ➡️ After the defense

```
python scripts/mark_done.py T47
python scripts/pre_defense_check.py   # final celebration dashboard
```

🎉 **Congratulations. Thesis done.**
