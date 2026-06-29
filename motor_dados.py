from nicegui import ui, app
import datetime
import calendar
import pandas as pd
import sqlite3
import os
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


def obter_dados_dashboard_fast(mes, ano):
    import pandas as pd
    import calendar
    
    _, quant_dias = calendar.monthrange(ano, mes)
    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d}"

    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            query_vendas = """
                SELECT data_venda, filial, loja, venda_venda_real 
                FROM vw_relatorio_venda_venda 
                WHERE data_venda >= ? AND data_venda <= ?
            """
            df_vendas = pd.read_sql(query_vendas, conn, params=(data_inicio, data_fim))

            query_compras = """
                SELECT data_emissao, filial, loja, valor_total 
                FROM vw_resumo_notas_fiscais 
                WHERE data_emissao >= ? AND data_emissao <= ?
            """
            df_compras = pd.read_sql(query_compras, conn, params=(data_inicio + " 00:00:00", data_fim + " 23:59:59"))
            conn.close()

            if not df_compras.empty:
                df_compras['data_compra'] = df_compras['data_emissao'].str[:10]
            else:
                df_compras = pd.DataFrame(columns=['data_compra', 'filial', 'loja', 'valor_total'])
        except Exception as e:
            print(f"Erro no Banco Local: {e}")
            df_vendas = pd.DataFrame(columns=['data_venda', 'filial', 'loja', 'venda_venda_real'])
            df_compras = pd.DataFrame(columns=['data_compra', 'filial', 'loja', 'valor_total'])
    else:
        try:
            r_vendas = supabase.table("vw_relatorio_venda_venda") \
                .select("data_venda, filial, loja, venda_venda_real") \
                .gte("data_venda", data_inicio) \
                .lte("data_venda", data_fim) \
                .execute()
            df_vendas = pd.DataFrame(r_vendas.data)

            r_compras = supabase.table("vw_resumo_notas_fiscais") \
                .select("data_emissao, filial, loja, valor_total") \
                .gte("data_emissao", data_inicio + " 00:00:00") \
                .lte("data_emissao", data_fim + " 23:59:59") \
                .execute()
            df_compras = pd.DataFrame(r_compras.data)
            
            if not df_compras.empty:
                df_compras['data_compra'] = df_compras['data_emissao'].str[:10]
            else:
                df_compras = pd.DataFrame(columns=['data_compra', 'filial', 'loja', 'valor_total'])
        except Exception as e:
            print(f"Erro no Supabase: {e}")
            df_vendas = pd.DataFrame(columns=['data_venda', 'filial', 'loja', 'venda_venda_real'])
            df_compras = pd.DataFrame(columns=['data_compra', 'filial', 'loja', 'valor_total'])

    # =========================================================================
    # TRATAMENTO DE DADOS (Comum aos dois ambientes)
    # =========================================================================
    mapa_lojas = {}
    
    if not df_vendas.empty:
        for _, r in df_vendas[['filial', 'loja']].drop_duplicates().iterrows():
            mapa_lojas[str(r['filial'])] = str(r['loja']).strip().upper()
            
    if not df_compras.empty:
        for _, r in df_compras[['filial', 'loja']].drop_duplicates().iterrows():
            mapa_lojas[str(r['filial'])] = str(r['loja']).strip().upper()

    lista_ids = sorted(list(mapa_lojas.keys()))

    totais = {}
    for fid in lista_ids:
        totais[f"vend_{fid}"] = 0.0
        totais[f"bol_{fid}"] = 0.0
        totais[f"comp_{fid}"] = 0.0
        totais[f"desp_{fid}"] = 0.0

    if not df_vendas.empty:
        df_vendas['filial'] = df_vendas['filial'].astype(str)
        t_vendas = df_vendas.groupby('filial')['venda_venda_real'].sum().to_dict()
        for fid, val in t_vendas.items():
            totais[f"vend_{fid}"] = float(val)

    if not df_compras.empty:
        df_compras['filial'] = df_compras['filial'].astype(str)
        t_compras = df_compras.groupby('filial')['valor_total'].sum().to_dict()
        for fid, val in t_compras.items():
            totais[f"comp_{fid}"] = float(val)

    dados_tabela = []
    for dia in range(1, quant_dias + 1):
        linha = {"dia": f"{dia:02d}"}
        for fid in lista_ids:
            linha[f"vend_{fid}"] = 0.0
            linha[f"bol_{fid}"] = 0.0
            linha[f"comp_{fid}"] = 0.0
            linha[f"desp_{fid}"] = 0.0
        dados_tabela.append(linha)

    if not df_vendas.empty:
        df_vendas['dia'] = pd.to_datetime(df_vendas['data_venda']).dt.day
        agrupado_v = df_vendas.groupby(['dia', 'filial'])['venda_venda_real'].sum().reset_index()
        for _, r in agrupado_v.iterrows():
            idx = int(r['dia']) - 1
            fid = str(r['filial'])
            if f"vend_{fid}" in dados_tabela[idx]:
                dados_tabela[idx][f"vend_{fid}"] = float(r['venda_venda_real'])

    if not df_compras.empty:
        df_compras['dia'] = pd.to_datetime(df_compras['data_compra']).dt.day
        agrupado_c = df_compras.groupby(['dia', 'filial'])['valor_total'].sum().reset_index()
        for _, r in agrupado_c.iterrows():
            idx = int(r['dia']) - 1
            fid = str(r['filial'])
            if f"comp_{fid}" in dados_tabela[idx]:
                dados_tabela[idx][f"comp_{fid}"] = float(r['valor_total'])

    for linha in dados_tabela:
        for fid in lista_ids:
            linha[f"vend_{fid}"] = formatar_moeda_brasil(linha[f"vend_{fid}"])
            linha[f"bol_{fid}"] = formatar_moeda_brasil(linha[f"bol_{fid}"])
            linha[f"comp_{fid}"] = formatar_moeda_brasil(linha[f"comp_{fid}"])
            linha[f"desp_{fid}"] = formatar_moeda_brasil(linha[f"desp_{fid}"])

    return dados_tabela, totais, mapa_lojas, quant_dias


def obter_dados_entregas_fast(mes_selecionado, ano_selecionado):
    import pandas as pd

    data_inicio_ano = f"{ano_selecionado}-01-01"
    data_fim_ano = f"{ano_selecionado}-12-31"

    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            query = """
                SELECT filial, loja, motoboy, data_entrega 
                FROM vw_logistica_entregas 
                WHERE data_entrega >= ? AND data_entrega <= ? AND status_entrega = 'F'
            """
            df = pd.read_sql(query, conn, params=(data_inicio_ano, data_fim_ano))
            conn.close()
        except Exception as e:
            print(f"Erro no Banco Local (Entregas): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'motoboy', 'data_entrega'])
    else:
        try:
            r = supabase.table("vw_logistica_entregas") \
                .select("filial, loja, motoboy, data_entrega") \
                .gte("data_entrega", data_inicio_ano) \
                .lte("data_entrega", data_fim_ano) \
                .eq("status_entrega", "F") \
                .execute()
            df = pd.DataFrame(r.data)
        except Exception as e:
            print(f"Erro no Supabase (Entregas): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'motoboy', 'data_entrega'])

    if df.empty:
        return 0, {}, [], {}, {}, {}

    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['motoboy'] = df['motoboy'].astype(str).str.strip().str.upper()

    mapa_lojas = dict(zip(df['filial'], df['loja']))

    # CORREÇÃO CIRÚRGICA PARA O RENDER: Garante que a data vire string limpa no formato YYYY-MM-DD
    # Evita que o fuso horário UTC do Render altere o dia/mês do registro.
    df['data_entrega_str'] = df['data_entrega'].astype(str).str[:10]
    
    # Extrai o mês cortando os caracteres da string diretamente (Ex: '2026-06-29' -> '06' -> 6)
    df['mes'] = df['data_entrega_str'].str[5:7].astype(int)

    # Filtra o mês selecionado usando o índice imutável da string
    df_mes = df[df['mes'] == mes_selecionado]

    tot_entregas = len(df_mes)
    dict_filiais = df_mes.groupby('filial').size().to_dict()
    
    ranking_df = df_mes.groupby('motoboy').size().reset_index(name='qtd').sort_values('qtd', ascending=False)
    ranking = [{"nome": row['motoboy'], "qtd": row['qtd']} for _, row in ranking_df.iterrows()]

    evo_lojas = {fid: [0] * 12 for fid in mapa_lojas.keys()}
    loja_mes = df.groupby(['filial', 'mes']).size().reset_index(name='qtd')
    for _, r in loja_mes.iterrows():
        mes_idx = int(r['mes']) - 1
        if 0 <= mes_idx < 12:
            evo_lojas[str(r['filial'])][mes_idx] = int(r['qtd'])

    motoboys_unicos = df['motoboy'].unique()
    evo_mbs = {mb: [0] * 12 for mb in motoboys_unicos}
    mb_mes = df.groupby(['motoboy', 'mes']).size().reset_index(name='qtd')
    for _, r in mb_mes.iterrows():
        mes_idx = int(r['mes']) - 1
        if 0 <= mes_idx < 12:
            evo_mbs[str(r['motoboy'])][mes_idx] = int(r['qtd'])

    return tot_entregas, dict_filiais, ranking, evo_lojas, evo_mbs, mapa_lojas


def obter_dados_vendedores_fast(mes, ano):
    import pandas as pd

    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            query = """
                SELECT data_venda, id_vendedor, vendedor, participacao_em_vendas, valor_total_vendido 
                FROM vw_vendas_por_vendedor 
                WHERE data_venda LIKE ? OR data_venda LIKE ?
            """
            df = pd.read_sql(query, conn, params=(f"{ano}-%", f"%/{ano}"))
            conn.close()
        except Exception as e:
            print(f"Erro no Banco Local (Vendedores): {e}")
            df = pd.DataFrame(columns=['data_venda', 'id_vendedor', 'vendedor', 'participacao_em_vendas', 'valor_total_vendido'])
    else:
        try:
            # Filtra o ano completo direto na API do Supabase de forma otimizada
            data_inicio_ano = f"{ano}-01-01"
            data_fim_ano = f"{ano}-12-31"

            r = supabase.table("vw_vendas_por_vendedor") \
                .select("data_venda, id_vendedor, vendedor, participacao_em_vendas, valor_total_vendido") \
                .gte("data_venda", data_inicio_ano) \
                .lte("data_venda", data_fim_ano) \
                .execute()
            df = pd.DataFrame(r.data)
        except Exception as e:
            print(f"Erro no Supabase (Vendedores): {e}")
            df = pd.DataFrame(columns=['data_venda', 'id_vendedor', 'vendedor', 'participacao_em_vendas', 'valor_total_vendido'])

    if df.empty:
        return {}, {}, {}

    # CORREÇÃO CRÍTICA PARA O RENDER (Ignora o fuso horário UTC do Linux)
    # Forçamos a coluna a virar string e pegamos os 10 primeiros caracteres (YYYY-MM-DD)
    df['data_venda_str'] = df['data_venda'].astype(str).str[:10]
    
    # Cortamos direto a string para descobrir o mês de forma imutável (Ex: '2026-06-29' -> '06' -> 6)
    df['mes_int'] = df['data_venda_str'].str[5:7].astype(int)
    
    df['id_vendedor'] = df['id_vendedor'].astype(str).str.strip()
    df['vendedor'] = df['vendedor'].astype(str).str.strip().str.upper()
    df['valor_total_vendido'] = pd.to_numeric(df['valor_total_vendido'], errors='coerce').fillna(0)
    df['participacao_em_vendas'] = pd.to_numeric(df['participacao_em_vendas'], errors='coerce').fillna(0)

    mapa_vendedores = {}
    for _, r in df[['id_vendedor', 'vendedor']].drop_duplicates().iterrows():
        mapa_vendedores[r['id_vendedor']] = r['vendedor']

    lista_vend_ids = sorted(list(mapa_vendedores.keys()))

    # Agora a filtragem por mês vai bater exatamente com o que está escrito no banco
    df_mes = df[df['mes_int'] == mes]
    resumo_mes_vendedores = {}
    
    if not df_mes.empty:
        agrup_mes = df_mes.groupby('id_vendedor').agg({
            'valor_total_vendido': 'sum',
            'participacao_em_vendas': 'sum'
        }).reset_index()
        
        for _, r in agrup_mes.iterrows():
            resumo_mes_vendedores[r['id_vendedor']] = {
                'vendas': float(r['valor_total_vendido']),
                'tickets': int(r['participacao_em_vendas'])
            }

    evolucao_vendedores = {vid: [0.0] * 12 for vid in lista_vend_ids}
    if not df.empty:
        agrup_ano_vend = df.groupby(['mes_int', 'id_vendedor'])['valor_total_vendido'].sum().reset_index()
        for _, r in agrup_ano_vend.iterrows():
            m_idx = int(r['mes_int']) - 1
            vid = r['id_vendedor']
            if vid in evolucao_vendedores and 0 <= m_idx < 12:
                evolucao_vendedores[vid][m_idx] = float(r['valor_total_vendido'])

    return resumo_mes_vendedores, evolucao_vendedores, mapa_vendedores

def obter_dados_vendas_classificacao_fast(mes, ano):
    import pandas as pd
    import calendar

    _, quant_dias = calendar.monthrange(ano, mes)
    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d}"

    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            query = """
                SELECT filial, loja, data_venda, categoria_macro, valor_total_vendido 
                FROM vw_vendas_por_categoria 
                WHERE data_venda >= ? AND data_venda <= ?
            """
            df = pd.read_sql(query, conn, params=(data_inicio, data_fim))
            conn.close()
        except Exception as e:
            print(f"Erro no Banco Local (Categorias): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'data_venda', 'categoria_macro', 'valor_total_vendido'])
    else:
        try:
            r = supabase.table("vw_vendas_por_categoria") \
                .select("filial, loja, data_venda, categoria_macro, valor_total_vendido") \
                .gte("data_venda", data_inicio) \
                .lte("data_venda", data_fim) \
                .execute()
            df = pd.DataFrame(r.data)
        except Exception as e:
            print(f"Erro no Supabase (Categorias): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'data_venda', 'categoria_macro', 'valor_total_vendido'])

    if df.empty:
        return {}, {}, {}

    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['categoria_macro'] = df['categoria_macro'].astype(str).str.strip().str.upper()
    df['valor_total_vendido'] = pd.to_numeric(df['valor_total_vendido'], errors='coerce').fillna(0.0)

    mapa_lojas_class = dict(zip(df['filial'], df['loja']))

    df['data_venda'] = pd.to_datetime(df['data_venda'])
    df_mes = df[df['data_venda'].dt.month == mes]

    totais_loja = {}
    detalhe_classificacao = {}

    if not df_mes.empty:
        totais_loja = df_mes.groupby('filial')['valor_total_vendido'].sum().to_dict()
        agrup_cat = df_mes.groupby(['filial', 'categoria_macro'])['valor_total_vendido'].sum().reset_index()
        
        for _, r in agrup_cat.iterrows():
            fid = r['filial']
            cat = r['categoria_macro']
            val = float(r['valor_total_vendido'])
            
            if fid not in detalhe_classificacao:
                detalhe_classificacao[fid] = {}
            detalhe_classificacao[fid][cat] = val

        for fid in detalhe_classificacao:
            detalhe_classificacao[fid] = dict(sorted(detalhe_classificacao[fid].items(), key=lambda item: item[1], reverse=True))

    return totais_loja, detalhe_classificacao, mapa_lojas_class


def obter_dados_picos_horario_fast(mes, ano):
    import pandas as pd
    import calendar

    _, quant_dias = calendar.monthrange(ano, mes)
    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d}"

    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            query = """
                SELECT filial, loja, dia_semana, hora_venda, qtd_atendimentos 
                FROM vw_vendas_por_hora 
                WHERE data_venda >= ? AND data_venda <= ?
            """
            df = pd.read_sql(query, conn, params=(data_inicio, data_fim))
            conn.close()
        except Exception as e:
            print(f"Erro no Banco Local (Picos Horario): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'dia_semana', 'hora_venda', 'qtd_atendimentos'])
    else:
        try:
            # Puxa o ano inteiro ou os limites corretos da nuvem
            data_inicio_ano = f"{ano}-01-01"
            data_fim_ano = f"{ano}-12-31"

            r = supabase.table("vw_vendas_por_hora") \
                .select("filial, loja, data_venda, dia_semana, hora_venda, qtd_atendimentos") \
                .gte("data_venda", data_inicio_ano) \
                .lte("data_venda", data_fim_ano) \
                .execute()
            df = pd.DataFrame(r.data)
        except Exception as e:
            print(f"Erro no Supabase (Picos Horario): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'data_venda', 'dia_semana', 'hora_venda', 'qtd_atendimentos'])

    if df.empty:
        return {}, [], {}, []

    # CORREÇÃO DO FUSO HORÁRIO NO RENDER: Corta o mês direto do texto YYYY-MM-DD
    df['data_venda_str'] = df['data_venda'].astype(str).str[:10]
    df['mes_int'] = df['data_venda_str'].str[5:7].astype(int)

    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['dia_semana'] = df['dia_semana'].astype(str).str.strip()
    
    # Garante que a coluna de atendimentos seja numérica pura
    df['qtd_atendimentos'] = pd.to_numeric(df['qtd_atendimentos'], errors='coerce').fillna(0)

    # Formata a hora adicionando o 'h' (Ex: '14:00' -> '14h')
    df['hora_venda'] = df['hora_venda'].astype(str).str[:2] + 'h'

    mapa_lojas = dict(zip(df['filial'], df['loja']))
    lista_ids = sorted(list(mapa_lojas.keys()))

    # Filtra o mês selecionado usando a nossa coluna de string blindada
    df_mes = df[df['mes_int'] == mes]

    if df_mes.empty:
        return {}, [], mapa_lojas, []

    agrupado = df_mes.groupby(['filial', 'dia_semana', 'hora_venda'])['qtd_atendimentos'].sum().reset_index()

    tempos_unicos = sorted(agrupado['hora_venda'].unique().tolist())
    
    ordem_dias_padrao = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    dias_banco = agrupado['dia_semana'].unique().tolist()
    dias_semana_ordenados = [d for d in ordem_dias_padrao if d in dias_banco]
    
    for d in dias_banco:
        if d not in dias_semana_ordenados:
            dias_semana_ordenados.append(d)

    dados_picos = {fid: {dia: {t: 0 for t in tempos_unicos} for dia in dias_semana_ordenados} for fid in lista_ids}

    for _, row in agrupado.iterrows():
        dados_picos[row['filial']][row['dia_semana']][row['hora_venda']] = int(row['qtd_atendimentos'])

    return dados_picos, tempos_unicos, mapa_lojas, dias_semana_ordenados


def obter_dados_compras_fast(mes, ano):
    import pandas as pd
    import calendar

    _, quant_dias = calendar.monthrange(ano, mes)
    data_inicio = f"{ano}-{mes:02d}-01 00:00:00"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d} 23:59:59"

    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            query = """
                SELECT filial, loja, data_emissao, numero_nota, status_nota, fornecedor, valor_total 
                FROM vw_resumo_notas_fiscais 
                WHERE data_emissao >= ? AND data_emissao <= ? 
                ORDER BY data_emissao DESC
            """
            df = pd.read_sql(query, conn, params=(data_inicio, data_fim))
            conn.close()
        except Exception as e:
            print(f"Erro no Banco Local (Compras): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'data_emissao', 'numero_nota', 'status_nota', 'fornecedor', 'valor_total'])
    else:
        try:
            r = supabase.table("vw_resumo_notas_fiscais") \
                .select("filial, loja, data_emissao, numero_nota, status_nota, fornecedor, valor_total") \
                .gte("data_emissao", data_inicio) \
                .lte("data_emissao", data_fim) \
                .order("data_emissao", desc=True) \
                .execute()
            df = pd.DataFrame(r.data)
        except Exception as e:
            print(f"Erro no Supabase (Compras): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'data_emissao', 'numero_nota', 'status_nota', 'fornecedor', 'valor_total'])

    if df.empty:
        return []

    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['status_nota'] = df['status_nota'].astype(str).str.strip().str.upper()
    df['numero_nota'] = df['numero_nota'].astype(str).str.strip()
    df['valor_total'] = pd.to_numeric(df['valor_total'], errors='coerce').fillna(0)
    
    df['fornecedor'] = df['fornecedor'].fillna('FORNECEDOR NÃO IDENTIFICADO').astype(str).str.strip().str.upper()
    df.loc[df['fornecedor'] == '', 'fornecedor'] = 'FORNECEDOR NÃO IDENTIFICADO'

    df['data_emissao'] = pd.to_datetime(df['data_emissao']).dt.strftime('%d/%m/%Y')

    return df.to_dict('records')


def obter_dados_pagamentos_fast(mes, ano):
    import pandas as pd
    import calendar

    _, quant_dias = calendar.monthrange(ano, mes)
    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d}"

    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            query = """
                SELECT filial, loja, forma_pagamento, valor_liquido_real 
                FROM vw_vendas_por_pagamento 
                WHERE data_venda >= ? AND data_venda <= ?
            """
            df = pd.read_sql(query, conn, params=(data_inicio, data_fim))
            conn.close()
        except Exception as e:
            print(f"Erro no Banco Local (Pagamentos): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'forma_pagamento', 'valor_liquido_real'])
    else:
        try:
            r = supabase.table("vw_vendas_por_pagamento") \
                .select("filial, loja, forma_pagamento, valor_liquido_real") \
                .gte("data_venda", data_inicio) \
                .lte("data_venda", data_fim) \
                .execute()
            df = pd.DataFrame(r.data)
        except Exception as e:
            print(f"Erro no Supabase (Pagamentos): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'forma_pagamento', 'valor_liquido_real'])

    if df.empty:
        return {}, {}

    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['forma_pagamento'] = df['forma_pagamento'].fillna('NÃO INFORMADO').astype(str).str.strip().str.upper()
    df['valor_liquido_real'] = pd.to_numeric(df['valor_liquido_real'], errors='coerce').fillna(0.0)

    mapa_lojas_pgto = dict(zip(df['filial'], df['loja']))
    dados_pagamentos = {fid: {} for fid in mapa_lojas_pgto.keys()}
    
    agrupado = df.groupby(['filial', 'forma_pagamento'])['valor_liquido_real'].sum().reset_index()
    
    for _, r in agrupado.iterrows():
        if r['valor_liquido_real'] > 0:
            dados_pagamentos[r['filial']][r['forma_pagamento']] = float(r['valor_liquido_real'])

    return dados_pagamentos, mapa_lojas_pgto


def obter_dados_pagamentos_diarios_fast(mes, ano):
    import pandas as pd
    import calendar

    _, quant_dias = calendar.monthrange(ano, mes)
    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d}"

    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            query = """
                SELECT filial, loja, data_venda, forma_pagamento, valor_liquido_real 
                FROM vw_vendas_por_pagamento 
                WHERE data_venda >= ? AND data_venda <= ?
            """
            df = pd.read_sql(query, conn, params=(data_inicio, data_fim))
            conn.close()
        except Exception as e:
            print(f"Erro no Banco Local (Pagamentos Diários): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'data_venda', 'forma_pagamento', 'valor_liquido_real'])
    else:
        try:
            r = supabase.table("vw_vendas_por_pagamento") \
                .select("filial, loja, data_venda, forma_pagamento, valor_liquido_real") \
                .gte("data_venda", data_inicio) \
                .lte("data_venda", data_fim) \
                .execute()
            df = pd.DataFrame(r.data)
        except Exception as e:
            print(f"Erro no Supabase (Pagamentos Diários): {e}")
            df = pd.DataFrame(columns=['filial', 'loja', 'data_venda', 'forma_pagamento', 'valor_liquido_real'])

    if df.empty:
        return {}, {}

    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['forma_pagamento'] = df['forma_pagamento'].fillna('NÃO INFORMADO').astype(str).str.strip().str.upper()
    df['valor_liquido_real'] = pd.to_numeric(df['valor_liquido_real'], errors='coerce').fillna(0.0)

    mapa_lojas_pgto = dict(zip(df['filial'], df['loja']))
    df['dia'] = pd.to_datetime(df['data_venda']).dt.strftime('%d')

    dados_diarios = {}
    for d in range(1, quant_dias + 1):
        dia_str = f"{d:02d}"
        dados_diarios[dia_str] = {fid: {} for fid in mapa_lojas_pgto.keys()}

    agrupado = df.groupby(['dia', 'filial', 'forma_pagamento'])['valor_liquido_real'].sum().reset_index()

    for _, r in agrupado.iterrows():
        if r['valor_liquido_real'] > 0:
            dados_diarios[r['dia']][r['filial']][r['forma_pagamento']] = float(r['valor_liquido_real'])

    return dados_diarios, mapa_lojas_pgto

# =========================================================================================
# NOVA FUNÇÃO PARA A TELA DE RESUMO MOBILE
# =========================================================================================
def obter_resumo_rapido_fast(modo, data_iso):
    """
    Extrai apenas os dados do dia ou do mês exato para a tela de Resumo Mobile.
    modo: 'DIA' ou 'MÊS'
    data_iso: string no formato 'YYYY-MM-DD'
    """
    data_alvo = datetime.date.fromisoformat(data_iso)
    
    # 1. Definir os limites de data
    if modo == 'DIA':
        data_inicio = data_alvo.strftime("%Y-%m-%d")
        data_fim = data_alvo.strftime("%Y-%m-%d")
    else: # MÊS
        ultimo_dia = calendar.monthrange(data_alvo.year, data_alvo.month)[1]
        data_inicio = data_alvo.replace(day=1).strftime("%Y-%m-%d")
        data_fim = data_alvo.replace(day=ultimo_dia).strftime("%Y-%m-%d")

    resumo_lojas = {} 
    resumo_vendedores = [] 
    total_entregas = 0

    # =========================================================================
    # CONSULTA: VENDAS
    # =========================================================================
    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            query_vendas = """
                SELECT filial, loja, venda_venda_real 
                FROM vw_relatorio_venda_venda 
                WHERE data_venda >= ? AND data_venda <= ?
            """
            df_vendas = pd.read_sql(query_vendas, conn, params=(data_inicio, data_fim))
            conn.close()
        except Exception as e:
            print(f"Erro Vendas Local (Resumo): {e}")
            df_vendas = pd.DataFrame(columns=['filial', 'loja', 'venda_venda_real'])
    else:
        try:
            r_vendas = supabase.table("vw_relatorio_venda_venda") \
                .select("filial, loja, venda_venda_real") \
                .gte("data_venda", data_inicio) \
                .lte("data_venda", data_fim) \
                .execute()
            df_vendas = pd.DataFrame(r_vendas.data)
        except Exception as e:
            print(f"Erro Vendas Supabase (Resumo): {e}")
            df_vendas = pd.DataFrame(columns=['filial', 'loja', 'venda_venda_real'])

    # Processamento Vendas
    if not df_vendas.empty:
        df_vendas['filial'] = df_vendas['filial'].astype(str).str.strip()
        df_vendas['loja'] = df_vendas['loja'].astype(str).str.strip().str.upper()
        df_vendas['venda_venda_real'] = pd.to_numeric(df_vendas['venda_venda_real'], errors='coerce').fillna(0)
        
        for _, r in df_vendas[['filial', 'loja']].drop_duplicates().iterrows():
            fid = r['filial']
            if fid not in resumo_lojas:
                resumo_lojas[fid] = {'nome': r['loja'], 'vendas': 0.0, 'compras': 0.0, 'boletos': 0.0}
        
        agrup_v = df_vendas.groupby('filial')['venda_venda_real'].sum()
        for fid, val in agrup_v.items():
            resumo_lojas[fid]['vendas'] = float(val)

    # =========================================================================
    # CONSULTA: COMPRAS
    # =========================================================================
    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            query_compras = """
                SELECT filial, loja, valor_total 
                FROM vw_resumo_notas_fiscais 
                WHERE data_emissao >= ? AND data_emissao <= ?
            """
            df_compras = pd.read_sql(query_compras, conn, params=(data_inicio + " 00:00:00", data_fim + " 23:59:59"))
            conn.close()
        except Exception as e:
            print(f"Erro Compras Local (Resumo): {e}")
            df_compras = pd.DataFrame(columns=['filial', 'loja', 'valor_total'])
    else:
        try:
            r_compras = supabase.table("vw_resumo_notas_fiscais") \
                .select("filial, loja, valor_total") \
                .gte("data_emissao", data_inicio + " 00:00:00") \
                .lte("data_emissao", data_fim + " 23:59:59") \
                .execute()
            df_compras = pd.DataFrame(r_compras.data)
        except Exception as e:
            print(f"Erro Compras Supabase (Resumo): {e}")
            df_compras = pd.DataFrame(columns=['filial', 'loja', 'valor_total'])

    # Processamento Compras
    if not df_compras.empty:
        df_compras['filial'] = df_compras['filial'].astype(str).str.strip()
        df_compras['loja'] = df_compras['loja'].astype(str).str.strip().str.upper()
        df_compras['valor_total'] = pd.to_numeric(df_compras['valor_total'], errors='coerce').fillna(0)

        for _, r in df_compras[['filial', 'loja']].drop_duplicates().iterrows():
            fid = r['filial']
            if fid not in resumo_lojas:
                resumo_lojas[fid] = {'nome': r['loja'], 'vendas': 0.0, 'compras': 0.0, 'boletos': 0.0}
        
        agrup_c = df_compras.groupby('filial')['valor_total'].sum()
        for fid, val in agrup_c.items():
            resumo_lojas[fid]['compras'] = float(val)

    # =========================================================================
    # CONSULTA: VENDEDORES (Traz o mês todo e filtra a data na RAM p/ evitar erro de formato)
    # =========================================================================
    ano_str = str(data_alvo.year)
    mes_str = str(data_alvo.month).zfill(2)
    
    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            query_vend = """
                SELECT data_venda, vendedor, valor_total_vendido 
                FROM vw_vendas_por_vendedor 
                WHERE data_venda LIKE ? OR data_venda LIKE ?
            """
            df_vend = pd.read_sql(query_vend, conn, params=(f"{ano_str}-{mes_str}%", f"%/{mes_str}/{ano_str}"))
            conn.close()
        except Exception as e:
            print(f"Erro Vendedores Local (Resumo): {e}")
            df_vend = pd.DataFrame(columns=['data_venda', 'vendedor', 'valor_total_vendido'])
    else:
        try:
            r_vend = supabase.table("vw_vendas_por_vendedor") \
                .select("data_venda, vendedor, valor_total_vendido") \
                .gte("data_venda", data_inicio) \
                .lte("data_venda", data_fim) \
                .execute()
            df_vend = pd.DataFrame(r_vend.data)
        except Exception as e:
            print(f"Erro Vendedores Supabase (Resumo): {e}")
            df_vend = pd.DataFrame(columns=['data_venda', 'vendedor', 'valor_total_vendido'])

    # Processamento Vendedores
    if not df_vend.empty:
        df_vend['data_datetime'] = pd.to_datetime(df_vend['data_venda'], errors='coerce')
        if modo == 'DIA':
            df_vend = df_vend[df_vend['data_datetime'].dt.date == data_alvo]
        else:
            df_vend = df_vend[(df_vend['data_datetime'].dt.month == data_alvo.month) & (df_vend['data_datetime'].dt.year == data_alvo.year)]
            
        if not df_vend.empty:
            df_vend['vendedor'] = df_vend['vendedor'].astype(str).str.strip().str.upper()
            df_vend['valor_total_vendido'] = pd.to_numeric(df_vend['valor_total_vendido'], errors='coerce').fillna(0)
            
            agrup_vend = df_vend.groupby('vendedor')['valor_total_vendido'].sum().reset_index()
            for _, r in agrup_vend.iterrows():
                if r['valor_total_vendido'] > 0:
                    resumo_vendedores.append({
                        'nome': r['vendedor'],
                        'total': float(r['valor_total_vendido'])
                    })

    # Ordenar vendedores do maior para o menor
    resumo_vendedores = sorted(resumo_vendedores, key=lambda x: x['total'], reverse=True)

    # =========================================================================
    # CONSULTA: ENTREGAS
    # =========================================================================
    if config.AMBIENTE_ATUAL == "LOCAL":
        try:
            conn = conectar_sqlite_seguro(CAMINHO_BANCO_LOCAL)
            # Trazemos a coluna 'motoboy' da View
            query_ent = """
                SELECT motoboy 
                FROM vw_logistica_entregas 
                WHERE data_entrega >= ? AND data_entrega <= ? AND status_entrega = 'F'
            """
            df_ent = pd.read_sql(query_ent, conn, params=(data_inicio, data_fim))
            conn.close()
        except Exception as e:
            print(f"Erro Entregas Local (Resumo): {e}")
            df_ent = pd.DataFrame(columns=['motoboy'])
    else:
        try:
            r_ent = supabase.table("vw_logistica_entregas") \
                .select("motoboy") \
                .gte("data_entrega", data_inicio) \
                .lte("data_entrega", data_fim) \
                .eq("status_entrega", "F") \
                .execute()
            df_ent = pd.DataFrame(r_ent.data)
        except Exception as e:
            print(f"Erro Entregas Supabase (Resumo): {e}")
            df_ent = pd.DataFrame(columns=['motoboy'])

    total_entregas = len(df_ent)
    dados_motoboys = []
    
    # Processamento e Agrupamento dos Motoboys
    if not df_ent.empty:
        df_ent['motoboy'] = df_ent['motoboy'].astype(str).str.strip().str.upper()
        # Conta quantas vezes cada motoboy aparece no DataFrame
        agrup_ent = df_ent.groupby('motoboy').size().reset_index(name='corridas')
        for _, r in agrup_ent.iterrows():
            dados_motoboys.append({
                'nome': r['motoboy'],
                'corridas': int(r['corridas'])
            })
            
    # Ordena os motoboys pelo volume de corridas (do maior para o menor)
    dados_motoboys = sorted(dados_motoboys, key=lambda x: x['corridas'], reverse=True)

    return resumo_lojas, resumo_vendedores, total_entregas, dados_motoboys