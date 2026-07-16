from nicegui import ui, app
import datetime
import tema
from motor_dados import (
    obter_resumo_rapido_fast, 
    obter_dados_pagamentos_diarios_fast, 
    obter_dados_pagamentos_fast, 
    obter_dados_compras_fast, 
    formatar_moeda_brasil
)

def desenhar_tela_resumo():
    cor = tema.obter_cores()
    
    # === DECLARAÇÃO DOS MODAIS (DIALOGS FLUTUANTES MOBILE) ===
    dialog_vendas = ui.dialog()
    with dialog_vendas, ui.card().classes(f"w-full max-w-sm p-5 rounded-2xl {cor['fundo_card']} border {cor['borda']} gap-3"):
        container_vendas = ui.column().classes("w-full gap-2")
        ui.button("FECHAR", on_click=dialog_vendas.close).props("flat size=sm").classes(f"w-full mt-2 {cor['texto_secundario']} font-black tracking-widest")

    dialog_compras = ui.dialog()
    with dialog_compras, ui.card().classes(f"w-full max-w-sm p-5 rounded-2xl {cor['fundo_card']} border {cor['borda']} gap-3"):
        container_compras = ui.column().classes("w-full gap-2")
        ui.button("FECHAR", on_click=dialog_compras.close).props("flat size=sm").classes(f"w-full mt-2 {cor['texto_secundario']} font-black tracking-widest")

    dialog_cmv = ui.dialog()
    with dialog_cmv, ui.card().classes(f"w-full max-w-sm p-5 rounded-2xl {cor['fundo_card']} border {cor['borda']} gap-3"):
        container_cmv = ui.column().classes("w-full gap-2")
        ui.button("FECHAR", on_click=dialog_cmv.close).props("flat size=sm").classes(f"w-full mt-2 {cor['texto_secundario']} font-black tracking-widest")

    # Envelope mestre para atualização reativa
    container_mestre = ui.column().classes("w-full m-0 p-0 gap-0")

    def atualizar_tela():
        container_mestre.clear()
        with container_mestre:
            
            if 'resumo_modo' not in app.storage.user:
                app.storage.user['resumo_modo'] = 'DIA' 
            if 'resumo_data' not in app.storage.user:
                app.storage.user['resumo_data'] = datetime.date.today().isoformat()
            if 'ordem_vendedores' not in app.storage.user:
                app.storage.user['ordem_vendedores'] = 'alfabetica'

            modo_atual = app.storage.user['resumo_modo']
            data_atual = datetime.date.fromisoformat(app.storage.user['resumo_data'])
            ordem_atual = app.storage.user['ordem_vendedores']

            # Coleta os dados reais do banco
            dados_lojas, dados_vendedores, total_entregas, dados_motoboys = obter_resumo_rapido_fast(modo_atual, app.storage.user['resumo_data'])

            # =========================================================================
            # LÓGICA DE DETALHAMENTO DE VENDAS (MEIOS DE PAGAMENTO)
            # =========================================================================
            def abrir_modal_vendas(fid, nome_loja):
                container_vendas.clear()
                with container_vendas:
                    ui.label(nome_loja).classes(f"text-[9px] font-black {cor['texto_secundario']} tracking-widest uppercase")
                    texto_sub = f"Faturamento do Dia {data_atual.strftime('%d/%m/%Y')}" if modo_atual == 'DIA' else "Faturamento Consolidado do Mês"
                    ui.label(texto_sub).classes(f"text-sm font-black {cor['vendas_titulo']} mb-2")
                    
                    if modo_atual == 'DIA':
                        dados_diarios, _ = obter_dados_pagamentos_diarios_fast(data_atual.month, data_atual.year)
                        dia_str = f"{data_atual.day:02d}"
                        pgtos = dados_diarios.get(dia_str, {}).get(str(fid), {})
                    else:
                        dados_mensais, _ = obter_dados_pagamentos_fast(data_atual.month, data_atual.year)
                        pgtos = dados_mensais.get(str(fid), {})

                    if not pgtos:
                        ui.label("Sem recebimentos no período.").classes(f"text-xs italic {cor['texto_secundario']} my-4 text-center w-full")
                    else:
                        for forma, valor in sorted(pgtos.items(), key=lambda x: x[1], reverse=True):
                            with ui.row().classes(f"w-full justify-between items-center {cor['fundo_tela']} p-2.5 rounded-xl border {cor['borda']}"):
                                ui.label(forma).classes(f"text-xs font-bold {cor['texto_secundario']}")
                                ui.label(f"R$ {formatar_moeda_brasil(valor)}").classes(f"text-xs font-black !{cor['texto_principal']}")
                dialog_vendas.open()

            # =========================================================================
            # LÓGICA DE DETALHAMENTO DE COMPRAS (NOTAS FISCAIS)
            # =========================================================================
            def abrir_modal_compras(fid, nome_loja):
                container_compras.clear()
                with container_compras:
                    ui.label(nome_loja).classes(f"text-[9px] font-black {cor['texto_secundario']} tracking-widest uppercase")
                    texto_sub = f"Notas Fiscais do Dia {data_atual.strftime('%d/%m/%Y')}" if modo_atual == 'DIA' else "Notas Fiscais do Mês"
                    ui.label(texto_sub).classes(f"text-sm font-black {cor['compras_titulo']} mb-2")
                    
                    lista_todas_notas = obter_dados_compras_fast(data_atual.month, data_atual.year)
                    notas_filtradas = [n for n in lista_todas_notas if str(n['filial']) == str(fid)]
                    
                    if modo_atual == 'DIA':
                        data_pt = data_atual.strftime('%d/%m/%Y')
                        notas_filtradas = [n for n in notas_filtradas if n['data_emissao'] == data_pt]

                    if not notas_filtradas:
                        ui.label("Nenhuma nota emitida no período.").classes(f"text-xs italic {cor['texto_secundario']} my-4 text-center w-full")
                    else:
                        with ui.column().classes("w-full gap-1.5 max-h-[280px] overflow-y-auto pr-1"):
                            for nota in notas_filtradas:
                                with ui.row().classes(f"w-full justify-between items-center {cor['fundo_tela']} p-2 rounded-xl border {cor['borda']} flex-nowrap gap-2"):
                                    with ui.column().classes("gap-0 min-w-0 flex-1"):
                                        ui.label(nota['fornecedor']).classes(f"text-[10px] font-bold !{cor['texto_principal']} truncate w-full")
                                        ui.label(f"NFe {nota['numero_nota']}").classes(f"text-[8px] font-bold {cor['texto_secundario']}")
                                    ui.label(f"R$ {formatar_moeda_brasil(nota['valor_total'])}").classes(f"text-xs font-black {cor['compras_destaque']} shrink-0")
                dialog_compras.open()
            
            def abrir_modal_cmv(fid, nome_loja):
                container_cmv.clear()
                with container_cmv:
                    ui.label(nome_loja).classes(f"text-[9px] font-black {cor['texto_secundario']} tracking-widest uppercase")
                    texto_sub = f"Custo (CMV) do Dia {data_atual.strftime('%d/%m/%Y')}" if modo_atual == 'DIA' else "Custo (CMV) do Mês"
                    ui.label(texto_sub).classes(f"text-sm font-black {cor['destaque']} mb-2")
                    
                    info_loja = dados_lojas.get(str(fid), {})
                    custo_abs = info_loja.get('custo', 0)
                    cmv_percentual = info_loja.get('cmv', 0)
                    vendas_abs = info_loja.get('vendas', 0)

                    if custo_abs == 0:
                        ui.label("Sem movimentação de custo no período.").classes(f"text-xs italic {cor['texto_secundario']} my-4 text-center w-full")
                    else:
                        with ui.row().classes(f"w-full justify-between items-center {cor['fundo_tela']} p-2.5 rounded-xl border {cor['borda']}"):
                            ui.label("Custo dos produtos").classes(f"text-xs font-bold {cor['texto_secundario']}")
                            ui.label(f"R$ {formatar_moeda_brasil(custo_abs)}").classes(f"text-xs font-black !{cor['texto_principal']}")
                            
                        with ui.row().classes(f"w-full justify-between items-center {cor['fundo_tela']} p-2.5 rounded-xl border {cor['borda']}"):
                            ui.label("Percentual (CMV)").classes(f"text-xs font-bold {cor['texto_secundario']}")
                            ui.label(f"{cmv_percentual:.1f}%").classes(f"text-xs font-black {cor['destaque']}")
                dialog_cmv.open()

            # =========================================================================
            # GESTÃO DA ORDENAÇÃO DA EQUIPE
            # =========================================================================
            if ordem_atual == 'alfabetica':
                dados_vendedores = sorted(dados_vendedores, key=lambda x: x['nome'])
                icone_sort = "sort_by_alpha"
                dica_sort = "Ordenar por Faturamento"
            else:
                dados_vendedores = sorted(dados_vendedores, key=lambda x: x['total'], reverse=True)
                icone_sort = "sort"
                dica_sort = "Ordenar Alfabeticamente"

            def abrir_ou_fechar_ordenacao():
                app.storage.user['ordem_vendedores'] = 'valor' if ordem_atual == 'alfabetica' else 'alfabetica'
                atualizar_tela()

            # =========================================================================
            # CONTROLES TEMPORAIS & SELEÇÃO DIRETA
            # =========================================================================
            def alterar_modo(e):
                app.storage.user['resumo_modo'] = e.value
                atualizar_tela()

            def voltar_tempo():
                if modo_atual == 'DIA':
                    nova_data = data_atual - datetime.timedelta(days=1)
                else:
                    primeiro_dia = data_atual.replace(day=1)
                    nova_data = (primeiro_dia - datetime.timedelta(days=1)).replace(day=1)
                app.storage.user['resumo_data'] = nova_data.isoformat()
                atualizar_tela()

            def avancar_tempo():
                if modo_atual == 'DIA':
                    nova_data = data_atual + datetime.timedelta(days=1)
                else:
                    proximo_mes = data_atual.replace(day=28) + datetime.timedelta(days=4)
                    nova_data = proximo_mes.replace(day=1)
                app.storage.user['resumo_data'] = nova_data.isoformat()
                atualizar_tela()

            def obter_dia_da_semana():
                """Retorna o dia da semana em português de forma simples"""
                dias = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
                return dias[data_atual.weekday()]

            def formatar_data_exibicao():
                if modo_atual == 'DIA':
                    return data_atual.strftime("%d/%m/%Y")
                else:
                    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
                    return f"{meses[data_atual.month - 1]} / {data_atual.year}"

            def selecionar_data_direta(e):
                """Callback disparado quando o usuário escolhe uma data no calendário flutuante"""
                app.storage.user['resumo_data'] = e.value
                # Se mudou o dia e estava em modo MÊS, podemos manter ou forçar para DIA, 
                # mas manter a consistência do modo atual é o ideal.
                atualizar_tela()

            # --- RENDERIZAÇÃO DO CABEÇALHO ---
            with ui.column().classes("w-full items-center gap-4 mb-4"):
                ui.toggle(['DIA', 'MÊS'], value=modo_atual, on_change=alterar_modo).classes(f"font-bold {cor['destaque']} {cor['fundo_card']} shadow-sm rounded-full").props("unelevated size=sm")
                
                with ui.row().classes(f"w-full max-w-sm justify-between items-center {cor['fundo_card']} p-2 rounded-2xl shadow-sm border {cor['borda']}"):
                    ui.button(icon="chevron_left", on_click=voltar_tempo).props("flat round size=sm").classes(cor['texto_secundario'])
                    
                    # ÁREA CENTRAL: Clicável para abrir o calendário
                    with ui.column().classes("items-center gap-0 cursor-pointer hover:scale-105 transition-transform") as area_data:
                        ui.label("DATA").classes(f"text-[8px] font-black {cor['texto_secundario']} tracking-widest uppercase")
                        ui.label(formatar_data_exibicao()).classes(f"text-base font-black !{cor['texto_principal']} tracking-wider")
                        
                        # EXIBIÇÃO DO DIA DA SEMANA (Apenas quando o modo for DIA)
                        if modo_atual == 'DIA':
                            ui.label(obter_dia_da_semana()).classes(f"text-[10px] font-bold {cor['texto_secundario']} -mt-0.5 lowercase")
                        
                        # MENU FLUTUANTE DO CALENDÁRIO (Agora sem o 'if', abre tanto no DIA quanto no MÊS)
                        with ui.menu().props('anchor="bottom middle" self="top middle"').classes(f"p-1 rounded-2xl border {cor['borda']} {cor['fundo_card']} shadow-xl"):
                            ui.date(value=app.storage.user['resumo_data'], on_change=selecionar_data_direta).props(
                                f"flat color=primary {'dark' if cor['fundo_tela'] != 'bg-slate-50' else ''}"
                            )

                    ui.button(icon="chevron_right", on_click=avancar_tempo).props("flat round size=sm").classes(cor['texto_secundario'])
            
            # --- RENDERIZAÇÃO DO CORPO ---
            container_mobile = ui.column().classes("w-full max-w-sm mx-auto gap-4 pb-8")
            with container_mobile:
                
                ui.label("UNIDADES DE NEGÓCIO").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest mt-2 px-1")
                
                if not dados_lojas:
                    ui.label("Sem faturamento no período.").classes(f"text-xs italic {cor['texto_secundario']} w-full text-center py-4")
                else:
                    for id_loja, info_loja in dados_lojas.items():
                        with ui.card().classes(f"w-full p-0 rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']} gap-0 overflow-hidden mb-2"):
                            ui.label(info_loja['nome']).classes(f"w-full text-center {cor['tab_dia_head']} {cor['tab_dia_txt']} font-black py-2 text-[10px] tracking-widest uppercase border-b {cor['borda']}")
                            
                            # Card de Vendas da Filial
                            with ui.row().classes(f"w-full justify-between items-center p-3 border-b {cor['borda']} hover:bg-black/5 transition-colors"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon("point_of_sale", size="sm").classes(cor['vendas_destaque'])
                                    ui.label("Vendas").classes(f"text-sm font-bold {cor['vendas_titulo']}")
                                with ui.row().classes("items-center gap-2"):
                                    ui.label(f"R$ {formatar_moeda_brasil(info_loja.get('vendas', 0))}").classes(f"text-base font-black !{cor['texto_principal']}")
                                    ui.button(icon="search", on_click=lambda l=id_loja, n=info_loja['nome']: abrir_modal_vendas(l, n)).props("flat round size=xs").classes(cor['texto_secundario'])
                            
                            # Card de Compras da Filial
                            with ui.row().classes(f"w-full justify-between items-center p-3 border-b {cor['borda']} hover:bg-black/5 transition-colors"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon("receipt_long", size="sm").classes(cor['compras_destaque'])
                                    ui.label("Compras").classes(f"text-sm font-bold {cor['compras_titulo']}")
                                with ui.row().classes("items-center gap-2"):
                                    ui.label(f"R$ {formatar_moeda_brasil(info_loja.get('compras', 0))}").classes(f"text-base font-black !{cor['texto_principal']}")
                                    ui.button(icon="search", on_click=lambda l=id_loja, n=info_loja['nome']: abrir_modal_compras(l, n)).props("flat round size=xs").classes(cor['texto_secundario'])
                                
                            # Card de Boletos da Filial (Removido opacity-80)
                            with ui.row().classes(f"w-full justify-between items-center p-3 border-b {cor['borda']} hover:bg-black/5 transition-colors"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon("receipt", size="sm").classes(cor['boletos_destaque'])
                                    ui.label("Boletos").classes(f"text-sm font-bold {cor['boletos_titulo']}")
                                with ui.row().classes("items-center gap-2"):
                                    ui.label(f"R$ {formatar_moeda_brasil(info_loja.get('boletos', 0))}").classes(f"text-base font-black !{cor['texto_principal']}")

                            # Card de Cupons da Filial (Removido opacity-80 e adicionado border-b pois não é mais o último)
                            with ui.row().classes(f"w-full justify-between items-center p-3 border-b {cor['borda']} hover:bg-black/5 transition-colors"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon("local_activity", size="sm").classes(cor['boletos_destaque'])
                                    ui.label("Cupons").classes(f"text-sm font-bold {cor['boletos_titulo']}")
                                with ui.row().classes("items-center gap-2"):
                                    ui.label(f"{info_loja.get('cupons', 0)}").classes(f"text-base font-black !{cor['texto_principal']}")

                            # NOVO: Card do CMV (Ícone colorido, texto padrão igual aos outros)
                            with ui.row().classes(f"w-full justify-between items-center p-3 hover:bg-black/5 transition-colors"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon("donut_large", size="sm").classes(cor['destaque']) 
                                    ui.label("CMV").classes(f"text-sm font-bold !{cor['texto_principal']}")
                                with ui.row().classes("items-center gap-2"):
                                    cmv_percentual = info_loja.get('cmv', 0)
                                    ui.label(f"{cmv_percentual:.1f}%").classes(f"text-base font-black !{cor['texto_principal']}")
                                    ui.button(icon="search", on_click=lambda l=id_loja, n=info_loja['nome']: abrir_modal_cmv(l, n)).props("flat round size=xs").classes(cor['texto_secundario'])

                # Seção de Atendimento dos Vendedores
                with ui.row().classes("w-full justify-between items-end mt-2 px-1"):
                    ui.label("VENDAS").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest")
                    ui.button(icon=icone_sort, on_click=abrir_ou_fechar_ordenacao).props("flat round size=xs").classes(f"{cor['texto_secundario']} -mb-2 hover:brightness-125").tooltip(dica_sort)

                with ui.card().classes(f"w-full p-3 rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']} gap-3"):
                    if not dados_vendedores:
                        ui.label("Sem registos de vendas.").classes(f"text-xs italic {cor['texto_secundario']} w-full text-center py-2")
                    else:
                        for vendedor in dados_vendedores:
                            with ui.row().classes(f"w-full justify-between items-center border-b {cor['borda']} pb-2 last:border-0 last:pb-0"):
                                ui.label(vendedor['nome']).classes(f"text-xs font-bold !{cor['texto_principal']} uppercase truncate max-w-[150px]")
                                ui.label(f"R$ {formatar_moeda_brasil(vendedor['total'])}").classes(f"text-sm font-black {cor['destaque']}")

                # Seção do Volume Logístico
                ui.label("ENTREGAS").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest mt-2 px-1")
                
                with ui.card().classes(f"w-full p-3 rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']} gap-3"):
                    
                    # Cabeçalho: Total de Entregas
                    with ui.row().classes(f"w-full justify-between items-center border-b {cor['borda']} pb-2"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("two_wheeler", size="sm").classes(cor['texto_secundario'])
                            ui.label("ENTREGAS").classes(f"text-xs font-bold !{cor['texto_principal']}")
                        ui.label(f"{total_entregas} totais").classes(f"text-sm font-black !{cor['texto_principal']}")
                    
                    # Lista: Ranking de Motoboys
                    if not dados_motoboys:
                        ui.label("Nenhum despacho registado.").classes(f"text-xs italic {cor['texto_secundario']} w-full text-center py-2")
                    else:
                        for motoboy in dados_motoboys:
                            with ui.row().classes(f"w-full justify-between items-center border-b {cor['borda']} pb-2 last:border-0 last:pb-0"):
                                ui.label(motoboy['nome']).classes(f"text-xs font-bold !{cor['texto_principal']} uppercase truncate max-w-[150px]")
                                ui.label(f"{motoboy['corridas']} entregas").classes(f"text-sm font-black {cor['destaque']}")

    # Monta a estrutura primária
    atualizar_tela()