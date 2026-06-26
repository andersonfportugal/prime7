from nicegui import ui, app
import datetime
import tema
from motor_dados import obter_dados_compras_fast, formatar_moeda_brasil

def desenhar_tela_compras():
    # Puxa o motor de temas sem alterar a estrutura do arquivo
    cor = tema.obter_cores()
    
    hoje = datetime.date.today()
    ano_atual = int(app.storage.user.get("ano", hoje.year))
    mes_atual = int(app.storage.user.get("mes", hoje.month))

    # --- CABEÇALHO ---
    with ui.row().classes(f"w-full justify-between items-center mb-4 {cor['fundo_card']} p-4 rounded-2xl shadow-sm border {cor['borda']} flex-wrap gap-4"):
        with ui.column().classes("gap-1"):
            ui.label("Notas fiscais emitidas").classes(f"{cor['compras_titulo']} text-lg font-black tracking-widest uppercase")
            ui.label("Espelho de entrada de notas fiscais de fornecedores").classes(f"text-xs {cor['texto_secundario']} font-bold")

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

                with ui.card().classes(f"flex-1 p-4 rounded-2xl shadow-sm border {cor['compras_borda']} {cor['compras_bg']} min-w-[200px] gap-1"):
                    ui.label(nome_loja).classes(f"text-xs font-black {cor['compras_titulo']} tracking-widest uppercase")
                    ui.label(f"R$ {formatar_moeda_brasil(valor_total_loja)}").classes(f"text-3xl font-black {cor['compras_destaque']} tracking-tight")
                    ui.label(f"{qtd_notas} Nf-e").classes(f"text-[10px] font-bold {cor['compras_titulo']} opacity-80 uppercase")

    # --- RELATÓRIO GERAL UNIFICADO ---
    ui.label("EXTRATO GERAL DE NOTAS FISCAIS").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest px-1 mt-2 mb-2")

    if not lista_notas:
        with ui.card().classes(f"w-full p-8 text-center rounded-2xl shadow-sm border {cor['borda']} {cor['fundo_card']}"):
            ui.label("Nenhuma nota fiscal encontrada para o período.").classes(f"{cor['texto_secundario']} italic text-sm")
    else:
        # Mantém as cores semânticas (verde, laranja, fúcsia) apenas para identificar o status visualmente
        config_status = {
            'C': {"cor": "border-l-emerald-500", "texto": "CONCLUÍDA", "cor_texto": "text-emerald-500"},
            'R': {"cor": "border-l-orange-500", "texto": "RECEBIDA", "cor_texto": "text-orange-500"},
            'I': {"cor": "border-l-fuchsia-500", "texto": "INICIAL", "cor_texto": "text-fuchsia-500"},
        }

        with ui.column().classes("w-full gap-2 pb-8"):
            for nota in lista_notas:
                status_info = config_status.get(nota['status_nota'], {"cor": "border-l-slate-400", "texto": "DESCONHECIDO", "cor_texto": "text-slate-400"})
                
                with ui.card().classes(f"w-full p-3 rounded-xl shadow-sm border-l-4 {status_info['cor']} border-t border-r border-b {cor['borda']} {cor['fundo_card']} hover:shadow-md transition-shadow gap-0"):
                    
                    with ui.row().classes("w-full justify-between items-start flex-nowrap gap-2"):
                        with ui.row().classes("items-center gap-2 min-w-0 flex-1"):
                            ui.label(nota['fornecedor']).classes(f"text-xs font-bold !{cor['texto_principal']} truncate")
                            ui.label(f"NFe {nota['numero_nota']}").classes(f"text-[10px] font-bold {cor['texto_secundario']} shrink-0 {cor['fundo_tela']} px-1.5 py-0.5 rounded")
                        
                        ui.label(f"R$ {formatar_moeda_brasil(nota['valor_total'])}").classes(f"text-sm font-black !{cor['texto_principal']} shrink-0")
                    
                    with ui.row().classes("w-full justify-between items-center mt-1.5"):
                        with ui.row().classes("items-center gap-2"):
                            ui.label(status_info['texto']).classes(f"text-[9px] font-black {status_info['cor_texto']} tracking-widest uppercase")
                            ui.label("•").classes(f"{cor['texto_secundario']} opacity-50 text-[9px]")
                            # Mantém a exibição do nome bonitinho usando o dicionário
                            nome_exibicao = mapa_lojas.get(nota['filial'], "DESCONHECIDA")
                            ui.label(nome_exibicao).classes(f"text-[10px] font-black {cor['compras_titulo']} tracking-widest uppercase")
                        
                        with ui.row().classes("items-center gap-1"):
                            ui.icon("calendar_today", size="10px").classes(cor['texto_secundario'])
                            ui.label(nota['data_emissao']).classes(f"text-[10px] font-bold {cor['texto_secundario']}")