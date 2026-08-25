# agents.md — Agente de Formatação Editorial de E-book (Fi.E Editorial)

> **Versão:** 2.1  
> **Input:** arquivo `.txt` bruto ou `.md` parcial  
> **Output:** arquivo `.docx` com estilos Word, notas de rodapé nativas e tipografia editorial  
> **Normativa PT-BR:** Emanuel Araújo, *A Construção do Livro*  
> **Normativa EN:** Chicago Manual of Style, 17ª ed.  
> **Pipeline:** TXT/`.md` → Markdown estruturado → DOCX via `docx` (npm)

---

## VISÃO GERAL DO PIPELINE

```
arquivo.txt (bruto) ──┐
                      ├──→  FASE 0: Análise — detectar idioma, estrutura,
arquivo.md (parcial) ──┘      elementos especiais, lixo de pipeline
      │
      ▼
  FASE 0A: Correções pré-markdown — notes quebradas, lixo removido,
      │      capa invertida, headings mal nivelados, versos soltos
      ▼
  FASE 1: Markdown estruturado — aplicar/ajustar hierarquia, estilos, footnotes
      │         (formato interno de trabalho — não é o output final)
      ▼
  FASE 2: DOCX — converter markdown → .docx via script Node.js (docx npm)
      │         com estilos Word nativos e notas de rodapé reais
      ▼
  output.docx (publicação pronta para KDP)
```

Se o input for `.txt`, o agente constrói o markdown do zero. Se for `.md`, usa a estrutura existente como fonte, aplicando correções e enriquecendo com elementos que o markdown parcial não capturou (notas quebradas, versos, lixo de pipeline).

---

## FASE 0 — ANÁLISE PRELIMINAR OBRIGATÓRIA

**Leia o arquivo .txt ou .md inteiro antes de qualquer transformação.**

### 0.1 Detectar idioma

Leia os primeiros 50 parágrafos de corpo (excluindo possíveis títulos e metadados). Identifique o idioma predominante:

- **PT-BR** → normas Araújo + hierarquia: TOMO → LIVRO → PARTE → CAPÍTULO
- **EN** → normas Chicago 17ª ed. + hierarquia: VOLUME → BOOK → PART → CHAPTER
- **Outro / misto** → registrar e perguntar ao usuário antes de prosseguir

Registre: `idioma_detectado`, `confiança` (alta / média / baixa), `evidências` (3–5 palavras-chave).

---

### 0.2 Varredura estrutural plana

Percorra **todas** as linhas do .txt e classifique cada parágrafo/bloco:

| Classe | Critério |
|---|---|
| `TITULO_OBRA` | ALL-CAPS curto nas primeiras linhas, antes do primeiro parágrafo longo (> 150 chars) |
| `AUTOR` | Nome na página de rosto, após o título |
| `SUMARIO` | Bloco com entradas "Texto + espaços/tab + número de página" nas primeiras 80 linhas |
| `ROTULO_ESTRUTURAL` | Linha correspondente a padrão de heading no idioma detectado (ver §2.1) |
| `TITULO_LITERARIO` | Linha curta (< 80 chars) sem pontuação final, imediatamente após um rótulo estrutural |
| `EPIGRAFE` | Bloco curto imediatamente antes de rótulo de seção, com atribuição em linha seguinte |
| `CITACAO_LONGA` | Bloco de prosa longo, recuado visualmente ou com marcador no original |
| `POEMA` | Sequência de linhas curtas sem pontuação final com padrão de verso |
| `CARTA` | Bloco com cabeçalho (local/data), saudação, corpo, despedida, assinatura |
| `SEPARADOR` | Linha com `* * *`, `—`, `***`, linha em branco dupla ou símbolo isolado |
| `SECAO_NOTAS` | Linha que começa com `## Notas`, `# Notas`, `Notas` como título de seção |
| `NOTA_INLINE` | Marcador `[^n]` no corpo do texto e definição `[^n]: texto` ao final |
| `FRAGMENTO` | Linha curta (< 40 chars) sem pontuação final que parece continuação do parágrafo anterior |
| `VERSSOLTO` | Linha curta (< 50 chars) dentro de prosa normal, sem `:::poema`, mas com métrica/rima/estrofe detectável |
| `LIXO_PIPELINE` | Linha com `TRADUÇÃO`, `TEXTO TRADUZIDO`, `REVISÃO`, `TEXTO REVISADO`, `OCR`, `DIGITALIZAÇÃO` ou similares como linha isolada |
| `NORMAL` | Corpo narrativo padrão |
| `AMBIGUO` | Não se encaixa claramente em nenhuma classe |

---

### 0.3 Mapeamento de notas

Localizar **todos** os marcadores de nota no arquivo:

**Notas inline (formato padrão Markdown/Pandoc):**
```
Corpo do texto[^1] continua aqui.

[^1]: Texto completo da nota de rodapé.
```

**Seção de Notas ao final (formato alternativo):**
```
## Notas

[^1]: Texto da nota.
[^2]: Outra nota.
```

Para cada nota, registrar: `id`, `posição_no_texto` (parágrafo aproximado), `texto_completo`.

> **Regra crítica:** A seção `## Notas` e suas entradas `[^n]` **não são removidas nem ocultadas da análise**. Elas são a fonte de verdade para geração das footnotes nativas no Word. Após a extração e conversão, o bloco `## Notas` é suprimido do body do docx — as notas migram para footnotes reais, não ficam duplicadas no corpo.

**Definição quebrada:** aceitar `[^1] texto` sem `:` como definição de nota. Normalizar internamente para `[^1]: texto`. Detectar e registrar essas ocorrências no relatório.

**Notas por capítulo/trecho:** notas podem aparecer agrupadas ao final de cada capítulo, não só em seção `## Notas` única. Identificar blocos de definições `[^n]:` após cada heading — seja no markdown `.md` de entrada, seja no `.txt` bruto. Cada bloco de definições pertence ao heading anterior. Extrair todas para o footnoteMap global, preservando os ids originais.

**Renumeração global:** se `[^1]` aparece mais de uma vez (reinicía a cada capítulo), aplicar renumeração global sequencial. Mapear `[capítulo_n+nota_m]` → id único. Manter o mapeamento original → novo no relatório.

**Dedup de notas:** definições `[^n]: texto` com mesmo texto → deduplicar (mesmo id, uma footnote). Se textos diferentes compartilham o mesmo id (ex.: dois capítulos com `[^1]` mas textos distintos), tratar como notas distintas, atribuindo novos ids por ordem de ocorrência. Registrar no relatório.

**Verificação de paridade obrigatória:** contar referências `[^n]` no corpo e definições `[^n]:` (após normalização). Se os números não baterem, parar e reportar ao usuário antes de prosseguir.

---

### 0.4 Avaliar aplicabilidade das regras canônicas

**A. O texto usa marcadores estruturais explícitos?**
- Sim (CAPÍTULO, PARTE, numeração romana, etc.) → promoção automática padrão
- Parcialmente → aplicar onde explícito; listar ambíguos para confirmação
- Não → **não inventar hierarquia**; usar separadores (`* * *`) como Heading4 apenas se houver padrão consistente numerado; caso contrário, manter Normal

**B. Sumário presente?**
- Sim → extrair `titleMap` (hierarquia + títulos exatos); ele é a **fonte de verdade**
- Não → inferir hierarquia a partir dos rótulos no corpo

**C. Quais elementos especiais estão presentes?**  
Registrar contagens estimadas: poemas, cartas, citações longas, epígrafes, notas `[^n]`, seção `## Notas`.

**D. Fragmentação de parágrafos?**  
Linhas curtas consecutivas que parecem partidas → flagear para fusão.  
Versos de poema → **proteger da fusão**.

---

### 0.5 Relatório de análise ao usuário

Apresentar antes de qualquer transformação:

```
ANÁLISE PRELIMINAR
══════════════════════════════════════════════════
Idioma detectado: PT-BR (confiança: alta)
Evidências: "capítulo", "disse ele", "então"

Estrutura:
  Marcadores explícitos: sim (CAPÍTULO + numeral romano)
  Sumário: sim (linhas 1–28, 18 entradas)
  Hierarquia inferida: PARTE (H2) → CAPÍTULO (H3)
  Nível TOMO/LIVRO: não detectado

Elementos especiais:
  Epígrafes: 6 | Citações longas: 12 | Poemas: 3 | Cartas: 1
  Notas [^n] no corpo: 47
  Seção "## Notas" ao final: sim (linhas 1834–1901)
  Paridade de notas: ✓ (47 referências, 47 definições)

Fragmentos candidatos à fusão: 8
Ambíguos (aguardam confirmação):
  Linha 312: "A CHEGADA" — título sem rótulo precedente?
  Linha 891: "iv." — numeral romano minúsculo com ponto?

AÇÃO NECESSÁRIA ANTES DE PROSSEGUIR:
  ① Confirmar interpretação dos ambíguos acima
  ② Confirmar: diálogos em aspas devem ser convertidos para travessão? [PT-BR]
══════════════════════════════════════════════════
```

**Aguarde confirmação do usuário antes de iniciar a Fase 0A ou Fase 1.**

---

## FASE 0A — ENTRADA MARKDOWN PARCIAL / OCR PÓS-TRADUÇÃO

**Esta fase só é executada quando o input é `.md` (parcial/estruturado).**

Quando o arquivo de entrada já é um markdown (ex.: saída de OCR pós-tradução, chunking prévio), o agente **não refaz a estrutura do zero**. Em vez disso:

### 0A.1 Usar estrutura existente como fonte de verdade

- Headings `#`/`##`/`###` já presentes são mantidos como estão — o agente não redetecta hierarquia.
- Ajustes finos podem ser aplicados (ver 0A.3 e 0A.4 abaixo).
- O markdown existente informa a segmentação: cada bloco entre headings pertence ao heading anterior.

### 0A.2 Correção: capa invertida

Se as primeiras 1–3 linhas do arquivo forem `# NomeDoAutor` seguido de `## TituloDaObra`, inverter:

- `# Autor` → `## Autor` (Subtitle)
- `## Título` → `# Título` (Title allCaps)

Detectar pelo padrão: primeira linha com `# ` parece nome de pessoa (2–3 palavras, sem all-caps, sem numeral romano). Se confirmado, trocar os níveis.

### 0A.3 Correção: headings mal nivelados

Se o markdown tem **todos os headings em `#`** (ex.: `# CAPÍTULO I`, `# O Título do Capítulo`, `# PARTE I`), mas a hierarquia real exige níveis diferentes:

- Aplicar a tabela de rótulos da §1.2 (ex.: CAPÍTULO → `###`, PARTE → `##`, TOMO → `#`).
- Se o arquivo tem `#` misturado com outros níveis, não rebaixar — confiar na hierarquia existente.
- Se houver um sumário, usá-lo como referência de níveis.

### 0A.4 Correção: versos soltos sem `:::poema`

Linhas curtas consecutivas (2+) dentro de prosa normal, com padrão detectável:

- Métrica: contagem de sílabas consistente (±2 sílabas entre linhas)
- Rima: terminações fonéticas similares no final das linhas
- Estrofe: blocos de 2, 4, 6, 8 linhas separados por linha em branco

Se detectado, envolver em `:::poema` … `:::`.

**Não marcar como poema:** linhas curtas de diálogo, listas, cabeçalhos de carta.

### 0A.5 Remoção de lixo de pipeline

Linhas isoladas no início do arquivo contendo apenas:

| Padrão | Ação |
|---|---|
| `TRADUÇÃO`, `TEXTO TRADUZIDO`, `#tradução`, `REVISÃO`, `TEXTO REVISADO` | Remover linha |
| `OCR`, `DIGITALIZAÇÃO`, `CHUNK`, `ARQUIVO`, `ARQUIVO FINAL` | Remover linha |
| Qualquer combinação em ALL-CAPS destes termos, ou `#tradução` em minúsculo | Remover linha |

Remover também blocos de 2–5 linhas de metadados de pipeline (ex.: "Arquivo: capitulo1.txt" + "Revisado por: fulano"). Reportar cada remoção no relatório.

### 0A.6 Mapeamento de notas em markdown parcial

- Scan de `[^n]` no corpo e `[^n]:` / `[^n] texto` nas definições ao final de cada bloco de heading.
- Aplicar normalização de definição quebrada (ver 0.3).
- Aplicar renumeração global se necessário (ver 0.3).
- Aplicar dedup (ver 0.3).

---

## FASE 1 — MARKDOWN ESTRUTURADO (ESTÁGIO INTERMEDIÁRIO)

Transformar o .txt em um markdown estruturado que servirá de entrada para o gerador docx. Este arquivo é o buffer de trabalho interno do agente.

### 1.1 Convenções de markdown → estilos Word

| Markdown | Word Style | Notas |
|---|---|---|
| `# Título` (primeiras 5 linhas) | `Title` | Título da obra na página de rosto |
| `## Autor` (primeiras 10 linhas) | `Subtitle` | Nome do autor e demais dados de rosto |
| `# TOMO I` / `# VOLUME I` | `Heading1` | Divisão máxima |
| `## PARTE I` / `## PART I` | `Heading2` | |
| `### CAPÍTULO I — Título` / `### CHAPTER I — Title` | `Heading3` | Rótulo fundido com título literário |
| `#### Subcapítulo` | `Heading4` | Sem quebra de página |
| `> texto` | `CitacaoLonga` / `BlockQuote` | Citação longa em bloco |
| `:::epigrafe` … `:::` | `Epigrafe` | Fenced div customizado |
| `:::poema` … `:::` | `Poema` | Fenced div customizado |
| `:::carta` … `:::` | `Carta` | Fenced div customizado |
| `---` (linha isolada) | Separador centralizado `* * *` | |
| `[^n]` no texto | Footnote reference | Converte em footnote nativa no Word |
| `[^n]: texto` / bloco `## Notas` | Footnote body | Migrada para footnote nativa — suprimida do body |
| `*texto*` | itálico inline | |
| `**texto**` | negrito inline | |
| texto normal | `Normal` | |

### 1.2 Hierarquia e fusão de rótulo + título

**PT-BR — rótulos que viram Heading:**

| Padrão no TXT | Markdown | Word Style |
|---|---|---|
| `TOMO [romano/arábico/ordinal por extenso]` | `# TOMO …` | Heading1 |
| `LIVRO [romano/arábico/ordinal]` | `# LIVRO …` | Heading1 |
| `PARTE [romano/arábico/ordinal]`, `PRIMEIRA PARTE` etc. | `## PARTE …` | Heading2 |
| `CAPÍTULO [romano/arábico/ordinal]`, `[romano isolado]`, `[arábico isolado]` | `### CAPÍTULO …` | Heading3 |
| `INTRODUÇÃO`, `PREFÁCIO`, `PRÓLOGO`, `EPÍLOGO`, `POSFÁCIO`, `CONCLUSÃO` | `### …` | Heading3 |
| `APÊNDICE`, `NOTAS`, `BIBLIOGRAFIA`, `AGRADECIMENTOS` | `### …` | Heading3 |

**EN — rótulos que viram Heading:**

| Padrão no TXT | Markdown | Word Style |
|---|---|---|
| `VOLUME [roman/arabic/spelled]` | `# VOLUME …` | Heading1 |
| `BOOK [roman/arabic/spelled]` | `# BOOK …` | Heading1 |
| `PART [roman/arabic/spelled]`, `FIRST PART` etc. | `## PART …` | Heading2 |
| `CHAPTER [roman/arabic/spelled]`, `[isolated roman]`, `[isolated arabic]` | `### CHAPTER …` | Heading3 |
| `INTRODUCTION`, `PREFACE`, `PROLOGUE`, `EPILOGUE`, `FOREWORD`, `AFTERWORD` | `### …` | Heading3 |
| `APPENDIX`, `NOTES`, `BIBLIOGRAPHY`, `ACKNOWLEDGMENTS` | `### …` | Heading3 |

**Números por extenso → algarismo romano:**  
PT: um/primeiro → I, dois/segundo → II … dez/décimo → X … vinte e um → XXI (cobrir até L e C)  
EN: one/first → I, two/second → II … ten/tenth → X … twenty-one → XXI

**Fusão rótulo + título literário:**
```
### CAPÍTULO III — A Chegada dos Que Partiram
```
- Separador: em-dash (—) com espaço em cada lado
- PT-BR: title case editorial brasileiro (preposições/artigos minúsculos exceto no início)
- EN: Chicago title case — preposições/artigos minúsculos exceto no início e após dois-pontos
- Não fundir quando: título > 60 chars; subtítulo (H4) também presente

**Colapso de hierarquia:** usar apenas os níveis presentes. Nunca usar H2 para capítulos se há H1.

### 1.3 Notas: extração e marcação no markdown

Manter os marcadores `[^n]` no corpo do markdown exatamente onde estão no texto original.

As definições `[^n]: texto` são mantidas ao final do arquivo markdown (ou onde já estão).

O bloco `## Notas` do .txt original **não gera um heading no markdown intermediário** — é apenas o container das definições de footnotes, capturadas individualmente.

**Normalização de definição quebrada:** toda ocorrência de `[^n] texto` sem `:` no início da definição é normalizada internamente para `[^n]: texto` durante a extração. Aplicar tanto no `.txt` bruto quanto no `.md` parcial.

**Per-chapter notes:** definições que aparecem imediatamente após cada heading (antes do próximo heading) pertencem ao capítulo. Extrair todas para o footnoteMap do bloco correspondente. Se houver seção `## Notas` centralizada, fundir com as notas por capítulo.

### 1.4 Fusão de fragmentos

Parágrafo anterior termina sem pontuação final (`.`, `!`, `?`, `…`) E o fragmento começa com minúscula ou conjunção → fundir com espaço. Proteger versos de poema.

**Detecção de versos soltos antes da fusão:** antes de fundir fragmentos, verificar se as linhas curtas consecutivas (2+) formam verso detectável:

- Métrica: contagem de sílabas consistente (±2 sílabas entre linhas adjacentes)
- Rima: terminações fonéticas similares no final das linhas
- Estrofe: blocos de 2, 4, 6, 8 linhas separados por linha em branco

Se detectado como verso, **não fundir** e marcar com `:::poema`. Se ambíguo, preservar como linhas separadas e flagear no relatório.

### 1.5 Revisão tipográfica automática (aplicar durante transformação)

**PT-BR (Araújo):**

| Regra | Transformação |
|---|---|
| R1 | Reticências `....` / `..` → `…` |
| R2 | Ponto duplo após abreviatura (`etc..` → `etc.`) |
| R3 | Espaço antes de pontuação (`palavra ,` → `palavra,`) |
| R4 | Hífen como travessão em diálogos (`- Disse` → `— Disse`; `\s-\s` → ` — `) |
| R5 | Aspas datilográficas retas → tipográficas curvas |
| R6 | Espaço entre número e unidade (`10km` → `10 km`) |
| R7 | Meia-risca em intervalos numéricos (`10-25` → `10–25`) |

**EN (Chicago):**

| Regra | Transformação |
|---|---|
| R1 | Ellipsis → `…` |
| R2 | Double period after abbreviation |
| R3 | Space before punctuation |
| R4 | Em-dash sem espaços (`word — word` → `word—word`) |
| R5 | Straight quotes → curly; comma/period inside closing quote |
| R6 | Space between number and unit |
| R7 | En-dash in numerical ranges |

> **EN:** diálogos usam aspas duplas — nunca converter para travessão.

**Reportar (não corrigir automaticamente):** inconsistências terminológicas, siglas sem expansão, frases com algarismo inicial, mistura de sistemas de nota.

---

## FASE 2 — GERAÇÃO DO DOCX

### 2.1 Setup

```bash
npm install docx
```

### 2.2 Imports obrigatórios

```javascript
const {
  Document, Packer, Paragraph, TextRun,
  HeadingLevel, AlignmentType, FootnoteReferenceRun,
  PageBreak
} = require('docx');
const fs = require('fs');
```

### 2.3 Estilos customizados

```javascript
const STYLES = {
  default: {
    document: { run: { font: "Garamond", size: 24 } }  // 12pt
  },
  paragraphStyles: [
    {
      id: "Normal", name: "Normal", quickFormat: true,
      run: { font: "Garamond", size: 24 },
      paragraph: {
        spacing: { line: 360, lineRule: "auto" },  // 1.5 entrelinha
        indent: { firstLine: 720 }                 // 0.5 inch 1ª linha
      }
    },
    {
      id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal",
      run: { font: "Garamond", size: 36, bold: true, allCaps: true },
      paragraph: {
        alignment: AlignmentType.CENTER,
        spacing: { before: 480, after: 240 },
        outlineLevel: 0
      }
    },
    {
      id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal",
      run: { font: "Garamond", size: 30, bold: true },
      paragraph: {
        alignment: AlignmentType.CENTER,
        spacing: { before: 360, after: 180 },
        outlineLevel: 1
      }
    },
    {
      id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal",
      run: { font: "Garamond", size: 26, bold: true },
      paragraph: {
        alignment: AlignmentType.CENTER,
        spacing: { before: 240, after: 120 },
        outlineLevel: 2
      }
    },
    {
      id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal",
      run: { font: "Garamond", size: 24, bold: true, italics: true },
      paragraph: { spacing: { before: 180, after: 60 }, outlineLevel: 3 }
    },
    {
      id: "CitacaoLonga", name: "Citacao Longa", basedOn: "Normal",
      run: { font: "Garamond", size: 21 },          // 10.5pt
      paragraph: {
        indent: { left: 1400, right: 570 },
        spacing: { before: 240, after: 240 }
      }
    },
    {
      id: "Epigrafe", name: "Epigrafe", basedOn: "Normal",
      run: { font: "Garamond", size: 22 },           // 11pt
      paragraph: {
        indent: { left: 2270 },
        spacing: { before: 480, after: 120 }
      }
    },
    {
      id: "Poema", name: "Poema", basedOn: "Normal",
      run: { font: "Garamond", size: 24 },
      paragraph: {
        indent: { left: 1400 },
        spacing: { before: 0, after: 0 }
      }
    },
    {
      id: "Carta", name: "Carta", basedOn: "Normal",
      run: { font: "Garamond", size: 24 },
      paragraph: {
        indent: { left: 570 },
        spacing: { line: 276 }
      }
    }
  ]
};
```

### 2.4 Funções auxiliares de geração

```javascript
// Parsing de inline: *itálico*, **negrito**, [^n] → FootnoteReferenceRun
function parseInline(text, footnoteMap) {
  const runs = [];
  const TOKEN = /(\*\*([^*]+)\*\*|\*([^*]+)\*|\[\^(\d+)\])/g;
  let last = 0, match;
  while ((match = TOKEN.exec(text)) !== null) {
    if (match.index > last) runs.push(new TextRun(text.slice(last, match.index)));
    if (match[2]) runs.push(new TextRun({ text: match[2], bold: true }));
    else if (match[3]) runs.push(new TextRun({ text: match[3], italics: true }));
    else if (match[4]) runs.push(new FootnoteReferenceRun(parseInt(match[4])));
    last = match.index + match[0].length;
  }
  if (last < text.length) runs.push(new TextRun(text.slice(last)));
  return runs;
}

// Heading com pageBreakBefore para H1/H2/H3
function makeHeading(text, level, footnoteMap) {
  const lvlMap = {
    1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2,
    3: HeadingLevel.HEADING_3, 4: HeadingLevel.HEADING_4
  };
  return new Paragraph({
    heading: lvlMap[level],
    pageBreakBefore: level <= 3,
    children: parseInline(text, footnoteMap),
  });
}

// Parágrafo normal
function makeNormal(text, footnoteMap) {
  return new Paragraph({
    style: "Normal",
    children: parseInline(text, footnoteMap),
  });
}

// Blockquote / citação longa
function makeBlockQuote(text, footnoteMap) {
  return new Paragraph({
    style: "CitacaoLonga",
    children: parseInline(text, footnoteMap),
  });
}

// Verso de poema (nunca fundir)
function makePoem(text) {
  return new Paragraph({
    style: "Poema",
    children: [new TextRun(text)],
  });
}

// Epígrafe
function makeEpigrafe(text) {
  return new Paragraph({
    style: "Epigrafe",
    children: [new TextRun(text)],
  });
}

// Carta
function makeCarta(text, footnoteMap) {
  return new Paragraph({
    style: "Carta",
    children: parseInline(text, footnoteMap),
  });
}

// Separador de cena
function makeSeparator() {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun("* * *")],
  });
}

// Footnotes: { 1: "texto", 2: "texto", ... } → formato Document.footnotes
function buildFootnotes(footnoteMap) {
  const result = {};
  for (const [id, text] of Object.entries(footnoteMap)) {
    result[parseInt(id)] = {
      children: [new Paragraph({ children: [new TextRun(text)] })],
    };
  }
  return result;
}
```

### 2.5 Parser principal: markdown → docChildren + footnoteMap

```javascript
function parseMarkdown(markdownText) {
  const lines = markdownText.split('\n');
  const docChildren = [];
  const footnoteMap = {};
  let state = 'NORMAL';  // NORMAL | POEM | EPIGRAFE | CARTA
  let isRosto = true;    // flag: ainda estamos na página de rosto

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    const line = raw.trim();

    // ── Definições de footnote [^n]: texto ou [^n] texto ────────────────────
    // Capturar independente de estado ou posição — nunca viram parágrafos no body
    const fnDef = line.match(/^\[\^(\d+)\]:\s*(.+)$/) || line.match(/^\[\^(\d+)\]\s+(.+)$/);
    if (fnDef) {
      footnoteMap[parseInt(fnDef[1])] = fnDef[2];
      continue;
    }

    // ── Seção ## Notas — suprimir do body ───────────────────────────────────
    // As entradas [^n]: já são capturadas pelo bloco acima
    if (/^#{1,3}\s+Notas?\s*$/i.test(line)) continue;

    // ── Linha vazia ─────────────────────────────────────────────────────────
    if (line === '') continue;

    // ── Abertura/fechamento de fenced divs ──────────────────────────────────
    if (line === ':::epigrafe') { state = 'EPIGRAFE'; continue; }
    if (line === ':::poema')    { state = 'POEM';     continue; }
    if (line === ':::carta')    { state = 'CARTA';    continue; }
    if (line === ':::')         { state = 'NORMAL';   continue; }

    // ── Conteúdo dentro de fenced divs ──────────────────────────────────────
    if (state === 'POEM')     { docChildren.push(makePoem(line));              continue; }
    if (state === 'EPIGRAFE') { docChildren.push(makeEpigrafe(line));          continue; }
    if (state === 'CARTA')    { docChildren.push(makeCarta(line, footnoteMap)); continue; }

    // ── Separadores ─────────────────────────────────────────────────────────
    if (['---', '* * *', '***'].includes(line)) {
      docChildren.push(makeSeparator());
      continue;
    }

    // ── Headings ─────────────────────────────────────────────────────────────
    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const text  = headingMatch[2];

      // Página de rosto: # → Title, ## → Subtitle (nas primeiras 10 linhas)
      if (isRosto && level === 1) {
        docChildren.push(new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text, allCaps: true, bold: true, size: 48, font: "Garamond" })]
        }));
        continue;
      }
      if (isRosto && level === 2) {
        docChildren.push(new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text, size: 28, font: "Garamond" })]
        }));
        // Quebra de página após a página de rosto
        if (i + 1 < lines.length && lines[i + 1].trim() === '') {
          docChildren.push(new Paragraph({ children: [new PageBreak()] }));
          isRosto = false;
        }
        continue;
      }

      isRosto = false;
      docChildren.push(makeHeading(text, level, footnoteMap));
      continue;
    }

    // ── Blockquote ───────────────────────────────────────────────────────────
    if (line.startsWith('> ')) {
      docChildren.push(makeBlockQuote(line.slice(2), footnoteMap));
      continue;
    }

    // ── Parágrafo normal ─────────────────────────────────────────────────────
    isRosto = false;
    docChildren.push(makeNormal(line, footnoteMap));
  }

  return { docChildren, footnoteMap };
}
```

### 2.6 Montagem e exportação do Document

```javascript
async function gerarDocx(markdownPath, outputPath) {
  const markdownText = fs.readFileSync(markdownPath, 'utf8');
  const { docChildren, footnoteMap } = parseMarkdown(markdownText);

  const doc = new Document({
    styles: STYLES,
    footnotes: buildFootnotes(footnoteMap),
    sections: [{
      properties: {
        page: {
          // 6×9 polegadas — formato KDP padrão para e-books literários
          size: { width: 8640, height: 13920 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      children: docChildren
    }]
  });

  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputPath, buffer);
  console.log(`✓ Gerado: ${outputPath}`);
  console.log(`  Parágrafos: ${docChildren.length}`);
  console.log(`  Footnotes: ${Object.keys(footnoteMap).length}`);
}

gerarDocx('ebook_intermediario.md', 'output.docx');
```

### 2.7 Validação

```bash
python scripts/office/validate.py output.docx
```

Se `scripts/office/validate.py` não existir, validação alternativa:

```bash
# 1. Verificar integridade do zip do docx
unzip -t output.docx

# 2. Extrair e verificar estrutura
mkdir -p /tmp/docx_check
cp output.docx /tmp/docx_check/
cd /tmp/docx_check && unzip -o output.docx

# 3. Verificar se document.xml existe e tem conteúdo
test -s word/document.xml && echo "✓ document.xml presente"
test -s word/footnotes.xml && echo "✓ footnotes.xml presente"

# 4. Contar referências e definições de footnotes no document.xml
#    (deve bater com o relatório da Fase 3)
echo "Refs no document.xml:"
grep -o 'w:footnoteReference' word/document.xml | wc -l
echo "Defs no footnotes.xml:"
grep -o '<w:footnote ' word/footnotes.xml | wc -l
```

Se falhar, desempacotar e inspecionar:

```bash
python scripts/office/unpack.py output.docx unpacked/
# Verificar:
#   unpacked/word/document.xml  — estrutura dos parágrafos e heading styles
#   unpacked/word/footnotes.xml — presença e conteúdo de todas as notas
python scripts/office/pack.py unpacked/ output_fixed.docx --original output.docx
```

---

## FASE 3 — RELATÓRIO FINAL

```
RELATÓRIO DE FORMATAÇÃO
══════════════════════════════════════════════════
Idioma: PT-BR | Norma: Araújo
Pipeline: TXT → Markdown → DOCX

LIMPEZA E ESTRUTURA
  Fragmentos fundidos: N
  Sumário removido do body: sim (linhas X–Y)
  Hierarquia aplicada: H1: N | H2: N | H3: N | H4: N

TÍTULOS PROMOVIDOS (confirmar ausência de falsos positivos):
  L.34  → Heading3: "CAPÍTULO I — A Chegada"
  L.67  → Heading2: "PARTE SEGUNDA"
  [lista completa]

NOTAS DE RODAPÉ
  Referências [^n] no corpo: 47
  Definições capturadas (seção ## Notas): 47
  Footnotes Word nativas geradas: 47
  Paridade: ✓ completa

ELEMENTOS ESPECIAIS
  Epígrafes: N | Citações longas: N | Poemas: N | Cartas: N | Separadores: N

REVISÃO TIPOGRÁFICA
  Correções automáticas: N total
    R4 hífen → travessão: N | R5 aspas retas → tipográficas: N | [demais]
  Para revisão manual:
    Terminologia inconsistente: [lista ou "nenhuma"]
    Siglas sem expansão: [lista ou "nenhuma"]
    Frases com algarismo inicial: N

AMBÍGUOS NÃO RESOLVIDOS:
  L.312: "A CHEGADA" — mantido como Normal; aguarda decisão do editor

Arquivo: output.docx
Validação: ✓ passou
══════════════════════════════════════════════════
```

---

## REFERÊNCIA RÁPIDA — MAPA COMPLETO

| Elemento no TXT | Markdown intermediário | Word Style | Quebra de pág. |
|---|---|---|---|
| Título da obra (1ª linha) | `# Título` | `Title` (allCaps) | — |
| Nome do autor | `## Autor` | `Subtitle` | após |
| TOMO / VOLUME | `# TOMO I` | `Heading1` | antes |
| PARTE / PART | `## PARTE I` | `Heading2` | antes |
| CAPÍTULO / CHAPTER | `### CAPÍTULO I — Título` | `Heading3` | antes |
| Subcapítulo / cena | `#### texto` | `Heading4` | nunca |
| Citação longa | `> texto` | `CitacaoLonga` | — |
| Epígrafe | `:::epigrafe … :::` | `Epigrafe` | — |
| Poema | `:::poema … :::` | `Poema` | — |
| Carta | `:::carta … :::` | `Carta` | — |
| Separador de cena | `---` ou `* * *` | Normal, centralizado | — |
| Referência de nota | `[^n]` no texto | `FootnoteReferenceRun` | — |
| Definição de nota / `## Notas` | `[^n]: texto` | Footnote nativa Word | — |
| Texto narrativo | parágrafo simples | `Normal` | — |
| Itálico | `*texto*` | inline italic | — |
| Negrito | `**texto**` | inline bold | — |
| Lixo de pipeline | removido na Fase 0A | — | — |

---

## REGRAS DE OURO (nunca violar)

1. **Análise antes de qualquer escrita.** Completar a Fase 0 e apresentar o relatório antes de transformar uma linha.
2. **`## Notas` não é removida — é migrada.** As definições `[^n]:` viram footnotes Word nativas. O bloco `## Notas` é suprimido do body docx, não apagado antes da extração.
3. **Footnote sem par = erro bloqueante.** Se `[^3]` aparece no corpo mas não há `[^3]:` nas definições (ou vice-versa), parar e reportar ao usuário antes de gerar o docx.
4. **Não inventar hierarquia.** Sem rótulos estruturais reconhecíveis → não criar headings; reportar ao editor.
5. **Não fundir versos.** Linhas dentro de `:::poema` são intencionalmente curtas — nunca fundir.
6. **Formatação inline via TextRun, nunca via mudança de estilo de parágrafo.**
7. **Separadores como texto `* * *`, nunca como linha horizontal** — não converte bem em ePub.
8. **Padrões ambíguos vão para o relatório** — não promover automaticamente; flagear para revisão do editor.
9. **Validar o docx gerado** — sempre executar `validate.py` antes de entregar ao usuário.
10. **Normalizar definição quebrada:** `[^n] texto` sem `:` é definição válida — normalizar para `[^n]: texto` automaticamente.
11. **Dedup de notas:** mesmo texto → mesmo id; textos diferentes com mesmo id → IDs distintos por ordem de ocorrência.
12. **Remover lixo de pipeline antes de qualquer análise estrutural.** `TRADUÇÃO`, `#tradução`, `REVISÃO`, `OCR` etc. — eliminar como primeira etapa.
