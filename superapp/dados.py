"""Dados fictícios do protótipo — gerados de forma determinística por persona.

Nenhum dado aqui é real. As personas (Marisa e Lucas) vêm da pesquisa de campo
do Tech Challenge (FIAP, 2026).
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

import pandas as pd

HOJE = date(2026, 9, 28)

PERSONAS = {
    "padrao": {
        "id": "padrao",
        "nome": "Ana Lima",
        "primeiro_nome": "Ana",
        "idade": 35,
        "descricao": "Cliente padrão do protótipo.",
        "agencia": "1234",
        "conta": "56789-0",
        "saldo": 4_318.62,
        "limite_cartao": 6_000.00,
        "fatura_atual": 1_987.45,
        "fatura_vencimento": date(2026, 10, 8),
        "patrimonio_inv": 18_750.00,
        "pix_padrao_max": 400.00,
        "prefere_humano": False,
        "atalhos": ["Pix", "Pagar conta", "Cartão", "Assistente"],
        "chave_pix": "ana.lima@email.com",
        "salario": 5_400.00,
        "tempo_cliente": "9 anos",
    },
    "marisa": {
        "id": "marisa",
        "nome": "Marisa Andrade",
        "primeiro_nome": "Marisa",
        "idade": 48,
        "descricao": "Servidora pública, 48 anos. Usa o app algumas vezes por semana. "
        "Prioriza segurança e atendimento humano.",
        "agencia": "0912",
        "conta": "45871-3",
        "saldo": 6_842.17,
        "limite_cartao": 8_000.00,
        "fatura_atual": 2_143.60,
        "fatura_vencimento": date(2026, 10, 10),
        "patrimonio_inv": 48_350.00,
        "pix_padrao_max": 500.00,  # acima disso, confirmação reforçada
        "prefere_humano": True,
        "atalhos": ["Pix", "Pagar conta", "Extrato", "Segurança"],
        "chave_pix": "marisa.andrade@email.com",
        "salario": 7_900.00,
        "tempo_cliente": "22 anos",
    },
    "lucas": {
        "id": "lucas",
        "nome": "Lucas Ferreira",
        "primeiro_nome": "Lucas",
        "idade": 24,
        "descricao": "Estudante e CLT, 24 anos. Usa o app várias vezes ao dia. "
        "Quer resolver tudo sozinho, na hora.",
        "agencia": "3301",
        "conta": "77209-8",
        "saldo": 1_237.45,
        "limite_cartao": 3_500.00,
        "fatura_atual": 1_890.30,
        "fatura_vencimento": date(2026, 10, 5),
        "patrimonio_inv": 4_120.00,
        "pix_padrao_max": 300.00,
        "prefere_humano": False,
        "atalhos": ["Pix", "Cartão", "Gastos", "Assistente"],
        "chave_pix": "11 98877-6655",
        "salario": 3_200.00,
        "tempo_cliente": "3 anos",
    },
}

CATEGORIAS = {
    "Alimentação": ["iFood", "Mercado Bom Preço", "Padaria Estrela", "Restaurante Sabor", "Hortifruti Vila"],
    "Transporte": ["Uber", "99 App", "Posto Shell", "Bilhete Único", "Estacionamento Center"],
    "Moradia": ["Condomínio Ed. Aurora", "Enel Energia", "Sabesp", "Vivo Fibra"],
    "Lazer": ["Netflix", "Spotify", "Cinemark", "Steam", "Livraria Cultura"],
    "Saúde": ["Drogasil", "Unimed", "Academia Smart Fit"],
    "Compras": ["Amazon", "Mercado Livre", "Renner", "Magalu", "Shopee"],
    "Educação": ["FIAP", "Udemy", "Papelaria Central"],
}

CONTATOS_PIX = {
    "padrao": [
        {"nome": "Carla (irmã)", "chave": "carla.lima@email.com", "banco": "Nubank"},
        {"nome": "Bruno", "chave": "11 98811-2244", "banco": "Superapp"},
        {"nome": "Mãe", "chave": "11 97700-5566", "banco": "Caixa"},
        {"nome": "Dr. Paulo (dentista)", "chave": "22.333.444/0001-55", "banco": "Bradesco"},
    ],
    "marisa": [
        {"nome": "Ana Andrade (filha)", "chave": "ana.andrade@email.com", "banco": "Nubank"},
        {"nome": "Pedro Andrade (filho)", "chave": "11 97711-2233", "banco": "Superapp"},
        {"nome": "Dona Lourdes (diarista)", "chave": "123.456.789-00", "banco": "Caixa"},
        {"nome": "Condomínio Ed. Aurora", "chave": "cond.aurora@adm.com", "banco": "Bradesco"},
    ],
    "lucas": [
        {"nome": "Rafa (república)", "chave": "11 96655-4433", "banco": "Nubank"},
        {"nome": "Bia", "chave": "bia.souza@email.com", "banco": "Inter"},
        {"nome": "Mãe", "chave": "11 95544-3322", "banco": "Superapp"},
        {"nome": "Barbearia do Zé", "chave": "43.210.987/0001-55", "banco": "PicPay"},
    ],
}

CONTAS_A_PAGAR = {
    "padrao": [
        {"descricao": "Enel Energia", "valor": 218.70, "vencimento": date(2026, 10, 4), "recorrente": True, "status": "aberta"},
        {"descricao": "Vivo Fibra", "valor": 119.90, "vencimento": date(2026, 9, 26), "recorrente": True, "status": "vencida"},
        {"descricao": "Condomínio", "valor": 640.00, "vencimento": date(2026, 10, 10), "recorrente": True, "status": "aberta"},
        {"descricao": "Academia", "valor": 149.90, "vencimento": date(2026, 10, 12), "recorrente": True, "status": "aberta"},
        {"descricao": "IPVA parcela 3/3", "valor": 412.50, "vencimento": date(2026, 10, 20), "recorrente": False, "status": "aberta"},
    ],
    "marisa": [
        {"descricao": "Enel Energia", "valor": 312.40, "vencimento": date(2026, 10, 3), "recorrente": True, "status": "aberta"},
        {"descricao": "Sabesp", "valor": 148.90, "vencimento": date(2026, 10, 6), "recorrente": True, "status": "aberta"},
        {"descricao": "Condomínio Ed. Aurora", "valor": 890.00, "vencimento": date(2026, 10, 10), "recorrente": True, "status": "aberta"},
        {"descricao": "Vivo Fibra", "valor": 129.90, "vencimento": date(2026, 9, 25), "recorrente": True, "status": "vencida"},
        {"descricao": "IPTU parcela 9/10", "valor": 214.30, "vencimento": date(2026, 10, 15), "recorrente": False, "status": "aberta"},
    ],
    "lucas": [
        {"descricao": "Aluguel (Rafa)", "valor": 850.00, "vencimento": date(2026, 10, 5), "recorrente": True, "status": "aberta"},
        {"descricao": "Vivo Fibra", "valor": 99.90, "vencimento": date(2026, 10, 8), "recorrente": True, "status": "aberta"},
        {"descricao": "Mensalidade FIAP", "valor": 1_150.00, "vencimento": date(2026, 10, 10), "recorrente": True, "status": "aberta"},
        {"descricao": "Enel Energia", "valor": 96.20, "vencimento": date(2026, 9, 26), "recorrente": True, "status": "vencida"},
    ],
}

INVESTIMENTOS = {
    "padrao": [
        {"produto": "CDB Superapp 110% CDI", "tipo": "Renda fixa", "valor": 9_800.00, "rent_12m": 0.1125, "liquidez": "Diária"},
        {"produto": "Tesouro Selic 2029", "tipo": "Tesouro Direto", "valor": 5_150.00, "rent_12m": 0.108, "liquidez": "D+1"},
        {"produto": "Poupança", "tipo": "Poupança", "valor": 2_600.00, "rent_12m": 0.067, "liquidez": "Diária"},
        {"produto": "ETF IVVB11", "tipo": "Renda variável", "valor": 1_200.00, "rent_12m": 0.184, "liquidez": "D+2"},
    ],
    "marisa": [
        {"produto": "CDB Superapp 110% CDI", "tipo": "Renda fixa", "valor": 22_500.00, "rent_12m": 0.1125, "liquidez": "Diária"},
        {"produto": "Tesouro IPCA+ 2035", "tipo": "Tesouro Direto", "valor": 15_200.00, "rent_12m": 0.098, "liquidez": "D+1"},
        {"produto": "Poupança", "tipo": "Poupança", "valor": 6_650.00, "rent_12m": 0.067, "liquidez": "Diária"},
        {"produto": "Fundo Previdência Conservador", "tipo": "Previdência", "valor": 4_000.00, "rent_12m": 0.089, "liquidez": "D+30"},
    ],
    "lucas": [
        {"produto": "Caixinha Reserva (CDB 100% CDI)", "tipo": "Renda fixa", "valor": 2_400.00, "rent_12m": 0.105, "liquidez": "Diária"},
        {"produto": "Tesouro Selic 2029", "tipo": "Tesouro Direto", "valor": 1_120.00, "rent_12m": 0.108, "liquidez": "D+1"},
        {"produto": "ETF IVVB11", "tipo": "Renda variável", "valor": 600.00, "rent_12m": 0.184, "liquidez": "D+2"},
    ],
}

OFERTAS_PADRAO = {
    "conta": True,
    "cartao": True,
    "investimentos": True,
    "seguranca": True,
    "ofertas": False,
    "frequencia": "Só o essencial",
}


def _rng(persona_id: str) -> random.Random:
    return random.Random(f"superapp-{persona_id}-2026")


def gerar_extrato(persona_id: str, dias: int = 90) -> pd.DataFrame:
    """Extrato da conta corrente (últimos N dias), com saldo acumulado."""
    p = PERSONAS[persona_id]
    rng = _rng(persona_id)
    linhas = []
    inicio = HOJE - timedelta(days=dias)
    cats = list(CATEGORIAS.keys())
    for d in range(dias + 1):
        dia = inicio + timedelta(days=d)
        # salário no dia 5
        if dia.day == 5:
            empresa = {"marisa": "Prefeitura SP", "lucas": "TechCorp"}.get(persona_id, "Empresa Fictícia Ltda")
            linhas.append((dia, f"Salário — {empresa}", p["salario"], "Renda", "Crédito"))
        n = rng.choice([0, 1, 1, 2, 2, 3]) if persona_id != "marisa" else rng.choice([0, 0, 1, 1, 2])
        for _ in range(n):
            cat = rng.choices(cats, weights=[5, 4, 1, 3, 1, 3, 1])[0]
            estab = rng.choice(CATEGORIAS[cat])
            base = {"Alimentação": 55, "Transporte": 30, "Moradia": 250, "Lazer": 45,
                    "Saúde": 90, "Compras": 160, "Educação": 80}[cat]
            valor = round(base * rng.uniform(0.4, 2.2), 2)
            tipo = rng.choice(["Pix", "Débito", "Pix", "Boleto"]) if cat == "Moradia" else rng.choice(["Pix", "Débito", "Pix"])
            linhas.append((dia, f"{tipo} — {estab}", -valor, cat, "Débito"))
        if rng.random() < 0.08:
            quem = rng.choice(CONTATOS_PIX[persona_id])["nome"].split(" (")[0]
            linhas.append((dia, f"Pix recebido — {quem}", round(rng.uniform(40, 400), 2), "Transferência", "Crédito"))
    df = pd.DataFrame(linhas, columns=["data", "descricao", "valor", "categoria", "tipo"])
    df = df.sort_values("data", kind="stable").reset_index(drop=True)
    # ajusta para que o saldo final bata com o saldo da persona
    saldo_final = p["saldo"]
    df["saldo"] = saldo_final - df["valor"][::-1].cumsum()[::-1] + df["valor"]
    return df


def gerar_fatura(persona_id: str) -> pd.DataFrame:
    """Compras do cartão de crédito na fatura atual."""
    p = PERSONAS[persona_id]
    rng = random.Random(f"fatura-{persona_id}")
    cats = list(CATEGORIAS.keys())
    linhas = []
    total = 0.0
    alvo = p["fatura_atual"]
    dia = HOJE - timedelta(days=28)
    while total < alvo - 60:
        cat = rng.choices(cats, weights=[5, 2, 1, 4, 2, 5, 2])[0]
        estab = rng.choice(CATEGORIAS[cat])
        valor = round(min(rng.uniform(18, 420), alvo - total), 2)
        parcelas = rng.choice([1, 1, 1, 1, 3, 6, 10]) if valor > 150 else 1
        linhas.append((dia, estab, cat, valor, parcelas))
        total += valor
        dia += timedelta(days=rng.choice([0, 1, 1, 2]))
    if alvo - total > 0:
        linhas.append((HOJE - timedelta(days=1), "Ajuste de arredondamento", "Compras", round(alvo - total, 2), 1))
    df = pd.DataFrame(linhas, columns=["data", "estabelecimento", "categoria", "valor", "parcelas"])
    df["parcela_txt"] = df["parcelas"].apply(lambda n: "à vista" if n == 1 else f"1/{n}")
    return df


def gerar_notificacoes(persona_id: str) -> list[dict]:
    p = PERSONAS[persona_id]
    base = [
        {"quando": "Hoje, 08:12", "tipo": "seguranca", "titulo": "Novo acesso reconhecido",
         "texto": "Login pelo seu celular habitual. Se não foi você, toque aqui.", "lida": False},
        {"quando": "Hoje, 07:30", "tipo": "conta", "titulo": "Pix recebido",
         "texto": "Você recebeu R$ 180,00 de " + CONTATOS_PIX[persona_id][0]["nome"].split(" (")[0] + ".", "lida": False},
        {"quando": "Ontem, 19:05", "tipo": "cartao", "titulo": "Compra aprovada",
         "texto": "R$ 89,90 em iFood no cartão final 4417.", "lida": True},
        {"quando": "Ontem, 09:00", "tipo": "conta", "titulo": "Conta vencendo",
         "texto": f"{CONTAS_A_PAGAR[persona_id][0]['descricao']} vence em breve. Quer pagar agora?", "lida": True},
        {"quando": "Sáb, 14:40", "tipo": "ofertas", "titulo": "Oferta: seguro celular",
         "texto": "Proteja seu aparelho por R$ 12,90/mês.", "lida": True},
        {"quando": "Sex, 11:20", "tipo": "ofertas", "titulo": "Empréstimo pré-aprovado",
         "texto": "Você tem R$ 15.000 disponíveis. Simule agora.", "lida": True},
        {"quando": "Qui, 16:00", "tipo": "investimentos", "titulo": "Rendimento do mês",
         "texto": f"Seus investimentos renderam R$ {p['patrimonio_inv']*0.0085:,.2f} em setembro.".replace(",", "X").replace(".", ",").replace("X", "."), "lida": True},
        {"quando": "Qua, 10:15", "tipo": "ofertas", "titulo": "Cartão Black: upgrade",
         "texto": "Você foi selecionado para o cartão Black sem anuidade no 1º ano.", "lida": True},
    ]
    return base


def brl(v: float) -> str:
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {s}" if v < 0 else f"R$ {s}"


def data_br(d: date | datetime | str) -> str:
    if isinstance(d, str):
        d = pd.to_datetime(d).date()
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d/%m/%Y")
