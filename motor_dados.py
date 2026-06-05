from nicegui import ui, app
import datetime
import calendar
import pandas as pd
import os

# =========================================================================================
# NOVA CONEXÃO COM A NUVEM (SUPABASE)
# =========================================================================================
import config
from supabase import create_client, Client
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# =========================================================================================
# UTILIDADES
# =========================================================================================
def formatar_moeda_brasil(valor):
    if pd.isna(valor) or valor == 0: 
        return "-"
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def obter_dados_dashboard_fast(mes, ano):
    import pandas as pd
    import calendar
    
    _, quant_dias = calendar.monthrange(ano, mes)
    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d}"

    try:
        # 1. Busca as VENDAS no Supabase
        r_vendas = supabase.table("vw_relatorio_venda_venda") \
            .select("data_venda, filial, loja, venda_venda_real") \
            .gte("data_venda", data_inicio) \
            .lte("data_venda", data_fim) \
            .execute()
        df_vendas = pd.DataFrame(r_vendas.data)

        # 2. Busca as COMPRAS no Supabase
        r_compras = supabase.table("vw_resumo_notas_fiscais") \
            .select("data_emissao, filial, loja, valor_total") \
            .gte("data_emissao", data_inicio + " 00:00:00") \
            .lte("data_emissao", data_fim + " 23:59:59") \
            .execute()
        df_compras = pd.DataFrame(r_compras.data)
        
        # Mapeia a coluna data_compra (que antes era feita no substr do SQL)
        if not df_compras.empty:
            df_compras['data_compra'] = df_compras['data_emissao'].str[:10]
        else:
            df_compras = pd.DataFrame(columns=['data_compra', 'filial', 'loja', 'valor_total'])

    except Exception as e:
        print(f"Erro no Supabase: {e}")
        df_vendas = pd.DataFrame(columns=['data_venda', 'filial', 'loja', 'venda_venda_real'])
        df_compras = pd.DataFrame(columns=['data_compra', 'filial', 'loja', 'valor_total'])

    # =========================================================================
    # A SOLUÇÃO MAIS VIÁVEL: O Dicionário de Mapeamento (ID -> Nome)
    # =========================================================================
    mapa_lojas = {}
    
    if not df_vendas.empty:
        for _, r in df_vendas[['filial', 'loja']].drop_duplicates().iterrows():
            mapa_lojas[str(r['filial'])] = str(r['loja']).strip().upper()
            
    if not df_compras.empty:
        for _, r in df_compras[['filial', 'loja']].drop_duplicates().iterrows():
            mapa_lojas[str(r['filial'])] = str(r['loja']).strip().upper()

    lista_ids = sorted(list(mapa_lojas.keys()))

    # Configura totais em zero baseados no ID BLINDADO
    totais = {}
    for fid in lista_ids:
        totais[f"vend_{fid}"] = 0.0
        totais[f"bol_{fid}"] = 0.0
        totais[f"comp_{fid}"] = 0.0
        totais[f"desp_{fid}"] = 0.0

    # Popula Totais (VENDAS)
    if not df_vendas.empty:
        df_vendas['filial'] = df_vendas['filial'].astype(str)
        t_vendas = df_vendas.groupby('filial')['venda_venda_real'].sum().to_dict()
        for fid, val in t_vendas.items():
            totais[f"vend_{fid}"] = float(val)

    # Popula Totais (COMPRAS)
    if not df_compras.empty:
        df_compras['filial'] = df_compras['filial'].astype(str)
        t_compras = df_compras.groupby('filial')['valor_total'].sum().to_dict()
        for fid, val in t_compras.items():
            totais[f"comp_{fid}"] = float(val)

    # Cria matriz de dias do mês
    dados_tabela = []
    for dia in range(1, quant_dias + 1):
        linha = {"dia": f"{dia:02d}"}
        for fid in lista_ids:
            linha[f"vend_{fid}"] = 0.0
            linha[f"bol_{fid}"] = 0.0
            linha[f"comp_{fid}"] = 0.0
            linha[f"desp_{fid}"] = 0.0
        dados_tabela.append(linha)

    # Injeta faturamento VENDAS na grade diária
    if not df_vendas.empty:
        df_vendas['dia'] = pd.to_datetime(df_vendas['data_venda']).dt.day
        agrupado_v = df_vendas.groupby(['dia', 'filial'])['venda_venda_real'].sum().reset_index()
        for _, r in agrupado_v.iterrows():
            idx = int(r['dia']) - 1
            fid = str(r['filial'])
            if f"vend_{fid}" in dados_tabela[idx]:
                dados_tabela[idx][f"vend_{fid}"] = float(r['venda_venda_real'])

    # Injeta faturamento COMPRAS na grade diária
    if not df_compras.empty:
        df_compras['dia'] = pd.to_datetime(df_compras['data_compra']).dt.day
        agrupado_c = df_compras.groupby(['dia', 'filial'])['valor_total'].sum().reset_index()
        for _, r in agrupado_c.iterrows():
            idx = int(r['dia']) - 1
            fid = str(r['filial'])
            if f"comp_{fid}" in dados_tabela[idx]:
                dados_tabela[idx][f"comp_{fid}"] = float(r['valor_total'])

    # Formata números como R$ para o Front-End
    for linha in dados_tabela:
        for fid in lista_ids:
            linha[f"vend_{fid}"] = formatar_moeda_brasil(linha[f"vend_{fid}"])
            linha[f"bol_{fid}"] = formatar_moeda_brasil(linha[f"bol_{fid}"])
            linha[f"comp_{fid}"] = formatar_moeda_brasil(linha[f"comp_{fid}"])
            linha[f"desp_{fid}"] = formatar_moeda_brasil(linha[f"desp_{fid}"])

    return dados_tabela, totais, mapa_lojas, quant_dias

def obter_dados_entregas_fast(mes_selecionado, ano_selecionado):
    import pandas as pd

    # Para os gráficos de evolução, puxamos do dia 1º de Janeiro até 31 de Dezembro do ano escolhido
    data_inicio_ano = f"{ano_selecionado}-01-01"
    data_fim_ano = f"{ano_selecionado}-12-31"

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

    # Padronização e Limpeza
    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['motoboy'] = df['motoboy'].astype(str).str.strip().str.upper()

    # MÁGICA DA BLINDAGEM: Cria o dicionário { '216483': 'LOJA 01' }
    mapa_lojas = dict(zip(df['filial'], df['loja']))

    # Converte datas para extrair o mês
    df['data_entrega'] = pd.to_datetime(df['data_entrega'], errors='coerce')
    df['mes'] = df['data_entrega'].dt.month

    # Separação do mês exato para os cards superiores e ranking
    df_mes = df[df['mes'] == mes_selecionado]

    # 1. Total do mês
    tot_entregas = len(df_mes)

    # 2. Entregas por filial no mês (Baseado no ID)
    dict_filiais = df_mes.groupby('filial').size().to_dict()

    # 3. Ranking de motoboys no mês
    ranking_df = df_mes.groupby('motoboy').size().reset_index(name='qtd').sort_values('qtd', ascending=False)
    ranking = [{"nome": row['motoboy'], "qtd": row['qtd']} for _, row in ranking_df.iterrows()]

    # 4. Evolução Mensal Lojas (Matriz de 12 meses usando ID da filial)
    evo_lojas = {fid: [0] * 12 for fid in mapa_lojas.keys()}
    loja_mes = df.groupby(['filial', 'mes']).size().reset_index(name='qtd')
    for _, r in loja_mes.iterrows():
        mes_idx = int(r['mes']) - 1
        evo_lojas[str(r['filial'])][mes_idx] = int(r['qtd'])

    # 5. Evolução Mensal Motoboys (Matriz de 12 meses)
    motoboys_unicos = df['motoboy'].unique()
    evo_mbs = {mb: [0] * 12 for mb in motoboys_unicos}
    mb_mes = df.groupby(['motoboy', 'mes']).size().reset_index(name='qtd')
    for _, r in mb_mes.iterrows():
        mes_idx = int(r['mes']) - 1
        evo_mbs[str(r['motoboy'])][mes_idx] = int(r['qtd'])

    # Retorna o mapa_lojas no lugar da lista de strings antigas
    return tot_entregas, dict_filiais, ranking, evo_lojas, evo_mbs, mapa_lojas

def obter_dados_vendedores_fast(mes, ano):
    import pandas as pd

    try:
        # A requisição OR no Supabase para buscar o ano no formato -% e /%
        r = supabase.table("vw_vendas_por_vendedor") \
            .select("data_venda, id_vendedor, vendedor, participacao_em_vendas, valor_total_vendido") \
            .or_(f"data_venda.like.{ano}-%,data_venda.like.%/{ano}") \
            .execute()
        df = pd.DataFrame(r.data)
    except Exception as e:
        print(f"Erro no Supabase (Vendedores): {e}")
        df = pd.DataFrame(columns=['data_venda', 'id_vendedor', 'vendedor', 'participacao_em_vendas', 'valor_total_vendido'])

    if df.empty:
        return {}, {}, {}

    df['data_datetime'] = pd.to_datetime(df['data_venda'], errors='coerce')
    df['mes_int'] = df['data_datetime'].dt.month
    
    # Padronização
    df['id_vendedor'] = df['id_vendedor'].astype(str).str.strip()
    df['vendedor'] = df['vendedor'].astype(str).str.strip().str.upper()
    df['valor_total_vendido'] = pd.to_numeric(df['valor_total_vendido'], errors='coerce').fillna(0)
    df['participacao_em_vendas'] = pd.to_numeric(df['participacao_em_vendas'], errors='coerce').fillna(0)

    # 2. O MAPA BLINDADO: Agora ele liga estritamente o ID do funcionário ao Nome dele
    mapa_vendedores = {}
    for _, r in df[['id_vendedor', 'vendedor']].drop_duplicates().iterrows():
        mapa_vendedores[r['id_vendedor']] = r['vendedor']

    lista_vend_ids = sorted(list(mapa_vendedores.keys()))

    # --- DADOS DO MÊS ---
    df_mes = df[df['mes_int'] == mes]
    resumo_mes_vendedores = {}
    
    if not df_mes.empty:
        # Agrupa pelo ID blindado
        agrup_mes = df_mes.groupby('id_vendedor').agg({
            'valor_total_vendido': 'sum',
            'participacao_em_vendas': 'sum'
        }).reset_index()
        
        for _, r in agrup_mes.iterrows():
            resumo_mes_vendedores[r['id_vendedor']] = {
                'vendas': float(r['valor_total_vendido']),
                'tickets': int(r['participacao_em_vendas'])
            }

    # --- DADOS DO ANO ---
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

    # Limpeza e Padronização
    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['categoria_macro'] = df['categoria_macro'].astype(str).str.strip().str.upper()
    df['valor_total_vendido'] = pd.to_numeric(df['valor_total_vendido'], errors='coerce').fillna(0.0)

    # A MÁGICA DA BLINDAGEM: Cria o dicionário { '216483': 'LOJA 01' }
    mapa_lojas_class = dict(zip(df['filial'], df['loja']))

    # Filtra apenas o mês atual
    df['data_venda'] = pd.to_datetime(df['data_venda'])
    df_mes = df[df['data_venda'].dt.month == mes]

    totais_loja = {}
    detalhe_classificacao = {}

    if not df_mes.empty:
        # 1. Totais por Filial (ID)
        totais_loja = df_mes.groupby('filial')['valor_total_vendido'].sum().to_dict()

        # 2. Detalhamento de Categorias por Filial (ID)
        agrup_cat = df_mes.groupby(['filial', 'categoria_macro'])['valor_total_vendido'].sum().reset_index()
        
        for _, r in agrup_cat.iterrows():
            fid = r['filial']
            cat = r['categoria_macro']
            val = float(r['valor_total_vendido'])
            
            if fid not in detalhe_classificacao:
                detalhe_classificacao[fid] = {}
            detalhe_classificacao[fid][cat] = val

        # Ordena as categorias da que mais vendeu para a que menos vendeu
        for fid in detalhe_classificacao:
            detalhe_classificacao[fid] = dict(sorted(detalhe_classificacao[fid].items(), key=lambda item: item[1], reverse=True))

    return totais_loja, detalhe_classificacao, mapa_lojas_class

def obter_dados_picos_horario_fast(mes, ano):
    import pandas as pd
    import calendar

    _, quant_dias = calendar.monthrange(ano, mes)
    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d}"

    try:
        r = supabase.table("vw_vendas_por_hora") \
            .select("filial, loja, dia_semana, hora_venda, qtd_atendimentos") \
            .gte("data_venda", data_inicio) \
            .lte("data_venda", data_fim) \
            .execute()
        df = pd.DataFrame(r.data)
    except Exception as e:
        print(f"Erro no Supabase (Picos Horario): {e}")
        df = pd.DataFrame(columns=['filial', 'loja', 'dia_semana', 'hora_venda', 'qtd_atendimentos'])

    if df.empty:
        return {}, [], {}, []

    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['dia_semana'] = df['dia_semana'].astype(str).str.strip()
    df['qtd_atendimentos'] = pd.to_numeric(df['qtd_atendimentos'], errors='coerce').fillna(0)

    # MÁGICA 1: O Python pega '08:15', '08:30', '08:45' e converte TUDO para '08h'
    df['hora_venda'] = df['hora_venda'].astype(str).str[:2] + 'h'

    # MÁGICA 2: Mapeamento de Filial (Blindagem contra nomes duplicados)
    mapa_lojas = dict(zip(df['filial'], df['loja']))
    lista_ids = sorted(list(mapa_lojas.keys()))

    # Agrupa somando os atendimentos usando o novo bloco de Hora Cheia
    agrupado = df.groupby(['filial', 'dia_semana', 'hora_venda'])['qtd_atendimentos'].sum().reset_index()

    tempos_unicos = sorted(agrupado['hora_venda'].unique().tolist())
    
    ordem_dias_padrao = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    dias_banco = agrupado['dia_semana'].unique().tolist()
    dias_semana_ordenados = [d for d in ordem_dias_padrao if d in dias_banco]
    
    for d in dias_banco:
        if d not in dias_semana_ordenados:
            dias_semana_ordenados.append(d)

    # A matriz principal agora usa a FILIAL (ID) como chave principal, não o nome
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

    # Padronização garantindo que a filial vire uma string limpa para usarmos como Chave
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

    try:
        r = supabase.table("vw_venda_por_pagamento_real") \
            .select("filial, loja, forma_pagamento, total_liquido") \
            .gte("data_venda", data_inicio) \
            .lte("data_venda", data_fim) \
            .execute()
        df = pd.DataFrame(r.data)
    except Exception as e:
        print(f"Erro no Supabase (Pagamentos): {e}")
        df = pd.DataFrame(columns=['filial', 'loja', 'forma_pagamento', 'total_liquido'])

    if df.empty:
        return {}, {}

    # Limpeza e Padronização
    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['forma_pagamento'] = df['forma_pagamento'].fillna('NÃO INFORMADO').astype(str).str.strip().str.upper()
    df['total_liquido'] = pd.to_numeric(df['total_liquido'], errors='coerce').fillna(0.0)

    # Criação do Dicionário de Blindagem (ID -> Nome)
    mapa_lojas_pgto = dict(zip(df['filial'], df['loja']))
    
    # Estrutura Final: { '216483': {'DINHEIRO': 1500.0, 'PIX': 3000.0} }
    dados_pagamentos = {fid: {} for fid in mapa_lojas_pgto.keys()}
    
    agrupado = df.groupby(['filial', 'forma_pagamento'])['total_liquido'].sum().reset_index()
    
    for _, r in agrupado.iterrows():
        if r['total_liquido'] > 0:
            dados_pagamentos[r['filial']][r['forma_pagamento']] = float(r['total_liquido'])

    return dados_pagamentos, mapa_lojas_pgto

def obter_dados_pagamentos_diarios_fast(mes, ano):
    import pandas as pd
    import calendar

    _, quant_dias = calendar.monthrange(ano, mes)
    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{quant_dias:02d}"

    try:
        r = supabase.table("vw_venda_por_pagamento_real") \
            .select("filial, loja, data_venda, forma_pagamento, total_liquido") \
            .gte("data_venda", data_inicio) \
            .lte("data_venda", data_fim) \
            .execute()
        df = pd.DataFrame(r.data)
    except Exception as e:
        print(f"Erro no Supabase (Pagamentos Diários): {e}")
        df = pd.DataFrame(columns=['filial', 'loja', 'data_venda', 'forma_pagamento', 'total_liquido'])

    if df.empty:
        return {}, {}

    # Padronização e Blindagem
    df['filial'] = df['filial'].astype(str).str.strip()
    df['loja'] = df['loja'].astype(str).str.strip().str.upper()
    df['forma_pagamento'] = df['forma_pagamento'].fillna('NÃO INFORMADO').astype(str).str.strip().str.upper()
    df['total_liquido'] = pd.to_numeric(df['total_liquido'], errors='coerce').fillna(0.0)

    mapa_lojas_pgto = dict(zip(df['filial'], df['loja']))

    # O CORTE DO DIA: Isola apenas o '01', '02', '03' a partir da data de faturamento
    df['dia'] = pd.to_datetime(df['data_venda']).dt.strftime('%d')

    # Monta a base: dados[dia][filial][forma] = valor
    dados_diarios = {}
    for d in range(1, quant_dias + 1):
        dia_str = f"{d:02d}"
        dados_diarios[dia_str] = {fid: {} for fid in mapa_lojas_pgto.keys()}

    agrupado = df.groupby(['dia', 'filial', 'forma_pagamento'])['total_liquido'].sum().reset_index()

    for _, r in agrupado.iterrows():
        if r['total_liquido'] > 0:
            dados_diarios[r['dia']][r['filial']][r['forma_pagamento']] = float(r['total_liquido'])

    return dados_diarios, mapa_lojas_pgto