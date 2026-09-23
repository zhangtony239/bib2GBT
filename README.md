# bib2gbt

English | [简体中文](README_zh.md)

Convert BibTeX (`.bib`) references to GB/T 7714 style (e.g. `[J]`, `[D]`, `[C]`, `[N]`).

## Install (uv tool)

```bash
uv tool install .
```

Or run directly inside this project:

```bash
uv run bib2gbt refs.bib
```

## Usage

```bash
bib2gbt <path/to/file.bib>
```

When multiple references are converted, the output is numbered `[1]`, `[2]`, ...; a single reference is printed without a number.