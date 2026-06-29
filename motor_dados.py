from nicegui import ui, app
import datetime
import calendar
import pandas as pd
import sqlite3
import os
from functools import lru_cache
import config

# =========================================================================================
# CONEXÃO COM A NUVEM (SUPABASE)
# =========================================================================================
from supabase import create_client, Client
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# Caminho absoluto para o banco de dados local
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_BANCO_LOCAL = os.path.join(DIRETORIO_ATUAL, 'aprendizado1_views.db')

# =========================================================================================
# UTILIDADES
# =========================================================================================
def formatar_moeda_brasil(valor):
    if pd.isna(valor) or valor == 0: 
        return "-"
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def conectar_sqlite_seguro(caminho):
    """Abre a conexão aplicando os pragmas necessários para evitar erros de Database Locked"""
    conn = sqlite3.connect(caminho)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA busy_timeout = 5000;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    return conn

@lru_cache(maxsize=10)
def obter_dados_dashboard_fast(mes, ano):
    from supabase import create_client
    import calendar

    _, quant_dias = calendar.monthrange(ano, mes)

    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d}"

    supabase = config.supabase  # já vindo do seu config

    # =========================================================================
    # 1. BUSCA DADOS (SÓ SUPABASE)
    # =========================================================================

    r_vendas = supabase.table("vw_relatorio_venda_venda") \
        .select("data_venda, filial, loja, venda_venda_real") \
        .gte("data_venda", data_inicio) \
        .lte("data_venda", data_fim) \
        .execute()

    df_vendas = r_vendas.data or []

    r_compras = supabase.table("vw_resumo_notas_fiscais") \
        .select("data_emissao, filial, loja, valor_total") \
        .gte("data_emissao", data_inicio + " 00:00:00") \
        .lte("data_emissao", data_fim + " 23:59:59") \
        .execute()

    df_compras = r_compras.data or []

    # =========================================================================
    # 2. NORMALIZAÇÃO (SEM SQLITE, SEM DIFERENÇA LOCAL/NUVEM)
    # =========================================================================

    import pandas as pd

    df_vendas = pd.DataFrame(df_vendas)
    df_compras = pd.DataFrame(df_compras)

    if df_vendas.empty:
        df_vendas = pd.DataFrame(columns=["data_venda", "filial", "loja", "venda_venda_real"])

    if df_compras.empty:
        df_compras = pd.DataFrame(columns=["data_emissao", "filial", "loja", "valor_total"])

    # datas (Postgres sempre ISO → simples)
    if not df_vendas.empty:
        df_vendas["dia"] = pd.to_datetime(df_vendas["data_venda"]).dt.day

    if not df_compras.empty:
        df_compras["dia"] = pd.to_datetime(df_compras["data_emissao"]).dt.day

    # =========================================================================
    # 3. MAPA DE FILIAIS
    # =========================================================================

    mapa_lojas = {}

    for df in [df_vendas, df_compras]:
        if not df.empty:
            for _, r in df[["filial", "loja"]].drop_duplicates().iterrows():
                mapa_lojas[str(r["filial"])] = str(r["loja"]).strip().upper()

    lista_ids = sorted(mapa_lojas.keys())

    # =========================================================================
    # 4. ESTRUTURA BASE
    # =========================================================================

    totais = {
        f"vend_{fid}": 0.0 for fid in lista_ids
    }

    totais.update({
        f"comp_{fid}": 0.0 for fid in lista_ids
    })

    dados_tabela = []

    for dia in range(1, quant_dias + 1):
        linha = {"dia": f"{dia:02d}"}

        for fid in lista_ids:
            linha[f"vend_{fid}"] = 0.0
            linha[f"comp_{fid}"] = 0.0
            linha[f"bol_{fid}"] = 0.0
            linha[f"desp_{fid}"] = 0.0

        dados_tabela.append(linha)

    # =========================================================================
    # 5. AGREGACAO (AINDA PYTHON, MAS LEVE)
    # =========================================================================

    if not df_vendas.empty:
        agrupado = df_vendas.groupby(["dia", "filial"])["venda_venda_real"].sum()

        for (dia, fid), val in agrupado.items():
            idx = int(dia) - 1
            fid = str(fid)
            if idx < len(dados_tabela):
                dados_tabela[idx][f"vend_{fid}"] = float(val)
                totais[f"vend_{fid}"] = totais.get(f"vend_{fid}", 0) + float(val)

    if not df_compras.empty:
        agrupado = df_compras.groupby(["dia", "filial"])["valor_total"].sum()

        for (dia, fid), val in agrupado.items():
            idx = int(dia) - 1
            fid = str(fid)
            if idx < len(dados_tabela):
                dados_tabela[idx][f"comp_{fid}"] = float(val)
                totais[f"comp_{fid}"] = totais.get(f"comp_{fid}", 0) + float(val)

    # =========================================================================
    # 6. FORMATAÇÃO
    # =========================================================================

    for linha in dados_tabela:
        for fid in lista_ids:
            linha[f"vend_{fid}"] = formatar_moeda_brasil(linha[f"vend_{fid}"])
            linha[f"comp_{fid}"] = formatar_moeda_brasil(linha[f"comp_{fid}"])
            linha[f"bol_{fid}"] = formatar_moeda_brasil(linha[f"bol_{fid}"])
            linha[f"desp_{fid}"] = formatar_moeda_brasil(linha[f"desp_{fid}"])

    return dados_tabela, totais, mapa_lojas, quant_dias

@lru_cache(maxsize=10)
def obter_dados_entregas_fast(mes_selecionado, ano_selecionado):
    import pandas as pd
    import calendar

    supabase = config.supabase

    data_inicio = f"{ano_selecionado}-01-01"
    data_fim = f"{ano_selecionado}-12-31"

    # =========================================================================
    # 1. BUSCA DADOS (SOMENTE SUPABASE)
    # =========================================================================

    r = supabase.table("vw_logistica_entregas") \
        .select("filial, loja, motoboy, data_entrega") \
        .gte("data_entrega", data_inicio) \
        .lte("data_entrega", data_fim) \
        .eq("status_entrega", "F") \
        .execute()

    df = pd.DataFrame(r.data or [])

    # =========================================================================
    # 2. TRATAMENTO PADRÃO (SEM DIFERENÇA DE AMBIENTE)
    # =========================================================================

    if df.empty:
        return 0, {}, [], {}, {}, {}

    df["filial"] = df["filial"].astype(str).str.strip()
    df["loja"] = df["loja"].astype(str).str.strip().str.upper()
    df["motoboy"] = df["motoboy"].astype(str).str.strip().str.upper()

    # Postgres já vem ISO → simples e consistente
    df["data_entrega"] = pd.to_datetime(df["data_entrega"])
    df["mes"] = df["data_entrega"].dt.month

    # =========================================================================
    # 3. FILTRO DO MÊS
    # =========================================================================

    df_mes = df[df["mes"] == mes_selecionado]

    tot_entregas = len(df_mes)
    dict_filiais = df_mes.groupby("filial").size().to_dict()

    ranking_df = (
        df_mes.groupby("motoboy")
        .size()
        .reset_index(name="qtd")
        .sort_values("qtd", ascending=False)
    )

    ranking = [
        {"nome": r["motoboy"], "qtd": int(r["qtd"])}
        for _, r in ranking_df.iterrows()
    ]

    # =========================================================================
    # 4. EVOLUÇÃO LOJAS
    # =========================================================================

    mapa_lojas = (
        df.groupby("filial")["loja"]
        .first()
        .astype(str)
        .str.strip()
        .str.upper()
        .to_dict()
    )

    evo_lojas = {fid: [0] * 12 for fid in mapa_lojas.keys()}

    loja_mes = df.groupby(["filial", "mes"]).size().reset_index(name="qtd")

    for _, r in loja_mes.iterrows():
        evo_lojas[r["filial"]][int(r["mes"]) - 1] = int(r["qtd"])

    # =========================================================================
    # 5. EVOLUÇÃO MOTOBOYS
    # =========================================================================

    evo_mbs = {mb: [0] * 12 for mb in df["motoboy"].unique()}

    mb_mes = df.groupby(["motoboy", "mes"]).size().reset_index(name="qtd")

    for _, r in mb_mes.iterrows():
        evo_mbs[r["motoboy"]][int(r["mes"]) - 1] = int(r["qtd"])

    return tot_entregas, dict_filiais, ranking, evo_lojas, evo_mbs, mapa_lojas

@lru_cache(maxsize=10)
def obter_dados_vendedores_fast(mes, ano):
    import pandas as pd

    supabase = config.supabase

    data_inicio = f"{ano}-01-01"
    data_fim = f"{ano}-12-31"

    # =========================================================================
    # 1. BUSCA (SOMENTE SUPABASE)
    # =========================================================================

    r = supabase.table("vw_vendas_por_vendedor") \
        .select("data_venda, id_vendedor, vendedor, participacao_em_vendas, valor_total_vendido") \
        .gte("data_venda", data_inicio) \
        .lte("data_venda", data_fim) \
        .execute()

    df = pd.DataFrame(r.data or [])

    # =========================================================================
    # 2. TRATAMENTO BASE
    # =========================================================================

    if df.empty:
        return {}, {}, {}

    df["data_venda"] = pd.to_datetime(df["data_venda"])
    df["mes"] = df["data_venda"].dt.month

    df["id_vendedor"] = df["id_vendedor"].astype(str).str.strip()
    df["vendedor"] = df["vendedor"].astype(str).str.strip().str.upper()

    df["valor_total_vendido"] = pd.to_numeric(df["valor_total_vendido"], errors="coerce").fillna(0)
    df["participacao_em_vendas"] = pd.to_numeric(df["participacao_em_vendas"], errors="coerce").fillna(0)

    # =========================================================================
    # 3. MAPA DE VENDEDORES
    # =========================================================================

    mapa_vendedores = (
        df.groupby("id_vendedor")["vendedor"]
        .first()
        .to_dict()
    )

    lista_vend_ids = sorted(mapa_vendedores.keys())

    # =========================================================================
    # 4. RESUMO DO MÊS
    # =========================================================================

    df_mes = df[df["mes"] == mes]

    resumo_mes_vendedores = {}

    if not df_mes.empty:
        agrup_mes = df_mes.groupby("id_vendedor").agg({
            "valor_total_vendido": "sum",
            "participacao_em_vendas": "sum"
        })

        resumo_mes_vendedores = {
            vid: {
                "vendas": float(row["valor_total_vendido"]),
                "tickets": int(row["participacao_em_vendas"])
            }
            for vid, row in agrup_mes.iterrows()
        }

    # =========================================================================
    # 5. EVOLUÇÃO ANUAL
    # =========================================================================

    evolucao_vendedores = {vid: [0.0] * 12 for vid in lista_vend_ids}

    agrup_ano = df.groupby(["mes", "id_vendedor"])["valor_total_vendido"].sum()

    for (mes_i, vid), val in agrup_ano.items():
        if vid in evolucao_vendedores and 1 <= mes_i <= 12:
            evolucao_vendedores[vid][mes_i - 1] = float(val)

    return resumo_mes_vendedores, evolucao_vendedores, mapa_vendedores

@lru_cache(maxsize=10)
def obter_dados_picos_horario_fast(mes, ano):
    import pandas as pd
    import calendar

    supabase = config.supabase

    _, quant_dias = calendar.monthrange(ano, mes)

    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d}"

    # =========================================================================
    # 1. BUSCA (JÁ FILTRANDO NO BANCO)
    # =========================================================================

    r = supabase.table("vw_vendas_por_hora") \
        .select("filial, loja, data_venda, dia_semana, hora_venda, qtd_atendimentos") \
        .gte("data_venda", data_inicio) \
        .lte("data_venda", data_fim) \
        .execute()

    df = pd.DataFrame(r.data or [])

    if df.empty:
        return {}, [], {}, []

    # =========================================================================
    # 2. NORMALIZAÇÃO LEVE
    # =========================================================================

    df["filial"] = df["filial"].astype(str).str.strip()
    df["loja"] = df["loja"].astype(str).str.strip().str.upper()
    df["dia_semana"] = df["dia_semana"].astype(str).str.strip()

    df["qtd_atendimentos"] = pd.to_numeric(df["qtd_atendimentos"], errors="coerce").fillna(0)

    # hora já normalizada no banco ou aqui
    df["hora_venda"] = df["hora_venda"].astype(str).str[:2] + "h"

    # =========================================================================
    # 3. FILTRO DO MÊS (SEM SQL DUPLICADO)
    # =========================================================================

    df["mes"] = pd.to_datetime(df["data_venda"]).dt.month
    df_mes = df[df["mes"] == mes]

    if df_mes.empty:
        return {}, [], {}, []

    # =========================================================================
    # 4. MAPA DE FILIAIS
    # =========================================================================

    mapa_lojas = (
        df.groupby("filial")["loja"]
        .first()
        .astype(str)
        .str.strip()
        .str.upper()
        .to_dict()
    )

    lista_ids = sorted(mapa_lojas.keys())

    # =========================================================================
    # 5. AGRUPAMENTO (ÚNICO GROUPBY)
    # =========================================================================

    agrupado = df_mes.groupby(
        ["filial", "dia_semana", "hora_venda"]
    )["qtd_atendimentos"].sum().reset_index()

    # =========================================================================
    # 6. DIMENSÕES
    # =========================================================================

    tempos_unicos = sorted(agrupado["hora_venda"].unique().tolist())

    ordem_dias = [
        "Segunda-feira", "Terça-feira", "Quarta-feira",
        "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"
    ]

    dias_banco = agrupado["dia_semana"].unique().tolist()
    dias_ordenados = [d for d in ordem_dias if d in dias_banco]

    for d in dias_banco:
        if d not in dias_ordenados:
            dias_ordenados.append(d)

    # =========================================================================
    # 7. MATRIZ FINAL
    # =========================================================================

    dados_picos = {
        fid: {
            dia: {t: 0 for t in tempos_unicos}
            for dia in dias_ordenados
        }
        for fid in lista_ids
    }

    for _, row in agrupado.iterrows():
        dados_picos[row["filial"]][row["dia_semana"]][row["hora_venda"]] = int(row["qtd_atendimentos"])

    return dados_picos, tempos_unicos, mapa_lojas, dias_ordenados


@lru_cache(maxsize=10)
def obter_dados_vendas_classificacao_fast(mes, ano):
    import pandas as pd

    supabase = config.supabase

    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-31"

    # =========================================================================
    # 1. BUSCA
    # =========================================================================

    r = supabase.table("vw_vendas_por_categoria") \
        .select("filial, loja, data_venda, categoria_macro, valor_total_vendido") \
        .gte("data_venda", data_inicio) \
        .lte("data_venda", data_fim) \
        .execute()

    df = pd.DataFrame(r.data or [])

    if df.empty:
        return {}, {}, {}

    # =========================================================================
    # 2. NORMALIZAÇÃO
    # =========================================================================

    df["filial"] = df["filial"].astype(str).str.strip()
    df["loja"] = df["loja"].astype(str).str.strip().str.upper()
    df["categoria_macro"] = df["categoria_macro"].astype(str).str.strip().str.upper()
    df["valor_total_vendido"] = pd.to_numeric(df["valor_total_vendido"], errors="coerce").fillna(0)

    df["data_venda"] = pd.to_datetime(df["data_venda"])
    df["mes"] = df["data_venda"].dt.month

    df_mes = df[df["mes"] == mes]

    # =========================================================================
    # 3. MAPA LOJAS
    # =========================================================================

    mapa_lojas_class = (
        df.groupby("filial")["loja"]
        .first()
        .astype(str)
        .str.strip()
        .str.upper()
        .to_dict()
    )

    # =========================================================================
    # 4. TOTAL POR LOJA
    # =========================================================================

    totais_loja = (
        df_mes.groupby("filial")["valor_total_vendido"]
        .sum()
        .to_dict()
    )

    # =========================================================================
    # 5. DETALHE POR CATEGORIA
    # =========================================================================

    agrup_cat = (
        df_mes.groupby(["filial", "categoria_macro"])["valor_total_vendido"]
        .sum()
        .reset_index()
    )

    detalhe_classificacao = {}

    for _, r in agrup_cat.iterrows():
        fid = r["filial"]
        cat = r["categoria_macro"]
        val = float(r["valor_total_vendido"])

        if fid not in detalhe_classificacao:
            detalhe_classificacao[fid] = {}

        detalhe_classificacao[fid][cat] = val

    # ordenação (leve, pode manter no Python)
    for fid in detalhe_classificacao:
        detalhe_classificacao[fid] = dict(
            sorted(detalhe_classificacao[fid].items(), key=lambda x: x[1], reverse=True)
        )

    return totais_loja, detalhe_classificacao, mapa_lojas_class

@lru_cache(maxsize=10)
def obter_dados_compras_fast(mes, ano):
    import pandas as pd

    supabase = config.supabase

    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-31"

    # =========================================================================
    # 1. BUSCA
    # =========================================================================

    r = supabase.table("vw_resumo_notas_fiscais") \
        .select("filial, loja, data_emissao, numero_nota, status_nota, fornecedor, valor_total") \
        .gte("data_emissao", data_inicio) \
        .lte("data_emissao", data_fim) \
        .order("data_emissao", desc=True) \
        .execute()

    df = pd.DataFrame(r.data or [])

    if df.empty:
        return []

    # =========================================================================
    # 2. LIMPEZA LEVE
    # =========================================================================

    df["filial"] = df["filial"].astype(str).str.strip()
    df["loja"] = df["loja"].astype(str).str.strip().str.upper()
    df["status_nota"] = df["status_nota"].astype(str).str.strip().str.upper()
    df["numero_nota"] = df["numero_nota"].astype(str).str.strip()

    df["fornecedor"] = (
        df["fornecedor"]
        .fillna("FORNECEDOR NÃO IDENTIFICADO")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df.loc[df["fornecedor"] == "", "fornecedor"] = "FORNECEDOR NÃO IDENTIFICADO"

    # =========================================================================
    # 3. DATA FORMATADA
    # =========================================================================

    df["data_emissao"] = pd.to_datetime(df["data_emissao"]).dt.strftime("%d/%m/%Y")

    # =========================================================================
    # 4. OUTPUT
    # =========================================================================

    return df.to_dict("records")



@lru_cache(maxsize=10)
def obter_dados_pagamentos_fast(mes, ano):
    import pandas as pd

    supabase = config.supabase

    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-31"

    # =========================================================================
    # 1. BUSCA
    # =========================================================================

    r = supabase.table("vw_vendas_por_pagamento") \
        .select("filial, loja, forma_pagamento, valor_liquido_real") \
        .gte("data_venda", data_inicio) \
        .lte("data_venda", data_fim) \
        .execute()

    df = pd.DataFrame(r.data or [])

    if df.empty:
        return {}, {}

    # =========================================================================
    # 2. LIMPEZA
    # =========================================================================

    df["filial"] = df["filial"].astype(str).str.strip()
    df["loja"] = df["loja"].astype(str).str.strip().str.upper()

    df["forma_pagamento"] = (
        df["forma_pagamento"]
        .fillna("NÃO INFORMADO")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["valor_liquido_real"] = pd.to_numeric(
        df["valor_liquido_real"],
        errors="coerce"
    ).fillna(0.0)

    # =========================================================================
    # 3. MAPA LOJAS
    # =========================================================================

    mapa_lojas_pgto = (
        df.groupby("filial")["loja"]
        .first()
        .to_dict()
    )

    # =========================================================================
    # 4. AGRUPAMENTO
    # =========================================================================

    agrupado = (
        df.groupby(["filial", "forma_pagamento"])["valor_liquido_real"]
        .sum()
        .reset_index()
    )

    dados_pagamentos = {fid: {} for fid in mapa_lojas_pgto.keys()}

    for _, r in agrupado.iterrows():
        if r["valor_liquido_real"] > 0:
            dados_pagamentos[r["filial"]][r["forma_pagamento"]] = float(
                r["valor_liquido_real"]
            )

    return dados_pagamentos, mapa_lojas_pgto


@lru_cache(maxsize=10)
def obter_dados_pagamentos_diarios_fast(mes, ano):
    import pandas as pd
    import calendar

    supabase = config.supabase

    _, quant_dias = calendar.monthrange(ano, mes)

    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d}"

    # =========================================================================
    # 1. BUSCA
    # =========================================================================

    r = supabase.table("vw_vendas_por_pagamento") \
        .select("filial, loja, data_venda, forma_pagamento, valor_liquido_real") \
        .gte("data_venda", data_inicio) \
        .lte("data_venda", data_fim) \
        .execute()

    df = pd.DataFrame(r.data or [])

    if df.empty:
        return {}, {}

    # =========================================================================
    # 2. LIMPEZA
    # =========================================================================

    df["filial"] = df["filial"].astype(str).str.strip()
    df["loja"] = df["loja"].astype(str).str.strip().str.upper()

    df["forma_pagamento"] = (
        df["forma_pagamento"]
        .fillna("NÃO INFORMADO")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["valor_liquido_real"] = pd.to_numeric(
        df["valor_liquido_real"],
        errors="coerce"
    ).fillna(0.0)

    # =========================================================================
    # 3. DATA → DIA (mais simples e leve)
    # =========================================================================

    df["data_venda"] = pd.to_datetime(df["data_venda"])
    df["dia"] = df["data_venda"].dt.strftime("%d")

    # =========================================================================
    # 4. MAPA LOJAS
    # =========================================================================

    mapa_lojas_pgto = (
        df.groupby("filial")["loja"]
        .first()
        .to_dict()
    )

    # =========================================================================
    # 5. AGRUPAMENTO (ÚNICO GROUPBY)
    # =========================================================================

    agrupado = (
        df.groupby(["dia", "filial", "forma_pagamento"])["valor_liquido_real"]
        .sum()
        .reset_index()
    )

    # =========================================================================
    # 6. MATRIZ FINAL
    # =========================================================================

    dados_diarios = {}

    for d in range(1, quant_dias + 1):
        dia_str = f"{d:02d}"
        dados_diarios[dia_str] = {
            fid: {} for fid in mapa_lojas_pgto.keys()
        }

    for _, r in agrupado.iterrows():
        if r["valor_liquido_real"] > 0:
            dados_diarios[r["dia"]][r["filial"]][r["forma_pagamento"]] = float(
                r["valor_liquido_real"]
            )

    return dados_diarios, mapa_lojas_pgto

# =========================================================================================
# NOVA FUNÇÃO PARA A TELA DE RESUMO MOBILE
# =========================================================================================
@lru_cache(maxsize=10)
def obter_resumo_rapido_fast(modo, data_iso):
    import pandas as pd
    import datetime
    import calendar

    supabase = config.supabase

    data_alvo = datetime.date.fromisoformat(data_iso)

    # =========================================================================
    # PERÍODO
    # =========================================================================
    if modo == "DIA":
        data_inicio = data_alvo.strftime("%Y-%m-%d")
        data_fim = data_alvo.strftime("%Y-%m-%d")
    else:
        ultimo_dia = calendar.monthrange(data_alvo.year, data_alvo.month)[1]
        data_inicio = data_alvo.replace(day=1).strftime("%Y-%m-%d")
        data_fim = data_alvo.replace(day=ultimo_dia).strftime("%Y-%m-%d")

    resumo_lojas = {}
    resumo_vendedores = []
    total_entregas = 0

    # =========================================================================
    # VENDAS
    # =========================================================================
    r_vendas = supabase.table("vw_relatorio_venda_venda") \
        .select("filial, loja, venda_venda_real") \
        .gte("data_venda", data_inicio) \
        .lte("data_venda", data_fim) \
        .execute()

    df_vendas = pd.DataFrame(r_vendas.data or [])

    if not df_vendas.empty:
        df_vendas["filial"] = df_vendas["filial"].astype(str).str.strip()
        df_vendas["loja"] = df_vendas["loja"].astype(str).str.strip().str.upper()
        df_vendas["venda_venda_real"] = pd.to_numeric(df_vendas["venda_venda_real"], errors="coerce").fillna(0)

        agrup = df_vendas.groupby("filial")["venda_venda_real"].sum()

        for fid, val in agrup.items():
            resumo_lojas[fid] = resumo_lojas.get(fid, {
                "nome": "",
                "vendas": 0.0,
                "compras": 0.0,
                "boletos": 0.0
            })
            resumo_lojas[fid]["vendas"] = float(val)

        nomes = df_vendas.groupby("filial")["loja"].first()
        for fid, nome in nomes.items():
            resumo_lojas[fid]["nome"] = nome

    # =========================================================================
    # COMPRAS
    # =========================================================================
    r_compras = supabase.table("vw_resumo_notas_fiscais") \
        .select("filial, loja, valor_total") \
        .gte("data_emissao", data_inicio + " 00:00:00") \
        .lte("data_emissao", data_fim + " 23:59:59") \
        .execute()

    df_compras = pd.DataFrame(r_compras.data or [])

    if not df_compras.empty:
        df_compras["filial"] = df_compras["filial"].astype(str).str.strip()
        df_compras["loja"] = df_compras["loja"].astype(str).str.strip().str.upper()
        df_compras["valor_total"] = pd.to_numeric(df_compras["valor_total"], errors="coerce").fillna(0)

        agrup = df_compras.groupby("filial")["valor_total"].sum()

        for fid, val in agrup.items():
            resumo_lojas[fid] = resumo_lojas.get(fid, {
                "nome": "",
                "vendas": 0.0,
                "compras": 0.0,
                "boletos": 0.0
            })
            resumo_lojas[fid]["compras"] = float(val)

    # =========================================================================
    # VENDEDORES
    # =========================================================================
    r_vend = supabase.table("vw_vendas_por_vendedor") \
        .select("vendedor, valor_total_vendido, data_venda") \
        .gte("data_venda", data_inicio) \
        .lte("data_venda", data_fim) \
        .execute()

    df_vend = pd.DataFrame(r_vend.data or [])

    if not df_vend.empty:
        df_vend["vendedor"] = df_vend["vendedor"].astype(str).str.strip().str.upper()
        df_vend["valor_total_vendido"] = pd.to_numeric(df_vend["valor_total_vendido"], errors="coerce").fillna(0)

        agrup = df_vend.groupby("vendedor")["valor_total_vendido"].sum().sort_values(ascending=False)

        resumo_vendedores = [
            {"nome": v, "total": float(t)}
            for v, t in agrup.items()
            if t > 0
        ]

    # =========================================================================
    # ENTREGAS
    # =========================================================================
    r_ent = supabase.table("vw_logistica_entregas") \
        .select("motoboy") \
        .gte("data_entrega", data_inicio) \
        .lte("data_entrega", data_fim) \
        .eq("status_entrega", "F") \
        .execute()

    df_ent = pd.DataFrame(r_ent.data or [])

    if not df_ent.empty:
        df_ent["motoboy"] = df_ent["motoboy"].astype(str).str.strip().str.upper()

        agrup = df_ent.groupby("motoboy").size().sort_values(ascending=False)

        dados_motoboys = [
            {"nome": m, "corridas": int(q)}
            for m, q in agrup.items()
        ]
    else:
        dados_motoboys = []

    total_entregas = len(df_ent)

    return resumo_lojas, resumo_vendedores, total_entregas, dados_motoboys