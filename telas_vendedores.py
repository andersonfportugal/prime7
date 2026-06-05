from nicegui import ui, app
import datetime
from motor_dados import obter_dados_vendedores_fast, formatar_moeda_brasil

def desenhar_tela_performance_vendedores():
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))
    vendedores_marcados = app.storage.user.get("vendedores_marcados", [])

    # --- CABEÇALHO ---
    with ui.row().classes("w-full justify-between items-center mb-4 bg-white p-4 rounded-2xl shadow-sm border border-indigo-100 flex-wrap gap-4 text-slate-800"):
        with ui.column().classes("gap-1"):
            ui.label("Performance da Equipe Comercial").classes("text-indigo-800 text-lg font-black tracking-widest uppercase")
            ui.label("Análise comparativa de faturamento e atendimentos").classes("text-xs text-slate-500")

        def recarregar_dados_globais(e):
            app.storage.user["mes"] = int(sel_mes.value)
            app.storage.user["ano"] = int(sel_ano.value)
            ui.navigate.to('/')

        with ui.row().classes("items-center bg-indigo-50/50 p-2 rounded-xl border border-indigo-100 gap-2"):
            ui.icon("calendar_month", size="sm").classes("text-indigo-500 ml-2")
            meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            sel_mes = ui.select(meses_pt, value=mes_atual, on_change=recarregar_dados_globais).classes("w-28 font-bold text-indigo-900").props("borderless dense hide-bottom-space")
            sel_ano = ui.select([2024, 2025, 2026], value=ano_atual, on_change=recarregar_dados_globais).classes("w-20 font-bold text-indigo-900").props("borderless dense hide-bottom-space")

    # Extração usando o novo Motor com IDs Cegos
    resumo_mes, evolucao_ano, mapa_vendedores = obter_dados_vendedores_fast(mes_atual, ano_atual)
    
    # Extrai as chaves únicas (Ex: '216483||MARCOS')
    lista_vend_ids = sorted(list(mapa_vendedores.keys()))

    # Configuração de seleção padrão baseada nos IDs invisíveis
    vendedores_marcados = [v for v in vendedores_marcados if v in lista_vend_ids]
    if not vendedores_marcados and lista_vend_ids:
        vendedores_marcados = lista_vend_ids[:2]
        app.storage.user["vendedores_marcados"] = vendedores_marcados

    container_dinamico = ui.column().classes("w-full gap-4")

    def atualizar_checkbox(vend_id, marcado):
        if marcado and vend_id not in vendedores_marcados:
            vendedores_marcados.append(vend_id)
        elif not marcado and vend_id in vendedores_marcados:
            vendedores_marcados.remove(vend_id)
        
        app.storage.user["vendedores_marcados"] = vendedores_marcados
        desenhar_painel_dinamico()

    def desenhar_painel_dinamico():
        container_dinamico.clear()
        
        with container_dinamico:
            if not lista_vend_ids:
                ui.label("Nenhuma venda registrada neste período.").classes("text-slate-400 italic text-sm text-center w-full mt-6")
                return

            # =============================================================================
            # SEÇÃO DE CHECKBOXES TABULADOS
            # =============================================================================
            with ui.card().classes("w-full p-3 rounded-2xl shadow-sm border border-indigo-50 bg-white shadow-none"):
                ui.label("EQUIPE COMERCIAL").classes("text-[9px] font-black text-slate-400 tracking-widest mb-2 px-1")
                
                with ui.element('div').classes("w-full grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-x-4 gap-y-1 px-1"):
                    for vid in lista_vend_ids:
                        nome_exibicao = mapa_vendedores[vid]
                        ui.checkbox(
                            nome_exibicao, 
                            value=(vid in vendedores_marcados), 
                            on_change=lambda e, v=vid: atualizar_checkbox(v, e.value)
                        ).classes("text-xs font-bold text-slate-500 truncate w-full").props("dense")

            if not vendedores_marcados:
                ui.label("Marque os vendedores acima para exibir a análise.").classes("text-slate-400 text-xs italic mt-2")
                return

            # =============================================================================
            # BLOCO 1: CARDS DOS VENDEDORES COLORIDOS
            # =============================================================================
            ui.label("DESEMPENHO NO MÊS SELECIONADO").classes("text-[10px] font-black text-slate-400 tracking-widest mt-2 px-1")
            
            paleta_dinamica = [
                ("border-l-indigo-500", "text-indigo-800"), ("border-l-emerald-500", "text-emerald-800"),
                ("border-l-rose-500", "text-rose-800"), ("border-l-amber-500", "text-amber-800"),
                ("border-l-cyan-500", "text-cyan-800"), ("border-l-fuchsia-500", "text-fuchsia-800"),
                ("border-l-lime-500", "text-lime-800"), ("border-l-orange-500", "text-orange-800")
            ]

            with ui.row().classes("w-full flex-wrap gap-3 items-stretch"):
                for idx, vid in enumerate(vendedores_marcados):
                    dados = resumo_mes.get(vid, {'vendas': 0.0, 'tickets': 0})
                    nome_exibicao = mapa_vendedores[vid]
                    
                    vendas = dados['vendas']
                    tickets = dados['tickets']
                    tk_medio = vendas / tickets if tickets > 0 else 0.0
                    
                    classe_borda, classe_texto = paleta_dinamica[idx % len(paleta_dinamica)]
                    
                    with ui.card().classes(f"w-full sm:w-[240px] p-4 rounded-2xl shadow-sm border-l-4 {classe_borda} bg-white gap-0.5 hover:shadow-md transition-shadow"):
                        ui.label(nome_exibicao).classes(f"text-[10px] font-black {classe_texto} uppercase tracking-widest truncate w-full")
                        ui.label(f"R$ {formatar_moeda_brasil(vendas)}").classes("text-xl font-black text-slate-700 mt-0.5")
                        
                        with ui.row().classes("w-full justify-between items-center mt-3 pt-2 border-t border-slate-100"):
                            ui.label(f"{tickets} atend.").classes("text-[10px] font-bold text-slate-400")
                            ui.label(f"TM: R$ {formatar_moeda_brasil(tk_medio)}").classes("text-[10px] font-bold text-emerald-600")

            # =============================================================================
            # BLOCO 2: LINHA DO TEMPO ANUAL TABULAR
            # =============================================================================
            with ui.column().classes("w-full gap-0 rounded-2xl shadow-lg bg-white overflow-hidden border border-slate-200 mt-4"):
                ui.label("LINHA DO TEMPO ANUAL COMPARATIVA (R$)").classes("w-full text-center bg-indigo-100 text-indigo-900 font-black py-3 text-sm tracking-widest uppercase border-b border-slate-200")
                
                cols = [{"name": "mes", "label": "Mês", "field": "mes", "align": "center", "classes": "bg-slate-100 font-bold", "style": "min-width: 130px; width: 130px;"}]
                for vid in vendedores_marcados:
                    cols.append({
                        "name": str(vid), 
                        "label": mapa_vendedores[vid], 
                        "field": str(vid), 
                        "align": "right", 
                        "style": "min-width: 160px; width: 160px;", 
                        "headerClasses": "truncate"
                    })
                
                meses_nomes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
                rows = []
                for idx, nome_mes in enumerate(meses_nomes):
                    linha = {"mes": nome_mes}
                    for vid in vendedores_marcados:
                        valores_ano = evolucao_ano.get(vid, [0.0] * 12)
                        linha[str(vid)] = formatar_moeda_brasil(valores_ano[idx])
                    rows.append(linha)
                
                ui.table(columns=cols, rows=rows, row_key="mes").props(
                    'flat bordered dense separator="cell" hide-bottom hide-pagination :pagination="{rowsPerPage: 12}" hover'
                ).classes("w-full text-slate-700")

    desenhar_painel_dinamico()