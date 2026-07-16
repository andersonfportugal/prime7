from nicegui import app

paletas = {
    "PADRAO": {
        "nome_amigavel": "Claro",
        "descricao": "O visual original limpo e semântico.",
        # --- CASCA GLOBAL ---
        "fundo_tela": "bg-slate-50",
        "fundo_card": "bg-white",
        "texto_principal": "text-slate-700",
        "texto_secundario": "text-slate-500",
        "destaque": "text-cyan-800",
        "borda": "border-cyan-100",
        "gradiente_titulo": "from-cyan-500 to-emerald-400",
        
        # --- TOKENS DOS CARDS E TABELAS (CORES ORIGINAIS EXATAS) ---
        "vendas_bg": "bg-emerald-50", "vendas_borda": "border-slate-200", "vendas_titulo": "text-emerald-800", "vendas_destaque": "text-emerald-600",
        "tab_vend_head": "bg-emerald-100", "tab_vend_txt": "text-emerald-900", "tab_vend_bg": "bg-emerald-50/30",
        
        "compras_bg": "bg-blue-50", "compras_borda": "border-slate-200", "compras_titulo": "text-blue-800", "compras_destaque": "text-blue-600",
        "tab_comp_head": "bg-blue-100", "tab_comp_txt": "text-blue-900", "tab_comp_bg": "bg-blue-50/30",
        
        "boletos_bg": "bg-amber-50/50", "boletos_borda": "border-slate-200", "boletos_titulo": "text-amber-800", "boletos_destaque": "text-amber-600",
        "tab_bol_head": "bg-amber-100", "tab_bol_txt": "text-amber-900", "tab_bol_bg": "bg-amber-50/30",
        
        "despesas_bg": "bg-rose-50/50", "despesas_borda": "border-slate-200", "despesas_titulo": "text-rose-800", "despesas_destaque": "text-rose-600",
        "tab_desp_head": "bg-rose-100", "tab_desp_txt": "text-rose-900", "tab_desp_bg": "bg-rose-50/30",

        "tab_dia_head": "bg-slate-200", "tab_dia_txt": "text-slate-700", "tab_dia_bg": "bg-white"
    },
    
    "LUXO": {
        "nome_amigavel": "Escuro",
        "descricao": "Base chumbo elegante com detalhes em ouro, sem misturar cores.",
        # --- CASCA GLOBAL ---
        "fundo_tela": "bg-[#121212]",
        "fundo_card": "bg-[#1E1E1E]",
        "texto_principal": "text-[#F3F4F6]",
        "texto_secundario": "text-[#9CA3AF]",
        "destaque": "text-[#D4AF37]",
        "borda": "border-[#333333]",
        "gradiente_titulo": "from-[#D4AF37] to-[#AA8C2C]",

        # --- TOKENS UNIFICADOS (Remove o efeito colorido dos blocos) ---
        "vendas_bg": "bg-[#1E1E1E]", "vendas_borda": "border-[#333333]", "vendas_titulo": "text-[#F3F4F6]", "vendas_destaque": "text-[#D4AF37]",
        "tab_vend_head": "bg-[#2A2A2A]", "tab_vend_txt": "text-[#D4AF37]", "tab_vend_bg": "bg-[#1E1E1E]",
        
        "compras_bg": "bg-[#1E1E1E]", "compras_borda": "border-[#333333]", "compras_titulo": "text-[#F3F4F6]", "compras_destaque": "text-[#D4AF37]",
        "tab_comp_head": "bg-[#2A2A2A]", "tab_comp_txt": "text-[#D4AF37]", "tab_comp_bg": "bg-[#1E1E1E]",
        
        "boletos_bg": "bg-[#1E1E1E]", "boletos_borda": "border-[#333333]", "boletos_titulo": "text-[#F3F4F6]", "boletos_destaque": "text-[#D4AF37]",
        "tab_bol_head": "bg-[#2A2A2A]", "tab_bol_txt": "text-[#D4AF37]", "tab_bol_bg": "bg-[#1E1E1E]",
        
        "despesas_bg": "bg-[#1E1E1E]", "despesas_borda": "border-[#333333]", "despesas_titulo": "text-[#F3F4F6]", "despesas_destaque": "text-[#D4AF37]",
        "tab_desp_head": "bg-[#2A2A2A]", "tab_desp_txt": "text-[#D4AF37]", "tab_desp_bg": "bg-[#1E1E1E]",

        "tab_dia_head": "bg-[#2A2A2A]", "tab_dia_txt": "text-[#9CA3AF]", "tab_dia_bg": "bg-[#121212]"
    },

    "ECLIPSE": {
        "nome_amigavel": "Eclipse",
        "descricao": "Preto absoluto com tipografia de alto contraste e ouro pálido.",
        # --- CASCA GLOBAL ---
        "fundo_tela": "bg-[#000000]",
        "fundo_card": "bg-[#0A0A0A]",
        "texto_principal": "text-[#FFFFFF]",
        "texto_secundario": "text-[#737373]",
        "destaque": "text-[#FCD34D]",
        "borda": "border-[#262626]",
        "gradiente_titulo": "from-[#FFFFFF] to-[#FCD34D]",

        # --- TOKENS UNIFICADOS ECLIPSE ---
        "vendas_bg": "bg-[#0A0A0A]", "vendas_borda": "border-[#262626]", "vendas_titulo": "text-[#FFFFFF]", "vendas_destaque": "text-[#FCD34D]",
        "tab_vend_head": "bg-[#171717]", "tab_vend_txt": "text-[#FFFFFF]", "tab_vend_bg": "bg-[#0A0A0A]",
        
        "compras_bg": "bg-[#0A0A0A]", "compras_borda": "border-[#262626]", "compras_titulo": "text-[#FFFFFF]", "compras_destaque": "text-[#FCD34D]",
        "tab_comp_head": "bg-[#171717]", "tab_comp_txt": "text-[#FFFFFF]", "tab_comp_bg": "bg-[#0A0A0A]",
        
        "boletos_bg": "bg-[#0A0A0A]", "boletos_borda": "border-[#262626]", "boletos_titulo": "text-[#FFFFFF]", "boletos_destaque": "text-[#FCD34D]",
        "tab_bol_head": "bg-[#171717]", "tab_bol_txt": "text-[#FFFFFF]", "tab_bol_bg": "bg-[#0A0A0A]",
        
        "despesas_bg": "bg-[#0A0A0A]", "despesas_borda": "border-[#262626]", "despesas_titulo": "text-[#FFFFFF]", "despesas_destaque": "text-[#FCD34D]",
        "tab_desp_head": "bg-[#171717]", "tab_desp_txt": "text-[#FFFFFF]", "tab_desp_bg": "bg-[#0A0A0A]",

        "tab_dia_head": "bg-[#171717]", "tab_dia_txt": "text-[#737373]", "tab_dia_bg": "bg-[#000000]"
    },

    "OBSIDIAN": {
        "nome_amigavel": "Obsidian",
        "descricao": "Visual sóbrio inspirado em vidro vulcânico com realces em platina.",
        # --- CASCA GLOBAL ---
        "fundo_tela": "bg-[#0F1016]",
        "fundo_card": "bg-[#171923]",
        "texto_principal": "text-[#F7FAFC]",
        "texto_secundario": "text-[#A0AEC0]",
        "destaque": "text-[#CBD5E0]",
        "borda": "border-[#2D3748]",
        "gradiente_titulo": "from-[#EDF2F7] to-[#A0AEC0]",

        # --- TOKENS UNIFICADOS OBSIDIAN ---
        "vendas_bg": "bg-[#171923]", "vendas_borda": "border-[#2D3748]", "vendas_titulo": "text-[#F7FAFC]", "vendas_destaque": "text-[#CBD5E0]",
        "tab_vend_head": "bg-[#2D3748]", "tab_vend_txt": "text-[#F7FAFC]", "tab_vend_bg": "bg-[#171923]",
        
        "compras_bg": "bg-[#171923]", "compras_borda": "border-[#2D3748]", "compras_titulo": "text-[#F7FAFC]", "compras_destaque": "text-[#CBD5E0]",
        "tab_comp_head": "bg-[#2D3748]", "tab_comp_txt": "text-[#F7FAFC]", "tab_comp_bg": "bg-[#171923]",
        
        "boletos_bg": "bg-[#171923]", "boletos_borda": "border-[#2D3748]", "boletos_titulo": "text-[#F7FAFC]", "boletos_destaque": "text-[#CBD5E0]",
        "tab_bol_head": "bg-[#2D3748]", "tab_bol_txt": "text-[#F7FAFC]", "tab_bol_bg": "bg-[#171923]",
        
        "despesas_bg": "bg-[#171923]", "despesas_borda": "border-[#2D3748]", "despesas_titulo": "text-[#F7FAFC]", "despesas_destaque": "text-[#CBD5E0]",
        "tab_desp_head": "bg-[#2D3748]", "tab_desp_txt": "text-[#F7FAFC]", "tab_desp_bg": "bg-[#171923]",

        "tab_dia_head": "bg-[#2D3748]", "tab_dia_txt": "text-[#A0AEC0]", "tab_dia_bg": "bg-[#0F1016]"
    },
    "PINKIE": {
    "nome_amigavel": "Pinkie",
    "descricao": "Inspirado no Barbie Pink moderno, leve, limpo e agradável para uso prolongado.",

    # --- CASCA GLOBAL ---
    "fundo_tela": "bg-[#FAFAFC]",
    "fundo_card": "bg-white",

    "texto_principal": "text-slate-700",
    "texto_secundario": "text-slate-500",

    "destaque": "text-pink-600",

    "borda": "border-pink-100",

    "gradiente_titulo": "from-pink-500 to-rose-400",

    # VENDAS
    "vendas_bg": "bg-white",
    "vendas_borda": "border-pink-100",
    "vendas_titulo": "text-slate-700",
    "vendas_destaque": "text-pink-600",

    "tab_vend_head": "bg-pink-50",
    "tab_vend_txt": "text-pink-800",
    "tab_vend_bg": "bg-white",

    # COMPRAS
    "compras_bg": "bg-white",
    "compras_borda": "border-pink-100",
    "compras_titulo": "text-slate-700",
    "compras_destaque": "text-pink-600",

    "tab_comp_head": "bg-pink-50",
    "tab_comp_txt": "text-pink-800",
    "tab_comp_bg": "bg-white",

    # BOLETOS
    "boletos_bg": "bg-white",
    "boletos_borda": "border-pink-100",
    "boletos_titulo": "text-slate-700",
    "boletos_destaque": "text-pink-600",

    "tab_bol_head": "bg-pink-50",
    "tab_bol_txt": "text-pink-800",
    "tab_bol_bg": "bg-white",

    # DESPESAS
    "despesas_bg": "bg-white",
    "despesas_borda": "border-pink-100",
    "despesas_titulo": "text-slate-700",
    "despesas_destaque": "text-pink-600",

    "tab_desp_head": "bg-pink-50",
    "tab_desp_txt": "text-pink-800",
    "tab_desp_bg": "bg-white",

    "tab_dia_head": "bg-pink-50",
    "tab_dia_txt": "text-pink-700",
    "tab_dia_bg": "bg-white"
},
"NOITE_ESTRELADA": {
    "nome_amigavel": "Estrelas",
    "descricao": "Azul profundo inspirado em um céu estrelado.",

    "fundo_tela": "bg-[#0B1026]",
    "fundo_card": "bg-[#131C3D]",

    "texto_principal": "text-slate-100",
    "texto_secundario": "text-slate-400",

    "destaque": "text-amber-300",

    "borda": "border-[#24315F]",

    "gradiente_titulo": "from-amber-300 to-yellow-200",

    # VENDAS
    "vendas_bg": "bg-[#131C3D]",
    "vendas_borda": "border-[#24315F]",
    "vendas_titulo": "text-slate-100",
    "vendas_destaque": "text-amber-300",

    "tab_vend_head": "bg-[#1A2752]",
    "tab_vend_txt": "text-amber-200",
    "tab_vend_bg": "bg-[#131C3D]",

    # COMPRAS
    "compras_bg": "bg-[#131C3D]",
    "compras_borda": "border-[#24315F]",
    "compras_titulo": "text-slate-100",
    "compras_destaque": "text-amber-300",

    "tab_comp_head": "bg-[#1A2752]",
    "tab_comp_txt": "text-amber-200",
    "tab_comp_bg": "bg-[#131C3D]",

    # BOLETOS
    "boletos_bg": "bg-[#131C3D]",
    "boletos_borda": "border-[#24315F]",
    "boletos_titulo": "text-slate-100",
    "boletos_destaque": "text-amber-300",

    "tab_bol_head": "bg-[#1A2752]",
    "tab_bol_txt": "text-amber-200",
    "tab_bol_bg": "bg-[#131C3D]",

    # DESPESAS
    "despesas_bg": "bg-[#131C3D]",
    "despesas_borda": "border-[#24315F]",
    "despesas_titulo": "text-slate-100",
    "despesas_destaque": "text-amber-300",

    "tab_desp_head": "bg-[#1A2752]",
    "tab_desp_txt": "text-amber-200",
    "tab_desp_bg": "bg-[#131C3D]",

    "tab_dia_head": "bg-[#1A2752]",
    "tab_dia_txt": "text-slate-300",
    "tab_dia_bg": "bg-[#0B1026]"
}
}

def obter_cores():
    try:
        tema_escolhido = app.storage.user.get('tema_preferido', 'PADRAO')
        return paletas.get(tema_escolhido, paletas['PADRAO'])
    except Exception:
        return paletas['PADRAO']