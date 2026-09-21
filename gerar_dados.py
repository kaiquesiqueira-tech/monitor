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

PLANILHAS = (".xlsx", ".xlsm", ".xls")


def achar(inicio):
    """Acha o arquivo pelo comeco do nome, ignorando maiusculas, sobras como
    'mata121 (1).xlsx' e extensao duplicada como 'mata121.xlsx.xlsx'.
    Havendo mais de um, fica com o mais recente."""
    if not ENTRADA.exists():
        return None
    achados = [a for a in ENTRADA.iterdir()
               if a.is_file()
               and a.name.lower().startswith(inicio.lower())
               and a.suffix.lower() in PLANILHAS
               and not a.name.startswith("~$")]
    return max(achados, key=lambda a: a.stat().st_mtime) if achados else None


def achar_todos(inicio):
    """Todos os arquivos que começam com o nome dado. Os saldos vêm em mais de um
    arquivo porque as filiais estão em grupos diferentes no Protheus."""
    if not ENTRADA.exists():
        return []
    return sorted(a for a in ENTRADA.iterdir()
                  if a.is_file()
                  and a.name.lower().startswith(inicio.lower())
                  and a.suffix.lower() in PLANILHAS
                  and not a.name.startswith("~$"))


ARQ_SC = achar("mata110")
ARQ_PC = achar("mata121")
ARQ_PP = achar("PROD_EM_PP")
ARQ_SALDO = achar_todos("SALDO")
ARQ_CCUSTO = achar_todos("CENTRO")
ARQ_CLASSE = achar_todos("CLASSE")


def conferir_arquivos():
    faltando = [nome for nome, arq in
                (("mata110", ARQ_SC), ("mata121", ARQ_PC), ("PROD_EM_PP", ARQ_PP))
                if arq is None]
    if faltando:
        print("Nao achei na pasta 'dados': " + ", ".join(faltando))
        if ENTRADA.exists():
            tem = [a.name for a in sorted(ENTRADA.iterdir()) if a.is_file()]
            print("O que existe la: " + (", ".join(tem) if tem else "nada"))
        print("Exporte os browses do Protheus para essa pasta e rode de novo.")
        sys.exit(1)
    for rotulo, arq in (("pedidos", ARQ_PC), ("solicitacoes", ARQ_SC), ("ponto de pedido", ARQ_PP)):
        print(f"  {rotulo}: {arq.name}")
    for arq in ARQ_SALDO:
        print(f"  saldo em estoque: {arq.name}")
    if not ARQ_SALDO:
        print("  saldo em estoque: nenhum arquivo SALDO*.xlsx (a aba Reposicao fica vazia)")


def texto_codigo(v):
    """Códigos vêm como número na exportação; viram texto sem o .0."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


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


def ler_parametros_bruto():
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


def ler_centros_de_custo():
    """Descrição do centro de custo por filial. O arquivo já traz a coluna Filial,
    então a relação é direta."""
    nomes = {}
    for arq in ARQ_CCUSTO:
        df = pd.read_excel(arq, header=1)
        df.columns = [str(c).strip() for c in df.columns]
        if "C Custo" not in df.columns:
            continue
        for _, r in df.dropna(subset=["C Custo"]).iterrows():
            fil = str(r["Filial"]).split("-")[0].strip().zfill(6)
            cod = texto_codigo(r["C Custo"])
            desc = str(r.get("Desc Moeda 1", "")).strip()
            if cod and desc and desc.lower() != "nan":
                nomes[fil + "|" + cod] = desc
    return nomes


def ler_tabelas_de_classe():
    """Cada arquivo CLASSE_* é a tabela de uma empresa. Como o arquivo não diz a
    filial, a relação é descoberta pelo uso: para cada filial fica a tabela que
    reconhece mais códigos dos pedidos e solicitações dela."""
    tabelas = {}
    for arq in ARQ_CLASSE:
        df = pd.read_excel(arq, header=1)
        df.columns = [str(c).strip() for c in df.columns]
        col_cod = next((c for c in df.columns if "Cod" in c and "Valor" in c), None)
        col_desc = next((c for c in df.columns if "Desc" in c), None)
        if not col_cod or not col_desc:
            continue
        nome = arq.stem.split("_")[-1].upper()
        tabelas[nome] = {texto_codigo(r[col_cod]): str(r[col_desc]).strip()
                         for _, r in df.dropna(subset=[col_cod]).iterrows()}
    return tabelas


def relacionar_classes(tabelas, usos):
    """usos: {filial: set de códigos de classe usados}. Devolve {filial|codigo: descrição}."""
    nomes = {}
    if not tabelas:
        return nomes
    for fil, codigos in sorted(usos.items()):
        if not codigos:
            continue
        placar = sorted(((sum(1 for c in codigos if c in t), nome)
                         for nome, t in tabelas.items()), reverse=True)
        acertos, escolhida = placar[0]
        if acertos == 0:
            print(f"  classe de valor: filial {fil} sem tabela correspondente")
            continue
        print(f"  classe de valor: filial {fil} -> {escolhida} ({acertos} de {len(codigos)} codigos)")
        for cod, desc in tabelas[escolhida].items():
            nomes[fil + "|" + cod] = desc
    return nomes


def ler_saldos():
    """Junta os arquivos SB2 e devolve o saldo por filial+produto.
    Usa o armazém padrão 01, que é o mesmo do cadastro de ponto de pedido,
    e cai para a soma de todos os armazéns quando o item não está no 01."""
    if not ARQ_SALDO:
        return {}, {}
    partes = []
    for arq in ARQ_SALDO:
        df = pd.read_excel(arq, header=2)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(subset=["Produto"]).copy()
        df["fil"] = df["Filial"].astype(int).astype(str).str.zfill(6)
        df["cod"] = df["Produto"].apply(codigo)
        df["arm"] = pd.to_numeric(df["Armazem"], errors="coerce").fillna(0).astype(int)
        df["saldo"] = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
        df["desc"] = df["Nome Cientif"].astype(str).str.strip()
        partes.append(df[["fil", "cod", "arm", "saldo", "desc"]])
    sb2 = pd.concat(partes, ignore_index=True)

    padrao = sb2[sb2["arm"] == 1].groupby(["fil", "cod"])["saldo"].sum()
    geral = sb2.groupby(["fil", "cod"])["saldo"].sum()
    saldos = {f + "|" + c: float(v) for (f, c), v in geral.items()}
    saldos.update({f + "|" + c: float(v) for (f, c), v in padrao.items()})

    descricoes = {}
    for _, r in sb2.iterrows():
        if r["desc"] and r["desc"] != "nan":
            descricoes.setdefault(r["cod"], r["desc"])
    return saldos, descricoes


HISTORICO = BASE / "historico.js"
RESUMO = BASE / "resumo_do_dia.txt"


def gravar_historico(saida, reposicao):
    """Guarda um retrato por dia para o gráfico de tendência. Um dia só entra uma vez:
    rodando de novo no mesmo dia, o retrato é substituído pelo mais recente."""
    hoje = date.today()
    pc_cols, sc_cols = saida["pc_cols"], saida["sc_cols"]
    i = {c: n for n, c in enumerate(pc_cols)}
    j = {c: n for n, c in enumerate(sc_cols)}

    def atraso(linha):
        return (hoje - date.fromisoformat(linha[i["entrega"]])).days

    def idade(linha):
        return (hoje - date.fromisoformat(linha[j["emissao"]])).days

    pedidos = [l for l in saida["pc"] if l[i["pp"]] == 2]
    solic = [l for l in saida["sc"] if l[j["pp"]] == 2]
    vencidos = [l for l in pedidos if atraso(l) > 0]

    retrato = {
        "data": hoje.isoformat(),
        "pedidos": len(pedidos),
        "vencidos": len(vencidos),
        "valor_vencido": round(sum(l[i["qtd"]] * l[i["preco"]] for l in vencidos), 2),
        "solicitacoes": len(solic),
        "paradas30": len([l for l in solic if idade(l) > 30]),
        "abaixo_pp": len(reposicao),
    }

    antigos = []
    if HISTORICO.exists():
        texto = HISTORICO.read_text(encoding="utf-8")
        corte = texto.find("=")
        if corte > 0:
            try:
                antigos = json.loads(texto[corte + 1:].rstrip().rstrip(";"))
            except json.JSONDecodeError:
                antigos = []
    antigos = [r for r in antigos if r.get("data") != retrato["data"]]
    antigos.append(retrato)
    antigos.sort(key=lambda r: r["data"])
    antigos = antigos[-120:]                      # guarda os últimos 120 dias

    HISTORICO.write_text(
        "window.HISTORICO=" + json.dumps(antigos, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    print(f"historico.js com {len(antigos)} dia(s) de retrato.")


def gravar_resumo(saida):
    """Texto pronto para colar no WhatsApp, com os pedidos vencidos há mais tempo."""
    hoje = date.today()
    i = {c: n for n, c in enumerate(saida["pc_cols"])}
    vencidos = [l for l in saida["pc"] if l[i["pp"]] == 2
                and (hoje - date.fromisoformat(l[i["entrega"]])).days > 0]
    vencidos.sort(key=lambda l: l[i["entrega"]])

    linhas = ["*MONITOR PC E SC — ALMOXARIFADO*", ""]
    if vencidos:
        linhas.append("*Informações do pedido:*")
        for l in vencidos[:12]:
            emissao = date.fromisoformat(l[i["emissao"]]).strftime("%d/%m/%Y")
            linhas.append(f"• Pedido {l[i['pedido']]} — {l[i['produto']]} — emissão {emissao}")
            linhas.append("  " + l[i["desc"]])
            if l[i["comprador"]]:
                linhas.append("  Comprador: " + l[i["comprador"]])
        if len(vencidos) > 12:
            linhas.append(f"…e mais {len(vencidos) - 12} itens.")
    else:
        linhas.append("Nenhum pedido vencido hoje.")

    RESUMO.write_text("\n".join(linhas), encoding="utf-8")
    print("resumo_do_dia.txt pronto para colar no WhatsApp.")


def main():
    conferir_arquivos()
    sc = pd.read_excel(ARQ_SC, header=1)
    pc = pd.read_excel(ARQ_PC, header=1)

    usados = {codigo(x) for x in pc["Produto"]} | {codigo(x) for x in sc["Produto"]}
    parm_todo, total_pp = ler_parametros_bruto()
    saldos, desc_sb2 = ler_saldos()

    # saldo entra como 11º campo dos parâmetros
    for chave, valor in parm_todo.items():
        valor.append(saldos.get(chave, None))

    # o arquivo só leva o parâmetro de item que aparece em pedido, solicitação ou reposição
    abaixo = {c for c, v in parm_todo.items()
              if v[0] > 0 and v[10] is not None and v[10] < v[0]}
    parm = {c: v for c, v in parm_todo.items()
            if c.split("|")[1] in usados or c in abaixo}

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

    col_nome = next((c for c in ("Nome Fornecedor", "Nome Fornec", "Razao Social",
                                 "Nome do Fornecedor", "Fornecedor Nome", "Nome")
                     if c in pc.columns), None)
    if col_nome:
        print(f"  nome do fornecedor: coluna '{col_nome}'")

    col_solic = next((c for c in ("Solicitante", "Solicitado por", "Cod.Solicit",
                                  "Cod Solicitante", "Solicit", "Usuario")
                      if c in sc.columns), None)
    if col_solic:
        print(f"  solicitante: coluna '{col_solic}'")

    def texto(valor):
        """Centro de custo e classe de valor vêm como número; viram texto sem o .0."""
        if pd.isna(valor):
            return ""
        if isinstance(valor, float) and valor.is_integer():
            return str(int(valor))
        return str(valor).strip()

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
            texto(r.get("Centro Custo")), pp, p[0], p[1],
            "" if not col_nome or pd.isna(r[col_nome]) else str(r[col_nome]).strip(),
            texto(r.get("Classe Valor")),
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
            texto(r.get("Centro Custo")), pp, p[0], p[1],
            texto(r.get("Classe Valor")),
            "" if not col_solic or pd.isna(r[col_solic]) else str(r[col_solic]).strip(),
        ])

    # nomes das filiais a partir dos pedidos e solicitações
    nomes = {}
    for linha in pedidos:
        nomes[linha[0]] = linha[1]
    for linha in solicitacoes:
        nomes.setdefault(linha[0], linha[1])

    # itens abaixo do ponto de pedido
    descricoes = {}
    for linha in pedidos:
        descricoes[linha[3]] = linha[4]
    for linha in solicitacoes:
        descricoes.setdefault(linha[4], linha[5])

    reposicao = []
    for chave in sorted(abaixo):
        fil, cod = chave.split("|")
        v = parm_todo[chave]
        reposicao.append([fil, nomes.get(fil, fil), cod,
                          descricoes.get(cod) or desc_sb2.get(cod, "Sem descrição no cadastro"),
                          float(v[0]), float(v[1]), float(v[10])])

    # descrições de centro de custo e classe de valor, relacionadas por filial
    usos = {}
    i_cl_pc, i_fil = saida_indices = None, None
    for linha in pedidos:
        usos.setdefault(linha[0], set()).add(linha[19])
    for linha in solicitacoes:
        usos.setdefault(linha[0], set()).add(linha[14])
    for fil in usos:
        usos[fil].discard("")

    nomes_cc = ler_centros_de_custo()
    nomes_cl = relacionar_classes(ler_tabelas_de_classe(), usos)

    # só entram no arquivo os pares que aparecem em algum documento
    usados_cc = {l[0] + "|" + l[14] for l in pedidos if l[14]} | {l[0] + "|" + l[10] for l in solicitacoes if l[10]}
    usados_cl = {l[0] + "|" + l[19] for l in pedidos if l[19]} | {l[0] + "|" + l[14] for l in solicitacoes if l[14]}
    cc_desc = {k: v for k, v in nomes_cc.items() if k in usados_cc}
    cl_desc = {k: v for k, v in nomes_cl.items() if k in usados_cl}
    print(f"  {len(cc_desc)} centros de custo e {len(cl_desc)} classes de valor com descrição")

    saida = {
        "pc_cols": ["filial", "emp", "pedido", "produto", "desc", "qtd", "um", "preco",
                    "emissao", "entrega", "forn", "comprador", "sc", "grupo", "cc",
                    "pp", "ppq", "lote", "fornnome", "classe"],
        "sc_cols": ["filial", "emp", "sc", "item", "produto", "desc", "qtd", "um",
                    "emissao", "grupo", "cc", "pp", "ppq", "lote", "classe", "solicitante"],
        "parm_cols": ["pp", "lote", "emax", "seg", "emb", "ultpreco",
                      "ultcompra", "consini", "dtincl", "armazem", "saldo"],
        "rep_cols": ["filial", "emp", "produto", "desc", "pp", "lote", "saldo"],
        "ccdesc": cc_desc,
        "cldesc": cl_desc,
        "rep": reposicao,
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
    if ARQ_SALDO:
        print(f"{len(reposicao)} itens estão abaixo do ponto de pedido.")
    gravar_historico(saida, reposicao)
    gravar_resumo(saida)
    print("Agora é só commitar e dar push.")


if __name__ == "__main__":
    main()
