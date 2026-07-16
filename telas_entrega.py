from nicegui import ui, app
import datetime
import tema
from motor_dados import obter_dados_entregas_fast

def limpar_nome_colaborador(nome_completo):
    """Remove sufixos de sistema e retorna apenas os 2 primeiros nomes."""
    if not nome_completo:
        return ""
    
    nome = str(nome_completo).upper()
    palavras_lixo = ["FARMA", "ENTREGADOR", "MOTOBOY", "LOJA", "FILIAL"]
    for palavra in palavras_lixo:
        nome = nome.replace(palavra, "")
    
    partes = [p for p in nome.split() if p]
    return " ".join(partes[:2])

def desenhar_tela_entregas_motoboys():
    # Carrega a inteligência de cores do usuário atual
    cor = tema.obter_cores()
    
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))

    # --- CABEÇALHO COM SELETORES DE MÊS/ANO ---
    with ui.row().classes(f"w-full justify-between items-center mb-4 {cor['fundo_card']} p-4 rounded-2xl shadow-sm border {cor['borda']} flex-wrap gap-4"):
        with ui.column().classes("gap-1"):
            ui.label("Entregas e Performance").classes(f"{cor['destaque']} text-lg font-black tracking-widest uppercase")
            #ui.label("Estatísticas baseadas na coluna data_entrega").classes(f"text-xs {cor['texto_secundario']} font-bold")

    # Coleta de dados
    tot_entregas, dict_filiais, ranking, evo_lojas, evo_mbs, mapa_lojas = obter_dados_entregas_fast(mes_atual, ano_atual)

    # ORDENAÇÃO DE OURO: Força que o mapa de lojas (ID -> Nome) seja ordenado alfabeticamente pelo Nome
    mapa_lojas = dict(sorted(mapa_lojas.items(), key=lambda item: item[1]))

    # --- CARTÕES SUPERIORES DE RESUMO ---
    with ui.row().classes("w-full gap-4 mb-4 items-stretch flex-wrap"):
        with ui.card().classes(f"flex-[2] p-4 rounded-xl shadow-sm border {cor['borda']} {cor['fundo_tela']} min-w-[200px]"):
            ui.label("CORRIDAS DO MÊS").classes(f"text-[10px] font-bold {cor['destaque']} uppercase tracking-widest")
            ui.label(f"{tot_entregas} entregas").classes(f"text-3xl font-black {cor['texto_principal']} tracking-tight")

        # Como já ordenámos mapa_lojas acima, a "Loja 01" aparecerá obrigatoriamente antes da "Loja 02"
        for fid, nome_loja in mapa_lojas.items():
            qtd_loja = dict_filiais.get(fid, 0)
            with ui.card().classes(f"flex-1 p-4 rounded-xl shadow-sm border {cor['borda']} {cor['fundo_card']} min-w-[150px]"):
                ui.label(nome_loja).classes(f"text-[10px] font-bold {cor['texto_secundario']} uppercase tracking-widest")
                ui.label(str(qtd_loja)).classes(f"text-2xl font-black {cor['texto_principal']} mt-1")

    # --- CORPO CENTRAL: RANKING (AGORA 1º) E GRÁFICO (AGORA 2º) ---
    with ui.row().classes("w-full gap-4 items-stretch flex-wrap mb-4"):
        
        # === BLOCO 1: RANKING DO MÊS ===
        with ui.card().classes(f"flex-1 p-4 rounded-xl shadow-sm border {cor['borda']} {cor['fundo_card']} min-w-[280px] min-w-0"):
            ui.label(f"RANKING DO MÊS ({mes_atual:02d}/{ano_atual})").classes(f"text-[11px] font-bold {cor['texto_secundario']} uppercase mb-3")
            
            if not ranking:
                ui.label("Sem corridas no mês selecionado.").classes(f"{cor['texto_secundario']} italic text-sm mt-12 w-full text-center")
            else:
                max_corridas = max(r["qtd"] for r in ranking) if ranking else 1
                classe_bg_destaque = cor['destaque'].replace('text-', 'bg-')
                classe_bg_trilha = cor['borda'].replace('border-', 'bg-')

                with ui.column().classes("w-full gap-3 mt-1 overflow-y-auto max-h-[320px] pr-1"):
                    for idx, r in enumerate(ranking):
                        posicao = idx + 1
                        nome_motoboy = limpar_nome_colaborador(r["nome"])
                        qtd_corridas = r["qtd"]
                        porcentagem = (qtd_corridas / max_corridas) * 100 if max_corridas > 0 else 0
                        
                        cor_posicao = "text-amber-500 font-black" if posicao == 1 else \
                                      ("text-slate-400 font-black" if posicao == 2 else \
                                       ("text-amber-700 font-black" if posicao == 3 else f"{cor['texto_secundario']}"))
                        
                        with ui.column().classes("w-full gap-0.5"):
                            with ui.row().classes("w-full justify-between items-center text-xs"):
                                with ui.row().classes("items-center gap-1.5 min-w-0 flex-1"):
                                    ui.label(f"#{posicao}").classes(f"w-5 shrink-0 text-center {cor_posicao}")
                                    ui.label(nome_motoboy).classes(f"font-bold {cor['texto_principal']} truncate w-full")
                                ui.label(f"{qtd_corridas} crd.").classes(f"font-black {cor['destaque']} shrink-0 pl-1")
                            
                            with ui.element('div').classes(f'w-full h-2 {classe_bg_trilha} rounded-full overflow-hidden mt-0.5'):
                                ui.element('div').classes(f'h-full {classe_bg_destaque} rounded-full transition-all duration-500').style(f'width: {porcentagem}%')

        # === BLOCO 2: GRÁFICO DE LOJAS ===
        with ui.card().classes(f"flex-[2] p-4 rounded-xl shadow-sm border {cor['borda']} {cor['fundo_card']} min-w-[350px]"):
            ui.label("EVOLUÇÃO MENSAL DAS LOJAS (CORRIDAS)").classes(f"text-[11px] font-bold {cor['texto_secundario']} uppercase mb-2")
            
            series_lojas = []
            cores_lojas = ["#8b5cf6", "#10b981", "#f59e0b", "#f43f5e", "#3b82f6"]
            
            # O dicionário foi ordenado no topo, logo as linhas do gráfico estarão ordenadas também!
            for idx, (fid, nome_loja) in enumerate(mapa_lojas.items()):
                series_lojas.append({
                    "name": nome_loja, 
                    "type": "line", 
                    "smooth": True, 
                    "data": evo_lojas.get(fid, [0]*12), 
                    "symbolSize": 6, 
                    "lineStyle": {"width": 3}, 
                    "itemStyle": {"color": cores_lojas[idx % len(cores_lojas)]}
                })

            ui.echart({
                "tooltip": {"trigger": "axis"},
                "legend": {"bottom": "0%", "textStyle": {"fontSize": 11, "fontWeight": "bold", "color": "#888888"}},
                "grid": {"left": "2%", "right": "4%", "bottom": "12%", "containLabel": True},
                "xAxis": {"type": "category", "data": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], "axisLabel": {"color": "#888888"}},
                "yAxis": {"type": "value", "axisLabel": {"color": "#888888"}, "splitLine": {"lineStyle": {"color": "#333333", "type": "dashed"}}},
                "series": series_lojas,
            }).classes("w-full h-[320px]")


    # =============================================================================
    # SESSÃO 3: EVOLUÇÃO ANUAL (TRANSPOSIÇÃO MOBILE-FIRST COM FILTROS)
    # =============================================================================
    ui.label(f"ACOMPANHAMENTO - {ano_atual}").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest px-1 mt-4")
    container_tabela_anual = ui.column().classes("w-full gap-2")

    # Resgata a lista original de motoboys e o estado salvo das marcações
    # Resgata a lista original de motoboys e o estado salvo das marcações
    nomes_mbs_ano_originais = sorted(list(evo_mbs.keys()))
    
    if "entregadores_marcados_tab" not in app.storage.user:
        # Descobre qual dispositivo está acessando através do cabeçalho da requisição
        requisicao = ui.context.client.request
        user_agent = requisicao.headers.get('user-agent', '').lower() if requisicao else ''
        is_mobile = any(dispositivo in user_agent for dispositivo in ['mobile', 'android', 'iphone', 'ipod'])
        
        # Aplica a regra de negócio do dispositivo
        if is_mobile:
            app.storage.user["entregadores_marcados_tab"] = [] # Celular: nenhum marcado
        else:
            app.storage.user["entregadores_marcados_tab"] = nomes_mbs_ano_originais.copy() # PC: todos marcados
    # Limpa nomes que possam ter sumido do banco
    entregadores_marcados = [m for m in app.storage.user["entregadores_marcados_tab"] if m in nomes_mbs_ano_originais]

    def atualizar_entregadores_tab(mb_nome, marcado):
        if marcado and mb_nome not in entregadores_marcados:
            entregadores_marcados.append(mb_nome)
        elif not marcado and mb_nome in entregadores_marcados:
            entregadores_marcados.remove(mb_nome)
        
        app.storage.user["entregadores_marcados_tab"] = entregadores_marcados
        desenhar_tabela_anual()

    def desenhar_tabela_anual():
        container_tabela_anual.clear()
        
        with container_tabela_anual:
            # --- MENU DE SELEÇÃO (LIGAR/DESLIGAR MOTOBOYS) ---
            if nomes_mbs_ano_originais:
                with ui.card().classes(f"w-full p-3 rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']} shadow-none"):
                    ui.label("SELECIONE QUEM APARECE NA TABELA").classes(f"text-[9px] font-black {cor['texto_secundario']} tracking-widest mb-2 px-1")
                    with ui.element('div').classes("w-full grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-x-4 gap-y-1 px-1"):
                        for mb in nomes_mbs_ano_originais:
                            nome_exibicao = limpar_nome_colaborador(mb)
                            ui.checkbox(
                                nome_exibicao, 
                                value=(mb in entregadores_marcados), 
                                on_change=lambda e, m=mb: atualizar_entregadores_tab(m, e.value)
                            ).classes(f"text-xs font-bold {cor['texto_secundario']} truncate w-full").props("dense")

            if not entregadores_marcados:
                ui.label("Nenhum entregador selecionado.").classes(f"{cor['texto_secundario']} text-sm italic w-full text-center py-4 border {cor['borda']} rounded-xl mt-2")
                return

            # --- TABELA TRANSPOSTA RESPONSIVA (Mobile-First) ---
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

                    # 2. COLUNAS DINÂMICAS (OS MOTOBOYS SELECIONADOS)
                    for mb_original in entregadores_marcados:
                        valores_meses = evo_mbs[mb_original]
                        total_anual = sum(valores_meses)
                        
                        with ui.column().classes(f"w-20 shrink-0 gap-0 border-r {cor['borda']} hover:bg-black/5 transition-colors"):
                            # Cabeçalho: Nome do Motoboy
                            nome_limpo = limpar_nome_colaborador(mb_original)
                            ui.label(nome_limpo).classes(f"w-full text-center py-2.5 text-[9px] font-black tracking-widest uppercase !{cor['texto_principal']} border-b {cor['borda']} truncate px-1")
                            
                            # Corpo: Valores dos Meses
                            for val in valores_meses:
                                valor_str = str(val) if val > 0 else "-"
                                cor_texto = f"!{cor['texto_principal']}" if val > 0 else cor['texto_secundario']
                                ui.label(valor_str).classes(f"w-full text-center py-2 text-xs font-medium {cor_texto} border-b {cor['borda']}")
                            
                            # Rodapé: Total Anual
                            ui.label(str(total_anual)).classes(f"w-full text-center py-2.5 text-sm font-black {cor['destaque']}")

    # Chama a função para desenhar a tabela na inicialização da tela
    desenhar_tabela_anual()