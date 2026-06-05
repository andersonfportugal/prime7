from nicegui import ui, app
import datetime
from motor_dados import obter_dados_compras_fast, formatar_moeda_brasil

def desenhar_tela_compras():
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))

    # --- CABEÇALHO ---
    with ui.row().classes("w-full justify-between items-center mb-4 bg-white p-4 rounded-2xl shadow-sm border border-sky-100 flex-wrap gap-4 text-slate-800"):
        with ui.column().classes("gap-1"):
            ui.label("Gestão de Compras e NFe").classes("text-sky-800 text-lg font-black tracking-widest uppercase")
            ui.label("Espelho de entrada de notas fiscais de fornecedores").classes("text-xs text-slate-500 font-bold")

        def recarregar_compras(e):
            app.storage.user["mes"] = int(sel_mes.value)
            app.storage.user["ano"] = int(sel_ano.value)
            ui.navigate.to('/')

        with ui.row().classes("items-center bg-sky-50/50 p-2 rounded-xl border border-sky-100 gap-2"):
            ui.icon("receipt_long", size="sm").classes("text-sky-500 ml-2")
            meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            sel_mes = ui.select(meses_pt, value=mes_atual, on_change=recarregar_compras).classes("w-28 font-bold text-sky-900").props("borderless dense hide-bottom-space")
            sel_ano = ui.select([2024, 2025, 2026], value=ano_atual, on_change=recarregar_compras).classes("w-20 font-bold text-sky-900").props("borderless dense hide-bottom-space")

    # Coleta os dados
    lista_notas = obter_dados_compras_fast(mes_atual, ano_atual)
    
    # Cria o Dicionário de Lojas usando o ID (filial) como chave segura
    mapa_lojas = {}
    for n in lista_notas:
        mapa_lojas[n['filial']] = n['loja']

    # --- RESUMO FINANCEIRO SEPARADO POR LOJA NO TOPO (Baseado no ID) ---
    if mapa_lojas:
        with ui.row().classes("w-full mb-6 items-stretch gap-4 flex-wrap"):
            for fid, nome_loja in mapa_lojas.items():
                # Filtra as notas pelo ID da filial, não pelo nome!
                notas_loja = [n for n in lista_notas if n['filial'] == fid]
                valor_total_loja = sum(n['valor_total'] for n in notas_loja)
                qtd_notas = len(notas_loja)

                with ui.card().classes("flex-1 p-4 rounded-2xl shadow-sm border border-sky-200 bg-sky-50/40 min-w-[200px] gap-1"):
                    ui.label(nome_loja).classes("text-xs font-black text-sky-800 tracking-widest uppercase")
                    ui.label(f"R$ {formatar_moeda_brasil(valor_total_loja)}").classes("text-3xl font-black text-sky-700 tracking-tight")
                    ui.label(f"{qtd_notas} notas processadas").classes("text-[10px] font-bold text-sky-600/70 uppercase")

    # --- RELATÓRIO GERAL UNIFICADO ---
    ui.label("EXTRATO GERAL DE NOTAS FISCAIS").classes("text-[10px] font-black text-slate-400 tracking-widest px-1 mt-2 mb-2")

    if not lista_notas:
        with ui.card().classes("w-full p-8 text-center rounded-2xl shadow-sm border border-slate-100 bg-white"):
            ui.label("Nenhuma nota fiscal encontrada para o período.").classes("text-slate-400 italic text-sm")
    else:
        config_status = {
            'C': {"cor": "border-l-emerald-500", "texto": "CONCLUÍDA", "cor_texto": "text-emerald-600"},
            'R': {"cor": "border-l-orange-500", "texto": "RECEBIDA", "cor_texto": "text-orange-600"},
            'I': {"cor": "border-l-fuchsia-500", "texto": "INICIAL", "cor_texto": "text-fuchsia-600"},
        }

        with ui.column().classes("w-full gap-2 pb-8"):
            for nota in lista_notas:
                status_info = config_status.get(nota['status_nota'], {"cor": "border-l-slate-400", "texto": "DESCONHECIDO", "cor_texto": "text-slate-400"})
                
                with ui.card().classes(f"w-full p-3 rounded-xl shadow-sm border-l-4 {status_info['cor']} border-t border-r border-b border-slate-100 bg-white hover:bg-slate-50 transition-colors gap-0"):
                    
                    with ui.row().classes("w-full justify-between items-start flex-nowrap gap-2"):
                        with ui.row().classes("items-center gap-2 min-w-0 flex-1"):
                            ui.label(nota['fornecedor']).classes("text-xs font-bold text-slate-700 truncate")
                            ui.label(f"NFe {nota['numero_nota']}").classes("text-[10px] font-bold text-slate-400 shrink-0 bg-slate-100 px-1.5 py-0.5 rounded")
                        
                        ui.label(f"R$ {formatar_moeda_brasil(nota['valor_total'])}").classes("text-sm font-black text-slate-800 shrink-0")
                    
                    with ui.row().classes("w-full justify-between items-center mt-1.5"):
                        with ui.row().classes("items-center gap-2"):
                            ui.label(status_info['texto']).classes(f"text-[9px] font-black {status_info['cor_texto']} tracking-widest uppercase")
                            ui.label("•").classes("text-slate-300 text-[9px]")
                            # Mantém a exibição do nome bonitinho usando o dicionário
                            nome_exibicao = mapa_lojas.get(nota['filial'], "DESCONHECIDA")
                            ui.label(nome_exibicao).classes("text-[10px] font-black text-sky-800 tracking-widest uppercase")
                        
                        with ui.row().classes("items-center gap-1"):
                            ui.icon("calendar_today", size="10px").classes("text-slate-400")
                            ui.label(nota['data_emissao']).classes("text-[10px] font-bold text-slate-500")