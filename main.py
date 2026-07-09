from nicegui import ui, app
import datetime
import os
from supabase import create_client, Client
import config
import tema

from motor_dados import (
    obter_dados_dashboard_fast, obter_dados_entregas_fast, 
    obter_dados_vendedores_fast, obter_dados_vendas_classificacao_fast,
    obter_dados_picos_horario_fast, obter_dados_pagamentos_fast, limpar_caches_dados
)

# =============================================================================
# 1. VARIÁVEIS GLOBAIS E GESTÃO DE SESSÃO
# =============================================================================
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
sessoes_ativas = {}

# A cor foi removida daqui do topo para ser chamada de forma segura dentro da página do utilizador!

def limpar_memoria(client):
    if client.id in sessoes_ativas:
        del sessoes_ativas[client.id]
app.on_disconnect(limpar_memoria)

# =============================================================================
# 2. IMPORTAÇÃO DAS TELAS
# =============================================================================
from telas_painel import (
    desenhar_tela_vendas_loja, 
    desenhar_tela_resumo, 
    desenhar_tela_dashboard_principal
)
from telas_entrega import desenhar_tela_entregas_motoboys 
from telas_vendedores import desenhar_tela_performance_vendedores
from telas_vendas import desenhar_tela_vendas_loja
from telas_compras import desenhar_tela_compras
from telas_resumo import desenhar_tela_resumo
from telas_calendario import desenhar_tela_calendario
# IMPORTAÇÃO DAS TELAS DE LOGIN
from telas_login import desenhar_ecra_login, validar_regresso_google

# =============================================================================
# 3. ROTAS DE AUTENTICAÇÃO (O PORTEIRO)
# =============================================================================
@ui.page("/login")
def pagina_login():
    desenhar_ecra_login()

@ui.page("/autenticacao")
def pagina_autenticacao():
    validar_regresso_google()

def fazer_logout():
    """Limpa a sessão e desloga o utilizador."""
    cliente_supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    cliente_supabase.auth.sign_out()
    app.storage.user.clear()
    ui.navigate.to('/login')

# =============================================================================
# 4. CASCA DO PAINEL PRINCIPAL (A FORTALEZA)
# =============================================================================
@ui.page("/")
def painel_principal():
    # =========================================================================
    # A TRAVA DE SEGURANÇA
    # =========================================================================
    if not app.storage.user.get("autenticado", False):
        ui.navigate.to('/login')
        return

    # Inicializa variáveis padrão
    hoje = datetime.date.today()
    app.storage.user.setdefault("mes", hoje.month)
    app.storage.user.setdefault("ano", hoje.year)
    app.storage.user.setdefault("aba_atual", "dashboard")

    # =========================================================================
    # INTELIGÊNCIA DE CORES (Busca o tema específico deste utilizador)
    # =========================================================================
    cor = tema.obter_cores()

    # =========================================================================
    # CONFIGURAÇÃO DE FONTE E CSS DINÂMICO
    # =========================================================================
    # =========================================================================
    # CONFIGURAÇÃO DE FONTE E CSS DINÂMICO
    # =========================================================================
    NOME_DA_FONTE = "Roboto"
    ui.add_head_html(f'<link href="https://fonts.googleapis.com/css2?family={NOME_DA_FONTE}:wght@300;400;600;800;900&display=swap" rel="stylesheet">')
    ui.add_head_html('<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">')
    
    # Adicione isso aqui! Ele força o texto do componente a ir pro meio:
    ui.add_css('.seletor-centro .q-field__native { justify-content: center !important; }')
    # Aplica o fundo do tema ao corpo da página
    ui.query("body").classes(f"{cor['fundo_tela']} m-0 p-0").style(f"font-family: '{NOME_DA_FONTE}', sans-serif;")
    
    # --- CABEÇALHO SUPERIOR ---
    with ui.header().classes(f"{cor['fundo_card']} border-b {cor['borda']} p-2 md:p-3 justify-between items-center shadow-sm flex-nowrap"):
        
        # Lado Esquerdo: Menu e Logo
        with ui.row().classes("items-center gap-1 md:gap-3 shrink-0"):
            ui.button(icon="menu", on_click=lambda: drawer.toggle()).props("flat round size=sm").classes(cor['destaque'])
            # Removido o 'hidden'. Usando text-lg (pequeno) no celular para caber e md:text-3xl (grande) no PC
            ui.label("ADiretor").classes(f"text-lg md:text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r {cor['gradiente_titulo']} tracking-tighter")
        
        # Lado Direito: Filtros, Temas e Sair
        with ui.row().classes("items-center gap-1 md:gap-2 flex-nowrap shrink-0"):
            
            # --- FILTRO GLOBAL (SELETORES) ---
            def atualizar_data_global(e):
                app.storage.user["mes"] = int(sel_mes.value)
                app.storage.user["ano"] = int(sel_ano.value)
                ui.run_javascript('window.location.reload()')

            with ui.row().classes(f"items-center {cor['fundo_tela']} px-1 md:px-2 py-0.5 md:py-1 rounded-xl border {cor['borda']} gap-1 flex-nowrap"):
                ui.icon("calendar_month", size="xs").classes(f"{cor['destaque']} hidden md:block")
                meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
                
                props_dinamicas = f"borderless dense hide-bottom-space {'dark' if cor['fundo_tela'] != 'bg-slate-50' else ''}"
                
                mes_atual = app.storage.user.get('mes', datetime.date.today().month)
                ano_atual = app.storage.user.get('ano', datetime.date.today().year)
                
                # Injetamos o 'seletor-centro' nas classes de ambos:
                sel_mes = ui.select(meses_pt, value=mes_atual, on_change=atualizar_data_global).classes(f"seletor-centro w-16 md:w-20 text-xs md:text-sm font-bold !{cor['texto_principal']}").props(props_dinamicas)
                sel_ano = ui.select([2021, 2022, 2023, 2024, 2025, 2026], value=ano_atual, on_change=atualizar_data_global).classes(f"seletor-centro w-16 md:w-20 text-xs md:text-sm font-bold !{cor['texto_principal']}").props(props_dinamicas)
                # --- DADOS DO USUÁRIO E TEMAS ---
            nome_usuario = app.storage.user.get("nome", "Usuário")
            ui.label(f"Olá, {nome_usuario}").classes(f"text-sm font-bold {cor['texto_secundario']} hidden lg:block")
            
            def trocar_tema(id_tema):
                app.storage.user['tema_preferido'] = id_tema
                email_logado = app.storage.user.get('email')
                if email_logado:
                    supabase.table("tb_usuarios_permitidos").update({"tema_preferido": id_tema}).eq("email", email_logado).execute()
                ui.navigate.to('/') 
            
            with ui.button(icon="palette").props("flat round size=sm").classes(cor['texto_secundario']):
                with ui.menu().classes(f"p-2 rounded-xl border {cor['borda']} {cor['fundo_card']} shadow-lg"):
                    ui.label("PERSONALIZAR VISUAL").classes(f"text-[9px] font-black {cor['texto_secundario']} tracking-widest uppercase mb-2 px-2")
                    for id_tema, dados in tema.paletas.items():
                        ui.menu_item(
                            dados['nome_amigavel'], 
                            on_click=lambda t=id_tema: trocar_tema(t)
                        ).classes(f"text-xs font-bold {cor['texto_principal']} hover:brightness-125 rounded")
            
            # Botão de logout minimalista
            ui.button(icon="logout", on_click=fazer_logout).props("flat round size=sm").classes("text-rose-500 hover:brightness-125").tooltip("Sair do Sistema")

            
    # --- MENU LATERAL (DRAWER) ---
    with ui.left_drawer(value=False).classes(f"{cor['fundo_card']} border-r {cor['borda']}") as drawer:
        ui.label("MENU PRINCIPAL").classes(f"text-[10px] font-black {cor['destaque']} tracking-widest mb-2 px-4 mt-6")

        def mudar_pagina(nome_aba, pagina_func):
            app.storage.user["aba_atual"] = nome_aba
            cliente_id_atual = ui.context.client.id
            if cliente_id_atual in sessoes_ativas: 
                sessoes_ativas[cliente_id_atual]["pagina"] = pagina_func

            estado = sessoes_ativas.get(cliente_id_atual, {}).get("estado_malote")
            if estado and estado.get("footer"): 
                estado["footer"].visible = False

            drawer.set_value(False)
            container_principal.clear()
            with container_principal:
                pagina_func()

        # Botões do menu dinâmicos
        estilo_btn = f"w-full text-sm font-bold {cor['texto_secundario']} hover:!{cor['texto_principal']} hover:brightness-125 px-4 py-3 rounded-r-2xl transition-all"

        ui.button("Dashboard", icon="dashboard", on_click=lambda: mudar_pagina("dashboard", desenhar_tela_dashboard_principal)).classes(estilo_btn).props('flat align="left"')
        ui.button("Resumo", icon="summarize", on_click=lambda: mudar_pagina("resumo", desenhar_tela_resumo)).classes(estilo_btn).props('flat align="left"')
        ui.button("Entregas", icon="local_shipping", on_click=lambda: mudar_pagina("entregas", desenhar_tela_entregas_motoboys)).classes(estilo_btn).props('flat align="left"')
        ui.button("Vendas", icon="point_of_sale", on_click=lambda: mudar_pagina("vendas", desenhar_tela_vendas_loja)).classes(estilo_btn).props('flat align="left"')
        ui.button("Vendedores", icon="groups", on_click=lambda: mudar_pagina("vendedores", desenhar_tela_performance_vendedores)).classes(estilo_btn).props('flat align="left"')
        ui.button("Compras", icon="shopping_cart", on_click=lambda: mudar_pagina("compras", desenhar_tela_compras)).classes(estilo_btn).props('flat align="left"')
        #ui.button("Folgas", icon="calendar", on_click=lambda: mudar_pagina("Folgas", desenhar_tela_calendario)).classes(estilo_btn).props('flat align="left"')
    
    # --- REGISTRO DA SESSÃO ---
    cliente_id = ui.context.client.id
    if cliente_id not in sessoes_ativas:
        sessoes_ativas[cliente_id] = {"client": ui.context.client, "estado_malote": {"dias": [], "footer": None, "lbl": None}}

    # --- RODAPÉ FLUTUANTE (Também reage ao tema) ---
    with ui.footer().classes(f"{cor['fundo_card']} border-t {cor['borda']} p-2 md:p-3 justify-center items-center z-50 shadow-[0_-10px_15px_-3px_rgba(0,0,0,0.3)]") as rodape:
        rodape.visible = False
        sessoes_ativas[cliente_id]["estado_malote"]["footer"] = rodape
        
        with ui.row().classes("w-full max-w-[1600px] mx-auto justify-between items-center flex-nowrap px-2"):
            with ui.row().classes("items-center gap-2 shrink-0"):
                ui.icon("calculate", size="sm").classes(cor['destaque'])
                ui.label("SELEÇÃO").classes(f"text-[10px] md:text-sm font-bold {cor['destaque']} tracking-wider")
            with ui.row().classes("items-center gap-4 shrink-0"):
                lbl_soma_tot = ui.label("R$ 0.00").classes(f"text-sm md:text-lg font-bold {cor['texto_principal']}")
                sessoes_ativas[cliente_id]["estado_malote"]["lbl"] = lbl_soma_tot
                ui.button("Somente Leitura", icon="visibility").classes(f"{cor['fundo_tela']} {cor['texto_secundario']} font-bold py-1 px-3 md:px-4 rounded-lg").props("size=sm disable")

    # --- CONTAINER CENTRAL ---
    container_principal = ui.column().classes("w-full max-w-[1600px] mx-auto p-4 mt-2")
    sessoes_ativas[cliente_id]["container"] = container_principal

    limpar_caches_dados()

    # --- A MÁGICA DO PRÉ-CARREGAMENTO ---
    def pre_carregar_tudo():
        mes = app.storage.user.get("mes")
        ano = app.storage.user.get("ano")
        # Ao chamar estas funções, o @lru_cache já salva o resultado na RAM
        obter_dados_entregas_fast(mes, ano)
        obter_dados_vendedores_fast(mes, ano)
        obter_dados_vendas_classificacao_fast(mes, ano)
        obter_dados_picos_horario_fast(mes, ano)
        obter_dados_pagamentos_fast(mes, ano)
        # O Dashboard já foi carregado pela função que desenha a tela, 
        # então não precisa pre-carregar ele aqui.

    # Dispara o carregamento em background 1.5s após a tela abrir
    ui.timer(1.5, pre_carregar_tudo, once=True)

    with container_principal:
        aba = app.storage.user.get("aba_atual", "dashboard")
        
        if aba == "resumo":
            desenhar_tela_resumo()
        elif aba == "entregas":
            desenhar_tela_entregas_motoboys()
        elif aba == "vendas":
            desenhar_tela_vendas_loja()
        elif aba == "vendedores":
            desenhar_tela_performance_vendedores()
        elif aba == "compras":
            desenhar_tela_compras()
        else:
            #desenhar_tela_resumo()
            desenhar_tela_dashboard_principal()

# =============================================================================
# INICIALIZAÇÃO DO SERVIDOR
# =============================================================================
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="NeDiretor",
        language="pt-BR",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        storage_secret="chave_mestra_nediretor_2026",
    )