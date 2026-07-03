from nicegui import ui, app
import datetime
import calendar
import pandas as pd
import sqlite3
import os
import config
from functools import lru_cache

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

# =========================================================================================
# CONTROLE DE CACHE (LIMPEZA PARA ATUALIZAÇÃO EM TEMPO REAL)
# =========================================================================================
def limpar_caches_dados():
    """Limpa a memória do lru_cache para forçar uma nova busca no Supabase"""
    obter_dados_dashboard_fast.cache_clear()
    obter_dados_entregas_fast.cache_clear()
    obter_dados_vendedores_fast.cache_clear()
    obter_dados_vendas_classificacao_fast.cache_clear()
    obter_dados_compras_fast.cache_clear()
    obter_dados_picos_horario_fast.cache_clear()
    obter_dados_pagamentos_fast.cache_clear()
    obter_dados_pagamentos_diarios_fast.cache_clear()
    obter_resumo_rapido_fast.cache_clear()

#@lru_cache(maxsize=10)
def obter_dados_dashboard_fast(mes, ano):
    import calendar
    _, quant_dias = calendar.monthrange(ano, mes)

    # 1. Busca os dados brutos (deixa os dados como lista de dicionários nativa do Supabase)
    try:
        r_vendas = supabase.rpc("get_vendas_diarias", {"p_mes": mes, "p_ano": ano}).execute()
        vendas = r_vendas.data # Já vem como lista de dicionários
        
        r_compras = supabase.rpc("get_compras_diarias", {"p_mes": mes, "p_ano": ano}).execute()
        compras = r_compras.data
    except Exception as e:
        print(f"Erro no Supabase: {e}")
        return [], {}, {}, quant_dias

    # 2. Mapeamento de Lojas (Loop simples)
    mapa_lojas = {}
    for r in vendas + compras:
        mapa_lojas[str(r['filial'])] = str(r['loja']).strip().upper()
    lista_ids = sorted(list(mapa_lojas.keys()))

    # 3. Cálculo de totais (Dicionário de soma rápida)
    totais = {f"{pref}_{fid}": 0.0 for fid in lista_ids for pref in ["vend", "bol", "comp", "desp"]}
    for r in vendas:
        totais[f"vend_{r['filial']}"] += float(r['venda_venda_real'] or 0)
    for r in compras:
        totais[f"comp_{r['filial']}"] += float(r['valor_total'] or 0)

    # 4. Montagem da tabela (Matriz simples)
    dados_tabela = []
    for d in range(1, quant_dias + 1):
        dia_str = f"{d:02d}"
        linha = {"dia": dia_str}
        for fid in lista_ids:
            linha.update({f"vend_{fid}": 0.0, f"bol_{fid}": 0.0, f"comp_{fid}": 0.0, f"desp_{fid}": 0.0})
        dados_tabela.append(linha)

    # 5. Preenchimento (Sem groupby, direto no índice da lista)
    for r in vendas:
        idx = int(r['dia']) - 1
        dados_tabela[idx][f"vend_{r['filial']}"] += float(r['venda_venda_real'] or 0)
    
    for r in compras:
        idx = int(r['dia']) - 1
        dados_tabela[idx][f"comp_{r['filial']}"] += float(r['valor_total'] or 0)

    # 6. Formatação final (Só no finalzinho)
    for linha in dados_tabela:
        for key, val in linha.items():
            if key != "dia":
                linha[key] = formatar_moeda_brasil(val)

    return dados_tabela, totais, mapa_lojas, quant_dias

@lru_cache(maxsize=10)
def obter_dados_entregas_fast(mes_selecionado, ano_selecionado):
    import pandas as pd

    try:
        r = supabase.rpc("get_entregas_full", {"p_ano": ano_selecionado}).execute()
        df = pd.DataFrame(r.data)
    except Exception as e:
        print(f"Erro no Supabase (RPC Entregas): {e}")
        df = pd.DataFrame(columns=['filial', 'loja', 'motoboy', 'mes', 'valor'])

    if df.empty:
        return 0, {}, [], {}, {}, {}

    # 1. Totais do mês selecionado
    df_mes = df[df['mes'] == mes_selecionado]
    tot_entregas = int(df_mes['valor'].sum()) if not df_mes.empty else 0
    dict_filiais = df_mes.groupby('filial')['valor'].sum().to_dict() if not df_mes.empty else {}
    
    # 2. Ranking
    if not df_mes.empty:
        ranking_df = df_mes.groupby('motoboy')['valor'].sum().reset_index()
        ranking_df = ranking_df.sort_values('valor', ascending=False)
        ranking = [{"nome": row['motoboy'], "qtd": row['valor']} for _, row in ranking_df.iterrows()]
    else:
        ranking = []

    # 3. Evolução Anual
    evo_lojas = {fid: [0]*12 for fid in df['filial'].unique()}
    evo_mbs = {mb: [0]*12 for mb in df['motoboy'].unique()}

    for _, r in df.iterrows():
        idx = int(r['mes']) - 1
        if 0 <= idx < 12:
            evo_lojas[str(r['filial'])][idx] += int(r['valor'])
            evo_mbs[str(r['motoboy'])][idx] += int(r['valor'])

    return tot_entregas, dict_filiais, ranking, evo_lojas, evo_mbs, dict(zip(df['filial'], df['loja']))


@lru_cache(maxsize=10)
def obter_dados_vendedores_fast(mes, ano):
    import pandas as pd

    try:
        r = supabase.rpc("get_vendedores_full", {"p_ano": ano}).execute()
        df = pd.DataFrame(r.data)
    except Exception as e:
        print(f"Erro no Supabase (RPC Vendedores): {e}")
        df = pd.DataFrame(columns=['id_vendedor', 'vendedor', 'mes', 'vendas', 'tickets'])

    if df.empty:
        return {}, {}, {}

    df['id_vendedor'] = df['id_vendedor'].astype(str).str.strip()
    df['vendedor'] = df['vendedor'].astype(str).str.strip().str.upper()

    mapa_vendedores = dict(zip(df['id_vendedor'], df['vendedor']))
    lista_vend_ids = sorted(list(mapa_vendedores.keys()))

    df_mes = df[df['mes'] == mes]
    resumo_mes_vendedores = {}
    
    for _, r in df_mes.iterrows():
        resumo_mes_vendedores[r['id_vendedor']] = {
            'vendas': float(r['vendas']),
            'tickets': int(r['tickets'])
        }

    evolucao_vendedores = {vid: [0.0] * 12 for vid in lista_vend_ids}
    for _, r in df.iterrows():
        m_idx = int(r['mes']) - 1
        vid = r['id_vendedor']
        if vid in evolucao_vendedores and 0 <= m_idx < 12:
            evolucao_vendedores[vid][m_idx] = float(r['vendas'])

    return resumo_mes_vendedores, evolucao_vendedores, mapa_vendedores


@lru_cache(maxsize=10)
def obter_dados_vendas_classificacao_fast(mes, ano):
    import pandas as pd

    # Consulta única e direta no Supabase
    try:
        r = supabase.rpc("get_vendas_classificacao", {"p_mes": mes, "p_ano": ano}).execute()
        df = pd.DataFrame(r.data)
    except Exception as e:
        print(f"Erro no Supabase (RPC Categorias): {e}")
        df = pd.DataFrame(columns=['filial', 'loja', 'categoria_macro', 'valor_total_vendido'])

    if df.empty:
        return {}, {}, {}

    mapa_lojas_class = dict(zip(df['filial'], df['loja']))
    totais_loja = {}
    detalhe_classificacao = {}

    # O banco já entregou agrupado. O Python só distribui nos dicionários.
    for _, r in df.iterrows():
        fid = str(r['filial'])
        cat = str(r['categoria_macro'])
        val = float(r['valor_total_vendido'])
        
        # Alimenta o total da loja
        if fid not in totais_loja:
            totais_loja[fid] = 0.0
        totais_loja[fid] += val

        # Alimenta o detalhe por categoria
        if fid not in detalhe_classificacao:
            detalhe_classificacao[fid] = {}
        detalhe_classificacao[fid][cat] = val

    # Ordena as categorias do maior para o menor valor dentro de cada loja
    for fid in detalhe_classificacao:
        detalhe_classificacao[fid] = dict(sorted(detalhe_classificacao[fid].items(), key=lambda item: item[1], reverse=True))

    return totais_loja, detalhe_classificacao, mapa_lojas_class

@lru_cache(maxsize=10)
def obter_dados_compras_fast(mes, ano):
    # Consulta única e direta no Supabase
    try:
        r = supabase.rpc("get_compras_listagem", {"p_mes": mes, "p_ano": ano}).execute()
        dados = r.data if r.data else []
    except Exception as e:
        print(f"Erro no Supabase (RPC Compras Listagem): {e}")
        dados = []

    # Como o banco já formatou a data, tratou os fornecedores vazios 
    # e ordenou, só garantimos que o valor seja float para a tabela.
    for linha in dados:
        linha['valor_total'] = float(linha['valor_total']) if linha['valor_total'] else 0.0

    return dados


@lru_cache(maxsize=10)
def obter_dados_picos_horario_fast(mes, ano):
    import pandas as pd

    try:
        r = supabase.rpc("get_picos_horario", {"p_mes": mes, "p_ano": ano}).execute()
        df = pd.DataFrame(r.data)
    except Exception as e:
        print(f"Erro no Supabase (RPC Picos Horario): {e}")
        df = pd.DataFrame(columns=['filial', 'loja', 'dia_semana', 'hora_venda', 'qtd_atendimentos'])

    if df.empty:
        return {}, [], {}, []

    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['dia_semana'] = df['dia_semana'].astype(str).str.strip()
    df['qtd_atendimentos'] = pd.to_numeric(df['qtd_atendimentos'], errors='coerce').fillna(0).astype(int)
    df['hora_venda'] = df['hora_venda'].astype(str).str[:2] + 'h'

    mapa_lojas = dict(zip(df['filial'], df['loja']))
    lista_ids = sorted(list(mapa_lojas.keys()))

    tempos_unicos = sorted(df['hora_venda'].unique().tolist())
    ordem_dias_padrao = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    dias_banco = df['dia_semana'].unique().tolist()
    dias_semana_ordenados = [d for d in ordem_dias_padrao if d in dias_banco]
    
    for d in dias_banco:
        if d not in dias_semana_ordenados:
            dias_semana_ordenados.append(d)

    dados_picos = {fid: {dia: {t: 0 for t in tempos_unicos} for dia in dias_semana_ordenados} for fid in lista_ids}

    for _, row in df.iterrows():
        dados_picos[row['filial']][row['dia_semana']][row['hora_venda']] = int(row['qtd_atendimentos'])

    return dados_picos, tempos_unicos, mapa_lojas, dias_semana_ordenados

@lru_cache(maxsize=10)
def obter_dados_pagamentos_fast(mes, ano):
    import pandas as pd

    # Consulta única e direta no Supabase
    try:
        r = supabase.rpc("get_pagamentos_resumo", {"p_mes": mes, "p_ano": ano}).execute()
        df = pd.DataFrame(r.data)
    except Exception as e:
        print(f"Erro no Supabase (RPC Pagamentos): {e}")
        df = pd.DataFrame(columns=['filial', 'loja', 'forma_pagamento', 'valor_liquido_real'])

    if df.empty:
        return {}, {}

    mapa_lojas_pgto = dict(zip(df['filial'], df['loja']))
    dados_pagamentos = {fid: {} for fid in mapa_lojas_pgto.keys()}
    
    # Preenche o dicionário com os dados já mastigados pelo banco
    for _, r in df.iterrows():
        val = float(r['valor_liquido_real'])
        if val > 0:
            dados_pagamentos[str(r['filial'])][str(r['forma_pagamento'])] = val

    return dados_pagamentos, mapa_lojas_pgto

@lru_cache(maxsize=10)
def obter_dados_pagamentos_diarios_fast(mes, ano):
    import pandas as pd
    import calendar

    _, quant_dias = calendar.monthrange(ano, mes)

    # Consulta única e direta no Supabase
    try:
        r = supabase.rpc("get_pagamentos_diarios", {"p_mes": mes, "p_ano": ano}).execute()
        df = pd.DataFrame(r.data)
    except Exception as e:
        print(f"Erro no Supabase (RPC Pagamentos Diários): {e}")
        df = pd.DataFrame(columns=['dia', 'filial', 'loja', 'forma_pagamento', 'valor_liquido_real'])

    if df.empty:
        return {}, {}

    mapa_lojas_pgto = dict(zip(df['filial'], df['loja']))
    
    # Cria o esqueleto vazio para todos os dias do mês
    dados_diarios = {}
    for d in range(1, quant_dias + 1):
        dia_str = f"{d:02d}"
        dados_diarios[dia_str] = {fid: {} for fid in mapa_lojas_pgto.keys()}

    # Encaixa os dados que vieram do banco nas posições corretas
    for _, r in df.iterrows():
        val = float(r['valor_liquido_real'])
        if val > 0:
            dia_str = f"{int(r['dia']):02d}"
            dados_diarios[dia_str][str(r['filial'])][str(r['forma_pagamento'])] = val

    return dados_diarios, mapa_lojas_pgto

# =========================================================================================
# NOVA FUNÇÃO PARA A TELA DE RESUMO MOBILE
# =========================================================================================
@lru_cache(maxsize=10)
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