import pandas as pd
import re
import time
import sys
from difflib import SequenceMatcher


def reformatar_titulo(titulo):
    """Converte título para maiúsculas e remove caracteres não-alfabéticos."""
    if pd.isna(titulo):
        return ""
    titulo = str(titulo).upper()
    titulo = re.sub(r'[^A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ ]', '', titulo)
    titulo = re.sub(r'\s+', ' ', titulo).strip()
    return titulo


def similaridade_palavras(titulo1, titulo2):
    """
    Compara duas strings de título (já reformatadas) dividindo em listas de palavras
    e verificando se mais de 95% das palavras do título menor estão presentes
    na mesma ordem relativa no título maior.
    """
    palavras1 = titulo1.split()
    palavras2 = titulo2.split()

    if not palavras1 or not palavras2:
        return 0.0

    # Usar SequenceMatcher para comparar listas de palavras
    matcher = SequenceMatcher(None, palavras1, palavras2)
    blocos = matcher.get_matching_blocks()

    palavras_em_comum = sum(b.size for b in blocos)
    total_palavras = max(len(palavras1), len(palavras2))

    return palavras_em_comum / total_palavras


def main():
    print("=" * 60)
    print("   DETECTOR DE DUPLICATAS - MAPEAMENTO SISTEMÁTICO")
    print("=" * 60)

    # Leitura do arquivo de entrada
    nome_entrada = input("\nDigite o nome do arquivo CSV de entrada: ").strip()
    if not nome_entrada.lower().endswith('.csv'):
        nome_entrada += '.csv'

    print(f"\nCarregando '{nome_entrada}'...")
    try:
        df = pd.read_csv(nome_entrada, encoding='utf-8', low_memory=False)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(nome_entrada, encoding='latin-1', low_memory=False)
        except Exception as e:
            print(f"Erro ao ler o arquivo: {e}")
            sys.exit(1)
    except FileNotFoundError:
        print(f"Arquivo '{nome_entrada}' não encontrado.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        sys.exit(1)

    print(f"Arquivo carregado com sucesso: {len(df)} linhas.\n")

    # Verificar colunas obrigatórias
    colunas_necessarias = ['id', 'Title']
    for col in colunas_necessarias:
        if col not in df.columns:
            print(f"Erro: coluna '{col}' não encontrada no CSV.")
            sys.exit(1)

    tem_original = 'Title_original' in df.columns and 'id_original' in df.columns

    # Criar coluna de título reformatado (temporária)
    print("Reformatando títulos...")
    df['_titulo_fmt'] = df['Title'].apply(reformatar_titulo)

    # Inicializar coluna 'Repetido'
    df['Repetido'] = ''

    n = len(df)
    total_comparacoes = n * (n - 1) // 2
    comparacoes_feitas = 0
    duplicatas_encontradas = 0

    # Converter coluna id para lista para acesso rápido
    ids = df['id'].tolist()
    titulos = df['_titulo_fmt'].tolist()

    # ----------------------------------------------------------------
    # Construir lista deduplicada de Title_original
    # ----------------------------------------------------------------
    lista_originais = []  # cada item: {'titulo_fmt': str, 'id_original': str}
    if tem_original:
        print("Construindo lista deduplicada de Title_original...")
        vistos = {}  # titulo_fmt -> id_original (primeiro encontrado)
        for _, row in df.iterrows():
            t_fmt = reformatar_titulo(row['Title_original'])
            if t_fmt == "":
                continue
            if t_fmt not in vistos:
                vistos[t_fmt] = str(row['id_original'])
        lista_originais = [{'titulo_fmt': k, 'id_original': v} for k, v in vistos.items()]
        print(f"  → {len(df):,} linhas → {len(lista_originais):,} títulos originais únicos\n")
    else:
        print("  (colunas Title_original / id_original não encontradas — etapa ignorada)\n")

    total_comparacoes_orig = n * len(lista_originais)

    print(f"Iniciando comparações Title×Title ({total_comparacoes:,} pares)...")
    if lista_originais:
        print(f"Iniciando comparações Title×Title_original ({total_comparacoes_orig:,} pares)...")
    print()

    inicio = time.time()

    # Dicionário para acumular repetições: chave = índice da linha, valor = lista de ids repetidos
    repeticoes = {i: [] for i in range(n)}

    for i in range(n):
        # --- Fase 1: comparação Title × Title (apenas j > i) ---
        for j in range(i + 1, n):
            comparacoes_feitas += 1
            sim = similaridade_palavras(titulos[i], titulos[j])
            if sim > 0.95:
                repeticoes[i].append(str(ids[j]))
                repeticoes[j].append(str(ids[i]))
                duplicatas_encontradas += 1

        # --- Fase 2: comparação Title[i] × cada Title_original único ---
        for orig in lista_originais:
            sim = similaridade_palavras(titulos[i], orig['titulo_fmt'])
            if sim > 0.95:
                id_orig_str = orig['id_original']
                # Evitar adicionar o próprio id_original da linha caso sejam o mesmo artigo
                if id_orig_str not in repeticoes[i]:
                    repeticoes[i].append(id_orig_str)
                    duplicatas_encontradas += 1

        # Imprimir progresso ao final de cada linha verificada
        total_geral = total_comparacoes + total_comparacoes_orig
        comp_geral = comparacoes_feitas + (i + 1) * len(lista_originais)
        pct = comp_geral / total_geral * 100 if total_geral > 0 else 100.0
        elapsed = time.time() - inicio
        if comp_geral > 0 and elapsed > 0:
            taxa = comp_geral / elapsed
            restante = (total_geral - comp_geral) / taxa
            eta_str = f" | ETA: {restante:.0f}s"
        else:
            eta_str = ""

        print(
            f"\rLinha {i+1:>6}/{n} | Progresso: {pct:6.2f}% | "
            f"Duplicatas: {duplicatas_encontradas}{eta_str}          ",
            end='',
            flush=True
        )

    print("\n")  # Nova linha após a barra de progresso

    # Preencher coluna 'Repetido'
    for i in range(n):
        if repeticoes[i]:
            df.at[i, 'Repetido'] = ','.join(repeticoes[i])

    # Remover coluna temporária
    df.drop(columns=['_titulo_fmt'], inplace=True)

    # Leitura do nome do arquivo de saída
    nome_saida = input("Digite o nome do arquivo CSV de saída: ").strip()
    if not nome_saida.lower().endswith('.csv'):
        nome_saida += '.csv'

    df.to_csv(nome_saida, index=False, encoding='utf-8')

    tempo_total = time.time() - inicio

    # Estatísticas finais
    linhas_com_repeticao = df[df['Repetido'] != ''].shape[0]

    print("\n" + "=" * 60)
    print("   ESTATÍSTICAS FINAIS")
    print("=" * 60)
    print(f"  Total de artigos analisados   : {n:,}")
    print(f"  Comparações Title x Title     : {total_comparacoes:,}")
    if lista_originais:
        print(f"  Títulos originais únicos      : {len(lista_originais):,}")
        print(f"  Comparações Title x T.Orig.   : {total_comparacoes_orig:,}")
    print(f"  Duplicatas encontradas (total) : {duplicatas_encontradas:,}")
    print(f"  Artigos marcados como repet.  : {linhas_com_repeticao:,}")
    print(f"  Tempo de execução             : {tempo_total:.2f} segundos")
    print(f"  Arquivo de saída              : {nome_saida}")
    print("=" * 60)


if __name__ == '__main__':
    main()
