from nicegui import ui, app
import datetime

# Importamos a função de compras que já existe no motor!
from motor_dados import obter_dados_dashboard_fast, obter_dados_pagamentos_diarios_fast, obter_dados_compras_fast, formatar_moeda_brasil

# =========================================================================================
# TELAS EM CONSTRUÇÃO
# =========================================================================================
def desenhar_tela_resumo():
    ui.label("Tela de Resumo em construção...").classes("text-xl text-slate-400 font-bold p-10")

def desenhar_tela_vendas_loja():
    ui.label("Tela de Vendas da Loja em construção...").classes("text-xl text-slate-400 font-bold p-10")

# =========================================================================================
# INTERFACE FRONT-END - DASHBOARD PRINCIPAL
# =========================================================================================
def desenhar_tela_dashboard_principal():
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))

    # --- CABEÇALHO ---
    with ui.row().classes("w-full justify-between items-center mb-4 bg-white p-4 rounded-2xl shadow-sm border border-cyan-100 flex-wrap gap-4"):
        with ui.column().classes("gap-1"):
            ui.label("Visão Mensal Consolidada").classes("text-cyan-800 text-lg font-black tracking-widest uppercase")
            ui.label("Dashboard financeiro de todas as filiais").classes("text-xs text-slate-500")

        def recarregar_tela(e):
            app.storage.user["mes"] = int(sel_mes.value)
            app.storage.user["ano"] = int(sel_ano.value)
            ui.navigate.to('/')

        with ui.row().classes("items-center bg-cyan-50/50 p-2 rounded-xl border border-cyan-100 gap-2"):
            ui.icon("calendar_month", size="sm").classes("text-emerald-500 ml-2")
            meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            sel_mes = ui.select(meses_pt, value=mes_atual, on_change=recarregar_tela).classes("w-28 font-bold text-cyan-900").props("borderless dense hide-bottom-space")
            sel_ano = ui.select([2024, 2025, 2026], value=ano_atual, on_change=recarregar_tela).classes("w-20 font-bold text-cyan-900").props("borderless dense hide-bottom-space")

    # Extração de dados chamando os Motores (Execução Única super rápida)
    dados, totais, mapa_lojas, quant_dias = obter_dados_dashboard_fast(mes_atual, ano_atual)
    
    # DADOS EM RAM PARA OS CLIQUES (Sem requisições repetidas ao banco!)
    dados_pgto_diario, mapa_lojas_pgto = obter_dados_pagamentos_diarios_fast(mes_atual, ano_atual)
    lista_todas_notas_compras = obter_dados_compras_fast(mes_atual, ano_atual)

    # =====================================================================================
    # MODAL 1: DRILL-DOWN DE VENDAS
    # =====================================================================================
    dialog_detalhe_vendas = ui.dialog()
    with dialog_detalhe_vendas, ui.card().classes("w-full max-w-5xl p-6 rounded-2xl bg-slate-50 border border-slate-200"):
        container_detalhe_vendas = ui.column().classes("w-full gap-4")
        with ui.row().classes("w-full justify-end mb-[-20px] z-10"):
            ui.button(icon="close", on_click=dialog_detalhe_vendas.close).props("flat round color=slate size=sm")

    def abrir_detalhe_vendas_dia(dia_clicado):
        container_detalhe_vendas.clear()
        with container_detalhe_vendas:
            ui.label(f"Detalhamento de Faturamento - Dia {dia_clicado}/{mes_atual:02d}/{ano_atual}").classes("text-lg font-black text-emerald-800 tracking-widest uppercase mb-4")
            if not mapa_lojas_pgto:
                ui.label("Banco de dados não retornou meios de pagamento.").classes("text-slate-400 italic text-sm")
            else:
                with ui.row().classes("w-full items-stretch flex-col md:flex-row gap-4"):
                    for fid, nome_loja in mapa_lojas_pgto.items():
                        pgtos_loja_dia = dados_pgto_diario.get(str(dia_clicado), {}).get(fid, {})
                        total_dia_loja = sum(v for v in pgtos_loja_dia.values())
                        
                        with ui.card().classes("flex-1 p-4 rounded-xl shadow-sm border border-slate-200 bg-white min-w-[280px] gap-1"):
                            with ui.row().classes("w-full justify-between items-center mb-2 pb-2 border-b border-slate-100"):
                                ui.label(nome_loja).classes("text-xs font-black text-slate-500 tracking-widest uppercase")
                                ui.label(f"Total: R$ {formatar_moeda_brasil(total_dia_loja)}").classes("text-sm font-black text-emerald-600")
                            if not pgtos_loja_dia:
                                ui.label("Nenhum movimento registrado neste dia.").classes("text-slate-400 text-xs italic text-center w-full py-4")
                            else:
                                pgtos_ordenados = sorted(pgtos_loja_dia.items(), key=lambda item: item[1], reverse=True)
                                with ui.column().classes("w-full gap-2 mt-1"):
                                    for forma, valor in pgtos_ordenados:
                                        with ui.row().classes("w-full justify-between items-center bg-slate-50 px-2 py-1.5 rounded"):
                                            ui.label(forma).classes("text-[11px] font-bold text-slate-600")
                                            ui.label(f"R$ {formatar_moeda_brasil(valor)}").classes("text-xs font-black text-slate-800")
        dialog_detalhe_vendas.open()


    # =====================================================================================
    # MODAL 2: DRILL-DOWN DE COMPRAS (O Novo Design Compacto)
    # =====================================================================================
    dialog_detalhe_compras = ui.dialog()
    with dialog_detalhe_compras, ui.card().classes("w-full max-w-5xl p-6 rounded-2xl bg-slate-50 border border-slate-200"):
        container_detalhe_compras = ui.column().classes("w-full gap-4")
        with ui.row().classes("w-full justify-end mb-[-20px] z-10"):
            ui.button(icon="close", on_click=dialog_detalhe_compras.close).props("flat round color=slate size=sm")

    def abrir_detalhe_compras_dia(dia_clicado):
        container_detalhe_compras.clear()
        
        # A função original formata as datas em dd/mm/yyyy. Vamos montar a string para filtrar na memória
        dia_str_busca = f"{int(dia_clicado):02d}/{mes_atual:02d}/{ano_atual}"
        
        with container_detalhe_compras:
            ui.label(f"Entrada de Notas Fiscais - Dia {dia_clicado}/{mes_atual:02d}/{ano_atual}").classes("text-lg font-black text-blue-800 tracking-widest uppercase mb-4")
            
            # Filtra todas as notas do mês apenas para este dia específico (Feito em RAM, mega rápido)
            notas_do_dia = [n for n in lista_todas_notas_compras if n.get('data_emissao') == dia_str_busca]

            if not notas_do_dia:
                ui.label("Nenhuma nota fiscal registrada neste dia.").classes("text-slate-400 italic text-sm")
            else:
                with ui.row().classes("w-full items-stretch flex-col md:flex-row gap-4"):
                    for fid, nome_loja in mapa_lojas.items():
                        
                        notas_loja = [n for n in notas_do_dia if str(n.get('filial', '')) == str(fid)]
                        total_dia_loja = sum(n.get('valor_total', 0.0) for n in notas_loja)
                        
                        with ui.card().classes("flex-1 p-3 rounded-xl shadow-sm border border-slate-200 bg-white min-w-[280px] gap-0"):
                            # Cabeçalho do Card (Loja e Total)
                            with ui.row().classes("w-full justify-between items-center mb-2 pb-2 border-b border-slate-100"):
                                ui.label(nome_loja).classes("text-xs font-black text-slate-500 tracking-widest uppercase")
                                ui.label(f"Total: R$ {formatar_moeda_brasil(total_dia_loja)}").classes("text-sm font-black text-blue-600")
                            
                            if not notas_loja:
                                ui.label("Nenhuma entrada.").classes("text-slate-300 text-[10px] italic text-center w-full py-4")
                            else:
                                # Container com Scroll vertical caso haja 10, 20, 50 notas no mesmo dia
                                with ui.column().classes("w-full gap-1 mt-1 max-h-[250px] overflow-y-auto pr-1"):
                                    for nota in notas_loja:
                                        with ui.row().classes("w-full justify-between items-center bg-slate-50 px-2 py-1 rounded gap-2 flex-nowrap"):
                                            with ui.column().classes("gap-0 min-w-0 flex-1"):
                                                ui.label(nota['fornecedor']).classes("text-[10px] font-bold text-slate-600 truncate w-full")
                                                ui.label(f"NFe {nota['numero_nota']} - {nota['status_nota']}").classes("text-[8px] font-bold text-slate-400")
                                            
                                            ui.label(f"R$ {formatar_moeda_brasil(nota['valor_total'])}").classes("text-[11px] font-black text-slate-800 shrink-0")

        dialog_detalhe_compras.open()


    # =====================================================================================
    # --- CARTÕES SUPERIORES MODULARIZADOS ---
    # =====================================================================================
    with ui.row().classes("w-full flex-nowrap gap-4 overflow-x-auto pb-4 items-stretch"):
        ui.column().classes("w-20 shrink-0 bg-transparent")

        def desenhar_cartao_vendas():
            with ui.card().classes("flex-1 min-w-[280px] p-2 md:p-3 rounded-xl bg-emerald-50 border border-slate-200 shadow-none gap-0"):
                ui.label("Vendas").classes("text-[10px] font-bold tracking-widest uppercase text-emerald-800 mb-0")
                soma_geral = sum(totais.get(f"vend_{fid}", 0.0) for fid in mapa_lojas)
                ui.label(f"R$ {formatar_moeda_brasil(soma_geral)}").classes("text-lg md:text-xl font-bold text-emerald-600 tracking-tighter mb-1")
                with ui.row().classes("w-full justify-between items-center border-t border-slate-200/60 pt-1 mt-1"):
                    for fid, nome_loja in mapa_lojas.items():
                        val = totais.get(f"vend_{fid}", 0.0)
                        ui.label(f"{nome_loja}: R$ {formatar_moeda_brasil(val)}").classes("text-[9px] font-bold text-emerald-800")

        def desenhar_cartao_boletos():
            with ui.card().classes("flex-1 min-w-[280px] p-2 md:p-3 rounded-xl bg-amber-50/50 border border-slate-200 shadow-none gap-0 opacity-70"):
                ui.label("Boletos").classes("text-[10px] font-bold tracking-widest uppercase text-amber-800 mb-0")
                ui.label("R$ 0,00").classes("text-lg md:text-xl font-bold text-amber-600 tracking-tighter mb-1")
                with ui.row().classes("w-full justify-between items-center border-t border-slate-200/60 pt-1 mt-1"):
                    ui.label("Aguardando implantação").classes("text-[9px] font-bold text-amber-800 italic")

        def desenhar_cartao_compras():
            with ui.card().classes("flex-1 min-w-[280px] p-2 md:p-3 rounded-xl bg-blue-50 border border-slate-200 shadow-none gap-0"):
                ui.label("Compras").classes("text-[10px] font-bold tracking-widest uppercase text-blue-800 mb-0")
                soma_geral = sum(totais.get(f"comp_{fid}", 0.0) for fid in mapa_lojas)
                ui.label(f"R$ {formatar_moeda_brasil(soma_geral)}").classes("text-lg md:text-xl font-bold text-blue-600 tracking-tighter mb-1")
                with ui.row().classes("w-full justify-between items-center border-t border-slate-200/60 pt-1 mt-1"):
                    for fid, nome_loja in mapa_lojas.items():
                        val = totais.get(f"comp_{fid}", 0.0)
                        ui.label(f"{nome_loja}: R$ {formatar_moeda_brasil(val)}").classes("text-[9px] font-bold text-blue-800")

        def desenhar_cartao_despesas():
            with ui.card().classes("flex-1 min-w-[280px] p-2 md:p-3 rounded-xl bg-rose-50/50 border border-slate-200 shadow-none gap-0 opacity-70"):
                ui.label("Despesas").classes("text-[10px] font-bold tracking-widest uppercase text-rose-800 mb-0")
                ui.label("R$ 0,00").classes("text-lg md:text-xl font-bold text-rose-600 tracking-tighter mb-1")
                with ui.row().classes("w-full justify-between items-center border-t border-slate-200/60 pt-1 mt-1"):
                    ui.label("Aguardando implantação").classes("text-[9px] font-bold text-rose-800 italic")

        desenhar_cartao_vendas()
        desenhar_cartao_boletos()
        desenhar_cartao_compras()
        desenhar_cartao_despesas()

    # =====================================================================================
    # --- GRID GIGANTE DE TABELAS ---
    # =====================================================================================
    with ui.row().classes("w-full flex-nowrap gap-4 overflow-x-auto pb-4 items-stretch"):
        def desenhar_bloco_tabela(titulo, sub_titulo, bg_head, txt_head, bg_table, tamanho, prefixo):
            with ui.column().classes(f"gap-0 rounded-2xl shadow-lg bg-white overflow-hidden border border-slate-200 {tamanho}"):
                
                with ui.column().classes(f"w-full items-center justify-center {bg_head} {txt_head} py-2 border-b border-slate-200 gap-0"):
                    ui.label(titulo).classes("font-black text-sm tracking-widest uppercase")
                    if sub_titulo:
                        ui.label(sub_titulo).classes("text-[8px] font-bold opacity-70 tracking-widest uppercase")
                
                cols = []
                if prefixo == "dia":
                    cols.append({"name": "dia", "label": "Dia", "field": "dia", "align": "center", "classes": "bg-slate-100 font-bold"})
                else:
                    if not mapa_lojas:
                        cols.append({"name": "vazio", "label": "SEM DADOS", "field": "vazio", "align": "center", "classes": "text-slate-400 italic"})
                    for fid, nome_loja in mapa_lojas.items():
                        cols.append({"name": str(fid), "label": nome_loja, "field": f"{prefixo}_{fid}", "align": "right"})
                
                tabela = ui.table(columns=cols, rows=dados, row_key="dia").props(
                    f'flat bordered dense separator="cell" hide-bottom hide-pagination :pagination="{{rowsPerPage: {quant_dias}}}" hover'
                ).classes(f"w-full {bg_table}")

                # GATILHOS DE CLIQUE PARA AS DUAS COLUNAS
                if prefixo == "vend":
                    tabela.on('row-click', lambda e: abrir_detalhe_vendas_dia(e.args[1]['dia']))
                    tabela.classes("cursor-pointer hover:shadow-inner transition-all")
                elif prefixo == "comp":
                    tabela.on('row-click', lambda e: abrir_detalhe_compras_dia(e.args[1]['dia']))
                    tabela.classes("cursor-pointer hover:shadow-inner transition-all")

        desenhar_bloco_tabela("Data", None, "bg-slate-200", "text-slate-700", "bg-white", "w-20 shrink-0", "dia")
        desenhar_bloco_tabela("Vendas", "Clica na linha p/ detalhar", "bg-emerald-100", "text-emerald-900", "bg-emerald-50/30", "flex-1 min-w-[280px]", "vend")
        desenhar_bloco_tabela("Boletos", None, "bg-amber-100", "text-amber-900", "bg-amber-50/30", "flex-1 min-w-[280px]", "bol")
        
        # Inseri a dica de clique para as compras também
        desenhar_bloco_tabela("Compras", "Clica na linha p/ detalhar", "bg-blue-100", "text-blue-900", "bg-blue-50/30", "flex-1 min-w-[280px]", "comp")
        
        desenhar_bloco_tabela("Despesas", None, "bg-rose-100", "text-rose-900", "bg-rose-50/30", "flex-1 min-w-[280px]", "desp")