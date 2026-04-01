import pandas as pd
import re
import time
import sys
import unicodedata
from difflib import SequenceMatcher


def reformatar_titulo(titulo):
    """Converte título para maiúsculas e remove caracteres não-alfabéticos."""
    if pd.isna(titulo):
        return ""
    titulo = str(titulo).upper()
    titulo = re.sub(r'[^A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ ]', '', titulo)
    titulo = re.sub(r'\s+', ' ', titulo).strip()
    return titulo


def normalizar_sobrenome(s):
    """Remove acentos e caracteres especiais, retorna em maiúsculas."""
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^A-Za-z]', '', s)
    return s.upper()


def extrair_sobrenomes(autores_str):
    if pd.isna(autores_str) or str(autores_str).strip() == '':
        return set()

    raw = str(autores_str)
    # Separar autores
    partes = re.split(r';| and ', raw, flags=re.IGNORECASE)

    tokens = set()
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        # Remover pontuação e separar em palavras
        palavras = re.split(r'[\s,.\-]+', parte)
        for p in palavras:
            p_norm = normalizar_sobrenome(p)
            # Ignorar tokens muito curtos (iniciais soltas como "G", "M", "MN")
            if len(p_norm) > 2:
                tokens.add(p_norm)

    return tokens


def autores_compativeis(set_a, set_b):
    """
    True se os sets de sobrenomes têm ao menos um elemento em comum.
    Se qualquer set estiver vazio (info ausente), dá benefício da dúvida -> True.
    """
    if not set_a or not set_b:
        return True
    return bool(set_a & set_b)


def similaridade_palavras(titulo1, titulo2):
    palavras1 = titulo1.split()
    palavras2 = titulo2.split()

    if not palavras1 or not palavras2:
        return 0.0

    matcher = SequenceMatcher(None, palavras1, palavras2)
    palavras_em_comum = sum(b.size for b in matcher.get_matching_blocks())
    return palavras_em_comum / max(len(palavras1), len(palavras2))


def main():
    print("=" * 60)
    print("   DETECTOR DE DUPLICATAS - MAPEAMENTO SISTEMÁTICO")
    print("=" * 60)

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

    for col in ['id', 'Title']:
        if col not in df.columns:
            print(f"Erro: coluna '{col}' não encontrada no CSV.")
            sys.exit(1)

    tem_original = 'Title_original' in df.columns and 'id_original' in df.columns
    tem_autores  = 'Authors' in df.columns

    if not tem_autores:
        print("  (coluna 'Authors' não encontrada — validação por autores será ignorada)\n")

    print("Reformatando títulos...")
    df['_titulo_fmt'] = df['Title'].apply(reformatar_titulo)

    if tem_autores:
        print("Extraindo sobrenomes dos autores...")
        sobrenomes_por_linha = [extrair_sobrenomes(a) for a in df['Authors']]
    else:
        sobrenomes_por_linha = [set()] * len(df)

    df['Repetido'] = ''

    n               = len(df)
    total_t_t       = n * (n - 1) // 2
    comparacoes_tt  = 0
    duplicatas_titulo = 0

    ids     = df['id'].tolist()
    titulos = df['_titulo_fmt'].tolist()

    # ----------------------------------------------------------------
    # Lista deduplicada de Title_original
    # ----------------------------------------------------------------
    lista_originais = []
    if tem_original:
        print("Construindo lista deduplicada de Title_original...")
        vistos = {}
        for _, row in df.iterrows():
            t_fmt = reformatar_titulo(row['Title_original'])
            if t_fmt and t_fmt not in vistos:
                vistos[t_fmt] = str(row['id_original'])
        lista_originais = [{'titulo_fmt': k, 'id_original': v} for k, v in vistos.items()]
        print(f"  → {len(df):,} linhas → {len(lista_originais):,} títulos originais únicos\n")
    else:
        print("  (colunas Title_original / id_original não encontradas — etapa ignorada)\n")

    total_t_orig = n * len(lista_originais)

    print(f"Iniciando comparações Title×Title ({total_t_t:,} pares)...")
    if lista_originais:
        print(f"Iniciando comparações Title×Title_original ({total_t_orig:,} pares)...")
    print()

    inicio = time.time()

    repeticoes_raw = {i: [] for i in range(n)}

    for i in range(n):
        # Fase 1: Title × Title
        for j in range(i + 1, n):
            comparacoes_tt += 1
            if similaridade_palavras(titulos[i], titulos[j]) > 0.95:
                repeticoes_raw[i].append((str(ids[j]), j))
                repeticoes_raw[j].append((str(ids[i]), i))
                duplicatas_titulo += 1

        # Fase 2: Title[i] × Title_original único
        for orig in lista_originais:
            if similaridade_palavras(titulos[i], orig['titulo_fmt']) > 0.95:
                id_orig_str = orig['id_original']
                if not any(e[0] == id_orig_str for e in repeticoes_raw[i]):
                    repeticoes_raw[i].append((id_orig_str, None))
                    duplicatas_titulo += 1

        # Progresso
        total_geral = total_t_t + total_t_orig
        comp_geral  = comparacoes_tt + (i + 1) * len(lista_originais)
        pct = comp_geral / total_geral * 100 if total_geral > 0 else 100.0
        elapsed = time.time() - inicio
        eta_str = ""
        if comp_geral > 0 and elapsed > 0:
            eta_str = f" | ETA: {(total_geral - comp_geral) / (comp_geral / elapsed):.0f}s"

        print(
            f"\rLinha {i+1:>6}/{n} | Progresso: {pct:6.2f}% | "
            f"Duplicatas (título): {duplicatas_titulo}{eta_str}          ",
            end='', flush=True
        )

    print("\n")

    # ----------------------------------------------------------------
    # Validação por autores
    # ----------------------------------------------------------------
    descartados = 0
    # Cada entrada: {'id_A': str, 'title_A': str, 'authors_A': str,
    #                'id_B': str, 'title_B': str, 'authors_B': str}
    registros_descartados = []

    if tem_autores:
        print("Validando duplicatas por autores...")
        for i in range(n):
            validas = []
            for (id_str, j_idx) in repeticoes_raw[i]:
                if j_idx is not None:
                    compativel = autores_compativeis(
                        sobrenomes_por_linha[i],
                        sobrenomes_por_linha[j_idx]
                    )
                    if not compativel:
                        descartados += 1
                        # Registrar o par descartado (evitar duplicar: só registra quando i < j_idx)
                        if i < j_idx:
                            registros_descartados.append({
                                'id_A':      ids[i],
                                'Title_A':   df.at[i, 'Title'],
                                'Authors_A': df.at[i, 'Authors'],
                                'id_B':      ids[j_idx],
                                'Title_B':   df.at[j_idx, 'Title'],
                                'Authors_B': df.at[j_idx, 'Authors'],
                            })
                    else:
                        validas.append((id_str, j_idx))
                else:
                    # Veio de Title_original, sem Authors correspondente → mantém
                    validas.append((id_str, j_idx))

            repeticoes_raw[i] = validas

        print(f"  → {descartados:,} marcações removidas por autores incompatíveis\n")

    # ----------------------------------------------------------------
    # Preencher coluna 'Repetido' e salvar CSV principal
    # ----------------------------------------------------------------
    for i in range(n):
        ids_finais = [e[0] for e in repeticoes_raw[i]]
        if ids_finais:
            df.at[i, 'Repetido'] = ','.join(ids_finais)

    df.drop(columns=['_titulo_fmt'], inplace=True)

    nome_saida = input("Digite o nome do arquivo CSV de saída principal: ").strip()
    if not nome_saida.lower().endswith('.csv'):
        nome_saida += '.csv'

    df.to_csv(nome_saida, index=False, encoding='utf-8')

    # ----------------------------------------------------------------
    # Salvar CSV de descartados por autores
    # ----------------------------------------------------------------
    if tem_autores and registros_descartados:
        nome_descartados = input("Digite o nome do CSV de pares descartados por autores: ").strip()
        if not nome_descartados.lower().endswith('.csv'):
            nome_descartados += '.csv'

        df_descartados = pd.DataFrame(registros_descartados, columns=[
            'id_A', 'Title_A', 'Authors_A',
            'id_B', 'Title_B', 'Authors_B',
        ])
        df_descartados.to_csv(nome_descartados, index=False, encoding='utf-8')
        print(f"  → CSV de descartados salvo: '{nome_descartados}' ({len(df_descartados)} pares)\n")
    elif tem_autores:
        print("  (nenhum par foi descartado por autores — CSV de descartados não gerado)\n")
        nome_descartados = None
    else:
        nome_descartados = None

    # ----------------------------------------------------------------
    # Estatísticas finais
    # ----------------------------------------------------------------
    tempo_total = time.time() - inicio
    linhas_com_repeticao = df[df['Repetido'] != ''].shape[0]

    print("\n" + "=" * 60)
    print("   ESTATÍSTICAS FINAIS")
    print("=" * 60)
    print(f"  Total de artigos analisados        : {n:,}")
    print(f"  Comparações Title x Title          : {total_t_t:,}")
    if lista_originais:
        print(f"  Títulos originais únicos           : {len(lista_originais):,}")
        print(f"  Comparações Title x T.Original     : {total_t_orig:,}")
    print(f"  Duplicatas por título (brutas)     : {duplicatas_titulo:,}")
    if tem_autores:
        print(f"  Removidas por autores diferentes   : {descartados:,}")
        print(f"  Duplicatas confirmadas             : {duplicatas_titulo - descartados:,}")
    print(f"  Artigos marcados como repet.       : {linhas_com_repeticao:,}")
    print(f"  Tempo de execução                  : {tempo_total:.2f} segundos")
    print(f"  Arquivo principal                  : {nome_saida}")
    if nome_descartados:
        print(f"  Arquivo de descartados             : {nome_descartados}")
    print("=" * 60)


if __name__ == '__main__':
    main()
