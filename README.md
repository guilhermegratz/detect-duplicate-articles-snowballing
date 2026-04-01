# Detector e Removedor de Duplicatas — Mapeamento Sistemático

Dois scripts Python para identificação e remoção de artigos duplicados em bases bibliográficas geradas durante a fase de snowballing de um mapeamento sistemático.

---

## Requisitos

- **Python 3.10+**
- Biblioteca `pandas` (`pip install pandas`)
- Uso de ambiente virtual é recomendado: [tutorial venv](https://docs.python.org/3/library/venv.html)

---

## Script 1 — `detect_duplicates.py`

Detecta duplicatas e anota os ids dos artigos duplicados em uma nova coluna `Repetido`.

### Uso

```bash
python detect_duplicates.py
```

O script pedirá no terminal o nome do CSV de entrada e os nomes dos arquivos de saída.

### CSV de entrada

| Coluna | Obrigatória | Descrição |
|---|---|---|
| `id` | Sim | Identificador único de cada artigo |
| `Title` | Sim | Título do artigo |
| `Authors` | Não | Autores. Se ausente, a validação por autores é ignorada |
| `Title_original` | Não (par) | Título na base de origem (snowballing) |
| `id_original` | Não (par) | ID na base de origem. Deve estar presente junto com `Title_original` |

Colunas adicionais são preservadas integralmente. O arquivo deve estar em UTF-8 (latin-1 é tentado como fallback).

### Saídas

**CSV principal** — idêntico à entrada, com a coluna `Repetido` adicionada ao final. Ela fica vazia se o artigo não tem duplicatas, ou contém os `id`s dos artigos duplicados separados por vírgula (ex: `733,1583`).

**CSV de descartados** — gerado apenas se houver pares rejeitados na validação de autores. Contém as colunas `id_A`, `Title_A`, `Authors_A`, `id_B`, `Title_B`, `Authors_B` para revisão manual.

---

## Script 2 — `remover_duplicatas.py`

Lê o CSV de saída do Script 1 e remove as linhas duplicadas, mantendo para cada grupo de duplicatas apenas o artigo com o **menor `id`**.

### Uso

```bash
python remover_duplicatas.py
```

O script pedirá no terminal o nome do CSV de entrada e o nome do arquivo de saída.

### CSV de entrada

Deve ser o arquivo gerado pelo Script 1. As colunas `id` e `Repetido` são obrigatórias.

### Saída

CSV idêntico à entrada, sem a coluna `Repetido` e sem as linhas removidas.

---

## Fluxo recomendado

```
CSV bruto  →  detect_duplicates.py  →  CSV com coluna Repetido  →  remover_duplicatas.py  →  CSV limpo
                                    ↘
                                      CSV de descartados (revisão manual opcional)
```

---

## Limitações

- Nomes de autores com caracteres especiais podem ser corrompidos dependendo do encoding do arquivo de origem, causando falsos negativos na validação de autores.
- O número de comparações cresce quadraticamente com N. Para bases acima de 5.000 artigos a execução pode demorar vários minutos.
