"""Superapp — protótipo de banco digital centrado no cliente (Tech Challenge FIAP, Fase 03).

Execute localmente com:  streamlit run app.py
"""
import streamlit as st

from superapp import estilo, telas

st.set_page_config(page_title="Superapp — protótipo", page_icon="🟠", layout="centered",
                   initial_sidebar_state="collapsed")
estilo.aplicar_css()

# rota "?admin=1" abre o painel de resultados do grupo
if st.query_params.get("admin") == "1":
    telas.tela_resultados()
    st.stop()

if "persona" not in st.session_state:
    telas.tela_entrada()
    st.stop()

# navegação — o valor do widget é sincronizado com st.session_state.tela ANTES de o widget ser criado,
# assim tanto o clique na pílula quanto a navegação por código (atalhos, assistente) funcionam.
opcoes = [f"{telas.ICONES[t]} {t}" for t in telas.TELAS]
st.session_state["nav"] = f"{telas.ICONES[st.session_state.tela]} {st.session_state.tela}"


def _navegar():
    escolha = st.session_state.get("nav")
    if escolha:
        telas.ir_para(escolha.split(" ", 1)[1])


st.pills("Navegação", opcoes, key="nav", on_change=_navegar, label_visibility="collapsed")

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
}[st.session_state.tela]()

st.divider()
c1, c2 = st.columns([3, 1])
with c1:
    if not st.session_state.get("avaliado"):
        if st.button("⭐ Terminou de explorar? Avalie o protótipo", width="stretch", type="primary"):
            telas.ir_para("Avalie")
            st.rerun()
with c2:
    if st.button("Sair", width="stretch"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
estilo.rodape()
