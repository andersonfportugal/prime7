from nicegui import ui, app
import datetime
import os
from supabase import create_client, Client
import config

# =============================================================================
# 1. VARIÁVEIS GLOBAIS E GESTÃO DE SESSÃO
# =============================================================================
sessoes_ativas = {}

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

# IMPORTAÇÃO DAS TELAS DE LOGIN
from telas_login import desenhar_ecra_login, validar_regresso_google

# =============================================================================
# 3. ROTAS DE AUTENTICAÇÃO (O PORTEIRO)
# =============================================================================
@ui.page("/login")
def pagina_login():
    # Desenha a tela com o botão do Google
    desenhar_ecra_login()

@ui.page("/autenticacao")
def pagina_autenticacao():
    # Rota que recebe o usuário de volta do Google e checa a Lista VIP
    validar_regresso_google()

def fazer_logout():
    """Limpa a sessão e desloga o usuário."""
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    supabase.auth.sign_out()
    app.storage.user.clear()
    ui.navigate.to('/login')

# =============================================================================
# 4. CASCA DO PAINEL PRINCIPAL (A FORTALEZA)
# =============================================================================
@ui.page("/")
def painel_principal():
    # =========================================================================
    # A TRAVA DE SEGURANÇA: Se não tiver o crachá, manda pro Login!
    # =========================================================================
    if not app.storage.user.get("autenticado", False):
        ui.navigate.to('/login')
        return

    # Inicializa variáveis padrão na sessão do usuário
    hoje = datetime.date.today()
    app.storage.user.setdefault("mes", hoje.month)
    app.storage.user.setdefault("ano", hoje.year)
    app.storage.user.setdefault("aba_atual", "dashboard") # Tela inicial padrão

    # =========================================================================
    # CONFIGURAÇÃO DE FONTE E CSS
    # =========================================================================
    NOME_DA_FONTE = "Roboto"
    ui.add_head_html(f'<link href="https://fonts.googleapis.com/css2?family={NOME_DA_FONTE}:wght@300;400;600;800;900&display=swap" rel="stylesheet">')
    ui.add_head_html('<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">')
    ui.query("body").classes("bg-slate-50 m-0 p-0").style(f"font-family: '{NOME_DA_FONTE}', sans-serif;")
    
    # --- CABEÇALHO SUPERIOR ---
    with ui.header().classes("bg-white border-b border-cyan-100 p-3 justify-between items-center shadow-sm"):
        with ui.row().classes("items-center gap-3"):
            ui.button(icon="menu", on_click=lambda: drawer.toggle()).props("flat round size=sm text-color=cyan-800")
            ui.label("NeDiretor").classes("text-2xl md:text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-500 to-emerald-400 tracking-tighter")
        
        with ui.row().classes("items-center gap-4"):
            # Exibe quem está logado e o botão de Sair
            nome_usuario = app.storage.user.get("nome", "Usuário")
            ui.label(f"Olá, {nome_usuario}").classes("text-sm font-bold text-slate-500 hidden md:block")
            ui.button("Sair", icon="logout", on_click=fazer_logout).props("flat size=sm text-color=rose-500").classes("ml-2")

    # --- MENU LATERAL (DRAWER) ---
    with ui.left_drawer(value=False).classes("bg-white border-r border-cyan-100") as drawer:
        ui.label("MENU PRINCIPAL").classes("text-[10px] font-black text-cyan-800 tracking-widest mb-2 px-4 mt-6")

        def mudar_pagina(nome_aba, pagina_func):
            app.storage.user["aba_atual"] = nome_aba
            cliente_id = ui.context.client.id
            if cliente_id in sessoes_ativas: 
                sessoes_ativas[cliente_id]["pagina"] = pagina_func

            estado = sessoes_ativas.get(cliente_id, {}).get("estado_malote")
            if estado and estado.get("footer"): 
                estado["footer"].visible = False

            drawer.set_value(False)
            container_principal.clear()
            with container_principal:
                pagina_func()

        estilo_btn = "w-full text-sm font-bold text-slate-600 hover:text-cyan-800 hover:bg-cyan-50 px-4 py-3 rounded-r-2xl transition-all"

        ui.button("Dashboard", icon="dashboard", on_click=lambda: mudar_pagina("dashboard", desenhar_tela_dashboard_principal)).classes(estilo_btn).props('flat align="left"')
        ui.button("Resumo", icon="summarize", on_click=lambda: mudar_pagina("resumo", desenhar_tela_resumo)).classes(estilo_btn).props('flat align="left"')
        ui.button("Entregas", icon="local_shipping", on_click=lambda: mudar_pagina("entregas", desenhar_tela_entregas_motoboys)).classes(estilo_btn).props('flat align="left"')
        ui.button("Vendas", icon="point_of_sale", on_click=lambda: mudar_pagina("vendas", desenhar_tela_vendas_loja)).classes(estilo_btn).props('flat align="left"')
        ui.button("Vendedores", icon="groups", on_click=lambda: mudar_pagina("vendedores", desenhar_tela_performance_vendedores)).classes(estilo_btn).props('flat align="left"')
        ui.button("Compras", icon="shopping_cart", on_click=lambda: mudar_pagina("compras", desenhar_tela_compras)).classes(estilo_btn).props('flat align="left"')
    
    # --- REGISTRO DA SESSÃO ---
    cliente_id = ui.context.client.id
    if cliente_id not in sessoes_ativas:
        sessoes_ativas[cliente_id] = {"client": ui.context.client, "estado_malote": {"dias": [], "footer": None, "lbl": None}}

    # --- RODAPÉ FLUTUANTE ---
    with ui.footer().classes("bg-slate-900 text-white p-2 md:p-3 justify-center items-center z-50 shadow-[0_-10px_15px_-3px_rgba(0,0,0,0.3)]") as rodape:
        rodape.visible = False
        sessoes_ativas[cliente_id]["estado_malote"]["footer"] = rodape
        
        with ui.row().classes("w-full max-w-[1600px] mx-auto justify-between items-center flex-nowrap px-2"):
            with ui.row().classes("items-center gap-2 shrink-0"):
                ui.icon("calculate", size="sm").classes("text-cyan-400")
                ui.label("SELEÇÃO").classes("text-[10px] md:text-sm font-bold text-cyan-400 tracking-wider")
            with ui.row().classes("items-center gap-4 shrink-0"):
                lbl_soma_tot = ui.label("R$ 0.00").classes("text-sm md:text-lg font-bold text-white")
                sessoes_ativas[cliente_id]["estado_malote"]["lbl"] = lbl_soma_tot
                ui.button("Somente Leitura", icon="visibility").classes("bg-slate-700 text-slate-300 font-bold py-1 px-3 md:px-4 rounded-lg").props("size=sm disable")

    # --- CONTAINER CENTRAL ---
    container_principal = ui.column().classes("w-full max-w-[1600px] mx-auto p-4 mt-2")
    sessoes_ativas[cliente_id]["container"] = container_principal

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