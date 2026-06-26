from urllib.parse import parse_qsl, urlparse, parse_qs
from nicegui import ui, app
import config
import tema
from supabase import create_client, Client, ClientOptions
import asyncio

# Desliga o PKCE e força o Fluxo Implícito
opcoes = ClientOptions(flow_type="implicit")
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY, options=opcoes)

def desenhar_ecra_login():
    cor = tema.obter_cores()
    
    ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;600;800;900&display=swap" rel="stylesheet">')
    ui.query('body').classes(f"{cor['fundo_tela']} m-0 p-0").style("font-family: 'Roboto', sans-serif;")
    
    with ui.column().classes("w-full h-screen items-center justify-center p-4"):
        with ui.card().classes(f"w-full max-w-sm p-8 rounded-2xl shadow-lg border {cor['borda']} {cor['fundo_card']} items-center text-center gap-6"):
            
            with ui.column().classes("items-center gap-1 w-full"):
                ui.icon("admin_panel_settings", size="3xl").classes(f"{cor['destaque']} mb-2")
                ui.label("NeDiretor").classes(f"text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r {cor['gradiente_titulo']} tracking-tighter")
                ui.label("ACESSO RESTRITO").classes(f"text-[10px] font-black {cor['texto_secundario']} tracking-widest uppercase")

            classe_bg_separador = cor['borda'].replace('border-', 'bg-')
            ui.separator().classes(f"w-full {classe_bg_separador} my-2")

            # =====================================================================================
            # A MÁGICA DO MODO DESENVOLVEDOR (BYPASS)
            # =====================================================================================
            def executar_login_bifurcado(provedor):
                if config.AMBIENTE_ATUAL == "LOCAL":
                    # Pula o Supabase, ignora a Microsoft/Google e injeta os dados na hora
                    app.storage.user['autenticado'] = True
                    app.storage.user['email'] = 'desenvolvedor@local.com'
                    app.storage.user['nome'] = 'Desenvolvedor (Local)'
                    app.storage.user['cargo'] = 'Diretor'
                    # Mantém o tema que você escolheu no PC, ou usa o Padrão
                    app.storage.user['tema_preferido'] = app.storage.user.get('tema_preferido', 'PADRAO')
                    
                    ui.notify("Modo Desenvolvedor: Login Bypass Ativado!", type="positive", position="top")
                    ui.navigate.to('/')
                else:
                    # Modo Nuvem: Aciona o Supabase e os guardas de segurança reais
                    resposta = supabase.auth.sign_in_with_oauth({
                        "provider": provedor,
                        "options": {
                            "redirect_to": f"{config.URL_SISTEMA}/autenticacao",
                            "scopes": "email" if provedor == "azure" else None
                        }
                    })
                    ui.navigate.to(resposta.url)
            # =====================================================================================

            with ui.column().classes("w-full gap-3 mt-2"):
                ui.button("CONTINUAR COM GOOGLE", icon="login", on_click=lambda: executar_login_bifurcado("google"))\
                    .classes(f"w-full bg-transparent border {cor['borda']} !{cor['texto_principal']} text-[11px] font-black tracking-widest rounded-xl py-3.5 hover:brightness-125 transition-all")\
                    .props("unelevated")
                
                ui.button("CONTINUAR COM MICROSOFT", icon="window", on_click=lambda: executar_login_bifurcado("azure"))\
                    .classes(f"w-full bg-transparent border {cor['borda']} !{cor['texto_principal']} text-[11px] font-black tracking-widest rounded-xl py-3.5 hover:brightness-125 transition-all")\
                    .props("unelevated")
                
            ui.label("Protected by Supabase Auth").classes(f"text-[9px] {cor['texto_secundario']} tracking-widest mt-2 uppercase")

# =========================================================================================
# A CATRACA / ROTA DE VERIFICAÇÃO 
# =========================================================================================
def validar_regresso_google():
    cor = tema.obter_cores()
    
    ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;600;800;900&display=swap" rel="stylesheet">')
    ui.query('body').classes(f"{cor['fundo_tela']} m-0 p-0").style("font-family: 'Roboto', sans-serif;")
    
    with ui.column().classes("w-full h-screen items-center justify-center"):
        ui.spinner('dots', size='lg').classes(f"{cor['destaque']} mb-4")
        ui.label("VALIDANDO CREDENCIAIS...").classes(f"text-[11px] font-black {cor['texto_secundario']} tracking-widest uppercase")

    async def processar_autenticacao():
        try:
            await ui.context.client.connected()
            url_completa = await ui.run_javascript('window.location.href', timeout=5.0)
            hash_fragment = await ui.run_javascript('window.location.hash', timeout=5.0)
            
            if 'error=' in url_completa:
                ui.notify("Falha na autenticação.", type="negative", position="top")
                await asyncio.sleep(2)
                ui.navigate.to('/login')
                return

            if '?code=' in url_completa:
                parsed_url = urlparse(url_completa)
                code = parse_qs(parsed_url.query).get('code', [None])[0]
                if code:
                    sessao_resp = supabase.auth.exchange_code_for_session({"auth_code": code})
                    sessao = sessao_resp.session if hasattr(sessao_resp, 'session') else sessao_resp
                    email_usuario = sessao.user.email
                else:
                    raise Exception("Código não extraído.")
            elif hash_fragment and 'access_token' in hash_fragment:
                params = dict(parse_qsl(hash_fragment.lstrip('#')))
                access_token = params.get('access_token')
                refresh_token = params.get('refresh_token')
                sessao = supabase.auth.set_session(access_token, refresh_token)
                email_usuario = sessao.user.email
            else:
                ui.notify("Falha na receção dos dados.", type="negative", position="top")
                await asyncio.sleep(2)
                ui.navigate.to('/login')
                return

            resposta = supabase.table("tb_usuarios_permitidos").select("*").eq("email", email_usuario).execute()
            
            if not resposta.data:
                ui.notify("Acesso Negado: Utilizador não autorizado.", type="negative", position="top")
                supabase.auth.sign_out()
                await asyncio.sleep(2)
                ui.navigate.to('/login')
                return
                
            utilizador = resposta.data[0]
            
            if not utilizador['ativo']:
                ui.notify("Acesso Bloqueado.", type="negative", position="top")
                supabase.auth.sign_out()
                await asyncio.sleep(2)
                ui.navigate.to('/login')
                return
                
            app.storage.user['autenticado'] = True
            app.storage.user['email'] = email_usuario
            app.storage.user['nome'] = utilizador['nome']
            app.storage.user['cargo'] = utilizador['cargo']
            app.storage.user['tema_preferido'] = utilizador.get('tema_preferido') or 'PADRAO'
            
            ui.notify(f"Bem-vindo, {utilizador['nome']}.", type="positive", position="top")
            await ui.run_javascript('window.history.replaceState({}, document.title, "/");')
            ui.navigate.to('/')
            
        except Exception as e:
            print(f"[Erro] {e}")
            ui.notify("Erro técnico de autenticação.", type="negative", position="top")
            await asyncio.sleep(3)
            ui.navigate.to('/login')

    ui.timer(1.0, processar_autenticacao, once=True)