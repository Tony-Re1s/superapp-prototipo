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
    "golpe", "fraude", "roubar", "roubaram", "clonad", "nao reconheco", "nao fui eu", "invadir",
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


def _contexto_texto(ctx: dict) -> str:
    p = ctx["persona"]
    contas = "\n".join(
        f"- {c['descricao']}: {D.brl(c['valor'])}, vence {D.data_br(c['vencimento'])} ({c['status']})"
        for c in ctx["contas"]
    )
    contatos = "\n".join(f"- {c['nome']} ({c['banco']})" for c in ctx["contatos"])
    gastos = "\n".join(f"- {k}: {D.brl(v)}" for k, v in ctx["gastos_categoria"].items())
    return f"""
CLIENTE: {p['nome']}, {p['idade']} anos. Cliente há {p['tempo_cliente']}. {p['descricao']}
Prefere atendimento humano em temas sensíveis: {"sim" if p['prefere_humano'] else "não, prefere resolver sozinho"}.

SALDO EM CONTA: {D.brl(ctx['saldo'])}
CARTÃO: fatura atual {D.brl(p['fatura_atual'])}, vence {D.data_br(p['fatura_vencimento'])}; limite {D.brl(p['limite_cartao'])}, disponível {D.brl(p['limite_cartao'] - p['fatura_atual'])}. Cartão {"BLOQUEADO" if ctx['cartao_bloqueado'] else "ativo"}.
INVESTIMENTOS: patrimônio {D.brl(p['patrimonio_inv'])}.
CONTAS A PAGAR:
{contas}
CONTATOS PIX FAVORITOS:
{contatos}
GASTOS DO MÊS POR CATEGORIA (conta corrente):
{gastos}
LIMITE DE PIX SEM CONFIRMAÇÃO REFORÇADA: {D.brl(p['pix_padrao_max'])} (acima disso o app pede senha).
"""


SISTEMA = """Você é o assistente do Superapp, um banco digital fictício usado em um protótipo acadêmico (FIAP).
Fale em português do Brasil, de forma curta, clara e humana (2 a 4 frases). Nunca invente dados: use apenas o CONTEXTO.
Você EXECUTA ações, não apenas orienta. Quando o cliente pedir algo executável, devolva a ação correspondente.

Responda SEMPRE e SOMENTE com um JSON válido neste formato:
{"resposta": "<texto para o cliente>", "acao": {"tipo": "<tipo>", ...campos}}

Tipos de ação permitidos:
- {"tipo": "nenhuma"}
- {"tipo": "pix", "valor": <número>, "destinatario": "<nome do contato favorito ou chave>"}
- {"tipo": "pagar_conta", "descricao": "<nome da conta como aparece no contexto>"}
- {"tipo": "bloquear_cartao"} / {"tipo": "desbloquear_cartao"}
- {"tipo": "ver_fatura"} / {"tipo": "ver_extrato"} / {"tipo": "ver_gastos"} / {"tipo": "ver_investimentos"}
- {"tipo": "escalar_humano", "motivo": "<motivo curto>"}

Regras:
- Se faltar um dado essencial para a ação (ex.: valor do Pix), pergunte e use "nenhuma".
- Se o cliente demonstrar frustração, repetir o problema, ou pedir uma pessoa: use "escalar_humano" e acolha.
- Se o tema for golpe, fraude, compra não reconhecida, celular perdido ou senha vazada: primeiro proteja
  (sugira bloquear o cartão / limitar Pix) e use "escalar_humano" com motivo "segurança".
- Perguntas sobre saldo, fatura, contas, gastos e investimentos: responda com os números do contexto.
- Não fale de temas fora do banco; redirecione com gentileza.
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


def _numero(texto: str) -> float | None:
    m = re.search(r"(\d+(?:[.,]\d{1,2})?)", texto.replace(".", "").replace(",", "."))
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _regras(mensagem: str, ctx: dict) -> dict:
    m = _norm(mensagem)
    p = ctx["persona"]

    if re.search(r"\b(saldo|quanto (eu )?tenho|quanto tem na conta)\b", m):
        return {"resposta": f"Seu saldo disponível é {D.brl(ctx['saldo'])}.", "acao": {"tipo": "nenhuma"}}

    if "pix" in m or "transfer" in m or re.search(r"\b(manda|mande|envia|envie|passa|paga)\b.*\b(pra|pro|para)\b", m):
        valor = _numero(m)
        dest = None
        for c in ctx["contatos"]:
            primeiro = _norm(c["nome"].split(" ")[0])
            if primeiro in m:
                dest = c["nome"]
                break
        if valor and dest:
            return {"resposta": f"Preparei um Pix de {D.brl(valor)} para {dest}. Confira e confirme.",
                    "acao": {"tipo": "pix", "valor": valor, "destinatario": dest}}
        if valor:
            return {"resposta": f"Pix de {D.brl(valor)} — para quem? Seus favoritos: "
                    + ", ".join(c["nome"].split(" (")[0] for c in ctx["contatos"]) + ".",
                    "acao": {"tipo": "nenhuma"}}
        return {"resposta": "Claro! Me diga o valor e para quem (ex.: \"manda 50 pra Ana\").", "acao": {"tipo": "nenhuma"}}

    if "fatura" in m or ("cartao" in m and ("quanto" in m or "gast" in m)):
        return {"resposta": f"Sua fatura atual está em {D.brl(p['fatura_atual'])} e vence em "
                f"{D.data_br(p['fatura_vencimento'])}. Limite disponível: {D.brl(p['limite_cartao'] - p['fatura_atual'])}.",
                "acao": {"tipo": "ver_fatura"}}

    if "bloque" in m and "cartao" in m:
        if "desbloque" in m:
            return {"resposta": "Cartão desbloqueado. Se notar algo estranho, é só me chamar.", "acao": {"tipo": "desbloquear_cartao"}}
        return {"resposta": "Feito: seu cartão está bloqueado preventivamente. Você pode desbloquear quando quiser.",
                "acao": {"tipo": "bloquear_cartao"}}

    if "limite" in m:
        return {"resposta": f"Seu limite total é {D.brl(p['limite_cartao'])}; disponível agora: "
                f"{D.brl(p['limite_cartao'] - p['fatura_atual'])}.", "acao": {"tipo": "nenhuma"}}

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

    if "invest" in m or "render" in m or "aplic" in m:
        return {"resposta": f"Seu patrimônio investido é {D.brl(p['patrimonio_inv'])}. Abri a tela de investimentos.",
                "acao": {"tipo": "ver_investimentos"}}

    if "extrato" in m or "movimenta" in m:
        return {"resposta": "Abri seu extrato. Você pode filtrar por período e tipo.", "acao": {"tipo": "ver_extrato"}}

    if re.search(r"\b(oi|ola|bom dia|boa tarde|boa noite|eai|e ai)\b", m):
        return {"resposta": f"Oi, {p['primeiro_nome']}! Posso fazer Pix, pagar contas, mostrar fatura, gastos ou "
                "bloquear seu cartão. O que você precisa?", "acao": {"tipo": "nenhuma"}}

    return {"resposta": "Não entendi bem. Consigo fazer Pix, pagar contas, mostrar saldo, fatura, gastos e investimentos, "
            "ou bloquear seu cartão. Se preferir, chamo uma pessoa para te atender.",
            "acao": {"tipo": "nenhuma"}, "nao_entendi": True}


def responder(mensagem: str, historico: list[dict], ctx: dict) -> dict:
    """Retorna dict com: resposta, acao, fonte, frustrado, seguranca, escalar."""
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
            "Entendi — vamos proteger sua conta primeiro. Posso bloquear seu cartão agora e limitar o Pix até "
            "você falar com nossa central de segurança. " + obj.get("resposta", "")
        ).strip()
        obj["acao"] = {"tipo": "escalar_humano", "motivo": "segurança"}
    elif escalar and obj.get("acao", {}).get("tipo") != "escalar_humano":
        obj["acao"] = {"tipo": "escalar_humano", "motivo": "frustração" if frustrado else "não resolvido"}

    obj.update({"fonte": fonte, "frustrado": frustrado, "seguranca": seguranca, "escalar": escalar})
    return obj
