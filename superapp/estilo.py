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


    /* cabeçalho enxuto */
    .sa-ola {{ font-size: 1.25rem; color: {AZUL_ESCURO}; padding-top: 6px; }}
    div.stButton > button[kind="secondary"][data-testid] {{ }}

    /* cards de resumo (topo da Início) — botões pintados como cards, um por linha */
    [class*="st-key-card_"] button {{
        height: 58px; min-height: 58px; border: none; border-radius: 14px; color: white !important;
        text-align: left; justify-content: flex-start; padding: 4px 16px; margin-bottom: 0;
        box-shadow: 0 4px 14px rgba(0,0,0,0.12); white-space: normal;
    }}
    .st-key-card_conta button {{ background: linear-gradient(135deg, #EC7000 0%, #D25E00 100%); }}
    .st-key-card_cartao button {{ background: linear-gradient(135deg, #003A70 0%, #00264D 100%); }}
    .st-key-card_inv button {{ background: linear-gradient(135deg, #3A3D42 0%, #1E2024 100%); }}
    .st-key-card_cred button {{ background: linear-gradient(135deg, #1F5BA8 0%, #123F7A 100%); }}
    .st-key-card_seg button {{ background: linear-gradient(135deg, #5A6B7D 0%, #3B4856 100%); }}
    [class*="st-key-card_"] button:hover {{ filter: brightness(1.08); color: white !important; border: none; }}
    [class*="st-key-card_"] button > div, [class*="st-key-card_"] button > div > span, [class*="st-key-card_"] button [data-testid="stMarkdownContainer"] {{ width: 100%; display: block; }}
    [class*="st-key-card_"] button p {{
        color: white !important; margin: 0; display: grid; grid-template-columns: 1fr auto; grid-template-rows: auto auto;
        column-gap: 12px; align-items: center; overflow: visible; white-space: normal; text-overflow: clip; line-height: 1.2;
        font-size: 0.92rem;
    }}
    [class*="st-key-card_"] button em {{
        grid-column: 1; grid-row: 1; font-style: normal; font-size: 0.76rem; font-weight: 700; letter-spacing: 0.08em; opacity: 0.95;
    }}
    [class*="st-key-card_"] button strong {{
        grid-column: 2; grid-row: 1 / span 2; font-size: 1.65rem; font-weight: 800; white-space: nowrap; justify-self: end;
    }}
    [class*="st-key-card_"] button p::after {{ content: ""; }}
    /* cards mais próximos entre si (o Streamlit põe 1rem entre elementos) */
    [class*="st-key-card_"] {{ margin-bottom: -8px; }}

    /* linhas de alerta com ação (vencida, autorizações, vencimentos): mesmo esquadro e alinhamento */
    [class*="st-key-acao_"] {{
        background: white; border: 1px solid #E6E8EE; border-left: 5px solid #C9CDD4; border-radius: 14px;
        padding: 8px 10px 8px 12px; margin-bottom: -6px; min-height: 56px; box-sizing: border-box;
    }}
    .st-key-acao_vencida {{ background: #ECEDEF; border-color: #DADCE0; border-left-color: #8A8F98; margin-top: 4px; }}
    [class*="st-key-acao_compra_"] {{ background: #FFF6EE; border-color: #FBDDC2; border-left-color: {LARANJA}; }}
    [class*="st-key-acao_"] [data-testid="stMarkdownContainer"], [class*="st-key-acao_"] .stMarkdown {{ margin: 0 !important; }}
    [class*="st-key-acao_"] [data-testid="stElementContainer"] {{ margin: 0 !important; }}
    .sa-acao-txt {{ min-width: 0; line-height: 1.3; }}
    .sa-acao-txt .titulo {{ font-weight: 700; color: {AZUL_ESCURO}; font-size: 0.9rem; }}
    .sa-acao-txt .sub {{ color: #6B717B; font-size: 0.78rem; }}
    .sa-acao-txt.cinza .titulo {{ color: #4A4F57; }}
    [class*="st-key-acao_"] button {{
        min-height: 32px; height: 32px; padding: 0 14px; font-size: 0.82rem; border-radius: 999px !important; white-space: nowrap;
    }}
    [class*="st-key-acao_"] button[kind="secondary"] {{ background: white; border: 1.5px solid #B9C3D6; color: {AZUL_ESCURO}; }}
    .sa-secao {{ color: {AZUL_ESCURO}; font-weight: 700; font-size: 0.95rem; margin: 10px 0 4px 2px; }}

    /* Lia embutida na Início: fundo sutil e borda pontilhada separam o chat dos menus */
    .st-key-lia_box {{
        background: #F5F7FB; border: 1.5px dashed #B9C3D6; border-radius: 16px; padding: 8px 12px 10px 12px; margin-top: 6px;
    }}
    .st-key-lia_box [data-testid="stChatInput"] {{ background: white; }}
    .sa-lia-titulo {{ color: {AZUL_ESCURO}; font-size: 0.95rem; margin: 2px 0 2px 2px; }}

    /* dobra: o restante da Início começa abaixo do visor inicial */
    .sa-dobra {{
        margin-top: 20vh; padding-top: 10px; border-top: 1px solid #E6E8EE;
        color: #7A8391; font-size: 0.8rem; text-align: center;
    }}

    /* faixa fina de saldo nas demais telas */
    .sa-faixa {{
        background: {CINZA}; border-radius: 12px; padding: 8px 14px; font-size: 0.9rem; color: {AZUL_ESCURO};
        display: flex; justify-content: space-between; margin-bottom: 6px;
    }}

    /* popover de perfil */
    [data-testid="stPopover"] button {{ border-radius: 12px; }}


    /* no celular o Streamlit empilha as colunas; aqui o cabeçalho e os cards ficam lado a lado */
    @media (max-width: 640px) {{
        [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: 8px !important; }}
        [data-testid="stColumn"] {{ min-width: 0 !important; flex: 1 1 0 !important; }}
        [class*="st-key-card_"] button strong {{ font-size: 1.45rem; }}
        div.stButton > button {{ padding-left: 6px; padding-right: 6px; }}
    }}

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
