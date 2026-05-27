# ROT design retrospective — paper

A LaTeX paper describing the design of ROT (`https://github.com/omkarxpatel/ROT`),
written against v2.25.12. About 10–12 pages when typeset.

## Files

- `main.tex` — the paper.
- `references.bib` — BibTeX entries.

## Compile

With `latexmk` (preferred):

```
latexmk -pdf main.tex
```

Without it, the long form:

```
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Targets a standard TeX Live distribution. No exotic packages — only
`geometry`, `listings`, `xcolor`, `hyperref`, `booktabs`, `enumitem`,
`titlesec`, `microtype`, `lmodern`. All ship with TeX Live.

To clean intermediate files:

```
latexmk -C
```
