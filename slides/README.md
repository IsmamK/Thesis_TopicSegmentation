# Defense slides

Beamer deck for the defense talk. Built in **T41**.

## Build

```
make slides
# or
cd slides && pdflatex slides.tex && pdflatex slides.tex
```

Output: `slides/slides.pdf`.

## Theme

`metropolis`. Install via:
- TeX Live: `tlmgr install beamertheme-metropolis`
- MikTeX: package manager → `metropolis`

## Length budget

20-minute talk + 10-minute Q&A.
- ~25 main slides (1 minute each is the rule of thumb)
- Plus backup slides (appendix) for likely panel questions
- Use `\todo{...}` markers as placeholders during drafting

## Tips

- One idea per slide. If you can't summarise the slide in one sentence, split it.
- Number every figure and reference it from the script.
- Practise live-walking the panel through the **pipeline figure** — it is your
  spine for 60 % of likely questions.
