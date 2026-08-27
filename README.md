# fie-prompts

Prompts para processamento de textos com DeepSeek V4 Flash — limpeza OCR, tradução, enriquecimento e atualização ortográfica.

## Estrutura

### Limpeza OCR

| Arquivo | Descrição |
|---|---|
| `01-limpeza-grego-arabe.txt` | Remove aparato crítico e notas filológicas. Para textos antigos (grego, árabe). |
| `02-limpeza-academica-moderna.txt` | Preserva e renumera notas de rodapé. Para textos acadêmicos modernos. |

### Tradução (para português)

| Arquivo | Descrição |
|---|---|
| `03-trad-academica-moderna.txt` | Tradução acadêmica (filosofia, teologia, ciências). Com N. do T. |
| `04-trad-literatura.txt` | Tradução literária (prosa, romance). Preserva voz do autor. |
| `05-trad-latim.txt` | Latim clássico, escolástico e filosófico. |
| `06-trad-gregos.txt` | Grego clássico e helenístico. Com títulos analíticos e N. do T. |
| `07-trad-arabe.txt` | Árabe clássico (900-1400). Com hierarquia estrutural e honoríficos. |
| `08-trad-teatro.txt` | Tradução para teatro (performável). Diálogos em travessão. |

### Tradução (para inglês)

`promtps-to-english/` — prompts para traduzir **para o inglês** (mercado editorial americano).

| Arquivo | Descrição |
|---|---|
| `03-academic-modern-translation.txt` | Academic translation (Chicago Manual of Style). Com `[—Trans.]` |
| `04-literary-translation.txt` | Literary translation into contemporary American English. |

### Outros

| Arquivo | Descrição |
|---|---|
| `atualizacao-ortografica.txt` | Atualização de português antigo/PT-PT para PT-BR (Acordo 1990). |
| `enriquecimento.txt` | Enriquecimento pós-tradução (notas, relatório de melhorias). |

## Convenções

- **Notas de rodapé**: formato Markdown `[^n]`; cada definição vem no parágrafo imediatamente seguinte ao parágrafo da chamada (sem bloco `## Notes`/`## Notas` ao final).
- **Nota do tradutor**: `(N. do T.)` em português, `[—Trans.]` em inglês.
- **Capítulos**: preservar numeração original. Nunca converter romanos ↔ arábicos.
- **OCR**: unir linhas quebradas, remover headers/footers, corrigir espaçamento.

## Uso

Os prompts são consumidos pelo [fie-scripts](https://github.com/fleilanio/fie-scripts) (runner DeepSeek Batch). O runner baixa o `index.json`, filtra por `task_type` e apresenta o menu de prompts disponíveis.

`task_type` disponíveis: `limpeza`, `traducao`, `traducao_ingles`, `enriquecimento`, `atualizacao`.
