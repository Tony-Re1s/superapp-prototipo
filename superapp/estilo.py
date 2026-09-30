"""Identidade visual do protótipo: laranja + azul-marinho, cara de app de banco."""
import streamlit as st

LARANJA = "#EC7000"
LARANJA_ESCURO = "#C25C00"
AZUL = "#003399"
AZUL_ESCURO = "#00226B"
CINZA = "#F4F5F7"
TEXTO = "#1F2430"
VERDE = "#1B8A4A"
VERMELHO = "#C62828"

CSS = f"""
<style>
    /* container estreito, como uma tela de celular */
    .block-container {{
        max-width: 560px;
        padding-top: 1.2rem;
        padding-bottom: 4rem;
    }}
    /* a barra do Streamlit fica por cima da primeira linha do menu e rouba os cliques — some com ela */
    header[data-testid="stHeader"] {{ display: none; }}
    [data-testid="stAppViewContainer"] > .main {{ padding-top: 0; }}
    #MainMenu, footer {{ visibility: hidden; }}
    [data-testid="stSidebar"] {{ display: none; }}

    h1, h2, h3 {{ color: {AZUL_ESCURO}; letter-spacing: -0.01em; }}

    .sa-topo {{
        background: linear-gradient(135deg, {LARANJA} 0%, {LARANJA_ESCURO} 100%);
        color: white; border-radius: 18px; padding: 18px 20px 16px 20px; margin-bottom: 12px;
        box-shadow: 0 6px 18px rgba(236,112,0,0.25);
    }}
    .sa-topo .marca {{ font-weight: 800; font-size: 1.15rem; letter-spacing: 0.02em; }}
    .sa-topo .marca span {{ background: {AZUL}; padding: 2px 8px; border-radius: 8px; margin-left: 6px; font-size: 0.8rem; }}
    .sa-topo .ola {{ font-size: 0.95rem; opacity: 0.95; margin-top: 6px; }}
    .sa-topo .saldo-rotulo {{ font-size: 0.78rem; opacity: 0.9; margin-top: 14px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .sa-topo .saldo {{ font-size: 2rem; font-weight: 800; line-height: 1.1; }}
    .sa-topo .conta {{ font-size: 0.78rem; opacity: 0.85; margin-top: 4px; }}

    .sa-card {{
        background: white; border: 1px solid #E6E8EE; border-radius: 16px;
        padding: 14px 16px; margin-bottom: 10px;
    }}
    .sa-card .titulo {{ font-weight: 700; color: {AZUL_ESCURO}; margin-bottom: 4px; }}
    .sa-card .sub {{ color: #5B6472; font-size: 0.88rem; }}
    .sa-card.alerta {{ border-left: 5px solid {LARANJA}; background: #FFF6EE; }}
    .sa-card.perigo {{ border-left: 5px solid {VERMELHO}; background: #FDECEC; }}
    .sa-card.ok {{ border-left: 5px solid {VERDE}; background: #EDF7F0; }}
    .sa-card.ia {{ border-left: 5px solid {AZUL}; background: #EEF2FB; }}

    .sa-linha {{
        display: flex; justify-content: space-between; align-items: center;
        padding: 9px 2px; border-bottom: 1px solid #EEF0F4; font-size: 0.93rem;
    }}
    .sa-linha:last-child {{ border-bottom: none; }}
    .sa-linha .desc {{ color: {TEXTO}; }}
    .sa-linha .meta {{ color: #7A8391; font-size: 0.78rem; }}
    .sa-linha .val {{ font-weight: 700; white-space: nowrap; }}
    .sa-linha .val.neg {{ color: {TEXTO}; }}
    .sa-linha .val.pos {{ color: {VERDE}; }}

    .sa-pill {{
        display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600;
        background: {CINZA}; color: {AZUL_ESCURO}; margin-right: 4px;
    }}
    .sa-pill.laranja {{ background: #FFE7D1; color: {LARANJA_ESCURO}; }}
    .sa-pill.vermelho {{ background: #FDE0E0; color: {VERMELHO}; }}
    .sa-pill.verde {{ background: #DDF2E4; color: {VERDE}; }}
    .sa-pill.azul {{ background: #DCE4F7; color: {AZUL}; }}

    .sa-aviso {{
        font-size: 0.74rem; color: #7A8391; text-align: center; margin-top: 18px; line-height: 1.4;
    }}

    /* navegação em pílulas */
    div[data-testid="stPills"] {{ margin-bottom: 4px; }}
    div[data-testid="stPills"] button {{ border-radius: 999px !important; font-size: 0.85rem; }}
    div[data-testid="stPills"] button[aria-checked="true"], div[data-testid="stPills"] button[data-selected="true"] {{
        background: {AZUL} !important; color: white !important; border-color: {AZUL} !important;
    }}

    /* botões primários laranja */
    div.stButton > button[kind="primary"] {{
        background: {LARANJA}; border-color: {LARANJA}; color: white; border-radius: 12px; font-weight: 700;
    }}
    div.stButton > button[kind="primary"]:hover {{ background: {LARANJA_ESCURO}; border-color: {LARANJA_ESCURO}; }}
    div.stButton > button {{ border-radius: 12px; }}

    /* atalhos da tela inicial */
    .sa-atalho button {{ height: 72px !important; white-space: pre-line; }}

    [data-testid="stMetricValue"] {{ color: {AZUL_ESCURO}; }}
    .stProgress > div > div > div > div {{ background: {LARANJA}; }}
    [data-testid="stChatMessage"] {{ border-radius: 14px; }}
</style>
"""


def aplicar_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def topo(nome: str, saldo_txt: str, conta: str, mostrar_saldo: bool) -> None:
    saldo = saldo_txt if mostrar_saldo else "R$ ••••••"
    st.markdown(
        f"""
        <div class="sa-topo">
            <div class="marca">SUPERAPP <span>protótipo</span></div>
            <div class="ola">Olá, {nome} 👋</div>
            <div class="saldo-rotulo">Saldo disponível</div>
            <div class="saldo">{saldo}</div>
            <div class="conta">{conta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(titulo: str, sub: str = "", tipo: str = "") -> None:
    st.markdown(
        f'<div class="sa-card {tipo}"><div class="titulo">{titulo}</div>'
        f'<div class="sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def linhas(itens: list[tuple[str, str, str, bool]]) -> None:
    """itens: (descrição, meta, valor formatado, positivo?)"""
    html = ['<div class="sa-card">']
    for desc, meta, val, pos in itens:
        cls = "pos" if pos else "neg"
        html.append(
            f'<div class="sa-linha"><div><div class="desc">{desc}</div><div class="meta">{meta}</div></div>'
            f'<div class="val {cls}">{val}</div></div>'
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def pill(texto: str, cor: str = "") -> str:
    return f'<span class="sa-pill {cor}">{texto}</span>'


def rodape() -> None:
    st.markdown(
        '<div class="sa-aviso">Protótipo acadêmico — FIAP Pós-Tech, Tech Challenge Fase 03. '
        "Banco fictício. Nenhum dado real é coletado além da sua avaliação anônima. "
        "Não há biometria: a confirmação de segurança usa uma senha fictícia (qualquer 4 dígitos).</div>",
        unsafe_allow_html=True,
    )
