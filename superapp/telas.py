"""Telas do protótipo. Cada função `tela_*` desenha uma tela completa."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from . import dados as D
from . import db, estilo, ia

TELAS = ["Início", "Pix", "Cartão", "Pagar", "Extrato", "Investir", "Gastos", "Avisos", "Assistente", "Segurança", "Avalie"]
ICONES = {"Início": "🏠", "Pix": "⚡", "Cartão": "💳", "Pagar": "🧾", "Extrato": "📄", "Investir": "📈",
          "Gastos": "🧭", "Avisos": "🔔", "Assistente": "💬", "Segurança": "🛡️", "Avalie": "⭐",
          "Crédito": "🏦", "Seguros": "☂️"}


# ----------------------------------------------------------------------------- estado
ASSISTENTE = "Lia"
MAX_PRODUTOS = 4  # cards na tela inicial, incluindo a conta corrente
PRODUTOS_OPCIONAIS = [("cartao", "Cartão de crédito"), ("investimentos", "Investimentos"),
                      ("credito", "Crédito pessoal"), ("seguros", "Seguros")]


def iniciar_estado(persona_id: str, nome: str = "") -> None:
    p = D.PERSONAS[persona_id]
    ss = st.session_state
    ss.persona = persona_id
    ss.nome = (nome or p["primeiro_nome"]).strip().split(" ")[0].capitalize()
    ss.sessao = ss.get("sessao") or uuid.uuid4().hex[:12]
    ss.mostrar_saldo = True
    ss.produtos = {"cartao": True, "investimentos": True, "credito": False, "seguros": False}
    ss.saldo = p["saldo"]
    ss.cartao_bloqueado = False
    ss.cartao_virtual = None
    ss.contas = [dict(c) for c in D.CONTAS_A_PAGAR[persona_id]]
    ss.extrato = D.gerar_extrato(persona_id)
    ss.fatura = D.gerar_fatura(persona_id)
    ss.fatura_paga = False
    ss.notificacoes = D.gerar_notificacoes(persona_id)
    ss.prefs_notif = dict(D.OFERTAS_PADRAO)
    ss.chat = []
    ss.fila_humano = None
    ss.pix_pendente = None
    ss.pagamento_pendente = None
    ss.limite_pix_noturno = 1000.0
    ss.modo_viagem = False
    ss.investimentos = [dict(i) for i in D.INVESTIMENTOS[persona_id]]
    ss.credito = {"pre_aprovado": p["salario"] * 4, "contratos": []}
    ss.inv_pendente = None
    ss.credito_pendente = None
    ss.boleto_pendente = None
    ss.agendamentos = []
    ss.comprovante_pendente = None
    ss.prefere_humano = False
    ss.contato_confianca = None
    ss.cartao_virtual_fixo = None
    ss.tela = "Início"
    ss.telas_visitadas = {"Início"}
    ss.avaliado = False
    ss.pix_confirmados = 0


def persona() -> dict:
    """Perfil da pessoa logada — dados da persona base com o nome informado no login."""
    p = dict(D.PERSONAS[st.session_state.persona])
    nome = st.session_state.get("nome") or p["primeiro_nome"]
    p["primeiro_nome"] = nome
    p["nome"] = nome
    p["chave_pix"] = f"{_norm_txt(nome)}@email.com"
    return p


def telas_disponiveis() -> list[str]:
    """Menu montado pelos produtos: conta corrente é fixa; cartão e investimentos, só se a pessoa tiver."""
    prod = st.session_state.get("produtos", {})
    telas = ["Início", "Pix", "Pagar", "Extrato"]
    if prod.get("cartao", True):
        telas.append("Cartão")
    if prod.get("investimentos", True):
        telas.append("Investir")
    if prod.get("credito", False):
        telas.append("Crédito")
    if prod.get("seguros", False):
        telas.append("Seguros")
    telas += ["Gastos", "Avisos", "Assistente", "Segurança"]  # Avalie fica só no botão do fim da tela
    return telas


def ir_para(tela: str) -> None:
    st.session_state.tela = tela
    st.session_state.telas_visitadas.add(tela)


def evento(tela: str, acao: str, detalhe: dict | None = None) -> None:
    db.registrar_evento(st.session_state.sessao, st.session_state.persona, tela, acao, detalhe)


def gastos_por_categoria(dias: int = 30) -> dict[str, float]:
    df = st.session_state.extrato
    ini = pd.Timestamp(D.HOJE - timedelta(days=dias))
    df = df[(pd.to_datetime(df["data"]) >= ini) & (df["valor"] < 0)]
    g = df.groupby("categoria")["valor"].sum().abs().sort_values(ascending=False)
    return {k: round(float(v), 2) for k, v in g.items()}


def contexto_ia() -> dict:
    return {
        "persona": persona(),
        "saldo": st.session_state.saldo,
        "contas": st.session_state.contas,
        "contatos": D.CONTATOS_PIX[st.session_state.persona],
        "gastos_categoria": gastos_por_categoria(),
        "cartao_bloqueado": st.session_state.cartao_bloqueado,
        "assistente": ASSISTENTE,
        "investimentos": st.session_state.investimentos,
        "credito_disponivel": credito_disponivel(),
        "divida": divida_total(),
        "contratos": st.session_state.credito["contratos"],
        "produtos": st.session_state.produtos,
        "nome": st.session_state.nome,
        "prefere_humano": st.session_state.prefere_humano,
        "descricoes": sorted(set(st.session_state.extrato["descricao"].tolist())),
        "contato_confianca": st.session_state.contato_confianca,
    }


def lancar(descricao: str, valor: float, categoria: str) -> None:
    """Registra movimento no extrato e ajusta saldo."""
    ss = st.session_state
    ss.saldo = round(ss.saldo + valor, 2)
    nova = pd.DataFrame([{"data": D.HOJE, "descricao": descricao, "valor": valor, "categoria": categoria,
                          "tipo": "Crédito" if valor > 0 else "Débito", "saldo": ss.saldo}])
    ss.extrato = pd.concat([ss.extrato, nova], ignore_index=True)


def fatura_total() -> float:
    return 0.0 if st.session_state.fatura_paga else persona()["fatura_atual"]


def investido_total() -> float:
    return sum(i["valor"] for i in st.session_state.investimentos)


def credito_disponivel() -> float:
    c = st.session_state.credito
    return max(c["pre_aprovado"] - sum(x["saldo_devedor"] for x in c["contratos"]), 0.0)


def divida_total() -> float:
    return sum(x["saldo_devedor"] for x in st.session_state.credito["contratos"])


def ativar_produto(chave: str) -> bool:
    """Liga um produto respeitando o limite de cards. Devolve True se ficou ativo."""
    prod = st.session_state.produtos
    if prod.get(chave):
        return True
    if sum(1 for v in prod.values() if v) >= MAX_PRODUTOS - 1:
        return False
    prod[chave] = True
    return True


def valor(v: float) -> str:
    """Formata em R$ ou oculta, conforme o olho do cabeçalho."""
    return D.brl(v) if st.session_state.get("mostrar_saldo", True) else "R$ ••••••"


def confirmar_senha(chave: str, texto: str) -> bool:
    """Confirmação reforçada — senha fictícia de 4 dígitos (sem biometria, por LGPD)."""
    st.markdown(f'<div class="sa-card alerta"><div class="titulo">🔐 Confirmação de segurança</div>'
                f'<div class="sub">{texto}<br>Digite sua senha de 4 dígitos (protótipo: qualquer 4 números).</div></div>',
                unsafe_allow_html=True)
    with st.form(f"form_senha_{chave}", clear_on_submit=True):
        senha = st.text_input("Senha", type="password", max_chars=4, label_visibility="collapsed",
                              placeholder="••••")
        ok = st.form_submit_button("Confirmar", type="primary", width="stretch")
    if ok:
        if senha.isdigit() and len(senha) == 4:
            return True
        st.error("A senha precisa ter 4 dígitos numéricos.")
    return False


# ----------------------------------------------------------------------------- entrada
def tela_entrada() -> None:
    st.markdown(
        '<div class="sa-topo"><div class="marca">SUPERAPP</div>'
        '<div class="ola">Que bom ter você aqui</div>'
        '<div class="conta" style="margin-top:10px">Diga como quer ser chamado e use qualquer senha. '
        'Explore o app como faria no seu banco e, no final, avalie pelo botão no fim da tela.</div></div>',
        unsafe_allow_html=True,
    )
    with st.form("login"):
        nome = st.text_input("Como você quer ser chamado(a)?", placeholder="Seu primeiro nome", max_chars=30)
        st.text_input("Senha", type="password", placeholder="••••••", max_chars=12)
        st.checkbox("Lembrar meu acesso neste aparelho", value=True)
        entrar = st.form_submit_button("Entrar", type="primary", width="stretch")
    if entrar:
        if not nome.strip():
            st.warning("Só preciso do seu nome para continuar.")
        else:
            iniciar_estado("padrao", nome)
            evento("Entrada", "login", {})
            st.rerun()
    c1, c2 = st.columns(2)
    c1.button("Esqueci minha senha", width="stretch")
    c2.button("Abrir conta", width="stretch")
    st.markdown(
        '<div class="sa-card ia"><div class="titulo">Sobre este protótipo</div><div class="sub">'
        "O app simula um banco digital completo (conta, Pix, cartão, pagamentos, investimentos, controle de gastos, "
        "assistente com IA e central de segurança) desenhado a partir das dores levantadas na pesquisa de campo "
        "<i>“Você e seu banco”</i> (n=56). Todos os dados financeiros são fictícios. Seu nome fica só nesta sessão "
        "e não é gravado.</div></div>",
        unsafe_allow_html=True,
    )
    estilo.rodape()


# ----------------------------------------------------------------------------- cabeçalho, cards e faixa
def _alternar_pref() -> None:
    st.session_state.prefere_humano = bool(st.session_state.get("pref_humano"))


def _alternar_produto(chave: str) -> None:
    st.session_state.produtos[chave] = bool(st.session_state.get(f"prod_{chave}"))


def cabecalho() -> None:
    ss = st.session_state
    p = persona()
    c1, c2, c3 = st.columns([4, 1, 1])
    with c1:
        st.markdown(f'<div class="sa-ola">Olá, <b>{ss.nome}</b> 👋</div>', unsafe_allow_html=True)
    with c2:
        if st.button("🙈" if ss.mostrar_saldo else "👁️", key="olho", help="Ocultar/mostrar valores", width="stretch"):
            ss.mostrar_saldo = not ss.mostrar_saldo
            st.rerun()
    with c3:
        with st.popover("👤", width="stretch"):
            st.markdown(f"**{ss.nome}**  \nCliente há {p['tempo_cliente']}")
            st.caption(f"Agência {p['agencia']} · Conta {p['conta']}  \nChave Pix: {p['chave_pix']}")
            st.markdown("**Atendimento**")
            ss["pref_humano"] = ss.prefere_humano
            st.toggle("Prefiro falar com uma pessoa quando algo foge do normal", key="pref_humano", on_change=_alternar_pref,
                      help="Liga a fila prioritária de atendimento humano e faz a Lia oferecer uma pessoa mais cedo.")
            st.markdown("**Meus produtos**")
            st.caption("Conta corrente · sempre ativa")
            ativos = sum(1 for v in ss.produtos.values() if v)
            lotado = ativos >= MAX_PRODUTOS - 1  # conta corrente ocupa a 1ª vaga
            for chave, rotulo in PRODUTOS_OPCIONAIS:
                ligado = ss.produtos.get(chave, False)
                ss[f"prod_{chave}"] = ligado  # sincroniza o interruptor com o estado (a Lia também liga produtos)
                st.toggle(rotulo, key=f"prod_{chave}", disabled=(lotado and not ligado),
                          on_change=_alternar_produto, args=(chave,))
            if st.button("Sair", width="stretch", key="sair"):
                for k in list(ss.keys()):
                    del ss[k]
                st.rerun()


def cards_resumo() -> None:
    """Cards no topo (zona de leitura), um por produto, em coluna. O card é o botão."""
    ss = st.session_state
    p = persona()
    itens = [("Conta", "Saldo disponível", valor(ss.saldo), "Extrato", "conta")]
    if ss.produtos.get("cartao"):
        fat = fatura_total()
        sub = "Fatura paga ✓" if fat == 0 else f"Fatura · vence {D.data_br(p['fatura_vencimento'])}"
        itens.append(("Cartão", sub, valor(fat), "Cartão", "cartao"))
    if ss.produtos.get("investimentos"):
        tot = investido_total()
        itens.append(("Investimentos", f"+{valor(tot * 0.0085)} este mês", valor(tot), "Investir", "inv"))
    if ss.produtos.get("credito"):
        if ss.credito["contratos"]:
            prox = ss.credito["contratos"][0]
            itens.append(("Crédito", f"Saldo devedor · próxima parcela {valor(prox['parcela'])} em 05/10", valor(divida_total()), "Crédito", "cred"))
        else:
            itens.append(("Crédito", "Pré-aprovado · a partir de 1,49% a.m.", valor(credito_disponivel()), "Crédito", "cred"))
    if ss.produtos.get("seguros"):
        itens.append(("Seguros", "Vida + celular · próximo débito 05/10", valor(39.90), "Seguros", "seg"))
    for tit, sub, val, destino, cls in itens[:MAX_PRODUTOS]:
        rotulo = f"*{tit.upper()}* **{val}** {sub}".replace("$", "\\$")  # $ duplo vira LaTeX no Markdown
        if st.button(rotulo, key=f"card_{cls}", width="stretch"):
            ir_para(destino)
            st.rerun()


def faixa_saldo() -> None:
    """Nas demais telas: só uma faixa fina com o saldo."""
    st.markdown(f'<div class="sa-faixa">Saldo disponível <b>{valor(st.session_state.saldo)}</b></div>',
                unsafe_allow_html=True)


# ----------------------------------------------------------------------------- início
def tela_inicio() -> None:
    ss = st.session_state
    p = persona()

    # alertas inteligentes
    vencidas = [c for c in ss.contas if c["status"] == "vencida"]
    prox = [c for c in ss.contas if c["status"] == "aberta" and (c["vencimento"] - D.HOJE).days <= 7]
    if vencidas:
        c = vencidas[0]
        with st.container(key="venc_box"):
            col_a, col_b = st.columns([3, 1], vertical_alignment="center")
            with col_a:
                st.markdown(f'<div class="sa-venc"><div class="titulo">⚠️ {c["descricao"]} · vencida</div>'
                            f'<div class="sub">{D.brl(c["valor"])} · venceu em {D.data_br(c["vencimento"])[:5]}</div></div>',
                            unsafe_allow_html=True)
            with col_b:
                if st.button("Pagar", type="primary", width="content", key="pagar_vencida"):
                    ss.pagamento_pendente = c["descricao"]
                    ir_para("Pagar")
                    st.rerun()

    lia_inicio()
    st.markdown('<div class="sa-dobra">Alertas e movimentações ↓</div>', unsafe_allow_html=True)

    if prox:
        total = sum(c["valor"] for c in prox)
        estilo.card("📅 Próximos 7 dias", f"{len(prox)} conta(s) somando {D.brl(total)}: "
                    + ", ".join(f"{c['descricao']} ({D.data_br(c['vencimento'])})" for c in prox), "alerta")

    g = gastos_por_categoria()
    if g:
        top = next(iter(g))
        mensal = sum(g.values())
        estilo.card("✨ Insight da IA", f"Você gastou {valor(mensal)} nos últimos 30 dias. Maior categoria: {top} "
                    f"({valor(g[top])}). Previsão de fechar o mês com saldo de {valor(ss.saldo - sum(c['valor'] for c in ss.contas if c['status'] != 'paga'))} "
                    "após as contas pendentes.", "ia")

    if ss.produtos.get("cartao", True):
        lim = p["limite_cartao"]
        fat = fatura_total()
        st.progress(min(fat / lim, 1.0), text=f"Limite do cartão: {valor(fat)} usados de {valor(lim)}".replace("$", "\\$"))

    st.markdown("#### Últimas movimentações")
    ult = ss.extrato.sort_values("data", ascending=False).head(5)
    estilo.linhas([(r.descricao, f"{D.data_br(r.data)} · {r.categoria}", valor(r.valor), r.valor > 0) for r in ult.itertuples()])
    if st.button("Ver extrato completo", width="stretch"):
        ir_para("Extrato")
        st.rerun()


# ----------------------------------------------------------------------------- Lia na Início
def lia_inicio() -> None:
    """Chat compacto da Lia na tela inicial: a pessoa comanda operações sem procurar menus."""
    with st.container(key="lia_box"):
        _lia_inicio_conteudo()


def _lia_inicio_conteudo() -> None:
    ss = st.session_state
    st.markdown(f'<div class="sa-lia-titulo">💬 <b>{ASSISTENTE}</b> · peça qualquer operação, do seu jeito</div>',
                unsafe_allow_html=True)
    ultimas = ss.chat[-2:]
    if ultimas:
        for h in ultimas:
            with st.chat_message(h["role"], avatar="🧑" if h["role"] == "user" else "💬"):
                st.markdown(h["content"])
    vencida = next((c for c in ss.contas if c["status"] == "vencida"), None)
    sugestoes = [f"Pagar a {vencida['descricao']}" if vencida else "Qual conta vence esta semana?", "Manda 50 pra " + D.CONTATOS_PIX[ss.persona][0]["nome"].split(" ")[0],
                 "Quanto está minha fatura?", "Bloqueia meu cartão"]
    esc = st.pills("Sugestões da Lia", sugestoes, key="sug_inicio", label_visibility="collapsed")
    with st.container():
        entrada = st.chat_input(f"Ex.: pagar a conta de luz, fazer um Pix…", key="chat_inicio")
    msg = entrada or esc
    if msg and msg != ss.get("_ultima_sugestao_inicio"):
        if esc and not entrada:
            ss["_ultima_sugestao_inicio"] = esc
        with st.spinner(f"{ASSISTENTE} está resolvendo…"):
            r, destino = _processar_mensagem(msg, "Início")
        if r.get("acao", {}).get("tipo") == "escalar_humano":
            destino = "Assistente"
        if destino:
            ir_para(destino)
        st.rerun()
    if ss.chat:
        if st.button(f"Abrir conversa completa com a {ASSISTENTE}", width="stretch", key="abrir_lia"):
            ir_para("Assistente")
            st.rerun()


# ----------------------------------------------------------------------------- pix
def tela_pix() -> None:
    ss = st.session_state
    p = persona()
    st.markdown("### ⚡ Pix")
    aba1, aba2, aba3 = st.tabs(["Enviar / Pagar", "Receber", "Limite"])
    contatos = D.CONTATOS_PIX[ss.persona]

    # ------------------------------------------------------------- enviar / pagar
    with aba1:
        modo = st.pills("Como quer pagar?", ["👥 Para um contato", "📷 Ler QR Code", "📋 Copia e cola"],
                        default="👥 Para um contato", key="pix_modo", label_visibility="collapsed")

        if modo == "👥 Para um contato" or modo is None:
            pend = ss.pix_pendente or {}
            st.caption("Envio em 2 toques: escolha um favorito, informe o valor e confirme.")
            nomes = [c["nome"] for c in contatos]
            idx = nomes.index(pend["destinatario"]) if pend.get("destinatario") in nomes else 0
            dest = st.selectbox("Para quem?", nomes + ["Outra chave Pix…"], index=idx)
            chave = ""
            if dest == "Outra chave Pix…":
                chave = st.text_input("Chave Pix (CPF, e-mail, celular ou aleatória)")
            valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0, value=float(pend.get("valor", 0.0)), format="%.2f")
            st.text_input("Mensagem (opcional)", placeholder="Ex.: almoço de domingo")
            fora_padrao = valor > p["pix_padrao_max"]
            if fora_padrao and valor > 0:
                cc = ss.contato_confianca
                aviso = (f" {cc['nome']} ({cc['relacao']}), seu contato de confiança, será avisado(a) e pode ajudar a confirmar."
                         if cc else " Você pode cadastrar um contato de confiança em Segurança para ser avisado nessas horas.")
                st.markdown(f'<div class="sa-card alerta"><div class="titulo">🛡️ Operação fora do seu padrão</div>'
                            f'<div class="sub">Você costuma enviar até {D.brl(p["pix_padrao_max"])}. Por segurança, este Pix '
                            f'pedirá confirmação reforçada.{aviso}</div></div>', unsafe_allow_html=True)
            if valor > ss.saldo:
                st.error("Saldo insuficiente para este Pix.")
            elif valor > 0:
                if fora_padrao:
                    pode = confirmar_senha("pix", f"Pix de {D.brl(valor)} para {dest if chave == '' else chave}.")
                else:
                    pode = st.button(f"Confirmar Pix de {D.brl(valor)}", type="primary", width="stretch")
                if pode:
                    nome = dest if chave == "" else chave
                    lancar(f"Pix enviado — {nome.split(' (')[0]}", -valor, "Transferência")
                    ss.pix_pendente = None
                    ss.pix_confirmados += 1
                    evento("Pix", "enviado", {"valor": valor, "fora_padrao": fora_padrao})
                    st.success(f"Pix de {D.brl(valor)} enviado para {nome.split(' (')[0]}. Comprovante salvo no extrato.")
                    st.balloons()

        elif modo == "📷 Ler QR Code":
            st.caption("Aponte a câmera para o QR Code do recebedor.")
            foto = st.camera_input("Abrir câmera", label_visibility="collapsed", key="pix_camera")
            if foto is not None:
                codigo = _decodificar_qr(foto.getvalue())
                if codigo:
                    _pagar_codigo_pix(codigo, origem="qr")
                else:
                    st.warning("Não consegui ler um QR Code nessa imagem. Tente aproximar e alinhar o código.")

        else:
            st.caption("Cole o código Pix copia e cola que você recebeu.")
            cod = st.text_area("Código Pix", placeholder="00020126…", height=90, key="pix_cola", label_visibility="collapsed")
            if cod.strip():
                _pagar_codigo_pix(cod, origem="cola")

    # ------------------------------------------------------------- receber
    with aba2:
        st.markdown("**Sua chave Pix** — toque para copiar")
        _chave_copiavel(p["chave_pix"])
        st.markdown("**QR Code da sua chave** (fixo, sem valor)")
        st.image(_qr(_codigo_pix(p["chave_pix"], 0, "", ss.nome)), width=200)
        st.divider()
        st.markdown("**QR Code com valor** (dinâmico)")
        v = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f", key="qr_valor")
        desc = st.text_input("Descrição (opcional)", placeholder="Ex.: rateio do jantar", key="qr_desc")
        if v > 0:
            codigo = _codigo_pix(p["chave_pix"], v, desc, ss.nome)
            st.image(_qr(codigo), width=200)
            st.caption("Ou envie o código copia e cola:")
            _chave_copiavel(codigo, rotulo="Copiar código", pequeno=True)

    # ------------------------------------------------------------- limite
    with aba3:
        st.caption("Limites que você mesmo controla — mudanças reduzem o dano em caso de golpe.")
        ss.limite_pix_noturno = st.slider("Limite Pix noturno (20h–6h)", 0, 5000, int(ss.limite_pix_noturno), 100, format="R$ %d")
        st.slider("Limite Pix diário", 0, 20000, 5000, 500, format="R$ %d", key="lim_diario")
        st.toggle("Exigir senha em todo Pix para contatos novos", value=True)
        st.toggle("Avisar meu contato de confiança em Pix acima do padrão", value=p["prefere_humano"])


def _pagar_codigo_pix(cod: str, origem: str) -> None:
    ss = st.session_state
    v_cola, quem = _ler_codigo_pix(cod)
    estilo.card("Pagamento identificado", f"Para: {quem} · Valor {D.brl(v_cola)}")
    estilo.card("🛡️ Verificação antifraude", "Recebedor sem denúncias e valor coerente com o seu histórico.", "ok")
    if v_cola > ss.saldo:
        st.error("Saldo insuficiente.")
    elif st.button(f"Pagar {D.brl(v_cola)}", type="primary", width="stretch", key=f"pagar_{origem}"):
        lancar(f"Pix {'QR Code' if origem == 'qr' else 'copia e cola'} — {quem}", -v_cola, "Transferência")
        evento("Pix", origem, {"valor": v_cola})
        st.success(f"Pix de {D.brl(v_cola)} pago para {quem}.")


def _chave_copiavel(texto: str, rotulo: str = "", pequeno: bool = False) -> None:
    """Caixa clicável que copia o texto e mostra 'Copiada!'."""
    import html
    t = html.escape(texto)
    fonte = "0.78rem" if pequeno else "1.05rem"
    quebra = "break-all" if pequeno else "normal"
    st.iframe(f"""
    <div id="cx" onclick="copiar()" style="cursor:pointer;background:#F4F5F7;border:1.5px dashed #EC7000;border-radius:14px;
         padding:14px 16px;font-family:sans-serif;color:#00226B;display:flex;justify-content:space-between;align-items:center;gap:10px">
      <span style="font-size:{fonte};font-weight:700;word-break:{quebra}">{t}</span>
      <span id="st" style="font-size:0.8rem;color:#EC7000;white-space:nowrap">📋 {rotulo or 'Copiar'}</span>
    </div>
    <script>
      function copiar() {{
        const txt = {texto!r};
        const ok = () => {{ const s = document.getElementById('st'); s.textContent = '✅ Copiada!'; s.style.color = '#1B8A4A';
                            setTimeout(() => {{ s.textContent = '📋 {rotulo or "Copiar"}'; s.style.color = '#EC7000'; }}, 2500); }};
        if (navigator.clipboard && navigator.clipboard.writeText) {{
          navigator.clipboard.writeText(txt).then(ok).catch(() => fallback());
        }} else {{ fallback(); }}
        function fallback() {{
          const ta = document.createElement('textarea'); ta.value = txt; document.body.appendChild(ta); ta.select();
          try {{ document.execCommand('copy'); ok(); }} catch (e) {{}} document.body.removeChild(ta);
        }}
      }}
    </script>
    """, height=64 if not pequeno else 84)


def _decodificar_qr(png: bytes) -> str | None:
    try:
        import cv2
        import numpy as np
        img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
        det = cv2.QRCodeDetector()
        for cand in (img, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY),
                     cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)):
            texto, _, _ = det.detectAndDecode(cand)
            if texto:
                return texto
        return None
    except Exception:  # noqa: BLE001
        return None


def _norm_txt(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", str(t).lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _codigo_pix(chave: str, valor: float, desc: str, nome: str = "SUPERAPP") -> str:
    nome = nome[:25]
    v = f"5406{valor:.2f}" if valor > 0 else ""
    d = f"62{len(desc) + 4:02d}05{len(desc):02d}{desc}" if desc else ""
    return f"00020126{len(chave) + 22:02d}0014BR.GOV.BCB.PIX01{len(chave):02d}{chave}52040000530398{v}5802BR59{len(nome):02d}{nome}6009SAO PAULO{d}6304ABCD"


def _ler_codigo_pix(cod: str) -> tuple[float, str]:
    import re
    m = re.search(r"5406(\d+\.\d{2})", cod.replace(",", "."))
    if m:
        v = float(m.group(1))
    else:
        v = round(20 + (sum(ord(c) for c in cod) % 480), 2)
    quem = "Loja Fictícia ME"
    m2 = re.search(r"59\d{2}([A-Za-z ]{3,25})", cod)
    if m2:
        quem = m2.group(1).strip()
    return v, quem


@st.cache_data(show_spinner=False)
def _qr(texto: str):
    import io
    import qrcode
    img = qrcode.make(texto, box_size=8, border=4)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ----------------------------------------------------------------------------- cartão
def tela_cartao() -> None:
    ss = st.session_state
    p = persona()
    st.markdown("### 💳 Cartão de crédito")
    fat = fatura_total()
    disp = p["limite_cartao"] - fat
    st.markdown(
        f'<div class="sa-topo" style="background:linear-gradient(135deg,{estilo.AZUL} 0%,{estilo.AZUL_ESCURO} 100%);'
        f'box-shadow:0 6px 18px rgba(0,51,153,.25)"><div class="marca">SUPERAPP <span style="background:{estilo.LARANJA}">'
        f'{"BLOQUEADO" if ss.cartao_bloqueado else "Platinum"}</span></div>'
        f'<div class="conta" style="margin-top:22px;font-size:1.05rem;letter-spacing:.15em">•••• •••• •••• 4417</div>'
        f'<div class="conta">{ss.nome.upper()} · VAL 09/31</div>'
        f'<div class="saldo-rotulo">Fatura atual</div><div class="saldo">{valor(fat)}</div>'
        f'<div class="conta">Vence {D.data_br(p["fatura_vencimento"])} · Limite disponível {valor(disp)}</div></div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔓 Desbloquear" if ss.cartao_bloqueado else "🔒 Bloquear", width="stretch"):
            ss.cartao_bloqueado = not ss.cartao_bloqueado
            evento("Cartão", "bloqueio", {"bloqueado": ss.cartao_bloqueado})
            st.rerun()
    with c2:
        if st.button("📈 Ajustar limite", width="stretch"):
            st.toast("Solicitação enviada. Resposta em até 1 dia útil.")
    if ss.cartao_bloqueado:
        estilo.card("Cartão bloqueado preventivamente", "Compras serão recusadas até você desbloquear. Débito e Pix seguem normais.", "perigo")

    aba1, aba2, aba3, aba4, aba5 = st.tabs(["Fatura atual", "Passadas", "Recentes", "Parcelados", "Virtuais"])
    with aba1:
        if ss.fatura_paga:
            estilo.card("Fatura paga ✅", "Nada pendente no cartão. Limite totalmente disponível.", "ok")
        else:
            opc = st.radio("Como quer pagar?", [f"Total — {D.brl(fat)}", f"Mínimo — {D.brl(fat * 0.15)} (juros de 12,9% a.m. no restante)",
                                                 "Parcelar em 3x sem juros"], index=0)
            valor_pg = fat if opc.startswith("Total") else (fat * 0.15 if opc.startswith("Mínimo") else fat / 3)
            if valor_pg > ss.saldo:
                st.error("Saldo insuficiente na conta.")
            elif st.button("Pagar fatura", type="primary", width="stretch"):
                lancar("Pagamento fatura cartão", -round(valor_pg, 2), "Cartão")
                ss.fatura_paga = opc.startswith("Total")
                evento("Cartão", "pagar_fatura", {"valor": valor_pg})
                st.success(f"Pagamento de {D.brl(valor_pg)} realizado.")
                st.rerun()
        g = ss.fatura.groupby("categoria")["valor"].sum().sort_values(ascending=False)
        st.markdown("**Por categoria**")
        st.bar_chart(g, color=estilo.LARANJA, horizontal=True, height=220)
        estilo.card("✨ Leitura da IA", f"{g.index[0]} representa {g.iloc[0] / g.sum():.0%} da fatura. "
                    "Em relação ao mês passado, sua fatura está 6% maior.", "ia")
        st.markdown("**Lançamentos**")
        df = ss.fatura.sort_values("data", ascending=False)
        estilo.linhas([(r.estabelecimento, f"{D.data_br(r.data)} · {r.categoria} · {r.parcela_txt}", D.brl(r.valor), False)
                       for r in df.itertuples()])
    with aba2:
        for k, (mes, val, status) in enumerate([("Setembro/2026", fat * 0.94, "paga"), ("Agosto/2026", fat * 1.08, "paga"),
                                                 ("Julho/2026", fat * 0.87, "paga"), ("Junho/2026", fat * 0.99, "paga")]):
            st.markdown(f'<div class="sa-card"><div class="titulo">{mes} {estilo.pill("paga", "verde")}</div>'
                        f'<div class="sub">{D.brl(val)} · paga em dia</div></div>', unsafe_allow_html=True)
            st.download_button("⬇️ PDF", f"Fatura {mes} — {D.brl(val)} — PAGA (fictícia)".encode(), f"fatura_{k}.txt", key=f"fat_{k}")
    with aba3:
        st.caption("Compras dos últimos 7 dias, inclusive as que ainda não entraram na fatura.")
        df = ss.fatura[pd.to_datetime(ss.fatura["data"]) >= pd.Timestamp(D.HOJE - timedelta(days=7))].sort_values("data", ascending=False)
        if df.empty:
            st.info("Nenhuma compra nos últimos 7 dias.")
        estilo.linhas([(r.estabelecimento, f"{D.data_br(r.data)} · {r.categoria}", D.brl(r.valor), False) for r in df.itertuples()])
    with aba4:
        df = ss.fatura[ss.fatura["parcelas"] > 1]
        if df.empty:
            st.info("Nenhuma compra parcelada.")
        total_rest = 0.0
        for r in df.itertuples():
            rest = r.valor * (r.parcelas - 1)
            total_rest += rest
            st.markdown(f'<div class="sa-card"><div class="titulo">{r.estabelecimento} — {r.parcelas}x de {D.brl(r.valor)}</div>'
                        f'<div class="sub">Parcela 1 de {r.parcelas} nesta fatura · faltam {D.brl(rest)} em {r.parcelas - 1} parcelas</div></div>',
                        unsafe_allow_html=True)
            st.progress(1 / r.parcelas)
        if total_rest:
            estilo.card("✨ Compromisso futuro", f"Suas parcelas somam {D.brl(total_rest)} nas próximas faturas — "
                        f"cerca de {D.brl(df['valor'].sum())} por mês.", "ia")
    with aba5:
        st.caption("Dois cartões virtuais: um fixo para assinaturas e um temporário para compras únicas.")
        if not ss.get("cartao_virtual_fixo"):
            ss.cartao_virtual_fixo = f"5312 {uuid.uuid4().int % 10000:04d} {uuid.uuid4().int % 10000:04d} {uuid.uuid4().int % 10000:04d}"
        st.markdown(f'<div class="sa-card ia"><div class="titulo">🔁 Virtual fixo (assinaturas)</div>'
                    f'<div class="sub">{ss.cartao_virtual_fixo} · CVV 218 · VAL 09/31<br>Use em Netflix, Spotify e cobranças recorrentes. '
                    f'Se vazar, troque o número sem afetar o cartão físico.</div></div>', unsafe_allow_html=True)
        if st.button("Trocar número do fixo", width="stretch"):
            ss.cartao_virtual_fixo = f"5312 {uuid.uuid4().int % 10000:04d} {uuid.uuid4().int % 10000:04d} {uuid.uuid4().int % 10000:04d}"
            st.rerun()
        if ss.cartao_virtual:
            estilo.card("⏱️ Virtual temporário", f"{ss.cartao_virtual} · CVV 731 · válido por 24h · uma compra. "
                        "Depois disso, o número deixa de existir.", "ok")
            if st.button("Encerrar temporário", width="stretch"):
                ss.cartao_virtual = None
                st.rerun()
        else:
            if st.button("Criar virtual temporário (24h)", type="primary", width="stretch"):
                ss.cartao_virtual = f"5312 {uuid.uuid4().int % 10000:04d} {uuid.uuid4().int % 10000:04d} {uuid.uuid4().int % 10000:04d}"
                st.rerun()


# ----------------------------------------------------------------------------- pagamentos
def _pagar_ou_agendar(chave: str, descricao: str, valor_pg: float, categoria: str, ao_pagar=None) -> None:
    """Par de botões Pagar agora / Agendar com data."""
    ss = st.session_state
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Pagar agora", key=f"pg_{chave}", type="primary", width="stretch"):
            if valor_pg > ss.saldo:
                st.error("Saldo insuficiente.")
            else:
                lancar(f"Pagamento — {descricao}", -valor_pg, categoria)
                if ao_pagar:
                    ao_pagar()
                evento("Pagar", "pago", {"desc": descricao, "valor": valor_pg})
                st.success(f"{descricao} paga. Comprovante em Extrato → Comprovantes.")
                st.rerun()
    with c2:
        with st.popover("📅 Agendar", width="stretch"):
            data = st.date_input("Pagar em", value=D.HOJE + timedelta(days=3), min_value=D.HOJE, key=f"dt_{chave}", format="DD/MM/YYYY")
            if st.button("Confirmar agendamento", key=f"ag_{chave}", type="primary", width="stretch"):
                ss.agendamentos.append({"descricao": descricao, "valor": valor_pg, "data": data, "categoria": categoria})
                if ao_pagar:
                    ao_pagar(agendado=True)
                evento("Pagar", "agendado", {"desc": descricao, "valor": valor_pg})
                st.success(f"{descricao} agendada para {D.data_br(data)}.")
                st.rerun()


def tela_pagar() -> None:
    ss = st.session_state
    st.markdown("### 🧾 Pagamentos")
    aba1, aba2, aba3 = st.tabs(["Contas a pagar", "Boleto", "Agendamentos"])
    with aba1:
        pend = [c for c in ss.contas if c["status"] not in ("paga", "agendada")]
        if not pend:
            estilo.card("Tudo em dia ✅", "Nenhuma conta pendente.", "ok")
        for c in pend:
            atras = c["status"] == "vencida"
            selo = estilo.pill("VENCIDA", "vermelho") if atras else estilo.pill(f"vence {D.data_br(c['vencimento'])}", "laranja")
            rec = estilo.pill("recorrente", "azul") if c["recorrente"] else ""
            destaque = ss.pagamento_pendente == c["descricao"]
            st.markdown(f'<div class="sa-card {"perigo" if atras else ("ia" if destaque else "")}"><div class="titulo">{c["descricao"]} — {D.brl(c["valor"])}</div>'
                        f'<div class="sub">{selo}{rec}{" · preparado pela Lia" if destaque else ""}</div></div>', unsafe_allow_html=True)

            def _marcar(agendado=False, c=c):
                c["status"] = "agendada" if agendado else "paga"
                ss.pagamento_pendente = None

            _pagar_ou_agendar(_norm_txt(c["descricao"]).replace(" ", "_"), c["descricao"], c["valor"], "Moradia", _marcar)
        st.toggle("Débito automático para contas recorrentes", value=False,
                  help="A IA identifica contas que se repetem todo mês e sugere colocar em débito automático.")
    with aba2:
        modo = st.pills("Como?", ["⌨️ Digitar código", "📷 Ler código de barras"], default="⌨️ Digitar código",
                        key="boleto_modo", label_visibility="collapsed")
        cod = ""
        if modo == "📷 Ler código de barras":
            foto = st.camera_input("Abrir câmera", label_visibility="collapsed", key="boleto_camera")
            if foto is not None:
                cod = _decodificar_qr(foto.getvalue()) or "23793381286000000000300000000400199990000012345"
                st.caption("Código lido.")
        else:
            cod = st.text_input("Código de barras ou linha digitável", value=ss.get("boleto_pendente") or "",
                                placeholder="Cole ou digite (protótipo aceita qualquer coisa)")
        if cod:
            v = round(37.0 + (sum(ord(ch) for ch in cod) % 900), 2)
            venc = D.HOJE + timedelta(days=3)
            estilo.card("Boleto identificado", f"Beneficiário: Cia. Fictícia de Serviços · Valor {D.brl(v)} · Vencimento {D.data_br(venc)}")
            estilo.card("🛡️ Verificação antifraude", "Beneficiário conhecido, valor coerente com seu histórico. Nenhum sinal de boleto falso.", "ok")

            def _limpar(agendado=False):
                ss.boleto_pendente = None

            _pagar_ou_agendar("boleto", "Boleto Cia. Fictícia de Serviços", v, "Compras", _limpar)
    with aba3:
        if not ss.agendamentos:
            st.info("Nenhum pagamento agendado. Agende pelas abas Contas a pagar ou Boleto.")
        for k, a in enumerate(sorted(ss.agendamentos, key=lambda x: x["data"])):
            st.markdown(f'<div class="sa-card"><div class="titulo">{a["descricao"]} — {D.brl(a["valor"])}</div>'
                        f'<div class="sub">{estilo.pill("agendado para " + D.data_br(a["data"]), "azul")} · débito automático na data</div></div>',
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Pagar hoje", key=f"agpg_{k}", width="stretch"):
                    lancar(f"Pagamento — {a['descricao']}", -a["valor"], a["categoria"])
                    ss.agendamentos.remove(a)
                    for c in ss.contas:
                        if c["descricao"] == a["descricao"]:
                            c["status"] = "paga"
                    st.rerun()
            with c2:
                if st.button("Cancelar", key=f"agcl_{k}", width="stretch"):
                    ss.agendamentos.remove(a)
                    for c in ss.contas:
                        if c["descricao"] == a["descricao"]:
                            c["status"] = "aberta"
                    st.rerun()


# ----------------------------------------------------------------------------- extrato
def _extrato_filtrado() -> tuple[pd.DataFrame, date, date]:
    ss = st.session_state
    periodo = st.pills("Período", ["Mês atual", "7 dias", "30 dias", "90 dias", "De / até"], default=ss.get("ext_periodo", "Mês atual"),
                       key="ext_periodo_sel", label_visibility="collapsed")
    periodo = periodo or "Mês atual"
    ss.ext_periodo = periodo
    if periodo == "Mês atual":
        ini, fim = D.HOJE.replace(day=1), D.HOJE
    elif periodo == "De / até":
        c1, c2 = st.columns(2)
        ini = c1.date_input("De", value=D.HOJE - timedelta(days=30), max_value=D.HOJE, format="DD/MM/YYYY", key="ext_de")
        fim = c2.date_input("Até", value=D.HOJE, max_value=D.HOJE, format="DD/MM/YYYY", key="ext_ate")
    else:
        ini, fim = D.HOJE - timedelta(days=int(periodo.split()[0])), D.HOJE
    df = ss.extrato.copy()
    df["data"] = pd.to_datetime(df["data"])
    df = df[(df["data"] >= pd.Timestamp(ini)) & (df["data"] <= pd.Timestamp(fim))]
    return df, ini, fim


def tela_extrato() -> None:
    ss = st.session_state
    st.markdown("### 📄 Extrato da conta")
    if ss.get("comprovante_pendente"):
        st.info("A Lia abriu seus comprovantes — veja a aba **Comprovantes**.")
    aba1, aba2 = st.tabs(["Movimentações", "Comprovantes"])
    with aba1:
        df, ini, fim = _extrato_filtrado()
        ent, sai = df[df["valor"] > 0]["valor"].sum(), df[df["valor"] < 0]["valor"].sum()
        # saldo inicial = saldo antes do primeiro lançamento do período
        antes = ss.extrato.copy()
        antes["data"] = pd.to_datetime(antes["data"])
        antes = antes[antes["data"] < pd.Timestamp(ini)]
        saldo_ini = float(antes.iloc[-1]["saldo"]) if not antes.empty else float(df.iloc[0]["saldo"] - df.iloc[0]["valor"]) if not df.empty else ss.saldo
        saldo_fim = saldo_ini + ent + sai

        # os três cartões são filtros
        filtro = st.pills("Filtro", ["Tudo", f"⬆️ Entradas {valor(ent)}", f"⬇️ Saídas {valor(sai)}", "📊 Saldo por dia"],
                          default="Tudo", key="ext_filtro", label_visibility="collapsed") or "Tudo"

        st.markdown("**Fluxo de caixa do período** — " + f"{D.data_br(ini)} a {D.data_br(fim)}")
        st.markdown(
            f'<div class="sa-card"><div class="sa-linha"><div class="desc">Saldo inicial</div><div class="val">{valor(saldo_ini)}</div></div>'
            f'<div class="sa-linha"><div class="desc">(+) Entradas</div><div class="val pos">{valor(ent)}</div></div>'
            f'<div class="sa-linha"><div class="desc">(−) Saídas</div><div class="val">{valor(abs(sai))}</div></div>'
            f'<div class="sa-linha"><div class="desc"><b>(=) Resultado</b></div><div class="val {"pos" if ent + sai >= 0 else ""}"><b>{valor(ent + sai)}</b></div></div>'
            f'<div class="sa-linha"><div class="desc"><b>Saldo final</b></div><div class="val"><b>{valor(saldo_fim)}</b></div></div></div>',
            unsafe_allow_html=True)

        if filtro.startswith("📊"):
            if not df.empty:
                por_dia = df.groupby(df["data"].dt.date)["saldo"].last()
                st.line_chart(por_dia, color=estilo.AZUL, height=200)
                estilo.linhas([(D.data_br(d), "saldo ao fim do dia", valor(v), True) for d, v in por_dia.sort_index(ascending=False).items()][:31])
        else:
            if filtro.startswith("⬆️"):
                df = df[df["valor"] > 0]
            elif filtro.startswith("⬇️"):
                df = df[df["valor"] < 0]
            busca = st.text_input("Buscar", placeholder="Ex.: iFood, Pix, energia", key="ext_busca", label_visibility="collapsed")
            if busca:
                df = df[df["descricao"].str.contains(busca, case=False)]
            df = df.sort_values("data", ascending=False)
            if df.empty:
                st.info("Nada nesse filtro.")
            estilo.linhas([(r.descricao, f"{D.data_br(r.data)} · {r.categoria}", valor(r.valor), r.valor > 0) for r in df.head(60).itertuples()])
        st.download_button("⬇️ Baixar extrato (CSV)", df.to_csv(index=False).encode("utf-8"), "extrato.csv", "text/csv", width="stretch")
    with aba2:
        tela_comprovantes()


def _comprovante_txt(r) -> str:
    return (f"SUPERAPP — COMPROVANTE (fictício)\n{'-' * 40}\nOperação: {r.descricao}\nData: {D.data_br(r.data)}\n"
            f"Valor: {D.brl(r.valor)}\nCategoria: {r.categoria}\nAutenticação: {uuid.uuid5(uuid.NAMESPACE_DNS, f'{r.descricao}{r.data}{r.valor}').hex[:20].upper()}\n")


def tela_comprovantes() -> None:
    ss = st.session_state
    pend = ss.get("comprovante_pendente") or {}
    st.caption("Todo Pix, pagamento e transferência gera um comprovante aqui. Busque por valor ou por nome.")
    busca = st.text_input("Buscar comprovante", value=pend.get("busca", ""), placeholder="Ex.: 50, Mãe, Enel, boleto", key="cmp_busca")
    df = ss.extrato.copy()
    df = df[df["descricao"].str.contains("Pix|Pagamento|Boleto|Aplicação|Resgate|Crédito|Antecipação", case=False, regex=True)]
    if busca.strip():
        b = busca.strip()
        v = None
        try:
            v = float(b.replace("R$", "").replace(".", "").replace(",", "."))
        except ValueError:
            pass
        if v is not None:
            df = df[(df["valor"].abs() - v).abs() < 0.005]
        else:
            df = df[df["descricao"].str.contains(b, case=False)]
    df = df.sort_values("data", ascending=False)
    if df.empty:
        st.info("Nenhum comprovante encontrado.")
    if pend:
        ss.comprovante_pendente = None
    for k, r in enumerate(df.head(20).itertuples()):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f'<div class="sa-card"><div class="titulo">{r.descricao}</div><div class="sub">{D.data_br(r.data)} · {D.brl(r.valor)}</div></div>',
                        unsafe_allow_html=True)
        with c2:
            st.download_button("📄 Baixar", _comprovante_txt(r).encode("utf-8"), f"comprovante_{k}.txt", key=f"cmp_{k}", width="stretch")


# ----------------------------------------------------------------------------- investimentos
def tela_investir() -> None:
    ss = st.session_state
    p = persona()
    st.markdown("### 📈 Investimentos")
    total = sum(i["valor"] for i in ss.investimentos)
    rend = sum(i["valor"] * i["rent_12m"] for i in ss.investimentos)
    m1, m2, m3 = st.columns(3)
    m1.metric("Patrimônio", D.brl(total))
    m2.metric("Rendimento 12m", D.brl(rend), f"{rend / total:.1%}")
    m3.metric("Disponível p/ aplicar", D.brl(ss.saldo))
    aba1, aba2, aba3 = st.tabs(["Carteira", "Aplicar / Resgatar", "Simulador"])
    with aba1:
        for i in ss.investimentos:
            st.markdown(f'<div class="sa-card"><div class="titulo">{i["produto"]} <span class="sa-pill azul">{i["tipo"]}</span></div>'
                        f'<div class="sub">{D.brl(i["valor"])} · rentabilidade 12m {i["rent_12m"]:.1%} · liquidez {i["liquidez"]}</div></div>',
                        unsafe_allow_html=True)
        idx = pd.date_range(end=pd.Timestamp(D.HOJE).replace(day=1), periods=12, freq="MS")
        serie = pd.Series([total * (1 - 0.0075 * (11 - k)) for k in range(12)], index=idx)
        st.line_chart(serie, color=estilo.LARANJA, height=180)
        estilo.card("✨ Sugestão da IA", "Você tem R$ " + f"{max(ss.saldo - 800, 0):,.0f}".replace(",", ".") +
                    " parados na conta acima do que costuma usar até o próximo salário. No CDB 110% CDI, renderiam cerca de "
                    + D.brl(max(ss.saldo - 800, 0) * 0.009) + " ao mês.", "ia")
    with aba2:
        pend = ss.inv_pendente or {}
        nomes = [i["produto"] for i in ss.investimentos]
        idx = 0
        if pend.get("produto"):
            alvo = _norm_txt(pend["produto"])
            for k, n in enumerate(nomes):
                if alvo in _norm_txt(n) or _norm_txt(n).split(" ")[0] in alvo:
                    idx = k
                    break
        if pend:
            estilo.card("✨ Preparado pela Lia", f"{pend.get('op', 'Aplicar')} {D.brl(pend.get('valor', 0))} em {nomes[idx]}. Confira e confirme.", "ia")
        prod = st.selectbox("Produto", nomes, index=idx)
        op = st.radio("Operação", ["Aplicar", "Resgatar"], horizontal=True, index=0 if pend.get("op", "Aplicar") == "Aplicar" else 1)
        v = st.number_input("Valor (R$)", min_value=0.0, step=50.0, value=float(pend.get("valor", 0.0)), format="%.2f", key="inv_valor")
        if v > 0 and st.button(f"{op} {D.brl(v)}", type="primary", width="stretch"):
            item = next(i for i in ss.investimentos if i["produto"] == prod)
            if op == "Aplicar":
                if v > ss.saldo:
                    st.error("Saldo insuficiente.")
                else:
                    item["valor"] += v
                    ss.inv_pendente = None
                    lancar(f"Aplicação — {prod}", -v, "Investimentos")
                    evento("Investir", "aplicar", {"valor": v})
                    st.success("Aplicação realizada.")
                    st.rerun()
            else:
                if v > item["valor"]:
                    st.error("Valor maior que o saldo aplicado.")
                else:
                    item["valor"] -= v
                    ss.inv_pendente = None
                    lancar(f"Resgate — {prod}", v, "Investimentos")
                    evento("Investir", "resgatar", {"valor": v})
                    st.success("Resgate solicitado (cai na conta conforme a liquidez do produto).")
                    st.rerun()
    with aba3:
        vi = st.number_input("Valor inicial (R$)", 0.0, 1_000_000.0, 1000.0, 100.0, key="sim_vi")
        vm = st.number_input("Aporte mensal (R$)", 0.0, 100_000.0, 200.0, 50.0, key="sim_vm")
        anos = st.slider("Prazo (anos)", 1, 30, 5)
        taxa = st.slider("Taxa anual estimada", 5.0, 20.0, 11.0, 0.5, format="%.1f%%") / 100
        i = (1 + taxa) ** (1 / 12) - 1
        n = anos * 12
        fv = vi * (1 + i) ** n + vm * (((1 + i) ** n - 1) / i)
        st.metric("Valor estimado ao final", D.brl(fv), f"{D.brl(fv - vi - vm * n)} de juros")
        st.caption("Simulação didática, sem impostos.")


# ----------------------------------------------------------------------------- gastos
def tela_gastos() -> None:
    ss = st.session_state
    p = persona()
    st.markdown("### 🧭 Controle de gastos")
    g = gastos_por_categoria(30)
    g_ant = gastos_por_categoria(60)
    ant = {k: g_ant.get(k, 0) - g.get(k, 0) for k in g_ant}
    total = sum(g.values())
    total_ant = sum(ant.values())
    m1, m2 = st.columns(2)
    m1.metric("Gastos últimos 30 dias", D.brl(total), f"{(total - total_ant) / max(total_ant, 1):+.0%} vs. 30 dias anteriores", delta_color="inverse")
    contas_pend = sum(c["valor"] for c in ss.contas if c["status"] != "paga")
    m2.metric("Previsão de contas até o fim do mês", D.brl(contas_pend))
    df = pd.DataFrame({"Este mês": pd.Series(g), "Mês anterior": pd.Series(ant)}).fillna(0)
    st.bar_chart(df, color=[estilo.LARANJA, "#B8C2D9"], height=260)
    st.markdown("#### Categorização automática")
    for k, v in g.items():
        pct = v / total if total else 0
        st.progress(min(pct, 1.0), text=f"{k}: {D.brl(v)} ({pct:.0%})")
    st.markdown("#### O que a IA recomenda")
    sug = []
    if g.get("Alimentação", 0) > 0.25 * total:
        sug.append(f"Alimentação por app está em {D.brl(g['Alimentação'])}. Trocar 4 pedidos por mês por mercado economizaria ~{D.brl(g['Alimentação'] * 0.18)}.")
    if g.get("Lazer", 0) > 0:
        sug.append("Você tem 3 assinaturas de streaming ativas; a IA identificou uma sem uso há 40 dias (R$ 34,90/mês).")
    if ss.saldo - contas_pend < 0.15 * p["salario"]:
        sug.append("Seu saldo após as contas ficará abaixo de 15% do salário. Sugiro adiar compras parceladas até o dia 5.")
    else:
        sug.append(f"Sobra prevista de {D.brl(ss.saldo - contas_pend)}: vale separar uma parte para a reserva de emergência.")
    for s in sug:
        estilo.card("✨", s, "ia")
    st.markdown("#### Metas")
    meta = st.number_input("Meta mensal de gastos (R$)", 0.0, 50_000.0, float(round(total * 0.9, -1)), 50.0)
    if meta:
        st.progress(min(total / meta, 1.0), text=f"{total / meta:.0%} da meta consumida")


# ----------------------------------------------------------------------------- notificações
def tela_avisos() -> None:
    ss = st.session_state
    st.markdown("### 🔔 Avisos e notificações")
    aba1, aba2 = st.tabs(["Central", "Preferências"])
    prefs = ss.prefs_notif
    with aba2:
        st.caption("Dor da pesquisa: propaganda não solicitada (20 menções) e notificações demais (13). Aqui você manda.")
        prefs["frequencia"] = st.radio("Frequência", ["Tudo em tempo real", "Só o essencial", "Resumo diário"],
                                       index=["Tudo em tempo real", "Só o essencial", "Resumo diário"].index(prefs["frequencia"]))
        prefs["conta"] = st.toggle("Movimentações da conta (Pix, débitos)", value=prefs["conta"])
        prefs["cartao"] = st.toggle("Compras no cartão", value=prefs["cartao"])
        prefs["seguranca"] = st.toggle("Alertas de segurança (sempre recomendado)", value=prefs["seguranca"])
        prefs["investimentos"] = st.toggle("Rendimentos e investimentos", value=prefs["investimentos"])
        prefs["ofertas"] = st.toggle("Ofertas e produtos", value=prefs["ofertas"], help="Desligado por padrão: a IA só oferece algo se você demonstrou interesse.")
    with aba1:
        vis = [n for n in ss.notificacoes if prefs.get(n["tipo"], True)]
        ocultas = len(ss.notificacoes) - len(vis)
        if ocultas:
            estilo.card("✨ Filtro inteligente ativo", f"{ocultas} notificação(ões) de ofertas foram silenciadas conforme suas preferências.", "ia")
        for n in vis:
            cor = {"seguranca": "perigo", "ofertas": "", "conta": "ok", "cartao": "", "investimentos": "ia"}[n["tipo"]]
            st.markdown(f'<div class="sa-card {cor}"><div class="titulo">{"" if n["lida"] else "🔵 "}{n["titulo"]}</div>'
                        f'<div class="sub">{n["texto"]}<br><small>{n["quando"]}</small></div></div>', unsafe_allow_html=True)
        if st.button("Marcar todas como lidas", width="stretch"):
            for n in ss.notificacoes:
                n["lida"] = True
            st.rerun()


# ----------------------------------------------------------------------------- assistente
def _executar_acao(acao: dict) -> str | None:
    ss = st.session_state
    t = acao.get("tipo", "nenhuma")
    if t == "pix":
        ss.pix_pendente = {"valor": float(acao.get("valor") or 0), "destinatario": acao.get("destinatario", "")}
        return "Pix"
    if t == "pagar_conta":
        ss.pagamento_pendente = acao.get("descricao")
        return "Pagar"
    if t == "bloquear_cartao":
        ss.cartao_bloqueado = True
        return None
    if t == "desbloquear_cartao":
        ss.cartao_bloqueado = False
        return None
    if t == "ver_fatura":
        return "Cartão"
    if t == "ver_extrato":
        return "Extrato"
    if t == "ver_gastos":
        return "Gastos"
    if t == "ver_investimentos":
        return "Investir"
    if t in ("aplicar", "resgatar"):
        ss.inv_pendente = {"op": "Aplicar" if t == "aplicar" else "Resgatar", "produto": acao.get("produto"),
                           "valor": float(acao.get("valor") or 0)}
        return "Investir"
    if t == "contratar_credito":
        ativar_produto("credito")
        ss.credito_pendente = {"valor": float(acao.get("valor") or 0), "parcelas": int(acao.get("parcelas") or 12)}
        return "Crédito"
    if t == "ver_credito":
        ativar_produto("credito")
        return "Crédito"
    if t == "cartao_virtual":
        ss.cartao_virtual = f"5312 {uuid.uuid4().int % 10000:04d} {uuid.uuid4().int % 10000:04d} {uuid.uuid4().int % 10000:04d}"
        return None
    if t == "pagar_boleto":
        ss.boleto_pendente = str(acao.get("codigo") or "")
        return "Pagar"
    if t == "ativar_produto":
        ativar_produto(str(acao.get("produto") or ""))
        return None
    if t == "comprovante":
        ss.comprovante_pendente = {"busca": str(acao.get("busca") or "")}
        return "Extrato"
    if t == "escalar_humano":
        prioridade = ss.prefere_humano or "segurança" in str(acao.get("motivo", ""))
        ss.fila_humano = {"motivo": acao.get("motivo", "atendimento"), "posicao": 1 if prioridade else 5,
                          "espera": "2 min" if prioridade else "8 min"}
        return None
    return None


def _digitando(texto: str, delay: float = 0.012):
    """Gera a resposta palavra por palavra, como alguém digitando."""
    import time
    for palavra in texto.split(" "):
        yield palavra + " "
        time.sleep(delay)


def _botao_microfone() -> None:
    """Ditado por voz: usa o reconhecimento do próprio navegador (pt-BR) e escreve na caixa da conversa."""
    st.iframe("""
    <div style="font-family:sans-serif;display:flex;align-items:center;gap:10px">
      <button id="mic" onclick="ouvir()" style="border:1.5px solid #EC7000;background:#FFF6EE;color:#C25C00;border-radius:999px;
              padding:8px 14px;font-weight:700;cursor:pointer;font-size:0.9rem">🎤 Falar com a Lia</button>
      <span id="stt" style="font-size:0.8rem;color:#5B6472"></span>
    </div>
    <script>
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      const st = document.getElementById('stt');
      if (!SR) { st.textContent = 'Seu navegador não tem ditado por voz — use Chrome ou Safari.'; }
      function enviar(texto) {
        try {
          const doc = window.parent.document;
          const ta = doc.querySelector('textarea[data-testid="stChatInputTextArea"]');
          if (!ta) { st.textContent = 'Não achei a caixa de mensagem.'; return; }
          const setter = Object.getOwnPropertyDescriptor(window.parent.HTMLTextAreaElement.prototype, 'value').set;
          setter.call(ta, texto);
          ta.dispatchEvent(new Event('input', { bubbles: true }));
          setTimeout(() => {
            const btn = doc.querySelector('button[data-testid="stChatInputSubmitButton"]');
            if (btn) btn.click();
          }, 150);
        } catch (e) { st.textContent = 'Fale e depois toque em enviar.'; }
      }
      function ouvir() {
        if (!SR) return;
        const r = new SR(); r.lang = 'pt-BR'; r.interimResults = false; r.maxAlternatives = 1;
        st.textContent = 'Ouvindo… pode falar.'; document.getElementById('mic').textContent = '🔴 Ouvindo';
        r.onresult = (e) => { const t = e.results[0][0].transcript; st.textContent = '“' + t + '”'; enviar(t); };
        r.onerror = (e) => { st.textContent = 'Não consegui ouvir (' + e.error + '). Tente de novo.'; };
        r.onend = () => { document.getElementById('mic').textContent = '🎤 Falar com a Lia'; };
        r.start();
      }
    </script>
    """, height=48)


def _processar_mensagem(msg: str, origem: str) -> tuple[dict, str | None]:
    """Envia a mensagem à Lia, executa a ação pedida e grava no histórico. Devolve (resposta, tela de destino)."""
    ss = st.session_state
    r = ia.responder(msg, ss.chat, contexto_ia())
    destino = _executar_acao(r.get("acao", {}))
    tipo = r.get("acao", {}).get("tipo")
    if tipo == "ativar_produto" and not ss.produtos.get(str(r["acao"].get("produto", ""))):
        r["resposta"] = (f"Você já tem {MAX_PRODUTOS} produtos na tela inicial, que é o máximo. Se quiser incluir este, "
                         "desative outro no seu perfil (ícone 👤) que eu ativo na hora.")
    if tipo == "cartao_virtual" and ss.cartao_virtual:
        r["resposta"] += f"\n\n**{ss.cartao_virtual}** · CVV 731 · válido por 24h para compras online."
    ss.chat.append({"role": "user", "content": msg})
    ss.chat.append({"role": "assistant", "content": r["resposta"]})
    evento(origem, "mensagem", {"fonte": r["fonte"], "acao": tipo, "escalar": r["escalar"], "uso": r.get("uso")})
    return r, destino


def tela_assistente() -> None:
    ss = st.session_state
    AV = "💬"
    st.markdown(f"### {AV} {ASSISTENTE}")
    modo = "IA generativa" if ia.api_disponivel() else "regras"
    st.caption(f"Assistente do Superapp · online agora · {modo}")
    sugestoes = ["Qual meu saldo?", "Manda 50 pra " + D.CONTATOS_PIX[ss.persona][0]["nome"].split(" ")[0],
                 "Quanto está minha fatura?", "Onde gastei mais esse mês?", "Comprovante do último Pix", "Bloqueia meu cartão"]
    esc = st.pills("Sugestões", sugestoes, key="sug_chat", label_visibility="collapsed")

    conversa = st.container()
    with conversa:
        if not ss.chat:
            with st.chat_message("assistant", avatar=AV):
                extra = (" Vi que você prefere falar com uma pessoa quando algo foge do normal — pode pedir a qualquer momento "
                         "que eu passo para o Rafael com prioridade." if ss.prefere_humano else
                         " E se em algum momento você preferir falar com uma pessoa, é só me dizer que eu chamo alguém da equipe — sem você repetir nada.")
                st.markdown(f"Oi, {ss.nome}! Eu sou a **{ASSISTENTE}**, assistente do Superapp. Sou uma IA, mas resolvo de verdade: "
                            "faço Pix, pago contas, mostro sua fatura, gastos e comprovantes." + extra + " O que você precisa hoje?")
        for h in ss.chat:
            with st.chat_message(h["role"], avatar="🧑" if h["role"] == "user" else AV):
                st.markdown(h["content"])
        if ss.fila_humano:
            f = ss.fila_humano
            st.markdown(f'<div class="sa-card alerta"><div class="titulo">🙋 Rafael, da nossa equipe, vai assumir</div><div class="sub">'
                        f'Motivo: {f["motivo"]}. Você é o nº {f["posicao"]} da fila {"prioritária" if f["posicao"] <= 2 else ""} '
                        f'(espera estimada {f["espera"]}). O Rafael já está lendo esta conversa — você não precisa repetir nada.</div></div>',
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📞 Prefiro que me liguem", width="stretch", type="primary"):
                    st.success("Combinado. O Rafael liga em até " + f["espera"] + ".")
                    evento("Assistente", "callback", f)
            with c2:
                if st.button(f"Continuar com a {ASSISTENTE}", width="stretch"):
                    ss.fila_humano = None
                    st.rerun()

    # caixa de mensagem logo abaixo da conversa (dentro de um container ela deixa de ficar presa ao rodapé)
    with st.container():
        entrada = st.chat_input(f"Fale com a {ASSISTENTE} do seu jeito…", key="chat_assistente")
        _botao_microfone()

    msg = entrada or esc
    if msg and msg != ss.get("_ultima_sugestao"):
        if esc and not entrada:
            ss["_ultima_sugestao"] = esc
        with conversa:
            with st.chat_message("user", avatar="🧑"):
                st.markdown(msg)
            with st.chat_message("assistant", avatar=AV):
                espaco = st.empty()
                espaco.caption(f"{ASSISTENTE} está digitando…")
                r, destino = _processar_mensagem(msg, "Assistente")
                espaco.empty()
                st.write_stream(_digitando(r["resposta"]))
        if destino:
            import time
            st.info(f"Abrindo {destino} para você…")
            time.sleep(0.8)
            ir_para(destino)
        st.rerun()
    if ss.get("ia_erro"):
        st.caption(f"⚠️ A API não respondeu ({ss['ia_erro'][:80]}…); usei o motor por regras.")


# ----------------------------------------------------------------------------- segurança
def tela_seguranca() -> None:
    ss = st.session_state
    p = persona()
    st.markdown("### 🛡️ Central de segurança")
    st.markdown('<div class="sa-card ok"><div class="titulo">Tudo certo com sua conta</div><div class="sub">'
                "Último acesso: hoje, 08:12, do seu aparelho habitual. Nenhuma operação suspeita nas últimas 24h.</div></div>",
                unsafe_allow_html=True)
    st.markdown("#### Se algo aconteceu agora")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚨 Fui vítima de golpe", type="primary", width="stretch"):
            ss.cartao_bloqueado = True
            ss.limite_pix_noturno = 0
            ss.fila_humano = {"motivo": "segurança — golpe relatado", "posicao": 1, "espera": "imediato"}
            evento("Segurança", "golpe", {})
            st.rerun()
    with c2:
        if st.button("📵 Perdi meu celular", width="stretch"):
            ss.fila_humano = {"motivo": "segurança — aparelho perdido", "posicao": 1, "espera": "imediato"}
            st.rerun()
    if ss.fila_humano and "segurança" in ss.fila_humano["motivo"]:
        st.markdown('<div class="sa-card perigo"><div class="titulo">Protegemos sua conta</div><div class="sub">'
                    "Cartão bloqueado, Pix noturno zerado e um atendente humano da equipe de segurança está sendo conectado agora "
                    "(fila prioritária, sem espera). Ele já vê o que aconteceu — você não precisa repetir.</div></div>",
                    unsafe_allow_html=True)
        if st.button("📞 Falar com a equipe de segurança agora", type="primary", width="stretch"):
            st.success("Conectando… (simulado). Um atendente humano assume a partir daqui.")
    st.markdown("#### Proteções ativas")
    st.toggle("Confirmação reforçada em Pix e compras fora do padrão", value=True,
              help="A IA aprende seu padrão de uso e pede senha só quando algo foge dele.")
    st.toggle("Alertas antifraude em linguagem simples", value=True)
    st.markdown("#### Contato de confiança")
    st.caption("Alguém que você escolhe para ser avisado quando uma operação sair do seu padrão — e que pode te ajudar a "
               "confirmar se é golpe. Você continua decidindo; a pessoa só recebe o aviso.")
    cc = ss.contato_confianca
    if cc:
        st.markdown(f'<div class="sa-card ok"><div class="titulo">👥 {cc["nome"]} · {cc["relacao"]}</div>'
                    f'<div class="sub">Avisado por WhatsApp em: Pix acima de {D.brl(p["pix_padrao_max"])}, compra em outro estado, '
                    f'troca de celular. Nunca vê seu saldo nem movimenta sua conta.</div></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Testar aviso", width="stretch"):
                st.toast(f"Aviso de teste enviado para {cc['nome']} (simulado).")
        with c2:
            if st.button("Remover contato", width="stretch"):
                ss.contato_confianca = None
                st.rerun()
    else:
        with st.form("form_cc"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome", placeholder="Ex.: Ana")
            relacao = c2.selectbox("Relação", ["filho(a)", "cônjuge", "irmão(ã)", "amigo(a)", "outro"])
            st.text_input("Celular", placeholder="(11) 9xxxx-xxxx")
            if st.form_submit_button("Cadastrar contato de confiança", type="primary", width="stretch"):
                if nome.strip():
                    ss.contato_confianca = {"nome": nome.strip(), "relacao": relacao}
                    evento("Segurança", "contato_confianca", {})
                    st.rerun()
                else:
                    st.warning("Informe o nome.")
    ss.modo_viagem = st.toggle("Modo viagem (libera compras em outro estado/país)", value=ss.modo_viagem)
    st.toggle("Bloquear Pix noturno (20h–6h) acima de " + D.brl(ss.limite_pix_noturno), value=True)
    st.markdown("#### Verificar se uma mensagem é golpe")
    txt = st.text_area("Cole aqui o SMS, e-mail ou mensagem que recebeu", placeholder="Ex.: 'Sua conta será bloqueada, clique no link…'")
    if txt:
        m = txt.lower()
        sinais = [s for s in ["link", "clique", "urgente", "bloquead", "senha", "atualize", "prêmio", "premio", "sorteio", "central 0800", "whatsapp"] if s in m]
        if sinais:
            estilo.card("🚩 Alto risco de golpe", "Sinais encontrados: " + ", ".join(sinais) + ". O Superapp nunca pede senha, "
                        "nem envia links por SMS. Não clique e, se já clicou, toque em 'Fui vítima de golpe'.", "perigo")
        else:
            estilo.card("Sem sinais claros de golpe", "Mesmo assim, confirme pelo app ou pela central oficial antes de agir.", "ok")
    st.markdown("#### Dispositivos conectados")
    estilo.linhas([("iPhone de " + p["primeiro_nome"], "Este aparelho · São Paulo", "ativo", True),
                   ("Notebook Windows", "Acesso web · 3 dias atrás", "encerrar", False)])


# ----------------------------------------------------------------------------- crédito e seguros
def tela_credito() -> None:
    ss = st.session_state
    p = persona()
    st.markdown("### 🏦 Crédito pessoal")
    disp = credito_disponivel()
    contratos = ss.credito["contratos"]
    pend = ss.credito_pendente or {}

    if contratos:
        st.markdown("#### Seus contratos")
        for k, c in enumerate(contratos):
            pagas = c["pagas"]
            selo = estilo.pill(f"{pagas}/{c['parcelas']} pagas", "azul")
            st.markdown(f'<div class="sa-card"><div class="titulo">Empréstimo de {D.brl(c["valor"])} {selo}</div>'
                        f'<div class="sub">Parcela {D.brl(c["parcela"])} · saldo devedor {D.brl(c["saldo_devedor"])} · próxima em 05/10/2026</div></div>',
                        unsafe_allow_html=True)
            st.progress(pagas / c["parcelas"], text=f"{pagas / c['parcelas']:.0%} quitado")
            if st.button("Antecipar parcela (com desconto de juros)", key=f"antecipa_{k}", width="stretch"):
                if c["parcela"] > ss.saldo:
                    st.error("Saldo insuficiente.")
                else:
                    c["pagas"] += 1
                    c["saldo_devedor"] = round(max(c["saldo_devedor"] - c["parcela"] * 0.97, 0), 2)
                    lancar("Antecipação de parcela — crédito", -round(c["parcela"] * 0.97, 2), "Crédito")
                    st.rerun()
        st.divider()

    if disp < 500:
        estilo.card("Novo crédito em reanálise", "Seu limite pré-aprovado está comprometido com o contrato atual. "
                    "Conforme as parcelas forem pagas, o limite volta a ficar disponível.", "alerta")
        return

    estilo.card("Pré-aprovado para você", f"Até {valor(disp)} · a partir de 1,49% a.m. · sem consulta adicional. "
                "Só é ofertado aqui porque você ativou o produto — não aparece em notificação.", "ok")
    if pend:
        estilo.card("✨ Preparado pela Lia", f"Empréstimo de {D.brl(pend['valor'])} em {pend['parcelas']}x. Confira e confirme.", "ia")
    v_ini = float(min(max(pend.get("valor") or 3000.0, 500.0), disp))
    v = st.slider("Quanto você precisa?", 500.0, float(disp), v_ini, 100.0, format="R$ %.0f")
    opcoes_n = [6, 12, 18, 24, 36, 48]
    n_ini = pend.get("parcelas", 12) if pend.get("parcelas", 12) in opcoes_n else 12
    n = st.select_slider("Em quantas parcelas?", options=opcoes_n, value=n_ini)
    i = 0.0149
    parcela = v * i / (1 - (1 + i) ** -n)
    c1, c2, c3 = st.columns(3)
    c1.metric("Parcela", D.brl(parcela))
    c2.metric("Total", D.brl(parcela * n))
    c3.metric("CET aprox.", f"{((1 + i) ** 12 - 1):.1%} a.a.")
    if parcela > 0.3 * p["salario"]:
        estilo.card("✨ Leitura da IA", f"Essa parcela compromete {parcela / p['salario']:.0%} da sua renda. "
                    "Recomendo até 30%: experimente mais parcelas ou um valor menor.", "alerta")
    else:
        estilo.card("✨ Leitura da IA", f"Parcela dentro do saudável ({parcela / p['salario']:.0%} da renda). "
                    "O dinheiro cai na conta na hora.", "ia")
    if ss.get("credito_confirmando") or st.button("Contratar", type="primary", width="stretch"):
        ss.credito_confirmando = True
        if confirmar_senha("credito", f"Empréstimo de {D.brl(v)} em {n}x de {D.brl(parcela)}."):
            contratos.append({"valor": v, "parcelas": n, "parcela": round(parcela, 2), "pagas": 0,
                              "saldo_devedor": round(parcela * n, 2)})
            lancar("Crédito pessoal liberado", v, "Renda")
            ss.credito_pendente = None
            ss.credito_confirmando = False
            evento("Crédito", "contratado", {"valor": v, "parcelas": n})
            st.success("Crédito liberado na sua conta. O contrato já aparece no seu card de Crédito.")
            st.rerun()


def tela_seguros() -> None:
    st.markdown("### ☂️ Seguros")
    for nome, cob, valor_m, status in [("Seguro de vida", "R$ 100.000 · cobertura 24h", 24.90, "ativo"),
                                        ("Seguro celular", "Roubo, furto e quebra · franquia 15%", 15.00, "ativo"),
                                        ("Residencial", "Incêndio, roubo e assistência", 29.90, "disponível")]:
        selo = estilo.pill("ativo", "verde") if status == "ativo" else estilo.pill("disponível", "azul")
        st.markdown(f'<div class="sa-card"><div class="titulo">{nome} {selo}</div>'
                    f'<div class="sub">{cob} · {D.brl(valor_m)}/mês</div></div>', unsafe_allow_html=True)
    estilo.card("Acionar um seguro", "Sem formulário: descreva o que aconteceu para a Lia e ela abre o sinistro com você.", "ia")
    if st.button("Falar com a Lia sobre um sinistro", width="stretch"):
        ir_para("Assistente")
        st.rerun()


# ----------------------------------------------------------------------------- avaliação
FAIXAS = ["16–24", "25–34", "35–44", "45–54", "55–64", "65+"]
OCUPACOES = ["CLT", "Servidor público", "Autônomo/PJ", "Estudante", "Aposentado", "Outro"]
BANCOS = ["Itaú", "Nubank", "Bradesco", "Banco do Brasil", "Caixa", "Santander", "Inter", "PicPay", "C6", "Outro"]
FREQ = ["Várias vezes ao dia", "Diariamente", "Algumas vezes por semana", "Raramente"]
PREF = ["Resolver na hora, mesmo que automático", "Falar com uma pessoa, mesmo esperando mais", "Depende do problema"]
MODULOS = [("nota_inicio", "Tela inicial e atalhos"), ("nota_pix", "Pix"), ("nota_cartao", "Cartão"),
           ("nota_pagamentos", "Pagamentos"), ("nota_extrato", "Extrato"), ("nota_investimentos", "Investimentos"),
           ("nota_gastos", "Controle de gastos"), ("nota_notificacoes", "Notificações"),
           ("nota_assistente", "Assistente com IA"), ("nota_seguranca", "Central de segurança")]


def tela_avaliar() -> None:
    ss = st.session_state
    st.markdown("### ⭐ Avalie o protótipo")
    if ss.avaliado:
        estilo.card("Obrigado! 🙏", "Sua avaliação foi registrada. Você pode continuar explorando o app.", "ok")
        return
    faltam = [t for t in TELAS if t not in ss.telas_visitadas and t != "Avalie"]
    if faltam:
        st.info("Você ainda não visitou: " + ", ".join(faltam) + ". Pode avaliar mesmo assim — deixe em branco o que não viu.")
    with st.form("avaliacao"):
        st.markdown("**De 0 a 10, qual a chance de você recomendar este app para um amigo?**")
        nps = st.slider("NPS", 0, 10, 8, label_visibility="collapsed")
        st.markdown("**Dê uma nota de 1 a 5 para cada parte (0 = não vi)**")
        notas = {}
        c1, c2 = st.columns(2)
        for i, (k, rot) in enumerate(MODULOS):
            with (c1 if i % 2 == 0 else c2):
                notas[k] = st.select_slider(rot, options=[0, 1, 2, 3, 4, 5], value=0)
        st.markdown("**Sobre você** (para cruzar com a pesquisa anterior)")
        c1, c2 = st.columns(2)
        with c1:
            faixa = st.selectbox("Faixa etária", FAIXAS, index=None, placeholder="Selecione")
            ocup = st.selectbox("Ocupação", OCUPACOES, index=None, placeholder="Selecione")
        with c2:
            banco = st.selectbox("Banco que mais usa", BANCOS, index=None, placeholder="Selecione")
            freq = st.selectbox("Frequência de uso de apps de banco", FREQ, index=None, placeholder="Selecione")
        pref = st.radio("Fora do horário comercial, você prefere…", PREF, index=None)
        gostou = st.text_area("O que você mais gostou?", height=80)
        mudaria = st.text_area("Se pudesse mudar uma única coisa, o que seria?", height=80)
        coment = st.text_area("Comentário livre (opcional)", height=70)
        nome = st.text_input("Nome (opcional)")
        enviar = st.form_submit_button("Enviar avaliação", type="primary", width="stretch")
    if enviar:
        reg = {"persona": ss.persona, "nps": nps, "faixa_etaria": faixa, "ocupacao": ocup, "banco_principal": banco,
               "frequencia_uso": freq, "preferencia_atendimento": pref, "o_que_mais_gostou": gostou,
               "o_que_mudaria": mudaria, "comentario": coment, "nome_opcional": nome,
               "modo_ia": "api" if ia.api_disponivel() else "regras", **notas}
        ok, msg = db.salvar_avaliacao(reg)
        if ok:
            ss.avaliado = True
            evento("Avalie", "enviada", {"nps": nps})
            st.success(msg)
            st.balloons()
            st.rerun()
        else:
            st.error(msg)


def tela_resultados() -> None:
    st.markdown("### 📊 Resultados da pesquisa")
    try:
        senha_ok = st.secrets["admin"]["senha"]
    except Exception:
        senha_ok = "fiap2026"
    if not st.session_state.get("admin"):
        s = st.text_input("Senha do grupo", type="password")
        if st.button("Entrar"):
            if s == senha_ok:
                st.session_state.admin = True
                st.rerun()
            st.error("Senha incorreta.")
        return
    df = db.listar_avaliacoes()
    st.caption(("Fonte: Supabase" if db.usando_supabase() else "Fonte: CSV local") + f" · {len(df)} avaliação(ões)")
    if df.empty:
        st.info("Nenhuma avaliação ainda.")
        return
    nps_s = pd.to_numeric(df["nps"], errors="coerce").dropna()
    prom = (nps_s >= 9).sum()
    det = (nps_s <= 6).sum()
    neu = len(nps_s) - prom - det
    nps = (prom - det) / len(nps_s) * 100 if len(nps_s) else 0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("NPS", f"{nps:+.1f}")
    m2.metric("Promotores", int(prom))
    m3.metric("Neutros", int(neu))
    m4.metric("Detratores", int(det))
    st.caption("Linha de base da pesquisa de campo (Fase 03): NPS +35,7 (24 promotores, 28 neutros, 4 detratores, n=56).")
    st.markdown("#### Nota média por módulo (1–5, ignorando 0 = não viu)")
    medias = {}
    for k, rot in MODULOS:
        s = pd.to_numeric(df[k], errors="coerce")
        s = s[s > 0]
        if len(s):
            medias[rot] = round(float(s.mean()), 2)
    if medias:
        st.bar_chart(pd.Series(medias).sort_values(), color=estilo.LARANJA, horizontal=True, height=320)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Por persona")
        st.dataframe(df.groupby("persona")["nps"].agg(["count", "mean"]).round(1), width="stretch")
    with c2:
        st.markdown("#### Preferência de atendimento")
        st.dataframe(df["preferencia_atendimento"].value_counts(), width="stretch")
    st.markdown("#### Respostas abertas")
    st.dataframe(df[["criado_em", "persona", "nps", "o_que_mais_gostou", "o_que_mudaria", "comentario"]], width="stretch", hide_index=True)
    st.download_button("⬇️ Baixar todas as avaliações (CSV)", df.to_csv(index=False).encode("utf-8"), "avaliacoes.csv", "text/csv")
    ev = db.listar_eventos()
    if not ev.empty:
        st.markdown("#### Uso do protótipo (telemetria)")
        st.dataframe(ev.groupby(["tela", "acao"]).size().rename("eventos").reset_index().sort_values("eventos", ascending=False),
                     width="stretch", hide_index=True)
