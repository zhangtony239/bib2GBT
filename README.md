# bib2gbt

将 BibTeX（`.bib`）文献条目转换为 GB/T 7714 参考文献格式（如 `[J]`、`[D]`、`[C]`、`[N]` 等）。

## 安装（uv tool）

```bash
uv tool install .
```

或在本项目内直接运行：

```bash
uv run bib2gbt refs.bib
```

## 使用

```bash
bib2gbt <path/to/file.bib>
```

多条文献时输出会带 `[1]`、`[2]` 等序号；单条文献直接输出。