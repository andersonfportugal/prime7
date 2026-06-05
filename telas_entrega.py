from nicegui import ui, app
import datetime
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
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))

    # --- CABEÇALHO COM SELETORES DE MÊS/ANO ---
    with ui.row().classes("w-full justify-between items-center mb-4 bg-white p-4 rounded-2xl shadow-sm border border-violet-100 flex-wrap gap-4 text-slate-800"):
        with ui.column().classes("gap-1"):
            ui.label("Módulo de Entregas e Performance").classes("text-violet-800 text-lg font-black tracking-widest uppercase")
            ui.label("Estatísticas baseadas na coluna data_entrega").classes("text-xs text-slate-500 font-bold")

        def recarregar_entregas(e):
            app.storage.user["mes"] = int(sel_mes.value)
            app.storage.user["ano"] = int(sel_ano.value)
            ui.navigate.to('/')

        with ui.row().classes("items-center bg-violet-50/50 p-2 rounded-xl border border-violet-100 gap-2"):
            ui.icon("two_wheeler", size="sm").classes("text-violet-500 ml-2")
            meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            sel_mes = ui.select(meses_pt, value=mes_atual, on_change=recarregar_entregas).classes("w-28 font-bold text-violet-900").props("borderless dense hide-bottom-space")
            sel_ano = ui.select([2024, 2025, 2026], value=ano_atual, on_change=recarregar_entregas).classes("w-20 font-bold text-violet-900").props("borderless dense hide-bottom-space")

    # Coleta de dados usando a nova integração blindada por ID
    tot_entregas, dict_filiais, ranking, evo_lojas, evo_mbs, mapa_lojas = obter_dados_entregas_fast(mes_atual, ano_atual)

    nomes_mbs_ano_originais = sorted(list(evo_mbs.keys()))
    entregadores_marcados = app.storage.user.get("entregadores_marcados_evo", [])
    entregadores_marcados = [m for m in entregadores_marcados if m in nomes_mbs_ano_originais]
    if not entregadores_marcados and nomes_mbs_ano_originais:
        entregadores_marcados = nomes_mbs_ano_originais[:4]
        app.storage.user["entregadores_marcados_evo"] = entregadores_marcados

    # --- CARTÕES SUPERIORES DE RESUMO ---
    with ui.row().classes("w-full gap-4 mb-4 items-stretch flex-wrap"):
        with ui.card().classes("flex-[2] p-4 rounded-xl shadow-sm border border-violet-100 bg-violet-50/50 min-w-[200px]"):
            ui.label("CORRIDAS DO MÊS").classes("text-[10px] font-bold text-violet-600 uppercase tracking-widest")
            ui.label(f"{tot_entregas} entregas").classes("text-3xl font-black text-violet-800 tracking-tight")

        # O Loop agora percorre os IDs do Dicionário
        for fid, nome_loja in mapa_lojas.items():
            qtd_loja = dict_filiais.get(fid, 0)
            with ui.card().classes("flex-1 p-4 rounded-xl shadow-sm border border-slate-100 bg-white min-w-[150px]"):
                ui.label(nome_loja).classes("text-[10px] font-bold text-slate-500 uppercase tracking-widest")
                ui.label(str(qtd_loja)).classes("text-2xl font-black text-slate-700 mt-1")

    # --- CORPO CENTRAL: GRÁFICOS DO MÊS E RANKING ---
    with ui.row().classes("w-full gap-4 items-stretch flex-wrap mb-4"):
        
        with ui.card().classes("flex-[2] p-4 rounded-xl shadow-sm border border-slate-100 bg-white min-w-[350px]"):
            ui.label("EVOLUÇÃO MENSAL DAS LOJAS (CORRIDAS)").classes("text-[11px] font-bold text-slate-500 uppercase mb-2")
            
            series_lojas = []
            cores_lojas = ["#8b5cf6", "#10b981", "#f59e0b", "#f43f5e", "#3b82f6"]
            # O Gráfico de Lojas agora puxa a lista de meses através do ID (fid)
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
                "legend": {"bottom": "0%", "textStyle": {"fontSize": 11, "fontWeight": "bold"}},
                "grid": {"left": "2%", "right": "4%", "bottom": "12%", "containLabel": True},
                "xAxis": {"type": "category", "data": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]},
                "yAxis": {"type": "value"},
                "series": series_lojas,
            }).classes("w-full h-[320px]")

        with ui.card().classes("flex-1 p-4 rounded-xl shadow-sm border border-slate-100 bg-white min-w-[280px] min-w-0"):
            ui.label(f"RANKING DO MÊS ({mes_atual:02d}/{ano_atual})").classes("text-[11px] font-bold text-slate-500 uppercase mb-3")
            
            if not ranking:
                ui.label("Sem corridas no mês selecionado.").classes("text-slate-400 italic text-sm mt-12 w-full text-center")
            else:
                max_corridas = max(r["qtd"] for r in ranking) if ranking else 1
                with ui.column().classes("w-full gap-3 mt-1 overflow-y-auto max-h-[320px] pr-1"):
                    for idx, r in enumerate(ranking):
                        posicao = idx + 1
                        nome_motoboy = limpar_nome_colaborador(r["nome"])
                        qtd_corridas = r["qtd"]
                        porcentagem = (qtd_corridas / max_corridas) * 100 if max_corridas > 0 else 0
                        cor_posicao = "text-amber-500 font-black" if posicao == 1 else \
                                      ("text-slate-400 font-black" if posicao == 2 else \
                                       ("text-amber-700 font-black" if posicao == 3 else "text-slate-400"))
                        
                        with ui.column().classes("w-full gap-0.5"):
                            with ui.row().classes("w-full justify-between items-center text-xs"):
                                with ui.row().classes("items-center gap-1.5 min-w-0 flex-1"):
                                    ui.label(f"#{posicao}").classes(f"w-5 shrink-0 text-center {cor_posicao}")
                                    ui.label(nome_motoboy).classes("font-bold text-slate-700 truncate w-full")
                                ui.label(f"{qtd_corridas} crd.").classes("font-black text-violet-700 shrink-0 pl-1")
                            
                            with ui.element('div').classes('w-full h-2 bg-slate-100 rounded-full overflow-hidden mt-0.5'):
                                ui.element('div').classes('h-full bg-violet-500 rounded-full transition-all duration-500').style(f'width: {porcentagem}%')

    # =============================================================================
    # SESSÃO 3: EVOLUÇÃO ANUAL DINÂMICA COM CHECKBOXES
    # =============================================================================
    ui.label("SESSÃO 3: EVOLUÇÃO ANUAL DOS ENTREGADORES").classes("text-[10px] font-black text-slate-400 tracking-widest px-1 mt-2")
    container_grafico_anual = ui.column().classes("w-full gap-2")

    def atualizar_entregadores_evo(mb_nome, marcado):
        if marcado and mb_nome not in entregadores_marcados:
            entregadores_marcados.append(mb_nome)
        elif not marcado and mb_nome in entregadores_marcados:
            entregadores_marcados.remove(mb_nome)
        
        app.storage.user["entregadores_marcados_evo"] = entregadores_marcados
        desenhar_grafico_anual()

    def desenhar_grafico_anual():
        container_grafico_anual.clear()
        
        with container_grafico_anual:
            if nomes_mbs_ano_originais:
                with ui.card().classes("w-full p-3 rounded-2xl shadow-sm border border-violet-50 bg-white shadow-none"):
                    ui.label("FILTRAR INTEGRANTES DA FROTA").classes("text-[9px] font-black text-slate-400 tracking-widest mb-2 px-1")
                    with ui.element('div').classes("w-full grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-x-4 gap-y-1 px-1"):
                        for mb in nomes_mbs_ano_originais:
                            nome_exibicao = limpar_nome_colaborador(mb)
                            ui.checkbox(
                                nome_exibicao, 
                                value=(mb in entregadores_marcados), 
                                on_change=lambda e, m=mb: atualizar_entregadores_evo(m, e.value)
                            ).classes("text-xs font-bold text-slate-500 truncate w-full").props("dense")

            if not entregadores_marcados:
                ui.label("Marque os entregadores acima para exibir a linha de evolução anual.").classes("text-slate-400 text-xs italic mt-2 px-1")
                return

            with ui.card().classes("w-full p-4 rounded-xl shadow-sm border border-slate-100 bg-white mt-1"):
                series_mb = []
                cores_mb = ["#f43f5e", "#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#06b6d4", "#ec4899", "#84cc16", "#a855f7", "#f97316"]
                
                for idx, mb_original in enumerate(entregadores_marcados):
                    nome_limpo = limpar_nome_colaborador(mb_original)
                    series_mb.append({
                        "name": nome_limpo, 
                        "type": "line", 
                        "smooth": True, 
                        "data": evo_mbs[mb_original], 
                        "symbolSize": 6, 
                        "lineStyle": {"width": 2}, 
                        "itemStyle": {"color": cores_mb[idx % len(cores_mb)]}
                    })

                ui.echart({
                    "tooltip": {"trigger": "axis"},
                    "legend": {"type": "scroll", "bottom": "0%", "textStyle": {"fontSize": 11, "fontWeight": "bold"}},
                    "grid": {"left": "2%", "right": "2%", "bottom": "12%", "containLabel": True},
                    "xAxis": {"type": "category", "data": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]},
                    "yAxis": {"type": "value"},
                    "series": series_mb,
                }).classes("w-full h-[350px]")

    desenhar_grafico_anual()