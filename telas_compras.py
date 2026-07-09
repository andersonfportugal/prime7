from nicegui import ui, app
import datetime
import tema
import re
from motor_dados import obter_dados_compras_fast, buscar_compras_avancado_fast, formatar_moeda_brasil

def desenhar_tela_compras():
    cor = tema.obter_cores()
    
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))

    estado = {'nf': '', 'fornecedor': '', 'dt_ini': '', 'dt_fim': ''}

    # --- CABEÇALHO ---
    with ui.row().classes(f"w-full justify-between items-center mb-4 {cor['fundo_card']} p-4 rounded-2xl shadow-sm border {cor['borda']} flex-wrap gap-4"):
        with ui.column().classes("gap-1"):
            ui.label("Notas fiscais emitidas").classes(f"{cor['compras_titulo']} text-lg font-black tracking-widest uppercase")
            #ui.label("Espelho de entrada de notas fiscais de fornecedores").classes(f"text-xs {cor['texto_secundario']} font-bold")

    # --- ÁREA DINÂMICA COMPLETA ---
    @ui.refreshable
    def area_resultados():
        nf = estado['nf'].strip()
        forn = estado['fornecedor'].strip()
        dt_ini = estado['dt_ini']
        dt_fim = estado['dt_fim']

        if nf or forn or dt_ini or dt_fim:
            lista_notas = buscar_compras_avancado_fast(nf, forn, dt_ini, dt_fim)
        else:
            lista_notas = obter_dados_compras_fast(mes_atual, ano_atual)

        mapa_lojas = {}
        for n in lista_notas:
            mapa_lojas[n['filial']] = n['loja']

        # 1. RESUMO FINANCEIRO SEPARADO POR LOJA NO TOPO
        if mapa_lojas:
            with ui.row().classes("w-full mb-6 items-stretch gap-4 flex-wrap"):
                for fid, nome_loja in mapa_lojas.items():
                    notas_loja = [n for n in lista_notas if n['filial'] == fid]
                    valor_total_loja = sum(n['valor_total'] for n in notas_loja)
                    qtd_notas = len(notas_loja)

                    with ui.card().classes(f"flex-1 p-4 rounded-2xl shadow-sm border {cor['compras_borda']} {cor['compras_bg']} min-w-[200px] gap-1"):
                        ui.label(nome_loja).classes(f"text-xs font-black {cor['compras_titulo']} tracking-widest uppercase")
                        ui.label(f"R$ {formatar_moeda_brasil(valor_total_loja)}").classes(f"text-3xl font-black {cor['compras_destaque']} tracking-tight")
                        ui.label(f"{qtd_notas} Nf-e").classes(f"text-[10px] font-bold {cor['compras_titulo']} opacity-80 uppercase")

        # 2. ÁREA DE FILTROS (AGORA COM AS BORDAS SUTIS IGUAIS AOS CARDS)
        with ui.card().classes(f"w-full mb-6 p-4 rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']}"):
            ui.label("FILTRAR NOTAS").classes(f"text-[10px] font-black {cor['compras_titulo']} tracking-widest uppercase mb-2")
            
            with ui.row().classes("w-full items-end gap-4 flex-wrap"):
                
                with ui.column().classes("gap-1"):
                    ui.label("NÚMERO DA NF").classes(f"text-[9px] font-black {cor['compras_titulo']} tracking-widest uppercase")
                    input_nf = ui.input(value=estado['nf']) \
                        .classes(f"w-28 border {cor['borda']} rounded-lg px-2 transition-colors") \
                        .props(f'borderless dense clearable input-class="!{cor["texto_principal"]}"')
                
                with ui.column().classes("gap-1 flex-1 min-w-[150px]"):
                    ui.label("FORNECEDOR").classes(f"text-[9px] font-black {cor['compras_titulo']} tracking-widest uppercase")
                    input_forn = ui.input(value=estado['fornecedor']) \
                        .classes(f"w-full border {cor['borda']} rounded-lg px-2 transition-colors") \
                        .props(f'borderless dense clearable input-class="!{cor["texto_principal"]}"')

                with ui.column().classes("gap-1"):
                    ui.label("DATA INICIAL").classes(f"text-[9px] font-black {cor['compras_titulo']} tracking-widest uppercase")
                    input_dt_ini = ui.input(value=estado['dt_ini']) \
                        .classes(f"w-36 border {cor['borda']} rounded-lg px-2 transition-colors") \
                        .props(f'type="date" borderless dense clearable input-class="!{cor["texto_principal"]}"')

                with ui.column().classes("gap-1"):
                    ui.label("DATA FINAL").classes(f"text-[9px] font-black {cor['compras_titulo']} tracking-widest uppercase")
                    input_dt_fim = ui.input(value=estado['dt_fim']) \
                        .classes(f"w-36 border {cor['borda']} rounded-lg px-2 transition-colors") \
                        .props(f'type="date" borderless dense clearable input-class="!{cor["texto_principal"]}"')
                
                def executar_pesquisa(e=None):
                    estado['nf'] = input_nf.value or ''
                    estado['fornecedor'] = input_forn.value or ''
                    estado['dt_ini'] = input_dt_ini.value or ''
                    estado['dt_fim'] = input_dt_fim.value or ''
                    area_resultados.refresh()

                input_nf.on('keydown.enter', executar_pesquisa)
                input_forn.on('keydown.enter', executar_pesquisa)
                
                ui.button("Buscar", on_click=executar_pesquisa, icon="search", color=None) \
                    .classes(f"h-10 px-6 rounded-lg font-black tracking-widest uppercase border {cor['borda']} {cor['compras_destaque']} hover:opacity-70 transition-all bg-transparent") \
                    .props('flat')

        # 3. LISTA DE NOTAS
        with ui.row().classes("w-full items-center justify-between mt-2 mb-2 px-1"):
            ui.label("EXTRATO GERAL DE NOTAS FISCAIS").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest")
            if nf or forn or dt_ini or dt_fim:
                ui.label("Exibindo resultados da pesquisa").classes(f"text-[10px] font-black {cor['compras_destaque']} uppercase tracking-widest")

        if not lista_notas:
            with ui.card().classes(f"w-full p-8 text-center rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']}"):
                ui.label("Nenhuma nota fiscal encontrada.").classes(f"{cor['texto_secundario']} italic text-sm")
        else:
            config_status = {
                'C': {"cor": "border-l-emerald-500", "texto": "CONCLUÍDA", "cor_texto": "text-emerald-500"},
                'R': {"cor": "border-l-orange-500", "texto": "RECEBIDA", "cor_texto": "text-orange-500"},
                'I': {"cor": "border-l-fuchsia-500", "texto": "INICIAL", "cor_texto": "text-fuchsia-500"},
            }

            with ui.column().classes("w-full gap-2 pb-8"):
                for nota in lista_notas:
                    status_info = config_status.get(nota['status_nota'], {"cor": "border-l-slate-400", "texto": "DESCONHECIDO", "cor_texto": "text-slate-400"})
                    
                    # Limpeza do Fornecedor
                    forn_bruto = str(nota.get('fornecedor', ''))
                    forn_sem_numeros = re.sub(r'[\d.\-/\:]', '', forn_bruto)
                    fornecedor_limpo = re.sub(r'\s+', ' ', forn_sem_numeros).strip()
                    if not fornecedor_limpo:
                        fornecedor_limpo = "FORNECEDOR NÃO IDENTIFICADO"

                    # Limpeza da Data
                    data_bruta = str(nota.get('data_emissao', '')).split('T')[0].split(' ')[0]
                    if '-' in data_bruta and len(data_bruta.split('-')[0]) == 4:
                        ano, mes, dia = data_bruta.split('-')
                        data_formatada = f"{dia}/{mes}/{ano}"
                    else:
                        data_formatada = data_bruta

                    with ui.card().classes(f"w-full p-3 rounded-xl shadow-sm border-l-4 {status_info['cor']} border-t border-r border-b {cor['borda']} {cor['fundo_card']} hover:shadow-md transition-shadow gap-0"):
                        with ui.row().classes("w-full justify-between items-start flex-nowrap gap-2"):
                            with ui.row().classes("items-center gap-2 min-w-0 flex-1"):
                                ui.label(fornecedor_limpo).classes(f"text-xs font-bold !{cor['texto_principal']} truncate")
                                ui.label(f"NFe {nota['numero_nota']}").classes(f"text-[10px] font-bold {cor['texto_secundario']} shrink-0 {cor['fundo_tela']} px-1.5 py-0.5 rounded")
                            ui.label(f"R$ {formatar_moeda_brasil(nota['valor_total'])}").classes(f"text-sm font-black !{cor['texto_principal']} shrink-0")
                        
                        with ui.row().classes("w-full justify-between items-center mt-1.5"):
                            with ui.row().classes("items-center gap-2"):
                                ui.label(status_info['texto']).classes(f"text-[9px] font-black {status_info['cor_texto']} tracking-widest uppercase")
                                ui.label("•").classes(f"{cor['texto_secundario']} opacity-50 text-[9px]")
                                nome_exibicao = mapa_lojas.get(nota['filial'], "DESCONHECIDA")
                                ui.label(nome_exibicao).classes(f"text-[10px] font-black {cor['compras_titulo']} tracking-widest uppercase")
                            
                            with ui.row().classes("items-center gap-1"):
                                ui.icon("calendar_today", size="10px").classes(cor['texto_secundario'])
                                ui.label(data_formatada).classes(f"text-[10px] font-bold {cor['texto_secundario']}")

    area_resultados()