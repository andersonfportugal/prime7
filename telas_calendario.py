from nicegui import ui, app
import calendar
import datetime
import tema

# Simulação de dados que viriam do seu motor_dados.py
DADOS_FOLGAS_SIMULADOS = [
    {"data": "2026-06-10", "nome": "MARCOS", "unidade_id": 1, "tipo": "Folga"},
    {"data": "2026-06-10", "nome": "ANA", "unidade_id": 2, "tipo": "Férias"},
    {"data": "2026-06-15", "nome": "CARLOS", "unidade_id": 1, "tipo": "Atestado"},
]

def desenhar_tela_calendario():
    cor = tema.obter_cores()
    
    # Puxa o mês e ano do cabeçalho global
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))
    
    # Estado local do seletor de loja
    if "cal_unidade" not in app.storage.user:
        app.storage.user["cal_unidade"] = 1 # Loja 01 como padrão

    unidade_selecionada = app.storage.user["cal_unidade"]

    container_calendario = ui.column().classes("w-full gap-4")

    def recarregar_calendario(e):
        app.storage.user["cal_unidade"] = e.value
        desenhar_grade()

    def desenhar_grade():
        container_calendario.clear()
        
        with container_calendario:
            # --- FILTRO DA TELA (SOMENTE UNIDADE) ---
            with ui.row().classes(f"w-full justify-between items-center {cor['fundo_card']} p-3 rounded-2xl border {cor['borda']} shadow-sm"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("event_available", size="sm").classes(cor['destaque'])
                    ui.label("Escala de Folgas e Ausências").classes(f"font-black tracking-widest {cor['texto_principal']} uppercase text-sm")
                
                lojas = {1: "LOJA 01 - MATRIZ", 2: "LOJA 02 - FILIAL"}
                props_select = f"borderless dense hide-bottom-space {'dark' if cor['fundo_tela'] != 'bg-slate-50' else ''}"
                ui.select(lojas, value=unidade_selecionada, on_change=recarregar_calendario).classes(f"w-48 font-bold !{cor['texto_principal']}").props(props_select)

            # --- CONSTRUÇÃO DO CALENDÁRIO ---
            # Gera a matriz do mês (semanas x dias). Dias fora do mês vêm como 0.
            matriz_mes = calendar.monthcalendar(ano_atual, mes_atual)
            dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]

            with ui.card().classes(f"w-full p-4 rounded-2xl border {cor['borda']} {cor['fundo_card']} shadow-sm"):
                
                # Cabeçalho dos dias da semana
                with ui.grid(columns=7).classes("w-full gap-2 mb-2"):
                    for dia in dias_semana:
                        ui.label(dia).classes(f"text-center text-[10px] font-black {cor['texto_secundario']} tracking-widest")

                # Grade de dias
                with ui.grid(columns=7).classes("w-full gap-2"):
                    for semana in matriz_mes:
                        for dia in semana:
                            if dia == 0:
                                # Espaço vazio (dias do mês anterior/próximo)
                                ui.element('div').classes(f"min-h-[80px] rounded-xl bg-transparent")
                            else:
                                data_str = f"{ano_atual}-{mes_atual:02d}-{dia:02d}"
                                
                                # A MÁGICA DO FILTRO: Pega só as folgas deste dia E desta unidade
                                folgas_do_dia = [
                                    f for f in DADOS_FOLGAS_SIMULADOS 
                                    if f['data'] == data_str and f['unidade_id'] == unidade_selecionada
                                ]

                                is_hoje = (ano_atual == hoje.year and mes_atual == hoje.month and dia == hoje.day)
                                borda_dia = f"border-2 border-rose-500" if is_hoje else f"border {cor['borda']}"
                                bg_dia = "bg-rose-500/10" if is_hoje else cor['fundo_tela']

                                with ui.column().classes(f"min-h-[80px] p-1.5 rounded-xl {borda_dia} {bg_dia} gap-1 relative overflow-hidden group hover:brightness-110 transition-all"):
                                    ui.label(str(dia)).classes(f"text-xs font-black {cor['texto_secundario']} w-full text-right")
                                    
                                    # Renderiza os funcionários de folga
                                    for folga in folgas_do_dia:
                                        cor_tag = "bg-emerald-500/20 text-emerald-500" if folga['tipo'] == 'Folga' else "bg-amber-500/20 text-amber-500"
                                        ui.label(folga['nome']).classes(f"text-[9px] font-bold w-full text-center py-0.5 rounded {cor_tag} truncate")

    desenhar_grade()