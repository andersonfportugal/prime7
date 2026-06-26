from nicegui import ui, app
import datetime
import tema

# Importamos a função de compras que já existe no motor!
from motor_dados import obter_dados_dashboard_fast, obter_dados_pagamentos_diarios_fast, obter_dados_compras_fast, formatar_moeda_brasil

# =========================================================================================
# TELAS EM CONSTRUÇÃO
# =========================================================================================
def desenhar_tela_resumo():
    cor = tema.obter_cores()
    ui.label("Tela de Resumo em construção...").classes(f"text-xl {cor['texto_secundario']} font-bold p-10")

def desenhar_tela_vendas_loja():
    cor = tema.obter_cores()
    ui.label("Tela de Vendas da Loja em construção...").classes(f"text-xl {cor['texto_secundario']} font-bold p-10")

# =========================================================================================
# INTERFACE FRONT-END - DASHBOARD PRINCIPAL
# =========================================================================================
def desenhar_tela_dashboard_principal():
    cor = tema.obter_cores()
    
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))

    # --- CABEÇALHO ---
    with ui.row().classes(f"w-full justify-between items-center mb-4 {cor['fundo_card']} p-4 rounded-2xl shadow-sm border {cor['borda']} flex-wrap gap-4"):
        with ui.column().classes("gap-1"):
            ui.label("Visão Mensal Consolidada").classes(f"{cor['destaque']} text-lg font-black tracking-widest uppercase")
            ui.label("Dashboard financeiro de todas as filiais").classes(f"text-xs {cor['texto_secundario']}")

        # Extração de dados chamando os Motores (Execução Única super rápida)
    dados, totais, mapa_lojas, quant_dias = obter_dados_dashboard_fast(mes_atual, ano_atual)
    
    # DADOS EM RAM PARA OS CLIQUES (Sem requisições repetidas ao banco!)
    dados_pgto_diario, mapa_lojas_pgto = obter_dados_pagamentos_diarios_fast(mes_atual, ano_atual)
    lista_todas_notas_compras = obter_dados_compras_fast(mes_atual, ano_atual)

    # =====================================================================================
    # MODAL 1: DRILL-DOWN DE VENDAS
    # =====================================================================================
    dialog_detalhe_vendas = ui.dialog()
    with dialog_detalhe_vendas, ui.card().classes(f"w-full max-w-5xl p-6 rounded-2xl {cor['fundo_tela']} border {cor['borda']}"):
        container_detalhe_vendas = ui.column().classes("w-full gap-4")
        with ui.row().classes("w-full justify-end mb-[-20px] z-10"):
            ui.button(icon="close", on_click=dialog_detalhe_vendas.close).props("flat round size=sm").classes(cor['texto_secundario'])

    def abrir_detalhe_vendas_dia(dia_clicado):
        container_detalhe_vendas.clear()
        with container_detalhe_vendas:
            ui.label(f"Detalhamento de Faturamento - Dia {dia_clicado}/{mes_atual:02d}/{ano_atual}").classes(f"text-lg font-black {cor['vendas_titulo']} tracking-widest uppercase mb-4")
            if not mapa_lojas_pgto:
                ui.label("Banco de dados não retornou meios de pagamento.").classes(f"{cor['texto_secundario']} italic text-sm")
            else:
                with ui.row().classes("w-full items-stretch flex-col md:flex-row gap-4"):
                    for fid, nome_loja in mapa_lojas_pgto.items():
                        pgtos_loja_dia = dados_pgto_diario.get(str(dia_clicado), {}).get(fid, {})
                        total_dia_loja = sum(v for v in pgtos_loja_dia.values())
                        
                        with ui.card().classes(f"flex-1 p-4 rounded-xl shadow-sm border {cor['vendas_borda']} {cor['fundo_card']} min-w-[280px] gap-1"):
                            with ui.row().classes(f"w-full justify-between items-center mb-2 pb-2 border-b {cor['borda']}"):
                                ui.label(nome_loja).classes(f"text-xs font-black {cor['texto_secundario']} tracking-widest uppercase")
                                ui.label(f"Total: R$ {formatar_moeda_brasil(total_dia_loja)}").classes(f"text-sm font-black {cor['vendas_destaque']}")
                            if not pgtos_loja_dia:
                                ui.label("Nenhum movimento registrado neste dia.").classes(f"{cor['texto_secundario']} text-xs italic text-center w-full py-4")
                            else:
                                pgtos_ordenados = sorted(pgtos_loja_dia.items(), key=lambda item: item[1], reverse=True)
                                with ui.column().classes("w-full gap-2 mt-1"):
                                    for forma, valor in pgtos_ordenados:
                                        with ui.row().classes(f"w-full justify-between items-center {cor['fundo_tela']} px-2 py-1.5 rounded"):
                                            ui.label(forma).classes(f"text-[11px] font-bold {cor['texto_secundario']}")
                                            ui.label(f"R$ {formatar_moeda_brasil(valor)}").classes(f"text-xs font-black {cor['texto_principal']}")
        dialog_detalhe_vendas.open()


    # =====================================================================================
    # MODAL 2: DRILL-DOWN DE COMPRAS
    # =====================================================================================
    dialog_detalhe_compras = ui.dialog()
    with dialog_detalhe_compras, ui.card().classes(f"w-full max-w-5xl p-6 rounded-2xl {cor['fundo_tela']} border {cor['borda']}"):
        container_detalhe_compras = ui.column().classes("w-full gap-4")
        with ui.row().classes("w-full justify-end mb-[-20px] z-10"):
            ui.button(icon="close", on_click=dialog_detalhe_compras.close).props("flat round size=sm").classes(cor['texto_secundario'])

    def abrir_detalhe_compras_dia(dia_clicado):
        container_detalhe_compras.clear()
        
        dia_str_busca = f"{int(dia_clicado):02d}/{mes_atual:02d}/{ano_atual}"
        
        with container_detalhe_compras:
            ui.label(f"Entrada de Notas Fiscais - Dia {dia_clicado}/{mes_atual:02d}/{ano_atual}").classes(f"text-lg font-black {cor['compras_titulo']} tracking-widest uppercase mb-4")
            
            notas_do_dia = [n for n in lista_todas_notas_compras if n.get('data_emissao') == dia_str_busca]

            if not notas_do_dia:
                ui.label("Nenhuma nota fiscal registrada neste dia.").classes(f"{cor['texto_secundario']} italic text-sm")
            else:
                with ui.row().classes("w-full items-stretch flex-col md:flex-row gap-4"):
                    for fid, nome_loja in mapa_lojas.items():
                        
                        notas_loja = [n for n in notas_do_dia if str(n.get('filial', '')) == str(fid)]
                        total_dia_loja = sum(n.get('valor_total', 0.0) for n in notas_loja)
                        
                        with ui.card().classes(f"flex-1 p-3 rounded-xl shadow-sm border {cor['compras_borda']} {cor['fundo_card']} min-w-[280px] gap-0"):
                            with ui.row().classes(f"w-full justify-between items-center mb-2 pb-2 border-b {cor['borda']}"):
                                ui.label(nome_loja).classes(f"text-xs font-black {cor['texto_secundario']} tracking-widest uppercase")
                                ui.label(f"Total: R$ {formatar_moeda_brasil(total_dia_loja)}").classes(f"text-sm font-black {cor['compras_destaque']}")
                            
                            if not notas_loja:
                                ui.label("Nenhuma entrada.").classes(f"{cor['texto_secundario']} opacity-60 text-[10px] italic text-center w-full py-4")
                            else:
                                with ui.column().classes("w-full gap-1 mt-1 max-h-[250px] overflow-y-auto pr-1"):
                                    for nota in notas_loja:
                                        with ui.row().classes(f"w-full justify-between items-center {cor['fundo_tela']} px-2 py-1 rounded gap-2 flex-nowrap"):
                                            with ui.column().classes("gap-0 min-w-0 flex-1"):
                                                ui.label(nota['fornecedor']).classes(f"text-[10px] font-bold {cor['texto_principal']} truncate w-full")
                                                ui.label(f"NFe {nota['numero_nota']} - {nota['status_nota']}").classes(f"text-[8px] font-bold {cor['texto_secundario']}")
                                            
                                            ui.label(f"R$ {formatar_moeda_brasil(nota['valor_total'])}").classes(f"text-[11px] font-black {cor['compras_destaque']} shrink-0")

        dialog_detalhe_compras.open()


    # =====================================================================================
    # --- CARTÕES SUPERIORES SEMÂNTICOS ---
    # =====================================================================================
    with ui.row().classes("w-full flex-nowrap gap-4 overflow-x-auto pb-4 items-stretch"):
        ui.column().classes("w-20 shrink-0 bg-transparent")

        def desenhar_cartao_vendas():
            with ui.card().classes(f"flex-1 min-w-[280px] p-2 md:p-3 rounded-xl {cor['vendas_bg']} border {cor['vendas_borda']} shadow-none gap-0"):
                ui.label("Vendas").classes(f"text-[10px] font-bold tracking-widest uppercase {cor['vendas_titulo']} mb-0")
                soma_geral = sum(totais.get(f"vend_{fid}", 0.0) for fid in mapa_lojas)
                ui.label(f"R$ {formatar_moeda_brasil(soma_geral)}").classes(f"text-lg md:text-xl font-bold {cor['vendas_destaque']} tracking-tighter mb-1")
                with ui.row().classes(f"w-full justify-between items-center border-t {cor['borda']} pt-1 mt-1"):
                    for fid, nome_loja in mapa_lojas.items():
                        val = totais.get(f"vend_{fid}", 0.0)
                        ui.label(f"{nome_loja}: R$ {formatar_moeda_brasil(val)}").classes(f"text-[9px] font-bold {cor['vendas_titulo']}")

        def desenhar_cartao_boletos():
            with ui.card().classes(f"flex-1 min-w-[280px] p-2 md:p-3 rounded-xl {cor['boletos_bg']} border {cor['boletos_borda']} shadow-none gap-0 opacity-80"):
                ui.label("Boletos").classes(f"text-[10px] font-bold tracking-widest uppercase {cor['boletos_titulo']} mb-0")
                ui.label("R$ 0,00").classes(f"text-lg md:text-xl font-bold {cor['boletos_destaque']} tracking-tighter mb-1")
                with ui.row().classes(f"w-full justify-between items-center border-t {cor['borda']} pt-1 mt-1"):
                    ui.label("Aguardando implantação").classes(f"text-[9px] font-bold {cor['boletos_titulo']} italic")

        def desenhar_cartao_compras():
            with ui.card().classes(f"flex-1 min-w-[280px] p-2 md:p-3 rounded-xl {cor['compras_bg']} border {cor['compras_borda']} shadow-none gap-0"):
                ui.label("Compras").classes(f"text-[10px] font-bold tracking-widest uppercase {cor['compras_titulo']} mb-0")
                soma_geral = sum(totais.get(f"comp_{fid}", 0.0) for fid in mapa_lojas)
                ui.label(f"R$ {formatar_moeda_brasil(soma_geral)}").classes(f"text-lg md:text-xl font-bold {cor['compras_destaque']} tracking-tighter mb-1")
                with ui.row().classes(f"w-full justify-between items-center border-t {cor['borda']} pt-1 mt-1"):
                    for fid, nome_loja in mapa_lojas.items():
                        val = totais.get(f"comp_{fid}", 0.0)
                        ui.label(f"{nome_loja}: R$ {formatar_moeda_brasil(val)}").classes(f"text-[9px] font-bold {cor['compras_titulo']}")

        def desenhar_cartao_despesas():
            with ui.card().classes(f"flex-1 min-w-[280px] p-2 md:p-3 rounded-xl {cor['despesas_bg']} border {cor['despesas_borda']} shadow-none gap-0 opacity-80"):
                ui.label("Despesas").classes(f"text-[10px] font-bold tracking-widest uppercase {cor['despesas_titulo']} mb-0")
                ui.label("R$ 0,00").classes(f"text-lg md:text-xl font-bold {cor['despesas_destaque']} tracking-tighter mb-1")
                with ui.row().classes(f"w-full justify-between items-center border-t {cor['borda']} pt-1 mt-1"):
                    ui.label("Aguardando implantação").classes(f"text-[9px] font-bold {cor['despesas_titulo']} italic")

        desenhar_cartao_vendas()
        desenhar_cartao_boletos()
        desenhar_cartao_compras()
        desenhar_cartao_despesas()

    # =====================================================================================
    # --- GRID GIGANTE DE TABELAS (RESTAURADO COM AS CORES ORIGINAIS) ---
    # =====================================================================================
    with ui.row().classes("w-full flex-nowrap gap-4 overflow-x-auto pb-4 items-stretch"):
        def desenhar_bloco_tabela(titulo, sub_titulo, bg_head, txt_head, bg_table, tamanho, prefixo):
            with ui.column().classes(f"gap-0 rounded-2xl shadow-lg {cor['fundo_card']} overflow-hidden border {cor['borda']} {tamanho}"):
                
                with ui.column().classes(f"w-full items-center justify-center {bg_head} {txt_head} py-2 border-b {cor['borda']} gap-0"):
                    ui.label(titulo).classes("font-black text-sm tracking-widest uppercase")
                    if sub_titulo:
                        ui.label(sub_titulo).classes("text-[8px] font-bold opacity-70 tracking-widest uppercase")
                
                cols = []
                if prefixo == "dia":
                    cols.append({"name": "dia", "label": "Dia", "field": "dia", "align": "center", "classes": f"{cor['fundo_tela']} font-bold !{cor['texto_principal']}", "headerClasses": f"{bg_head} {txt_head} font-bold"})
                else:
                    if not mapa_lojas:
                        cols.append({"name": "vazio", "label": "SEM DADOS", "field": "vazio", "align": "center", "classes": f"{cor['texto_secundario']} italic"})
                    for fid, nome_loja in mapa_lojas.items():
                        cols.append({"name": str(fid), "label": nome_loja, "field": f"{prefixo}_{fid}", "align": "right", "classes": f"!{cor['texto_principal']}", "headerClasses": f"{bg_head} {txt_head} font-bold"})
                
                tabela = ui.table(columns=cols, rows=dados, row_key="dia").props(
                    f'flat bordered dense separator="cell" hide-bottom hide-pagination :pagination="{{rowsPerPage: {quant_dias}}}" hover'
                ).classes(f"w-full {bg_table} !{cor['texto_principal']}")

                # GATILHOS DE CLIQUE PARA AS DUAS COLUNAS
                if prefixo == "vend":
                    tabela.on('row-click', lambda e: abrir_detalhe_vendas_dia(e.args[1]['dia']))
                    tabela.classes("cursor-pointer hover:shadow-inner transition-all")
                elif prefixo == "comp":
                    tabela.on('row-click', lambda e: abrir_detalhe_compras_dia(e.args[1]['dia']))
                    tabela.classes("cursor-pointer hover:shadow-inner transition-all")

        # Passando as variáveis exatas do dicionário para recriar as cores!
        desenhar_bloco_tabela("Data", None, cor["tab_dia_head"], cor["tab_dia_txt"], cor["tab_dia_bg"], "w-20 shrink-0", "dia")
        desenhar_bloco_tabela("Vendas", None, cor["tab_vend_head"], cor["tab_vend_txt"], cor["tab_vend_bg"], "flex-1 min-w-[280px]", "vend")
        desenhar_bloco_tabela("Boletos", None, cor["tab_bol_head"], cor["tab_bol_txt"], cor["tab_bol_bg"], "flex-1 min-w-[280px]", "bol")
        desenhar_bloco_tabela("Compras", None, cor["tab_comp_head"], cor["tab_comp_txt"], cor["tab_comp_bg"], "flex-1 min-w-[280px]", "comp")
        desenhar_bloco_tabela("Despesas", None, cor["tab_desp_head"], cor["tab_desp_txt"], cor["tab_desp_bg"], "flex-1 min-w-[280px]", "desp")