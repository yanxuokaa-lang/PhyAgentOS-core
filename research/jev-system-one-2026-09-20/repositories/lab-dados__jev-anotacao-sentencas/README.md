# Jev vs. LLMs generativos na anotação de sentenças judiciais

Experimento do [LabDados FGV Direito SP](https://github.com/lab-dados). Compara o **Jev**
([TypeSafe](https://docs.typesafe.ai)), um modelo "System One" que só responde perguntas tipadas
com probabilidades calibradas, com o **Gemini 3.8 Flash** e o **GPT-5.6 Luna** usados com saída
estruturada. A tarefa é anotar 12 variáveis em 120 sentenças cíveis do TJSP coletadas com o
[juscraper](https://github.com/jtrecenti/juscraper).

📄 **Relatório:** https://lab-dados.github.io/jev-anotacao-sentencas/ ·
[PDF (Typst)](https://lab-dados.github.io/jev-anotacao-sentencas/relatorio.pdf) ·
[fonte .typ](https://lab-dados.github.io/jev-anotacao-sentencas/relatorio.typ)

## Resultados principais

| Modelo | Acurácia | Latência mediana | US$ / mil sentenças |
|---|---|---|---|
| Gemini 3.8 Flash | 98,8% | 2,81 s | 6,56 |
| GPT-5.6 Luna | 96,8% | 3,49 s | 1,64 |
| Jev (latest) | 96,6% | 0,32 s | 0,25 |

## Estrutura

- `src/jevtest/schema.py`: esquema de anotação, fonte única das perguntas para os três provedores
- `src/jevtest/clientes.py`: chamadas assíncronas e medição de latência
- `src/jevtest/avaliacao.py`: métricas de qualidade, tempo, custo e calibração
- `scripts/`: coleta → anotação → padrão-ouro → publicação
- `data/anotacoes/`: respostas brutas de cada modelo (JSONL)
- `data/adjudicacao/`: divergências, auditoria e decisões da adjudicação cega (Claude Opus 5)
- `data/gold.parquet`: padrão-ouro; `data/amostra_meta.parquet`: metadados da amostra, sem texto
- `relatorio/relatorio.qmd`: relatório em Quarto (HTML interativo + PDF via Typst); `docs/`: GitHub Pages

O texto integral das sentenças não é redistribuído (LGPD, art. 6º, III). A coleta pode ser refeita
com `scripts/01_coletar.py`.

## Reproduzir

```bash
uv sync
uv run python scripts/01_coletar.py
uv run python scripts/02_anotar.py jev-latest jev-preview gemini-3.8-flash gpt-5.6-luna \
    ref-gpt-5.6-sol ref-gemini-3.1-pro
uv run python scripts/03_referencia.py      # lista divergências e auditoria
uv run python scripts/exportar_textos.py    # textos para a adjudicação cega
# adjudicação -> data/adjudicacao/decisoes.csv
uv run python scripts/03_referencia.py      # gera data/gold.parquet
./scripts/publicar.sh                       # renderiza o relatório e atualiza docs/
```

Chaves esperadas: `JEV_API_KEY` (ou `TYPESAFE_API_KEY`), `GEMINI_API_KEY` e `OPENAI_API_KEY`.
Os caminhos dos `.env` estão em `src/jevtest/config.py`.
