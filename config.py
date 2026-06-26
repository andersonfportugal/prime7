import os

EMPRESA = {
    "nome_filial": "Drogaria Portugal",
    "cnpj": "22.128.997/0001-00",
    "telefone": "(21) 99381-2257"
}

SUPABASE_URL = "https://qfzhcbywfwmorrgkcfvu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFmemhjYnl3Zndtb3JyZ2tjZnZ1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA1ODY0ODUsImV4cCI6MjA5NjE2MjQ4NX0.BcAzvdYapgb990OxBCzp5vREObefqIZsNpZomwtb2JE"

# Descobre automaticamente se está no Render (Render sempre tem a variável 'RENDER' configurada internamente)
if "RENDER" in os.environ:
    AMBIENTE_ATUAL = "NUVEM"
else:
    AMBIENTE_ATUAL = "LOCAL"

if AMBIENTE_ATUAL == "LOCAL":
    URL_SISTEMA = "http://localhost:8080"
else:
    URL_SISTEMA = "https://prime7.onrender.com" # Ou o link real que o Render te der

IP = "191.252.204.7"
BANCO = "drogarialegitimasaojoaoepenha_esc"
USUARIO = "ediretor"
SENHA = "JTC1fPn8hZLBLFDS"

# GRUPO 1: TABELAS TRANSACIONAIS (Fatiadas por Mês/Ano devido ao tamanho)
TABELAS_GRUPO_1 = {
    "venda": {
        "colunas": "id, status, usuarioid, datahoraabertura, datahorafechamento, valortotal, valortroco, unidadenegocioid",
        "campo_data": "datahoraabertura"
    },
    "itemvenda": {
        "colunas": "id, vendaid, status, embalagemid, quantidade, valorunitario, valortotal, datahora, unidadenegocioid, itemorcamentoid",
        "campo_data": "datahora"
    },
    "pagamentovenda": {
        "colunas": "id, vendaid, status, tipo, formapagamentoid, valor, datahora, unidadenegocioid",
        "campo_data": "datahora"
    },
    "notafiscal": {
        "colunas": "id, unidadenegocioid, fornecedorid, datahoraemissao, status, valortotal, totalproduto, totaldesconto, numero",
        "campo_data": "datahoraemissao"
    },
    "entrega": {
        "colunas": "id, orcamentoid, status, usuarioinicialid, datahorainicial, datahoraprogramada, datahorafinal, taxaentrega",
        "campo_data": "datahorainicial"
    }
}

# GRUPO 2: TABELAS DIMENSIONAIS (Cadastros - Carga Total / Full Load)
TABELAS_GRUPO_2 = {
    "produto": "SELECT id, nome, status FROM produto",
    "embalagem": "SELECT id, produtoid, codigobarras, precovenda FROM embalagem",
    "pessoa": "SELECT id, nome, cnpj, cpf FROM pessoa",
    "fornecedor": "SELECT id, pessoaid, status FROM fornecedor",
    "classificacao": "SELECT id, nome FROM classificacao",
    "classificacaoproduto": "SELECT id, produtoid, classificacaoid FROM classificacaoproduto",
    "unidadenegocio": "SELECT id, nome, nomefantasia FROM unidadenegocio",
    "formapagamento": "SELECT id, nome, tipo FROM formapagamento",
    "usuario": "SELECT id, apelido, unidadenegocioid FROM usuario",
    "grupousuario": "SELECT id, nome FROM grupousuario"
}

# CONFIGURAÇÃO DE DATAS DE EXTRAÇÃO PADRÃO
ANOS_EXTRACAO = [2021, 2022, 2023, 2024, 2025, 2026]