"""Superapp — protótipo de banco digital centrado no cliente (Tech Challenge FIAP, Fase 03).

Execute localmente com:  streamlit run app.py
"""
import streamlit as st

from superapp import estilo, telas

st.set_page_config(page_title="Superapp", page_icon="🟠", layout="centered",
                   initial_sidebar_state="collapsed")
estilo.aplicar_css()

# rota "?admin=1" abre o painel de resultados do grupo
if st.query_params.get("admin") == "1":
    telas.tela_resultados()
    st.stop()

if "persona" not in st.session_state:
    telas.tela_entrada()
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
# O valor do widget é sincronizado com ss.tela ANTES de o widget ser criado, assim tanto o toque na
# pílula quanto a navegação por código (cards, atalhos, assistente) funcionam.
telas_menu = telas.telas_disponiveis()
if ss.tela not in telas_menu:
    ss.tela = "Início"
opcoes = [f"{telas.ICONES[t]} {t}" for t in telas_menu]
ss["nav"] = f"{telas.ICONES[ss.tela]} {ss.tela}"


def _navegar():
    escolha = ss.get("nav")
    if escolha:
        telas.ir_para(escolha.split(" ", 1)[1])


st.pills("Navegação", opcoes, key="nav", on_change=_navegar, label_visibility="collapsed")

# ----------------------------------------------------------------------------- conteúdo
{
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
}[ss.tela]()

st.divider()
if not ss.get("avaliado") and ss.tela != "Avalie":
    if st.button("⭐ Terminou de explorar? Avalie o protótipo", width="stretch", type="primary"):
        telas.ir_para("Avalie")
        st.rerun()
estilo.rodape()
