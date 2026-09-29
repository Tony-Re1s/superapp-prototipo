"""Persistência das avaliações.

Prioridade: Postgres do Supabase (Session pooler, porta 5432) via secrets.
Sem secrets, grava em CSV local (útil para rodar no PC; no Streamlit Cloud o
arquivo some quando o app reinicia — use o Supabase para a pesquisa de verdade).
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

CAMPOS = [
    "criado_em", "persona", "nps", "nota_inicio", "nota_pix", "nota_cartao", "nota_pagamentos",
    "nota_extrato", "nota_investimentos", "nota_gastos", "nota_notificacoes", "nota_assistente",
    "nota_seguranca", "faixa_etaria", "ocupacao", "banco_principal", "frequencia_uso",
    "preferencia_atendimento", "o_que_mais_gostou", "o_que_mudaria", "comentario", "nome_opcional",
    "modo_ia",
]

PASTA_LOCAL = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados_local")
ARQ_LOCAL = os.path.join(PASTA_LOCAL, "avaliacoes.csv")

SQL_TABELA = """
CREATE TABLE IF NOT EXISTS avaliacoes (
    id BIGSERIAL PRIMARY KEY,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    persona TEXT,
    nps INTEGER,
    nota_inicio INTEGER, nota_pix INTEGER, nota_cartao INTEGER, nota_pagamentos INTEGER,
    nota_extrato INTEGER, nota_investimentos INTEGER, nota_gastos INTEGER,
    nota_notificacoes INTEGER, nota_assistente INTEGER, nota_seguranca INTEGER,
    faixa_etaria TEXT, ocupacao TEXT, banco_principal TEXT, frequencia_uso TEXT,
    preferencia_atendimento TEXT,
    o_que_mais_gostou TEXT, o_que_mudaria TEXT, comentario TEXT, nome_opcional TEXT,
    modo_ia TEXT
);
CREATE TABLE IF NOT EXISTS eventos_uso (
    id BIGSERIAL PRIMARY KEY,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    sessao TEXT, persona TEXT, tela TEXT, acao TEXT, detalhe JSONB
);
ALTER TABLE avaliacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE eventos_uso ENABLE ROW LEVEL SECURITY;
"""


def _url() -> str | None:
    try:
        return st.secrets["supabase"]["url"]
    except Exception:
        return os.environ.get("SUPABASE_DB_URL")


def usando_supabase() -> bool:
    return bool(_url())


@st.cache_resource(show_spinner=False)
def _preparar_tabelas(url: str) -> bool:
    import psycopg2

    with psycopg2.connect(url) as con:
        with con.cursor() as cur:
            cur.execute(SQL_TABELA)
        con.commit()
    return True


def _conectar():
    import psycopg2

    url = _url()
    _preparar_tabelas(url)
    return psycopg2.connect(url)


def salvar_avaliacao(reg: dict) -> tuple[bool, str]:
    reg = {c: reg.get(c) for c in CAMPOS}
    reg["criado_em"] = datetime.now(timezone.utc).isoformat()
    if usando_supabase():
        try:
            cols = [c for c in CAMPOS if c != "criado_em"]
            with _conectar() as con:
                with con.cursor() as cur:
                    cur.execute(
                        f"INSERT INTO avaliacoes ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                        [reg[c] for c in cols],
                    )
                con.commit()
            return True, "Avaliação gravada no banco. Obrigado!"
        except Exception as e:  # noqa: BLE001
            return False, f"Não consegui gravar no banco: {e}"
    os.makedirs(PASTA_LOCAL, exist_ok=True)
    novo = not os.path.exists(ARQ_LOCAL)
    with open(ARQ_LOCAL, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            w.writeheader()
        w.writerow(reg)
    return True, "Avaliação gravada localmente (modo sem Supabase). Obrigado!"


def listar_avaliacoes() -> pd.DataFrame:
    if usando_supabase():
        try:
            with _conectar() as con:
                return pd.read_sql("SELECT * FROM avaliacoes ORDER BY criado_em DESC", con)
        except Exception as e:  # noqa: BLE001
            st.error(f"Erro ao ler o banco: {e}")
            return pd.DataFrame(columns=CAMPOS)
    if os.path.exists(ARQ_LOCAL):
        return pd.read_csv(ARQ_LOCAL)
    return pd.DataFrame(columns=CAMPOS)


def registrar_evento(sessao: str, persona: str, tela: str, acao: str, detalhe: dict | None = None) -> None:
    """Telemetria leve de uso (best-effort; nunca quebra a tela)."""
    if not usando_supabase():
        return
    try:
        with _conectar() as con:
            with con.cursor() as cur:
                cur.execute(
                    "INSERT INTO eventos_uso (sessao, persona, tela, acao, detalhe) VALUES (%s,%s,%s,%s,%s)",
                    [sessao, persona, tela, acao, json.dumps(detalhe or {}, ensure_ascii=False)],
                )
            con.commit()
    except Exception:  # noqa: BLE001
        pass


def listar_eventos() -> pd.DataFrame:
    if not usando_supabase():
        return pd.DataFrame()
    try:
        with _conectar() as con:
            return pd.read_sql("SELECT * FROM eventos_uso ORDER BY criado_em DESC LIMIT 5000", con)
    except Exception:  # noqa: BLE001
        return pd.DataFrame()
