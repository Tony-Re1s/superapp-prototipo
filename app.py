"""Superapp — protótipo de banco digital centrado no cliente (Tech Challenge FIAP, Fase 03).

Execute localmente com:  streamlit run app.py
"""
import importlib
import os

import streamlit as st

from superapp import biometria, dados, db, estilo, ia, telas

# O Streamlit Cloud às vezes republica o app.py mas mantém em memória versões antigas dos módulos do
# pacote (erro "AttributeError: module 'superapp.telas' has no attribute ..."). Recarrega cada módulo
# cujo arquivo mudou desde a última carga — dependências primeiro, telas por último.
for _mod in (dados, db, estilo, ia, biometria, telas):
    _mtime = os.path.getmtime(_mod.__file__)
    if getattr(_mod, "_sa_mtime", None) != _mtime:
        if hasattr(_mod, "_sa_mtime"):
            importlib.reload(_mod)
        _mod._sa_mtime = _mtime
if not hasattr(telas, "tela_pre_login"):  # módulos antigos carregados antes desta checagem existir
    for _mod in (dados, db, estilo, ia, biometria, telas):
        importlib.reload(_mod)
        _mod._sa_mtime = os.path.getmtime(_mod.__file__)

st.set_page_config(page_title="Superapp", page_icon="🟠", layout="centered",
                   initial_sidebar_state="collapsed")
estilo.aplicar_css()

# rota "?admin=1" abre o painel de resultados do grupo
if st.query_params.get("admin") == "1":
    telas.tela_resultados()
    st.stop()

# Estado do cliente fictício (perfil padrão). Antes do login aparece a tela de entrada:
# atalhos rápidos (rosto ou senha e abre direto a aba) e a Lia por voz, sem entrar no app.
if "persona" not in st.session_state:
    telas.iniciar_estado("padrao")
    telas.evento("Entrada", "sessao", {})

if not st.session_state.get("logado"):
    telas.tela_pre_login()
    st.stop()

ss = st.session_state

# ----------------------------------------------------------------------------- cabeçalho
telas.cabecalho()

# ----------------------------------------------------------------------------- cards (só na Início)
if ss.tela == "Início":
    telas.cards_resumo()
else:
    telas.faixa_saldo()

# ----------------------------------------------------------------------------- menu (zona do polegar)
# O menu é montado pelos produtos que a pessoa tem; conta corrente é fixa.
# Cada bloco chama ir_para no clique; a navegação por código (cards, atalhos, Lia) usa o mesmo ir_para.
telas_menu = telas.telas_disponiveis()
FORA_DO_MENU = {"Avalie"}  # telas abertas por botão, sem pílula no menu
if ss.tela not in telas_menu and ss.tela not in FORA_DO_MENU:
    ss.tela = "Início"
telas.menu_app(telas_menu)  # blocos com ícone, no desenho da tela de entrada

# ----------------------------------------------------------------------------- conteúdo
TELAS = {
    "Início": telas.tela_inicio,
    "Pix": telas.tela_pix,
    "Cartão": telas.tela_cartao,
    "Pagar": telas.tela_pagar,
    "Extrato": telas.tela_extrato,
    "Investir": telas.tela_investir,
    "Gastos": telas.tela_gastos,
    "Avisos": telas.tela_avisos,
    "Assistente": telas.tela_assistente,
    "Segurança": telas.tela_seguranca,
    "Avalie": telas.tela_avaliar,
    "Crédito": telas.tela_credito,
    "Seguros": telas.tela_seguros,
}
if ss.tela in telas.PROTEGIDAS and ss.get("bio_liberada") != ss.tela:
    telas.tela_biometria(ss.tela)  # abre o menu e verifica o rosto (ou senha)
else:
    TELAS[ss.tela]()

st.divider()
if not ss.get("avaliado") and ss.tela != "Avalie":
    if st.button("⭐ Terminou de explorar? Avalie o protótipo", width="stretch", type="primary"):
        telas.ir_para("Avalie")
        st.rerun()
estilo.rodape()
