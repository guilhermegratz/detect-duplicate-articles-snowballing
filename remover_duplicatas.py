import pandas as pd
import sys


class UnionFind:
    def __init__(self):
        self.pai = {}

    def encontrar(self, x):
        if x not in self.pai:
            self.pai[x] = x
        if self.pai[x] != x:
            self.pai[x] = self.encontrar(self.pai[x])  # compressão de caminho
        return self.pai[x]

    def unir(self, x, y):
        rx, ry = self.encontrar(x), self.encontrar(y)
        if rx == ry:
            return
        # O menor id vira raiz do grupo
        if rx < ry:
            self.pai[ry] = rx
        else:
            self.pai[rx] = ry


def main():
    print("=" * 60)
    print("   REMOVEDOR DE DUPLICATAS - MAPEAMENTO SISTEMÁTICO")
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

    print(f"Arquivo carregado: {len(df)} linhas.\n")

    for col in ['id', 'Repetido']:
        if col not in df.columns:
            print(f"Erro: coluna '{col}' não encontrada no CSV.")
            sys.exit(1)

    df['id'] = df['id'].astype(str)

    # ----------------------------------------------------------------
    # Construir grupos de duplicatas com Union-Find
    # ----------------------------------------------------------------
    uf = UnionFind()

    for _, row in df.iterrows():
        repetido = str(row['Repetido']).strip()
        if repetido == '' or repetido == 'nan':
            continue
        id_linha = str(row['id'])
        for id_dup in repetido.split(','):
            id_dup = id_dup.strip()
            if id_dup:
                uf.unir(id_linha, id_dup)

    # Para cada id que participou de algum grupo, encontrar sua raiz.
    # A raiz de cada grupo é sempre o menor id (garantido pela lógica de unir).
    # Todos os ids que NÃO são raiz do próprio grupo devem ser deletados.
    ids_para_deletar = set()
    for id_str in uf.pai:
        raiz = uf.encontrar(id_str)
        if id_str != raiz:
            ids_para_deletar.add(id_str)

    print(f"Grupos de duplicatas encontrados : {len(set(uf.encontrar(x) for x in uf.pai)):,}")
    print(f"IDs marcados para remoção        : {len(ids_para_deletar):,}")

    n_antes = len(df)
    df_limpo = df[~df['id'].isin(ids_para_deletar)].copy()
    n_depois = len(df_limpo)

    print(f"Linhas removidas                 : {n_antes - n_depois:,}")
    print(f"Linhas restantes                 : {n_depois:,}\n")

    nome_saida = input("Digite o nome do arquivo CSV de saída: ").strip()
    if not nome_saida.lower().endswith('.csv'):
        nome_saida += '.csv'

    df_limpo = df_limpo.drop(columns=['Repetido'], errors='ignore')
    df_limpo.to_csv(nome_saida, index=False, encoding='utf-8')

    print("\n" + "=" * 60)
    print("   ESTATÍSTICAS FINAIS")
    print("=" * 60)
    print(f"  Linhas no arquivo original : {n_antes:,}")
    print(f"  Linhas removidas           : {n_antes - n_depois:,}")
    print(f"  Linhas no arquivo limpo    : {n_depois:,}")
    print(f"  Arquivo de saída           : {nome_saida}")
    print("=" * 60)


if __name__ == '__main__':
    main()
