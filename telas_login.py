from urllib.parse import parse_qsl, urlparse, parse_qs
from nicegui import ui, app
import config
from supabase import create_client, Client, ClientOptions
import asyncio

# Desliga o PKCE e força o Fluxo Implícito (Padrão Ouro do nosso Backend)
opcoes = ClientOptions(flow_type="implicit")
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY, options=opcoes)

def desenhar_ecra_login():
    # Fonte Roboto e fundo padrão do NeDiretor
    ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;600;800;900&display=swap" rel="stylesheet">')
    ui.query('body').classes('bg-slate-50 m-0 p-0').style("font-family: 'Roboto', sans-serif;")
    
    with ui.column().classes("w-full h-screen items-center justify-center p-4"):
        # Card respeitando o rounded-2xl, shadow-sm e bordas suaves dos seus módulos
        with ui.card().classes("w-full max-w-sm p-8 rounded-2xl shadow-lg border border-cyan-100 bg-white items-center text-center gap-6"):
            
            with ui.column().classes("items-center gap-1 w-full"):
                ui.icon("admin_panel_settings", size="3xl").classes("text-cyan-600 mb-2")
                # Título usando o mesmo gradiente do main.py
                ui.label("NeDiretor").classes("text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-500 to-emerald-400 tracking-tighter")
                ui.label("ACESSO RESTRITO").classes("text-[10px] font-black text-slate-400 tracking-widest uppercase")

            ui.separator().classes("w-full bg-slate-100 my-2")

            def iniciar_login_google():
                resposta = supabase.auth.sign_in_with_oauth({
                    "provider": "google",
                    "options": {"redirect_to": "https://prime7.onrender.com/autenticacao"}
                })
                ui.navigate.to(resposta.url)

            def iniciar_login_microsoft():
                resposta = supabase.auth.sign_in_with_oauth({
                    "provider": "azure",
                    "options": {
                        "redirect_to": "https://prime7.onrender.com/autenticacao",
                        "scopes": "email"
                    }
                })
                ui.navigate.to(resposta.url)

            with ui.column().classes("w-full gap-3 mt-2"):
                # Botão Google: Clean, hover em tons de cyan (padrão do painel)
                ui.button("CONTINUAR COM GOOGLE", icon="login", on_click=iniciar_login_google)\
                    .classes("w-full bg-white border border-slate-200 text-slate-600 text-[11px] font-black tracking-widest rounded-xl py-3.5 hover:border-cyan-300 hover:bg-cyan-50 hover:text-cyan-800 transition-all")\
                    .props("unelevated text-color=slate-600")
                
                # Botão Microsoft: Clean, hover em tons de índigo
                ui.button("CONTINUAR COM MICROSOFT", icon="window", on_click=iniciar_login_microsoft)\
                    .classes("w-full bg-white border border-slate-200 text-slate-600 text-[11px] font-black tracking-widest rounded-xl py-3.5 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-800 transition-all")\
                    .props("unelevated text-color=slate-600")
                
            ui.label("Protected by Supabase Auth").classes("text-[9px] text-slate-400 tracking-widest mt-2 uppercase")

# =========================================================================================
# A CATRACA / ROTA DE VERIFICAÇÃO 
# =========================================================================================
def validar_regresso_google():
    ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;600;800;900&display=swap" rel="stylesheet">')
    ui.query('body').classes('bg-slate-50 m-0 p-0').style("font-family: 'Roboto', sans-serif;")
    
    with ui.column().classes("w-full h-screen items-center justify-center"):
        ui.spinner('dots', size='lg', color='cyan-600').classes("mb-4")
        ui.label("VALIDANDO CREDENCIAIS...").classes("text-[11px] font-black text-slate-500 tracking-widest uppercase")

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
            
            ui.notify(f"Bem-vindo, {utilizador['nome']}.", type="positive", position="top")
            await ui.run_javascript('window.history.replaceState({}, document.title, "/");')
            ui.navigate.to('/')
            
        except Exception as e:
            print(f"[Erro] {e}")
            ui.notify("Erro técnico de autenticação.", type="negative", position="top")
            await asyncio.sleep(3)
            ui.navigate.to('/login')

    ui.timer(1.0, processar_autenticacao, once=True)