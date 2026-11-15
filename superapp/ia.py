"""Assistente do Superapp.

Dois motores:
1. API Claude (quando há chave em st.secrets["anthropic"]["api_key"]): entende linguagem
   natural e devolve JSON com resposta + ação a executar.
2. Regras (fallback): reconhecimento de intenção por expressões regulares.

Em ambos os casos, uma camada de segurança detecta frustração e temas sensíveis
(golpe, fraude) e força o escalonamento para atendimento humano — a "chave
inteligente" (switch) descrita na Fase 03.
"""
from __future__ import annotations

import json
import re
import unicodedata

import streamlit as st

from . import dados as D

MODELO_PADRAO = "claude-haiku-4-5-20251001"

PALAVRAS_FRUSTRACAO = [
    "nao resolve", "de novo", "outra vez", "ja falei", "ja disse", "irritad", "absurdo", "ninguem",
    "pessimo", "horrivel", "cansei", "que raiva", "ridiculo", "nao entende", "nao ajuda",
    "quero falar com", "atendente", "humano", "uma pessoa", "gente de verdade", "gerente",
]
PALAVRAS_SEGURANCA = [
    "golpe", "fraude", "roubar", "roubaram", "clonad", "clonar", "clonaram", "nao reconheco", "nao fui eu", "invadir",
    "invadiram", "hacke", "suspeit", "estranh", "perdi o celular", "roubaram meu celular", "senha vazou",
]


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def detectar_sinais(mensagem: str) -> tuple[bool, bool]:
    m = _norm(mensagem)
    frustrado = any(p in m for p in PALAVRAS_FRUSTRACAO)
    seguranca = any(p in m for p in PALAVRAS_SEGURANCA)
    return frustrado, seguranca


def api_disponivel() -> bool:
    try:
        return bool(st.secrets["anthropic"]["api_key"])
    except Exception:
        return False


def _fatura(ctx: dict) -> float:
    return float(ctx.get("fatura", ctx["persona"]["fatura_atual"]))


def _investido(ctx: dict) -> float:
    invs = ctx.get("investimentos")
    return float(sum(i["valor"] for i in invs)) if invs else float(ctx["persona"]["patrimonio_inv"])


# erros comuns de digitação e ditado vistos nas avaliações — corrigidos antes de interpretar
CORRECOES = {
    r"\blus\b": "luz", r"\bcomprovanti\w*": "comprovante", r"\bcomprovate\b": "comprovante", r"\bdentita\b": "dentista",
    r"\bintend\w*": "entendeu", r"\b(pisinero|pisineiro|piscinero|pineiro)\b": "piscineiro", r"\birma\b": "irmã",
    r"\bmae\b": "mãe", r"\bfatrua\b": "fatura", r"\bextarto\b": "extrato", r"\binvestimeto\w*": "investimento",
}
# apelidos de contas: "luz" = Enel, "internet" = Vivo, "água" = Sabesp
SINONIMOS_CONTA = {"luz": "enel", "energia": "enel", "internet": "vivo", "wifi": "vivo", "agua": "sabesp"}


def corrigir_digitacao(texto: str) -> str:
    t = texto
    for padrao, certo in CORRECOES.items():
        t = re.sub(padrao, certo, t, flags=re.I)
    return t


def _contexto_texto(ctx: dict) -> str:
    p = ctx["persona"]
    contas = "\n".join(
        f"- {c['descricao']}: {D.brl(c['valor'])}, vence {D.data_br(c['vencimento'])} ({c['status']})"
        for c in ctx["contas"]
    )
    contatos = "\n".join(f"- {c['nome']} ({c['banco']})" for c in ctx["contatos"])
    gastos = "\n".join(f"- {k}: {D.brl(v)}" for k, v in ctx["gastos_categoria"].items())
    invs = "\n".join(f"- {i['produto']} ({i['tipo']}): {D.brl(i['valor'])}, rentabilidade 12m {i['rent_12m']:.1%}, liquidez {i['liquidez']}"
                     for i in ctx.get("investimentos", [])) or "- nenhum"
    contratos = "".join(f"; contrato de {D.brl(c['valor'])} em {c['parcelas']}x de {D.brl(c['parcela'])}" for c in ctx.get("contratos", []))
    prods = ", ".join(k for k, v in ctx.get("produtos", {}).items() if v) or "só conta corrente"
    return f"""
PRIMEIRO NOME DO CLIENTE: {p['primeiro_nome']} (use SOMENTE este nome; nunca outro).
CLIENTE: {p['nome']}, {p['idade']} anos. Cliente há {p['tempo_cliente']}. {p['descricao']}
Prefere atendimento humano em temas sensíveis: {"sim" if p['prefere_humano'] else "não, prefere resolver sozinho"}.

SALDO EM CONTA: {D.brl(ctx['saldo'])}
CARTÃO: fatura atual {D.brl(_fatura(ctx))}{" (já paga)" if _fatura(ctx) == 0 else ""}, vence {D.data_br(p['fatura_vencimento'])}; limite {D.brl(p['limite_cartao'])}, disponível {D.brl(p['limite_cartao'] - _fatura(ctx))}. Cartão {"BLOQUEADO" if ctx['cartao_bloqueado'] else "ativo"}.
INVESTIMENTOS: total investido hoje {D.brl(_investido(ctx))}.
CONTAS A PAGAR:
{contas}
CONTATOS PIX FAVORITOS:
{contatos}
GASTOS DO MÊS POR CATEGORIA (conta corrente):
{gastos}
CONFIRMAÇÃO: todo Pix, pagamento, aplicação e empréstimo é confirmado pelo cliente na tela (rosto ou senha), qualquer valor.
Pix acima de {D.brl(p['pix_padrao_max'])} também avisa o contato de confiança.
INVESTIMENTOS (produtos que o cliente já tem; aplicar/resgatar usa um destes nomes):
{invs}
CRÉDITO PESSOAL: pré-aprovado disponível {D.brl(ctx.get('credito_disponivel', 0))}, a partir de 1,49% a.m., parcelas de 6 a 48x.
Dívida atual: {D.brl(ctx.get('divida', 0))}{contratos}.
PRODUTOS ATIVOS NO APP: {prods}.
PREFERE ATENDIMENTO HUMANO EM TEMAS SENSÍVEIS: {"sim — ofereça o Rafael mais cedo, na 1ª dúvida não resolvida" if ctx.get("prefere_humano") else "não"}.
CONTATO DE CONFIANÇA: {ctx.get("contato_confianca") or "não cadastrado (sugira em Segurança se o tema for golpe)"}. Produtos que podem ser ativados: cartao, investimentos, credito, seguros.
"""


SISTEMA = """Você é a Lia, assistente do Superapp, um banco digital fictício usado em um protótipo acadêmico (FIAP).
Você é uma IA e não esconde isso, mas fala como uma pessoa da equipe: calorosa, direta, sem formalidade excessiva.
Chame o cliente pelo PRIMEIRO NOME DO CONTEXTO de vez em quando (não em toda frase) e nunca por outro nome.
Não presuma gênero: evite "obrigado/obrigada", "o senhor/a senhora" e adjetivos de gênero. Reconheça a situação antes de dar o número
("Entendi, vamos ver isso juntos."). Português do Brasil, 2 a 4 frases, sem listas. Nunca invente dados: use apenas o CONTEXTO.
Você EXECUTA ações, não apenas orienta. Quando o cliente pedir algo executável, devolva a ação correspondente.

Responda SEMPRE e SOMENTE com um JSON válido neste formato:
{"resposta": "<texto para o cliente>", "acao": {"tipo": "<tipo>", ...campos}}

Tipos de ação permitidos:
- {"tipo": "nenhuma"}
- {"tipo": "pix", "valor": <número>, "destinatario": "<nome do contato favorito ou chave>"}
- {"tipo": "pagar_conta", "descricao": "<nome da conta como aparece no contexto>"}
- {"tipo": "bloquear_cartao"} / {"tipo": "desbloquear_cartao"}
- {"tipo": "ver_fatura"} / {"tipo": "ver_extrato"} / {"tipo": "ver_gastos"} / {"tipo": "ver_investimentos"} / {"tipo": "ver_credito"}
- {"tipo": "aplicar", "produto": "<nome do investimento do contexto>", "valor": <número>}
- {"tipo": "resgatar", "produto": "<nome do investimento do contexto>", "valor": <número>}
- {"tipo": "contratar_credito", "valor": <número>, "parcelas": <6|12|18|24|36|48>}
- {"tipo": "cartao_virtual"}
- {"tipo": "pagar_boleto", "codigo": "<código de barras/linha digitável que o cliente enviou>"}
- {"tipo": "ativar_produto", "produto": "<cartao|investimentos|credito|seguros>"}
- {"tipo": "comprovante", "busca": "<valor ou nome citado, ex.: 50 ou Mãe>"} — abre os comprovantes já filtrados
- {"tipo": "escalar_humano", "motivo": "<motivo curto>"}

Regras:
- Se faltar um dado essencial para a ação (ex.: valor do Pix), pergunte e use "nenhuma". Se o pedido já tem valor e
  destinatário, NÃO pergunte de novo: devolva a ação.
- Você só PREPARA a operação; quem conclui é o cliente, confirmando na tela. NUNCA diga "enviei", "paguei", "apliquei",
  "contratei" ou "já foi": diga "Preparei ... é só confirmar na tela". NUNCA diga que não precisa de senha ou confirmação.
- Pix para alguém que não está nos favoritos (ex.: "minha irmã" sem "Irmã" na lista): use "pix" com destinatario = o nome
  citado; a tela abre para digitar a chave. Nunca troque por outro contato da lista.
- Comprovante: nunca pergunte valor ou destinatário. Use "comprovante" com o que o cliente citou (nome ou valor) ou, se
  ele não citou nada, busca "Pix" (abre o último Pix).
- Se o cliente mudar de assunto, abandone o pedido anterior e não volte a ele.
- A mensagem pode ter erros de digitação ("lus" = luz, "comprovanti" = comprovante): interprete pelo sentido.
- Contas por apelido: "luz"/"energia" = Enel; "internet" = Vivo; "água" = Sabesp.
- Investir sem dizer o produto: apresente em uma frase as opções do contexto (nome, rentabilidade, liquidez) e pergunte
  qual; se disser "o mais seguro/líquido", escolha o CDB. Com produto e valor, use "aplicar" — a pessoa confirma na tela.
- Empréstimo: mostre o pré-aprovado disponível; com valor (e parcelas, ou 12 por padrão) use "contratar_credito".
  Se a dívida atual já comprometer o pré-aprovado, explique que fica em reanálise — nunca escale por isso.
- NUNCA use "escalar_humano" só porque não há ação exata para o pedido: oriente e abra a tela mais próxima (ver_*).
  Escale apenas por frustração, pedido explícito de pessoa, ou tema de segurança.
- Se o cliente demonstrar frustração, repetir o problema, ou pedir uma pessoa: acolha, diga que vai chamar o Rafael
  da equipe e que ele já vê a conversa (não precisa repetir nada), e use "escalar_humano".
- Se o tema for golpe, fraude, compra não reconhecida, celular perdido ou senha vazada: primeiro proteja
  (sugira bloquear o cartão / limitar Pix) e use "escalar_humano" com motivo "segurança".
- Perguntas sobre saldo, fatura, contas, gastos e investimentos: responda com os números do contexto.
- Não fale de temas fora do banco; redirecione com gentileza.
- Saudação ("oi", "bom dia"): responda como pessoa ("Oi, <primeiro nome do contexto>! Em que posso te ajudar?"), sem listar o que você faz.
  Só liste suas funções se o cliente perguntar o que você faz ou se já não entendeu duas vezes.
- O texto pode vir de reconhecimento de voz, com palavras trocadas ("pineiro" por "piscineiro", "15 e 90" por R$ 15,90):
  interprete pelo contexto e pelos nomes do CONTEXTO antes de dizer que não entendeu.
"""


def _chamar_api(mensagem: str, historico: list[dict], ctx: dict) -> dict | None:
    try:
        import anthropic

        cliente = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])
        modelo = st.secrets["anthropic"].get("modelo", MODELO_PADRAO)
        msgs = [{"role": h["role"], "content": h["content"]} for h in historico[-8:]]
        msgs.append({"role": "user", "content": mensagem})
        resp = cliente.messages.create(
            model=modelo,
            max_tokens=400,
            system=[
                {"type": "text", "text": SISTEMA, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "CONTEXTO ATUAL:\n" + _contexto_texto(ctx)},
            ],
            messages=msgs,
        )
        texto = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        m = re.search(r"\{.*\}", texto, re.S)
        if not m:
            return {"resposta": texto.strip(), "acao": {"tipo": "nenhuma"}}
        obj = json.loads(m.group(0))
        obj.setdefault("acao", {"tipo": "nenhuma"})
        obj["uso"] = {"entrada": resp.usage.input_tokens, "saida": resp.usage.output_tokens}
        return obj
    except Exception as e:  # noqa: BLE001
        st.session_state["ia_erro"] = str(e)
        return None


def _contato_citado(nome: str, m: str) -> bool:
    """'Piscineiro (Seu Carlos)' é citado por "piscineiro" ou por "seu carlos"; "Irmã" por "irma"."""
    n = _norm(nome)
    partes = [n.split(" (")[0].split(" ")[0]] + [x.strip() for x in re.findall(r"\(([^)]+)\)", n)]
    return any(p and re.search(rf"\b{re.escape(p)}\b", m) for p in partes)


def _numero(texto: str) -> float | None:
    me = re.search(r"\b(\d+)\s*(?:reais\s*)?e\s*(\d{1,2})\b(?!\s*(x|vezes|parcelas))", texto)  # "15 e 90" = 15,90
    if me:
        return float(f"{me.group(1)}.{me.group(2).ljust(2, '0')}")
    t = texto.replace(".", "").replace(",", ".")
    m = re.search(r"(\d+(?:\.\d{1,2})?)\s*(mil)?", t)
    if not m:
        return None
    try:
        v = float(m.group(1))
        return v * 1000 if m.group(2) else v
    except ValueError:
        return None


def _regras(mensagem: str, ctx: dict) -> dict:
    m = _norm(mensagem)
    p = ctx["persona"]

    if re.search(r"\b(saldo|quanto (eu )?tenho|quanto tem na conta)\b", m) and not re.search(r"invest|aplicad|carteira|rend", m):
        return {"resposta": f"Seu saldo disponível é {D.brl(ctx['saldo'])}.", "acao": {"tipo": "nenhuma"}}

    if "comprovante" in m or "recibo" in m:
        valor = _numero(m)
        quem = None
        for c in ctx["contatos"]:
            if _contato_citado(c["nome"], m):
                quem = c["nome"].split(" (")[0]
        if not quem:
            # qualquer palavra da mensagem que apareça nas descrições do extrato (ex.: Vivo, Enel, iFood)
            palavras = [w for w in re.findall(r"[a-z0-9]{3,}", m) if w not in ("comprovante", "recibo", "pix", "pagamento", "para", "pra", "manda", "quero", "ultimo", "meu", "minha", "conta", "boleto")]
            for d in ctx.get("descricoes", []):
                dn = _norm(d)
                for w in palavras:
                    if w in dn:
                        quem = d.split("— ")[-1] if "— " in d else d
                        break
                if quem:
                    break
        busca = quem or (f"{valor:.2f}".replace(".", ",") if valor else "") or ("Pix" if "pix" in m else "")
        return {"resposta": "Abri seus comprovantes" + (f" filtrados por {busca}" if busca else "") + ". É só tocar em Baixar.",
                "acao": {"tipo": "comprovante", "busca": busca}}

    if "pix" in m or "transfer" in m or re.search(r"\b(manda|mande|envia|envie|passa|paga)\b.*\b(pra|pro|para)\b", m):
        valor = _numero(m)
        dest = None
        for c in ctx["contatos"]:
            if _contato_citado(c["nome"], m):
                dest = c["nome"]
                break
        if valor and dest:
            return {"resposta": f"Preparei um Pix de {D.brl(valor)} para {dest}. Confira e confirme.",
                    "acao": {"tipo": "pix", "valor": valor, "destinatario": dest}}
        mq = re.search(r"\b(?:pra|pro|para)\s+(?:a |o |minha |meu )?([a-z][a-z ]{1,25}?)(?:\s+\d|$)", m)
        if valor and mq and mq.group(1).strip() not in ("mim", "voce", "vc"):
            nome_citado = mq.group(1).strip().title()
            return {"resposta": f"Não achei {nome_citado} nos seus favoritos. Abri o Pix de {D.brl(valor)}: é só informar a chave e confirmar.",
                    "acao": {"tipo": "pix", "valor": valor, "destinatario": nome_citado}}
        if valor:
            return {"resposta": f"Pix de {D.brl(valor)} — para quem? Seus favoritos: "
                    + ", ".join(c["nome"].split(" (")[0] for c in ctx["contatos"]) + ".",
                    "acao": {"tipo": "nenhuma"}}
        return {"resposta": "Claro! Me diga o valor e para quem (ex.: \"manda 50 pra Ana\").", "acao": {"tipo": "nenhuma"}}

    if "fatura" in m or ("cartao" in m and ("quanto" in m or "gast" in m)):
        if _fatura(ctx) == 0:
            return {"resposta": "Sua fatura deste mês já está paga. Abri o cartão para você ver as compras.", "acao": {"tipo": "ver_fatura"}}
        return {"resposta": f"Sua fatura atual está em {D.brl(_fatura(ctx))} e vence em "
                f"{D.data_br(p['fatura_vencimento'])}. Limite disponível: {D.brl(p['limite_cartao'] - _fatura(ctx))}.",
                "acao": {"tipo": "ver_fatura"}}

    if "bloque" in m and "cartao" in m:
        if "desbloque" in m:
            return {"resposta": "Cartão desbloqueado. Se notar algo estranho, é só me chamar.", "acao": {"tipo": "desbloquear_cartao"}}
        return {"resposta": "Feito: seu cartão está bloqueado preventivamente. Você pode desbloquear quando quiser.",
                "acao": {"tipo": "bloquear_cartao"}}

    if "limite" in m:
        return {"resposta": f"Seu limite total é {D.brl(p['limite_cartao'])}; disponível agora: "
                f"{D.brl(p['limite_cartao'] - _fatura(ctx))}.", "acao": {"tipo": "nenhuma"}}

    mb = re.search(r"(\d[\d .]{30,60}\d)", mensagem)
    if mb and ("boleto" in m or "codigo" in m or "barras" in m or len(re.sub(r"\D", "", mb.group(1))) >= 44):
        return {"resposta": "Identifiquei o boleto. Abri o pagamento com o código preenchido e a verificação antifraude feita — é só confirmar.",
                "acao": {"tipo": "pagar_boleto", "codigo": mb.group(1)}}

    # "pagar a Vivo Fibra", "paga a conta vencida": vai direto ao pagamento da conta citada
    if re.search(r"\b(paga|pagar|pague|quita|quitar)\b", m):
        pend = [c for c in ctx["contas"] if c["status"] != "paga"]
        alvo = next((c for c in pend if _norm(c["descricao"].split(" ")[0]) in m), None)
        if not alvo:
            for apelido, chave in SINONIMOS_CONTA.items():
                if re.search(rf"\b{apelido}\b", m):
                    alvo = next((c for c in pend if chave in _norm(c["descricao"])), None)
                    if alvo:
                        break
        if not alvo and "vencid" in m:
            alvo = next((c for c in pend if c["status"] == "vencida"), None)
        if alvo:
            return {"resposta": f"Preparei o pagamento de {alvo['descricao']} ({D.brl(alvo['valor'])}). Confirme na tela.",
                    "acao": {"tipo": "pagar_conta", "descricao": alvo["descricao"]}}

    if re.search(r"\b(conta|boleto|luz|agua|energia|internet|condominio|aluguel|mensalidade)\b", m) and \
            re.search(r"\b(paga|pagar|vence|vencid|atras|pendente|aberta)\w*", m):
        pend = [c for c in ctx["contas"] if c["status"] != "paga"]
        venc = [c for c in pend if c["status"] == "vencida"]
        alvo = None
        for c in pend:
            if _norm(c["descricao"].split(" ")[0]) in m:
                alvo = c
        if alvo and re.search(r"\b(paga|pagar)\b", m):
            return {"resposta": f"Preparei o pagamento de {alvo['descricao']} ({D.brl(alvo['valor'])}). Confirme na tela.",
                    "acao": {"tipo": "pagar_conta", "descricao": alvo["descricao"]}}
        txt = "; ".join(f"{c['descricao']} {D.brl(c['valor'])} ({D.data_br(c['vencimento'])})" for c in pend)
        extra = f" Atenção: {venc[0]['descricao']} está vencida." if venc else ""
        return {"resposta": f"Contas em aberto: {txt}.{extra} Quer que eu pague alguma?", "acao": {"tipo": "nenhuma"}}

    if "gast" in m or "onde foi" in m or "categoria" in m:
        top = sorted(ctx["gastos_categoria"].items(), key=lambda kv: kv[1], reverse=True)[:3]
        txt = ", ".join(f"{k} ({D.brl(v)})" for k, v in top)
        return {"resposta": f"Neste mês seus maiores gastos foram: {txt}. Abri o controle de gastos para você.",
                "acao": {"tipo": "ver_gastos"}}

    if re.search(r"\b(emprest|credito|financi)\w*", m) or (re.search(r"\b(preciso|precisando|pega|pegar)\b", m) and (_numero(m) or 0) >= 500 and "pix" not in m and "invest" not in m and "aplic" not in m):
        disp = ctx.get("credito_disponivel", 0)
        if disp < 500:
            return {"resposta": f"Seu pré-aprovado está comprometido com o contrato atual (dívida de {D.brl(ctx.get('divida', 0))}). "
                    "Um novo crédito fica em reanálise conforme as parcelas forem pagas.", "acao": {"tipo": "ver_credito"}}
        valor = _numero(m)
        mp = re.search(r"(\d+)\s*(x|vezes|parcelas)", m)
        parcelas = int(mp.group(1)) if mp else 12
        if valor and valor >= 500:
            return {"resposta": f"Preparei um empréstimo de {D.brl(valor)} em {parcelas}x, dentro do seu pré-aprovado de {D.brl(disp)}. "
                    "Confira a parcela e confirme com sua senha.", "acao": {"tipo": "contratar_credito", "valor": valor, "parcelas": parcelas}}
        return {"resposta": f"Você tem {D.brl(disp)} pré-aprovados, a partir de 1,49% ao mês, em até 48x. "
                "Me diga o valor e em quantas vezes (ex.: \"3 mil em 12x\") que eu preparo.", "acao": {"tipo": "ver_credito"}}

    if "invest" in m or "render" in m or "aplic" in m or "resgat" in m:
        invs = ctx.get("investimentos", [])
        valor = _numero(m)
        op = "resgatar" if "resgat" in m else "aplicar"
        alvo = None
        for i in invs:
            chave = _norm(i["produto"]).split(" ")[0]
            if chave in m or (("segur" in m or "liquid" in m) and "cdb" in _norm(i["produto"])):
                alvo = i["produto"]
                break
        if valor and alvo:
            return {"resposta": f"Preparei {'um resgate' if op == 'resgatar' else 'uma aplicação'} de {D.brl(valor)} em {alvo}. Confira e confirme.",
                    "acao": {"tipo": op, "produto": alvo, "valor": valor}}
        if "aplic" in m or "resgat" in m or "quero invest" in m:
            opcoes = "; ".join(f"{i['produto']} ({i['rent_12m']:.1%} a.a., liquidez {i['liquidez']})" for i in invs)
            return {"resposta": f"Suas opções: {opcoes}. Me diga o produto e o valor (ex.: \"aplica 500 no CDB\").",
                    "acao": {"tipo": "nenhuma"}}
        return {"resposta": f"Hoje você tem {D.brl(_investido(ctx))} investidos. Abri a tela de investimentos.",
                "acao": {"tipo": "ver_investimentos"}}

    if "virtual" in m and "cart" in m:
        return {"resposta": "Criei um cartão virtual para você, válido por 24h para compras online. Os dados estão logo abaixo.",
                "acao": {"tipo": "cartao_virtual"}}

    if "seguro" in m and ("quero" in m or "ativar" in m or "contratar" in m):
        return {"resposta": "Ativei Seguros no seu app. Você já tem vida e celular disponíveis; veja no card da tela inicial.",
                "acao": {"tipo": "ativar_produto", "produto": "seguros"}}

    if "extrato" in m or "movimenta" in m:
        return {"resposta": "Abri seu extrato. Você pode filtrar por período e tipo.", "acao": {"tipo": "ver_extrato"}}

    if re.search(r"\b(o que (voce|vc) (faz|sabe|consegue)|me ajuda|ajuda|como funciona)\b", m):
        return {"resposta": f"Claro, {p['primeiro_nome']}. Eu faço Pix, pago contas, mostro saldo, fatura, gastos e investimentos, "
                "bloqueio o cartão e, se precisar, chamo alguém da equipe. É só pedir.", "acao": {"tipo": "nenhuma"}}

    if re.search(r"\b(oi|ola|bom dia|boa tarde|boa noite|eai|e ai|tudo bem)\b", m):
        return {"resposta": f"Oi, {p['primeiro_nome']}! Tudo bem? Em que posso te ajudar hoje?", "acao": {"tipo": "nenhuma"}}

    return {"resposta": f"Desculpa, {p['primeiro_nome']}, não peguei bem. Consigo fazer Pix, pagar contas, mostrar saldo, fatura, gastos e investimentos, "
            "ou bloquear seu cartão. Se preferir, chamo o Rafael, da equipe, para falar com você.",
            "acao": {"tipo": "nenhuma"}, "nao_entendi": True}


def responder(mensagem: str, historico: list[dict], ctx: dict) -> dict:
    """Retorna dict com: resposta, acao, fonte, frustrado, seguranca, escalar."""
    mensagem = corrigir_digitacao(mensagem)
    frustrado, seguranca = detectar_sinais(mensagem)
    fonte = "regras"
    obj = None
    if api_disponivel():
        obj = _chamar_api(mensagem, historico, ctx)
        if obj:
            fonte = "api"
    if obj is None:
        obj = _regras(mensagem, ctx)

    # contador de "não entendi" — na 2ª vez o app oferece humano (dor nº 1 da pesquisa)
    if obj.get("nao_entendi"):
        st.session_state["ia_nao_entendi"] = st.session_state.get("ia_nao_entendi", 0) + 1
    else:
        st.session_state["ia_nao_entendi"] = 0
    repetido = st.session_state.get("ia_nao_entendi", 0) >= 2

    escalar = frustrado or seguranca or repetido or obj.get("acao", {}).get("tipo") == "escalar_humano"
    if seguranca and obj.get("acao", {}).get("tipo") not in ("bloquear_cartao", "escalar_humano"):
        obj["resposta"] = (
            "Entendi, e fico do seu lado nisso. Vamos proteger sua conta primeiro: posso bloquear o cartão agora e limitar o Pix. "
            "Já estou chamando o Rafael, da equipe de segurança — ele vê nossa conversa, não precisa repetir nada. "
            + ("" if obj.get("nao_entendi") else obj.get("resposta", ""))
        ).strip()
        obj["acao"] = {"tipo": "escalar_humano", "motivo": "segurança"}
    elif escalar and obj.get("acao", {}).get("tipo") != "escalar_humano":
        obj["acao"] = {"tipo": "escalar_humano", "motivo": "frustração" if frustrado else "não resolvido"}
        if fonte == "regras":
            obj["resposta"] = (f"Entendi, {ctx['persona']['primeiro_nome']}, e desculpa por não ter resolvido. Vou te passar para o Rafael, "
                               "da nossa equipe. Ele já está vendo nossa conversa, então você não precisa explicar de novo.")

    _coerencia_acao(obj)
    obj.update({"fonte": fonte, "frustrado": frustrado, "seguranca": seguranca, "escalar": escalar})
    return obj


PREPARA = {"pix", "pagar_conta", "pagar_boleto", "aplicar", "resgatar", "contratar_credito"}
JA_FEZ = re.compile(r"\b(j[aá] )?(enviei|mandei|transferi|paguei|apliquei|resgatei|contratei|foi enviado|foi pago|est[aá] feito)\b", re.I)
SEM_SENHA = re.compile(r"[,;]?\s*[^.!?,;]*\bn[aã]o (precisa|é preciso|vai precisar)[^.!?]*(senha|confirma)[^.!?]*", re.I)


def _coerencia_acao(obj: dict) -> None:
    """A Lia prepara; quem conclui é o cliente na tela. O texto não pode dizer que já fez, nem que dispensa confirmação."""
    tipo = obj.get("acao", {}).get("tipo")
    if tipo not in PREPARA:
        return
    txt = SEM_SENHA.sub("", obj.get("resposta", "")).strip()
    txt = JA_FEZ.sub("preparei", txt).strip()
    if txt and txt[-1] not in ".!?":
        txt += "."
    if not re.search(r"confirm", txt, re.I):
        txt = (txt + " Abri a tela com tudo preenchido: é só conferir e confirmar.").strip()
    obj["resposta"] = txt[:1].upper() + txt[1:]


# ------------------------------------------------------------------ Lia por voz: entender o comando
TELAS_VOZ = ["Extrato", "Pix", "Cartão", "Pagar", "Investir", "Gastos", "Início"]

FERRAMENTA_VOZ = {
    "name": "entender_comando",
    "description": "Devolve o que o cliente pediu à Lia por voz, de forma estruturada.",
    "input_schema": {
        "type": "object",
        "properties": {
            "intencao": {"type": "string", "enum": [
                "saudacao", "ajuda", "consulta_saldo", "consulta_limite", "consulta_fatura", "consulta_vencimento_fatura",
                "consulta_contas", "info_investimentos", "consulta_investimentos", "aplicar", "resgatar",
                "abrir_tela", "pix", "pagar_conta", "cancelar", "outro"]},
            "contato": {"type": ["integer", "null"], "description": "Número do contato da lista, no Pix para alguém salvo"},
            "contato_novo": {"type": ["string", "null"], "description": "Nome dito, se o destinatário NÃO está na lista"},
            "conta": {"type": ["integer", "null"], "description": "Número da conta a pagar da lista"},
            "produto": {"type": ["integer", "null"], "description": "Número do produto de investimento da lista, em aplicar/resgatar"},
            "valor": {"type": ["number", "null"], "description": "Valor em reais, se foi dito"},
            "tela": {"type": ["string", "null"], "enum": TELAS_VOZ + [None], "description": "Tela a abrir, em abrir_tela"},
            "resposta": {"type": "string", "description": "Frase curta e natural para a Lia FALAR em saudacao, ajuda, info_investimentos ou outro (vazia nas demais)"},
            "confianca": {"type": "number", "description": "0 a 1: quão certa é a interpretação"},
        },
        "required": ["intencao", "resposta", "confianca"],
    },
}

SISTEMA_VOZ = """Você é a Lia, assistente de voz de um banco digital (protótipo acadêmico). Você recebe a TRANSCRIÇÃO do que
o cliente falou — pode ter erros do reconhecimento de voz — e devolve a intenção pela ferramenta entender_comando.
Regras:
- Nomes trocados pelo ditado: escolha o contato ou a conta mais parecida em som/escrita ("pineiro", "pisineiro" = Piscineiro;
  "luz" = conta de energia). Só use contato_novo se nada na lista for parecido.
- Valores falados: "quinze e noventa", "15 e 90", "15 reais e 90" = 15,90. "trezentos" = 300. "um pix" NÃO é valor.
  "dois mil" = 2000. Se não houver valor, deixe nulo.
- "pagar o piscineiro 300 reais" é pix (contato), não pagar_conta. pagar_conta é para contas da lista (luz, internet…).
- Saudação ("oi", "bom dia", "tudo bem"): intencao saudacao, resposta curta e calorosa, SEM listar funções.
- Pedido de ajuda ("o que você faz?"): intencao ajuda, resposta listando em uma frase: Pix, pagar contas, saldo, limite,
  fatura, contas a vencer e abrir telas do app.
- Pergunta sobre investimentos em geral ("qual o melhor investimento?", "onde rende mais?", "quais opções tenho?"):
  intencao info_investimentos. Na resposta, apresente 2 ou 3 produtos da lista pelo objetivo — reserva com resgate
  rápido, prazo longo protegido da inflação, renda variável com mais risco —, citando a rentabilidade de 12 meses e a
  liquidez, e termine perguntando o objetivo ou se a pessoa quer aplicar. NÃO diga que um produto é "o melhor para você":
  recomendação personalizada exige o perfil de investidor (suitability, CVM). Não cite valores que o cliente tem.
- "quanto eu tenho investido?", "quanto rendeu minha carteira?": consulta_investimentos (dado pessoal, sem resposta).
- "aplicar/investir 500 no CDB", "quero aplicar": aplicar (produto e valor se ditos). "resgatar 200 do Tesouro": resgatar.
- Fora do banco ou sem sentido: intencao outro, resposta pedindo para repetir ou dizendo com gentileza que não faz isso.
- Responda em português do Brasil, frases curtas, pois a resposta é falada em voz alta."""


def interpretar_voz(texto: str, alternativas: list[str], nome: str, contatos: list[dict], contas: list[dict],
                    logado: bool = False, produtos: list[dict] | None = None) -> dict | None:
    """Entende o comando de voz com a API. None = sem API ou erro (o navegador usa as regras locais)."""
    if not api_disponivel():
        return None
    try:
        import anthropic

        cliente = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"], timeout=8.0, max_retries=0)
        modelo = st.secrets["anthropic"].get("modelo", MODELO_PADRAO)
        alts = [a for a in (alternativas or []) if a and a.strip() and a.strip() != texto.strip()][:4]
        ctx = (f"Cliente: {nome}. {'Já está dentro do app.' if logado else 'Ainda não entrou no app.'}\n"
               "Contatos Pix salvos:\n" + "\n".join(f"{i}. {c['nome']} ({c.get('banco', '')})" for i, c in enumerate(contatos)) +
               "\nContas a pagar:\n" + "\n".join(f"{i}. {c['descricao']} — R$ {c['valor']:.2f}, vence {c['vencimento']}"
                                                   for i, c in enumerate(contas)) +
               "\nProdutos de investimento do banco:\n" + "\n".join(
                   f"{i}. {p['produto']} — {p['tipo']}, rentabilidade 12 meses {p['rent_12m']:.1%}, liquidez {p['liquidez']}"
                   for i, p in enumerate(produtos or [])) +
               "\nTelas do app: " + ", ".join(TELAS_VOZ) +
               f"\n\nO cliente falou: \"{texto}\"" +
               ("\nOutras leituras possíveis do mesmo áudio: " + " | ".join(f'"{a}"' for a in alts) if alts else ""))
        resp = cliente.messages.create(
            model=modelo, max_tokens=400,
            system=[{"type": "text", "text": SISTEMA_VOZ, "cache_control": {"type": "ephemeral"}}],
            tools=[FERRAMENTA_VOZ], tool_choice={"type": "tool", "name": "entender_comando"},
            messages=[{"role": "user", "content": ctx}],
        )
        bloco = next(b for b in resp.content if getattr(b, "type", "") == "tool_use")
        d = dict(bloco.input)

        def _idx(v, n):
            try:
                i = int(v)
                return i if 0 <= i < n else None
            except (TypeError, ValueError):
                return None

        d["contato"] = _idx(d.get("contato"), len(contatos))
        d["conta"] = _idx(d.get("conta"), len(contas))
        d["produto"] = _idx(d.get("produto"), len(produtos or []))
        if d.get("valor") is not None:
            try:
                d["valor"] = abs(float(d["valor"]))
            except (TypeError, ValueError):
                d["valor"] = None
        if d.get("tela") not in TELAS_VOZ:
            d["tela"] = None
        d["uso"] = {"entrada": resp.usage.input_tokens, "saida": resp.usage.output_tokens}
        return d
    except Exception as e:  # noqa: BLE001
        st.session_state["ia_erro_voz"] = str(e)
        return None
