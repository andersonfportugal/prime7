from nicegui import ui, app
import datetime
import tema
from motor_dados import obter_dados_vendas_classificacao_fast, obter_dados_picos_horario_fast, obter_dados_pagamentos_fast, formatar_moeda_brasil

def desenhar_tela_vendas_loja():
    # Carrega a inteligência de cores do usuário atual
    cor = tema.obter_cores()
    
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))

    # --- CABEÇALHO ---
    with ui.row().classes(f"w-full justify-between items-center mb-4 {cor['fundo_card']} p-4 rounded-2xl shadow-sm border {cor['borda']} flex-wrap gap-4"):
        with ui.column().classes("gap-1"):
            ui.label("Diretoria de Vendas e Faturamento").classes(f"{cor['vendas_titulo']} text-lg font-black tracking-widest uppercase")
            ui.label("Análise macro por filiais, departamentos e picos de horários").classes(f"text-xs {cor['texto_secundario']}")

        # Extração de Dados 100% ancorada em IDs
    totais_loja, detalhe_classificacao, mapa_lojas_class = obter_dados_vendas_classificacao_fast(mes_atual, ano_atual)
    dados_picos, tempos_unicos, mapa_lojas_picos, dias_semana_disp = obter_dados_picos_horario_fast(mes_atual, ano_atual)
    dados_pagamentos, mapa_lojas_pgto = obter_dados_pagamentos_fast(mes_atual, ano_atual)

    # Inicialização da Sessão 2 (Checkbox)
    dias_marcados = app.storage.user.get("dias_marcados_vendas", [])
    dias_marcados = [d for d in dias_marcados if d in dias_semana_disp]
    if not dias_marcados and dias_semana_disp:
        dias_marcados = dias_semana_disp.copy()
        app.storage.user["dias_marcados_vendas"] = dias_marcados

    # =============================================================================
    # SESSÃO 1: ANÁLISE DE VENDAS POR CLASSIFICAÇÃO (Agora com ID)
    # =============================================================================
    ui.label("SESSÃO 1: FATURAMENTO POR CLASSIFICAÇÃO MACRO").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest px-1 mt-2")
    
    with ui.row().classes("w-full items-stretch flex-col md:flex-row gap-4 mb-6"):
        if not mapa_lojas_class:
            with ui.card().classes(f"w-full p-6 text-center shadow-sm border {cor['borda']} {cor['fundo_card']}"):
                ui.label("Nenhum movimento de faturamento encontrado para este período.").classes(f"{cor['texto_secundario']} italic text-sm")
        else:
            # Itera cega usando o Dicionário, protegendo contra Loja 01 duplicada
            for fid, nome_loja in mapa_lojas_class.items():
                with ui.column().classes("w-full md:flex-1 min-w-0 gap-3"):
                    total_faturado = totais_loja.get(fid, 0.0)
                    with ui.card().classes(f"w-full p-4 rounded-2xl shadow-sm border {cor['vendas_borda']} {cor['vendas_bg']} gap-1"):
                        ui.label(nome_loja).classes(f"text-xs font-black {cor['vendas_titulo']} tracking-widest uppercase")
                        ui.label(f"R$ {formatar_moeda_brasil(total_faturado)}").classes(f"text-2xl font-black {cor['vendas_destaque']} tracking-tight")

                    categorias_da_loja = detalhe_classificacao.get(fid, {})
                    with ui.element('div').classes("w-full max-w-full overflow-x-auto pb-2"):
                        with ui.row().classes("flex flex-nowrap w-max gap-2"):
                            for cat_nome, cat_valor in categorias_da_loja.items():
                                with ui.card().classes(f"w-[140px] shrink-0 p-3 rounded-xl shadow-sm border {cor['borda']} {cor['fundo_card']} gap-0.5 hover:shadow-md transition-shadow"):
                                    ui.label(cat_nome).classes(f"text-[9px] font-black {cor['texto_secundario']} tracking-widest uppercase truncate w-full")
                                    ui.label(f"R$ {formatar_moeda_brasil(cat_valor)}").classes(f"text-sm font-black {cor['texto_principal']}")

    # =============================================================================
    # SESSÃO 2: GRÁFICO DE PICOS BLINDADO POR ID
    # =============================================================================
    ui.label("SESSÃO 2: FLUXO DE ATENDIMENTOS E PICOS DE MOVIMENTO").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest px-1 mt-2")
    container_grafico = ui.column().classes("w-full gap-2 mb-6")

    def atualizar_dias(dia, marcado):
        if marcado and dia not in dias_marcados:
            dias_marcados.append(dia)
        elif not marcado and dia in dias_marcados:
            dias_marcados.remove(dia)
        app.storage.user["dias_marcados_vendas"] = dias_marcados
        desenhar_grafico_picos()

    def desenhar_grafico_picos():
        container_grafico.clear()
        with container_grafico:
            if dias_semana_disp:
                with ui.card().classes(f"w-full p-3 rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']} shadow-none"):
                    ui.label("FILTRAR POR DIA DA SEMANA").classes(f"text-[9px] font-black {cor['texto_secundario']} tracking-widest mb-2 px-1")
                    with ui.element('div').classes("w-full grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-x-4 gap-y-1 px-1"):
                        for dia in dias_semana_disp:
                            ui.checkbox(dia, value=(dia in dias_marcados), on_change=lambda e, d=dia: atualizar_dias(d, e.value)).classes(f"text-xs font-bold {cor['texto_secundario']} truncate w-full").props("dense")

            if not dias_marcados:
                ui.label("Selecione ao menos um dia da semana para exibir o gráfico.").classes(f"{cor['texto_secundario']} text-xs italic mt-2")
                return

            with ui.card().classes(f"w-full p-4 rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']} mt-2"):
                if not tempos_unicos:
                    ui.label("Sem dados de horário registrados.").classes(f"{cor['texto_secundario']} italic text-sm w-full text-center py-8")
                else:
                    series_picos = []
                    cores_picos = ["#10b981", "#14b8a6", "#0ea5e9", "#6366f1"] 
                    for idx, (fid, nome_loja) in enumerate(mapa_lojas_picos.items()):
                        cor_atual = cores_picos[idx % len(cores_picos)]
                        dados_consolidados_loja = []
                        for tempo in tempos_unicos:
                            soma_hora = sum(dados_picos[fid][d][tempo] for d in dias_marcados if d in dados_picos[fid])
                            dados_consolidados_loja.append(soma_hora if soma_hora > 0 else None)
                        
                        series_picos.append({
                            "name": nome_loja, 
                            "type": "bar",
                            "data": dados_consolidados_loja,
                            "itemStyle": {"color": cor_atual, "borderRadius": [4, 4, 0, 0]},
                            "label": {"show": True, "position": "top", "fontSize": 9, "color": cor_atual, "fontWeight": "bold"}
                        })

                    ui.echart({
                        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}, "valueFormatter": "(value) => value + ' Clientes'"},
                        "legend": {"bottom": "0%", "textStyle": {"fontSize": 11, "fontWeight": "bold", "color": "#888888"}},
                        "grid": {"left": "0%", "right": "1%", "bottom": "12%", "top": "10%", "containLabel": True},
                        "xAxis": {"type": "category", "data": tempos_unicos, "axisLabel": {"fontSize": 10, "fontWeight": "bold", "color": "#888888", "interval": 0}, "axisTick": {"show": False}},
                        "yAxis": {"type": "value", "axisLabel": {"show": False}, "splitLine": {"lineStyle": {"type": "dashed", "color": "#333333"}}},
                        "series": series_picos,
                    }).classes("w-full h-[320px]")

    desenhar_grafico_picos()

    # =============================================================================
    # SESSÃO 3: ANÁLISE POR FORMA DE PAGAMENTO (ATIVA)
    # =============================================================================
    ui.label("SESSÃO 3: FATURAMENTO POR MEIOS DE PAGAMENTO").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest px-1 mt-2")

    if not mapa_lojas_pgto:
        with ui.card().classes(f"w-full p-8 text-center rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']}"):
            ui.label("Nenhum dado financeiro encontrado.").classes(f"{cor['texto_secundario']} italic text-sm")
    else:
        with ui.row().classes("w-full items-stretch flex-col md:flex-row gap-4 pb-8 mt-2"):
            for fid, nome_loja in mapa_lojas_pgto.items():
                pgtos_loja = dados_pagamentos.get(fid, {})
                series_data = [{"name": k, "value": v} for k, v in pgtos_loja.items()]
                
                with ui.card().classes(f"flex-1 p-4 rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']} min-w-[300px]"):
                    ui.label(nome_loja).classes(f"text-xs font-black {cor['texto_principal']} tracking-widest uppercase text-center w-full mb-2")
                    
                    if not series_data:
                        ui.label("Sem movimentação financeira.").classes(f"{cor['texto_secundario']} text-xs italic text-center w-full py-10")
                    else:
                        ui.echart({
                            "tooltip": {"trigger": "item", "valueFormatter": "(value) => 'R$ ' + value.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})"},
                            "legend": {"bottom": "0%", "type": "scroll", "textStyle": {"fontSize": 10, "fontWeight": "bold", "color": "#888888"}},
                            "series": [{
                                "name": "Faturamento",
                                "type": "pie",
                                "radius": ["45%", "75%"],
                                "avoidLabelOverlap": False,
                                "itemStyle": {"borderRadius": 10},
                                "label": {"show": False, "position": "center"},
                                "emphasis": {"label": {"show": True, "fontSize": 12, "fontWeight": "bold", "formatter": "{b}\n{d}%"}},
                                "labelLine": {"show": False},
                                "data": series_data
                            }]
                        }).classes("w-full h-[300px]")