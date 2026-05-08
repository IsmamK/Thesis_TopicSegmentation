# IEEE Paper

8-page IEEE conference-style version of the thesis. Built in **T38**.

## Build

```
make paper
# or
cd paper && pdflatex ieee.tex && bibtex ieee && pdflatex ieee.tex && pdflatex ieee.tex
```

Output: `paper/ieee.pdf`.

## Required class file

`IEEEtran.cls` and `IEEEtran.bst` are usually included with TeX Live and MikTeX.
If your installation does not have them, download from
https://www.ieee.org/conferences/publishing/templates.html and place in this
folder.

## Length budget

- 8 pages, IEEE conference template, 10pt, two columns.
- The paper shares the bibliography with the thesis (`../thesis/bibliography/references.bib`).
- Figures are pulled from `../thesis/figures/`.
