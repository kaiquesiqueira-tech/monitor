"""
Gera o arquivo dados.js do monitor de compras a partir dos relatórios do Protheus.

Como usar:
    1) Exporte os três browses para Excel e salve na pasta ./dados com estes nomes:
         dados/mata110.xlsx      -> Solicitações de compra em aberto
         dados/mata121.xlsx      -> Pedidos de compra em aberto
         dados/PROD_EM_PP.xlsx   -> SBZ, produtos com ponto de pedido
    2) pip install pandas openpyxl
    3) python gerar_dados.py
    4) commit e push. O site atualiza sozinho.

O script não altera o index.html: toda a lógica da tela fica lá, os dados ficam aqui.
"""

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
ENTRADA = BASE / "dados"
SAIDA = BASE / "dados.js"

ARQ_SC = ENTRADA / "mata110.xlsx"
ARQ_PC = ENTRADA / "mata121.xlsx"
ARQ_PP = ENTRADA / "PROD_EM_PP.xlsx"


def conferir_arquivos():
    faltando = [a.name for a in (ARQ_SC, ARQ_PC, ARQ_PP) if not a.exists()]
    if faltando:
        print("Faltam arquivos na pasta 'dados': " + ", ".join(faltando))
        print("Exporte os browses do Protheus com esses nomes e rode de novo.")
        sys.exit(1)


def codigo(v):
    """Normaliza código de produto para 9 dígitos com zeros à esquerda."""
    if isinstance(v, float):
        v = int(v)
    return str(v).strip().zfill(9)


def filial(texto):
    """'020102-TGM - FILIAL BARRO ALTO' -> ('020102', 'TGM')."""
    cod, resto = str(texto).split("-", 1)
    empresa = resto.split(" - ")[0].strip()
    if "BARRO ALTO 2" in resto.upper():
        empresa += " 2"
    return cod.strip(), empresa


def data(v):
    return "" if pd.isna(v) else pd.Timestamp(v).strftime("%Y-%m-%d")


def inteiro(v):
    return "" if pd.isna(v) else str(int(v)).zfill(6)


def ler_parametros(codigos_usados):
    """Lê o SBZ e devolve os parâmetros de estoque por filial+produto."""
    df = pd.read_excel(ARQ_PP, header=2)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(subset=["Codigo"]).copy()
    df["cod"] = df["Codigo"].apply(codigo)
    df["fil"] = df["Filial"].astype(int).astype(str).str.zfill(6)

    def num(coluna):
        return pd.to_numeric(df[coluna], errors="coerce").fillna(0)

    campos = {
        "pp": num("Ponto Pedido"),
        "lote": num("Lote Econom."),
        "emax": num("Estoq Maximo"),
        "seg": num("Seguranca"),
        "emb": num("Qtd.Embalag."),
        "ultpreco": num("Ult. Preco"),
    }

    parm = {}
    for i, linha in df.iterrows():
        if linha["cod"] not in codigos_usados:
            continue  # só guarda parâmetro de item que aparece em pedido ou solicitação
        chave = linha["fil"] + "|" + linha["cod"]
        valor = [
            float(campos["pp"][i]), float(campos["lote"][i]), float(campos["emax"][i]),
            float(campos["seg"][i]), float(campos["emb"][i]), float(campos["ultpreco"][i]),
            data(linha["Ult. Compra"]), data(linha["Cons.Inicial"]), data(linha["Data Incl."]),
            str(linha["Armazem Pad."]).strip().zfill(2),
        ]
        if chave not in parm or valor[0] > parm[chave][0]:
            parm[chave] = valor

    total_pp = len(df)  # linhas com código válido
    return parm, total_pp


def main():
    conferir_arquivos()
    sc = pd.read_excel(ARQ_SC, header=1)
    pc = pd.read_excel(ARQ_PC, header=1)

    usados = {codigo(x) for x in pc["Produto"]} | {codigo(x) for x in sc["Produto"]}
    parm, total_pp = ler_parametros(usados)

    # melhor parâmetro do produto em qualquer filial, usado quando falta cadastro na filial da linha
    por_codigo = {}
    for chave, valor in parm.items():
        cod = chave.split("|")[1]
        if cod not in por_codigo or valor[0] > por_codigo[cod][0]:
            por_codigo[cod] = valor

    def situacao(fil, cod):
        """2 = tem ponto de pedido na filial, 1 = em outra filial, 0 = não tem."""
        if fil + "|" + cod in parm:
            return 2, parm[fil + "|" + cod]
        if cod in por_codigo:
            return 1, por_codigo[cod]
        return 0, [0, 0, 0, 0, 0, 0, "", "", "", ""]

    pedidos = []
    for _, r in pc.iterrows():
        f, empresa = filial(r["Filial"])
        cod = codigo(r["Produto"])
        pp, p = situacao(f, cod)
        pedidos.append([
            f, empresa, str(r["Numero"]).zfill(6), cod, str(r["Descricao"]).strip(),
            float(r["Quantidade"]), str(r["Unidade"]).strip(), float(r["Prc Unitario"]),
            data(r["Data Emissao"]), data(r["Dt. Entrega"]), str(r["Fornecedor"]).strip(),
            str(r["Comprador"]).strip(), inteiro(r["Numero da SC"]), cod[:4],
            "" if pd.isna(r["Centro Custo"]) else str(int(r["Centro Custo"])), pp, p[0], p[1],
        ])

    solicitacoes = []
    for _, r in sc.iterrows():
        f, empresa = filial(r["Filial"])
        cod = codigo(r["Produto"])
        pp, p = situacao(f, cod)
        solicitacoes.append([
            f, empresa, str(r["Numero da SC"]).zfill(6), str(r["Item da SC"]).zfill(4), cod,
            str(r["Descricao"]).strip(), float(r["Quantidade"]), str(r["Unid Medida"]).strip(),
            data(r["DT Emissao"]), cod[:4],
            "" if pd.isna(r["Centro Custo"]) else str(int(r["Centro Custo"])), pp, p[0], p[1],
        ])

    saida = {
        "pc_cols": ["filial", "emp", "pedido", "produto", "desc", "qtd", "um", "preco",
                    "emissao", "entrega", "forn", "comprador", "sc", "grupo", "cc",
                    "pp", "ppq", "lote"],
        "sc_cols": ["filial", "emp", "sc", "item", "produto", "desc", "qtd", "um",
                    "emissao", "grupo", "cc", "pp", "ppq", "lote"],
        "parm_cols": ["pp", "lote", "emax", "seg", "emb", "ultpreco",
                      "ultcompra", "consini", "dtincl", "armazem"],
        "pc": pedidos,
        "sc": solicitacoes,
        "parm": parm,
        "gerado": date.today().isoformat(),
        "npp": total_pp,
    }

    SAIDA.write_text(
        "window.DADOS=" + json.dumps(saida, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    com_pp = sum(1 for linha in pedidos if linha[15] == 2)
    print(f"dados.js gerado com {len(pedidos)} linhas de pedido e {len(solicitacoes)} de solicitação.")
    print(f"{com_pp} linhas de pedido são de itens com ponto de pedido na própria filial.")
    print("Agora é só commitar e dar push.")


if __name__ == "__main__":
    main()
