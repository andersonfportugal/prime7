from nicegui import ui, app
import datetime
import tema
from motor_dados import obter_dados_vendedores_fast, formatar_moeda_brasil

def desenhar_tela_performance_vendedores():
    # Puxa o motor de temas sem alterar a estrutura do arquivo
    cor = tema.obter_cores()
    
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))
    vendedores_marcados = app.storage.user.get("vendedores_marcados", [])

    # --- CABEÇALHO ---
    with ui.row().classes(f"w-full justify-between items-center mb-4 {cor['fundo_card']} p-4 rounded-2xl shadow-sm border {cor['borda']} flex-wrap gap-4"):
        with ui.column().classes("gap-1"):
            ui.label("Acompanhamento mensal").classes(f"{cor['destaque']} text-lg font-black tracking-widest uppercase")
            ui.label("Acompanhamento mensal dos vendedores").classes(f"text-xs {cor['texto_secundario']}")

        # Extração usando o novo Motor com IDs Cegos
    resumo_mes, evolucao_ano, mapa_vendedores = obter_dados_vendedores_fast(mes_atual, ano_atual)
    
    # ORDENAÇÃO DE OURO: Ordena o dicionário pelo Nome do Vendedor (item[1]) e não pelo ID (item[0])
    mapa_vendedores = dict(sorted(mapa_vendedores.items(), key=lambda item: item[1]))

    # Extrai as chaves únicas já na ordem alfabética correta para os checkboxes e tabela
    lista_vend_ids = list(mapa_vendedores.keys())

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
                ui.label("Nenhuma venda registrada neste período.").classes(f"{cor['texto_secundario']} italic text-sm text-center w-full mt-6")
                return

            # =============================================================================
            # SEÇÃO DE CHECKBOXES TABULADOS
            # =============================================================================
            with ui.card().classes(f"w-full p-3 rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']} shadow-none"):
                ui.label("EQUIPE COMERCIAL").classes(f"text-[9px] font-black {cor['texto_secundario']} tracking-widest mb-2 px-1")
                
                with ui.element('div').classes("w-full grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-x-4 gap-y-1 px-1"):
                    for vid in lista_vend_ids:
                        nome_exibicao = mapa_vendedores[vid]
                        ui.checkbox(
                            nome_exibicao, 
                            value=(vid in vendedores_marcados), 
                            on_change=lambda e, v=vid: atualizar_checkbox(v, e.value)
                        ).classes(f"text-xs font-bold {cor['texto_secundario']} truncate w-full").props("dense")

            if not vendedores_marcados:
                ui.label("Marque os vendedores acima para exibir a análise.").classes(f"{cor['texto_secundario']} text-xs italic mt-2")
                return

            # =============================================================================
            # BLOCO 1: CARDS DOS VENDEDORES COLORIDOS
            # =============================================================================
            ui.label("DESEMPENHO NO MÊS SELECIONADO").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest mt-2 px-1")
            
            # Mantive as bordas coloridas originais, mas os textos agora respeitam o Dark Mode
            paleta_bordas = [
                "border-l-indigo-500", "border-l-emerald-500",
                "border-l-rose-500", "border-l-amber-500",
                "border-l-cyan-500", "border-l-fuchsia-500",
                "border-l-lime-500", "border-l-orange-500"
            ]

            with ui.row().classes("w-full flex-wrap gap-3 items-stretch"):
                for idx, vid in enumerate(vendedores_marcados):
                    dados = resumo_mes.get(vid, {'vendas': 0.0, 'tickets': 0})
                    nome_exibicao = mapa_vendedores[vid]
                    
                    vendas = dados['vendas']
                    tickets = dados['tickets']
                    tk_medio = vendas / tickets if tickets > 0 else 0.0
                    
                    classe_borda = paleta_bordas[idx % len(paleta_bordas)]
                    
                    with ui.card().classes(f"w-full sm:w-[240px] p-4 rounded-2xl shadow-sm border-l-4 {classe_borda} {cor['fundo_card']} gap-0.5 hover:shadow-md transition-shadow"):
                        ui.label(nome_exibicao).classes(f"text-[10px] font-black {cor['texto_secundario']} uppercase tracking-widest truncate w-full")
                        ui.label(f"R$ {formatar_moeda_brasil(vendas)}").classes(f"text-xl font-black !{cor['texto_principal']} mt-0.5")
                        
                        with ui.row().classes(f"w-full justify-between items-center mt-3 pt-2 border-t {cor['borda']}"):
                            ui.label(f"{tickets} atend.").classes(f"text-[10px] font-bold {cor['texto_secundario']}")
                            ui.label(f"TM: R$ {formatar_moeda_brasil(tk_medio)}").classes(f"text-[10px] font-bold {cor['destaque']}")

            # =============================================================================
            # BLOCO 2: EVOLUÇÃO ANUAL (TRANSPOSIÇÃO MOBILE-FIRST)
            # =============================================================================
            ui.label(f"RELATÓRIO CONSOLIDADO: VENDAS - {ano_atual}").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest px-1 mt-4")
            
            meses_abrev = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
            
            with ui.card().classes(f"w-full p-0 rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']} mt-2 overflow-hidden"):
                # Container principal com scroll horizontal nativo (perfeito para touch)
                with ui.row().classes("w-full flex-nowrap overflow-x-auto"):
                    
                    # 1. COLUNA FIXA DA ESQUERDA (OS MESES)
                    with ui.column().classes(f"w-16 shrink-0 gap-0 border-r {cor['borda']} {cor['fundo_tela']}"):
                        ui.label("MÊS").classes(f"w-full text-center py-2.5 text-[9px] font-black tracking-widest {cor['texto_secundario']} border-b {cor['borda']}")
                        
                        for mes in meses_abrev:
                            ui.label(mes).classes(f"w-full text-center py-2 text-xs font-bold !{cor['texto_principal']} border-b {cor['borda']}")
                        
                        ui.label("TOTAL").classes(f"w-full text-center py-2.5 text-xs font-black {cor['destaque']}")

                    # 2. COLUNAS DINÂMICAS (OS VENDEDORES SELECIONADOS)
                    for vid in vendedores_marcados:
                        # Extrai o nome de exibição e os valores mensais do vendedor específico
                        nome_limpo = mapa_vendedores[vid]
                        valores_meses = evolucao_ano.get(vid, [0.0] * 12)
                        total_anual = sum(valores_meses)
                        
                        with ui.column().classes(f"w-[100px] shrink-0 gap-0 border-r {cor['borda']} hover:bg-black/5 transition-colors"):
                            # Cabeçalho: Nome do Vendedor (Tratado e Centralizado)
                            ui.label(nome_limpo).classes(f"w-full text-center py-2.5 text-[9px] font-black tracking-widest uppercase !{cor['texto_principal']} border-b {cor['borda']} truncate px-1")
                            
                            # Corpo: Valores Faturados por Mês
                            for val in valores_meses:
                                valor_str = formatar_moeda_brasil(val) if val > 0 else "-"
                                cor_texto = f"!{cor['texto_principal']}" if val > 0 else cor['texto_secundario']
                                ui.label(valor_str).classes(f"w-full text-center py-2 text-xs font-medium {cor_texto} border-b {cor['borda']}")
                            
                            # Rodapé: Faturamento Total do Ano
                            ui.label(formatar_moeda_brasil(total_anual)).classes(f"w-full text-center py-2.5 text-[11px] font-black {cor['destaque']}")

    # Inicializa o desenho do painel
    desenhar_painel_dinamico()