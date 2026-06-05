from nicegui import ui, app
import datetime
from motor_dados import obter_dados_vendas_classificacao_fast, obter_dados_picos_horario_fast, obter_dados_pagamentos_fast, formatar_moeda_brasil

def desenhar_tela_vendas_loja():
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))

    # --- CABEÇALHO ---
    with ui.row().classes("w-full justify-between items-center mb-4 bg-white p-4 rounded-2xl shadow-sm border border-emerald-100 flex-wrap gap-4 text-slate-800"):
        with ui.column().classes("gap-1"):
            ui.label("Diretoria de Vendas e Faturamento").classes("text-emerald-800 text-lg font-black tracking-widest uppercase")
            ui.label("Análise macro por filiais, departamentos e picos de horários").classes("text-xs text-slate-500")

        def recarregar_vendas(e):
            app.storage.user["mes"] = int(sel_mes.value)
            app.storage.user["ano"] = int(sel_ano.value)
            ui.navigate.to('/')

        with ui.row().classes("items-center bg-emerald-50/50 p-2 rounded-xl border border-emerald-100 gap-2"):
            ui.icon("monetization_on", size="sm").classes("text-emerald-500 ml-2")
            meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            sel_mes = ui.select(meses_pt, value=mes_atual, on_change=recarregar_vendas).classes("w-28 font-bold text-emerald-900").props("borderless dense hide-bottom-space")
            sel_ano = ui.select([2024, 2025, 2026], value=ano_atual, on_change=recarregar_vendas).classes("w-20 font-bold text-emerald-900").props("borderless dense hide-bottom-space")

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
    ui.label("SESSÃO 1: FATURAMENTO POR CLASSIFICAÇÃO MACRO").classes("text-[10px] font-black text-slate-400 tracking-widest px-1 mt-2")
    
    with ui.row().classes("w-full items-stretch flex-col md:flex-row gap-4 mb-6"):
        if not mapa_lojas_class:
            with ui.card().classes("w-full p-6 text-center shadow-sm border border-slate-100 bg-white"):
                ui.label("Nenhum movimento de faturamento encontrado para este período.").classes("text-slate-400 italic text-sm")
        else:
            # Itera cega usando o Dicionário, protegendo contra Loja 01 duplicada
            for fid, nome_loja in mapa_lojas_class.items():
                with ui.column().classes("w-full md:flex-1 min-w-0 gap-3"):
                    total_faturado = totais_loja.get(fid, 0.0)
                    with ui.card().classes("w-full p-4 rounded-2xl shadow-sm border border-emerald-200 bg-emerald-50/40 gap-1"):
                        ui.label(nome_loja).classes("text-xs font-black text-emerald-800 tracking-widest uppercase")
                        ui.label(f"R$ {formatar_moeda_brasil(total_faturado)}").classes("text-2xl font-black text-emerald-700 tracking-tight")

                    categorias_da_loja = detalhe_classificacao.get(fid, {})
                    with ui.element('div').classes("w-full max-w-full overflow-x-auto pb-2"):
                        with ui.row().classes("flex flex-nowrap w-max gap-2"):
                            for cat_nome, cat_valor in categorias_da_loja.items():
                                with ui.card().classes("w-[140px] shrink-0 p-3 rounded-xl shadow-sm border border-slate-100 bg-white gap-0.5 hover:shadow-md transition-shadow"):
                                    ui.label(cat_nome).classes("text-[9px] font-black text-slate-400 tracking-widest uppercase truncate w-full")
                                    ui.label(f"R$ {formatar_moeda_brasil(cat_valor)}").classes("text-sm font-black text-slate-700")

    # =============================================================================
    # SESSÃO 2: GRÁFICO DE PICOS BLINDADO POR ID
    # =============================================================================
    ui.label("SESSÃO 2: FLUXO DE ATENDIMENTOS E PICOS DE MOVIMENTO").classes("text-[10px] font-black text-slate-400 tracking-widest px-1 mt-2")
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
                with ui.card().classes("w-full p-3 rounded-2xl shadow-sm border border-emerald-50 bg-white shadow-none"):
                    ui.label("FILTRAR POR DIA DA SEMANA").classes("text-[9px] font-black text-slate-400 tracking-widest mb-2 px-1")
                    with ui.element('div').classes("w-full grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-x-4 gap-y-1 px-1"):
                        for dia in dias_semana_disp:
                            ui.checkbox(dia, value=(dia in dias_marcados), on_change=lambda e, d=dia: atualizar_dias(d, e.value)).classes("text-xs font-bold text-slate-500 truncate w-full").props("dense")

            if not dias_marcados:
                ui.label("Selecione ao menos um dia da semana para exibir o gráfico.").classes("text-slate-400 text-xs italic mt-2")
                return

            with ui.card().classes("w-full p-4 rounded-2xl shadow-sm border border-slate-100 bg-white mt-2"):
                if not tempos_unicos:
                    ui.label("Sem dados de horário registrados.").classes("text-slate-400 italic text-sm w-full text-center py-8")
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
                        "legend": {"bottom": "0%", "textStyle": {"fontSize": 11, "fontWeight": "bold"}},
                        "grid": {"left": "0%", "right": "1%", "bottom": "12%", "top": "10%", "containLabel": True},
                        "xAxis": {"type": "category", "data": tempos_unicos, "axisLabel": {"fontSize": 10, "fontWeight": "bold", "color": "#64748b", "interval": 0}, "axisTick": {"show": False}},
                        "yAxis": {"type": "value", "axisLabel": {"show": False}, "splitLine": {"lineStyle": {"type": "dashed", "color": "#f1f5f9"}}},
                        "series": series_picos,
                    }).classes("w-full h-[320px]")

    desenhar_grafico_picos()

    # =============================================================================
    # SESSÃO 3: ANÁLISE POR FORMA DE PAGAMENTO (ATIVA)
    # =============================================================================
    ui.label("SESSÃO 3: FATURAMENTO POR MEIOS DE PAGAMENTO").classes("text-[10px] font-black text-slate-400 tracking-widest px-1 mt-2")

    if not mapa_lojas_pgto:
        with ui.card().classes("w-full p-8 text-center rounded-2xl shadow-sm border border-slate-100 bg-white"):
            ui.label("Nenhum dado financeiro encontrado.").classes("text-slate-400 italic text-sm")
    else:
        with ui.row().classes("w-full items-stretch flex-col md:flex-row gap-4 pb-8 mt-2"):
            for fid, nome_loja in mapa_lojas_pgto.items():
                pgtos_loja = dados_pagamentos.get(fid, {})
                series_data = [{"name": k, "value": v} for k, v in pgtos_loja.items()]
                
                with ui.card().classes("flex-1 p-4 rounded-2xl shadow-sm border border-slate-100 bg-white min-w-[300px]"):
                    ui.label(nome_loja).classes("text-xs font-black text-slate-600 tracking-widest uppercase text-center w-full mb-2")
                    
                    if not series_data:
                        ui.label("Sem movimentação financeira.").classes("text-slate-400 text-xs italic text-center w-full py-10")
                    else:
                        ui.echart({
                            "tooltip": {"trigger": "item", "valueFormatter": "(value) => 'R$ ' + value.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})"},
                            "legend": {"bottom": "0%", "type": "scroll", "textStyle": {"fontSize": 10, "fontWeight": "bold"}},
                            "series": [{
                                "name": "Faturamento",
                                "type": "pie",
                                "radius": ["45%", "75%"],
                                "avoidLabelOverlap": False,
                                "itemStyle": {"borderRadius": 10, "borderColor": "#fff", "borderWidth": 2},
                                "label": {"show": False, "position": "center"},
                                "emphasis": {"label": {"show": True, "fontSize": 12, "fontWeight": "bold", "formatter": "{b}\n{d}%"}},
                                "labelLine": {"show": False},
                                "data": series_data
                            }]
                        }).classes("w-full h-[300px]")