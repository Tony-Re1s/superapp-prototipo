"""Contas de teste ("Criar minha conta"): usuário, senha, estado gravado e Pix entre contas.

Tudo aqui é fictício: o saldo é de mentira e o cadastro pede só um apelido e uma senha de 6 dígitos.
Nada de CPF, e-mail ou telefone. A senha e o código de recuperação são guardados como hash (PBKDF2),
nunca em texto. A assinatura do rosto, usada para recuperar a senha, fica só no aparelho da pessoa.

Banco: Postgres do Supabase (mesmos Secrets das avaliações). Sem Supabase, usa um SQLite local
(útil para rodar no PC e nos testes).
"""
from __future__ import annotations

import hashlib
import hmac
import math
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import date, datetime

import pandas as pd
import streamlit as st

from . import db

USUARIO_RE = re.compile(r"^[a-z0-9][a-z0-9._]{2,19}$")
RESERVADOS = {"admin", "superapp", "lia", "rafael", "suporte", "banco", "teste"}
ITERACOES = 120_000
MAX_FALHAS = 5          # senhas erradas seguidas antes de bloquear a conta
BLOQUEIO_S = 300        # bloqueio de 5 min (vale para a conta, em qualquer aba ou aparelho)
PIX_MAX = 1_000_000.00  # teto de segurança de um Pix entre contas de teste
ARQ_SQLITE = os.path.join(db.PASTA_LOCAL, "contas.sqlite3")

SQL_PG = """
CREATE TABLE IF NOT EXISTS sa_usuarios (
    id BIGSERIAL PRIMARY KEY,
    usuario TEXT UNIQUE NOT NULL,
    senha_hash TEXT NOT NULL, senha_sal TEXT NOT NULL,
    rec_hash TEXT, rec_sal TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_acesso TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acessos INTEGER NOT NULL DEFAULT 1,
    tutorial_visto INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sa_estado (
    usuario_id BIGINT PRIMARY KEY REFERENCES sa_usuarios(id) ON DELETE CASCADE,
    estado JSONB NOT NULL,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sa_pix (
    id BIGSERIAL PRIMARY KEY,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    de_id BIGINT, para_id BIGINT, de_usuario TEXT, para_usuario TEXT,
    valor NUMERIC(14, 2) NOT NULL, mensagem TEXT,
    recebido INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS sa_pix_para ON sa_pix (para_id, recebido);
ALTER TABLE sa_estado ADD COLUMN IF NOT EXISTS versao INTEGER NOT NULL DEFAULT 0;
ALTER TABLE sa_pix ADD COLUMN IF NOT EXISTS criado_ts BIGINT;
CREATE TABLE IF NOT EXISTS sa_sessoes (
    token_hash TEXT PRIMARY KEY,
    usuario_id BIGINT NOT NULL REFERENCES sa_usuarios(id) ON DELETE CASCADE,
    senha_sal TEXT, senha_hash TEXT,
    expira_ts BIGINT NOT NULL
);
ALTER TABLE sa_sessoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE sa_usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE sa_estado ENABLE ROW LEVEL SECURITY;
ALTER TABLE sa_pix ENABLE ROW LEVEL SECURITY;
CREATE TABLE IF NOT EXISTS sa_tentativas (
    usuario TEXT PRIMARY KEY,
    falhas INTEGER NOT NULL DEFAULT 0,
    bloqueado_ate BIGINT NOT NULL DEFAULT 0
);
ALTER TABLE sa_tentativas ENABLE ROW LEVEL SECURITY;
"""

SQL_SQLITE = """
CREATE TABLE IF NOT EXISTS sa_usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE NOT NULL,
    senha_hash TEXT NOT NULL, senha_sal TEXT NOT NULL,
    rec_hash TEXT, rec_sal TEXT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_acesso TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acessos INTEGER NOT NULL DEFAULT 1,
    tutorial_visto INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sa_estado (
    usuario_id INTEGER PRIMARY KEY,
    estado TEXT NOT NULL,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sa_pix (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    de_id INTEGER, para_id INTEGER, de_usuario TEXT, para_usuario TEXT,
    valor REAL NOT NULL, mensagem TEXT,
    recebido INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS sa_pix_para ON sa_pix (para_id, recebido);
CREATE TABLE IF NOT EXISTS sa_sessoes (
    token_hash TEXT PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    senha_sal TEXT, senha_hash TEXT,
    expira_ts INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sa_tentativas (
    usuario TEXT PRIMARY KEY,
    falhas INTEGER NOT NULL DEFAULT 0,
    bloqueado_ate INTEGER NOT NULL DEFAULT 0
);
"""
SQL_SQLITE_COLUNAS = ["ALTER TABLE sa_estado ADD COLUMN versao INTEGER NOT NULL DEFAULT 0",
                      "ALTER TABLE sa_pix ADD COLUMN criado_ts INTEGER"]


# ----------------------------------------------------------------------------- conexão
def _pg() -> bool:
    return db.usando_supabase()


@st.cache_resource(show_spinner=False)
def _preparar_pg(url: str) -> bool:
    import psycopg2

    with psycopg2.connect(url) as con:
        with con.cursor() as cur:
            cur.execute(SQL_PG)
        con.commit()
    return True


@st.cache_resource(show_spinner=False)
def _preparar_sqlite(arq: str) -> bool:
    os.makedirs(os.path.dirname(arq), exist_ok=True)
    with sqlite3.connect(arq) as con:
        con.executescript(SQL_SQLITE)
        for sql in SQL_SQLITE_COLUNAS:  # bases criadas antes destas colunas existirem
            try:
                con.execute(sql)
            except sqlite3.OperationalError:
                pass
    return True


def _conexao_pg(url: str):
    """Uma conexão por sessão do app, reaberta se cair."""
    import psycopg2

    try:
        ss = st.session_state
        con = ss.get("_pg_con")
    except Exception:  # noqa: BLE001  (fora do Streamlit, ex.: testes)
        ss, con = None, None
    if con is None or con.closed:
        con = psycopg2.connect(url, connect_timeout=10)
        con.autocommit = True
        if ss is not None:
            try:
                ss["_pg_con"] = con
            except Exception:  # noqa: BLE001
                pass
    return con


def _q(sql: str, params: tuple | list = (), fetch: str | None = None):
    """Executa uma instrução. fetch: None, 'one' ou 'all' (linhas como dict)."""
    if _pg():
        import psycopg2
        import psycopg2.extras

        url = db._url()
        _preparar_pg(url)
        for tentativa in (1, 2):
            con = _conexao_pg(url)
            try:
                with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    if fetch == "one":
                        r = cur.fetchone()
                        return dict(r) if r else None
                    if fetch == "all":
                        return [dict(r) for r in cur.fetchall()]
                    return None
            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                try:
                    con.close()
                except Exception:  # noqa: BLE001
                    pass
                if tentativa == 2:
                    raise
    _preparar_sqlite(ARQ_SQLITE)
    with sqlite3.connect(ARQ_SQLITE) as con:
        con.row_factory = sqlite3.Row
        cur = con.execute(sql.replace("%s", "?"), tuple(params))
        if fetch == "one":
            r = cur.fetchone()
            out = dict(r) if r else None
        elif fetch == "all":
            out = [dict(r) for r in cur.fetchall()]
        else:
            out = None
        con.commit()
    return out


# ----------------------------------------------------------------------------- senha e usuário
def _hash(segredo: str, sal: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", segredo.encode(), bytes.fromhex(sal), ITERACOES).hex()


def _novo_hash(segredo: str) -> tuple[str, str]:
    sal = secrets.token_hex(16)
    return _hash(segredo, sal), sal


def normalizar_usuario(u: str) -> str:
    return (u or "").strip().lstrip("@").lower()


def validar_usuario(u: str) -> str | None:
    """Devolve a mensagem de erro, ou None se o apelido serve."""
    u = normalizar_usuario(u)
    if not USUARIO_RE.match(u):
        return "Use de 3 a 20 caracteres: letras sem acento, números, ponto ou sublinhado (ex.: tony, joao.m)."
    if u in RESERVADOS:
        return "Esse apelido é reservado. Escolha outro."
    return None


def validar_senha(s: str) -> str | None:
    return None if re.fullmatch(r"\d{6}", s or "") else "A senha precisa ter exatamente 6 números."


def novo_codigo_recuperacao() -> str:
    alfa = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O e 1/I, para não confundir
    s = "".join(secrets.choice(alfa) for _ in range(8))
    return f"{s[:4]}-{s[4:]}"


def _norm_codigo(c: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (c or "").upper())


def existe(usuario: str) -> bool:
    return bool(_q("SELECT id FROM sa_usuarios WHERE usuario = %s", (normalizar_usuario(usuario),), "one"))


def buscar(usuario: str) -> dict | None:
    return _q("SELECT id, usuario, tutorial_visto FROM sa_usuarios WHERE usuario = %s",
              (normalizar_usuario(usuario),), "one")


def criar(usuario: str, senha: str) -> tuple[dict | None, str, str]:
    """Cria a conta. Devolve (usuário, mensagem, código de recuperação)."""
    u = normalizar_usuario(usuario)
    erro = validar_usuario(u) or validar_senha(senha)
    if erro:
        return None, erro, ""
    if existe(u):
        return None, f"O apelido @{u} já está em uso. Escolha outro.", ""
    codigo = novo_codigo_recuperacao()
    h, s = _novo_hash(senha)
    rh, rs = _novo_hash(_norm_codigo(codigo))
    try:
        _q("INSERT INTO sa_usuarios (usuario, senha_hash, senha_sal, rec_hash, rec_sal) VALUES (%s,%s,%s,%s,%s)",
           (u, h, s, rh, rs))
    except Exception as e:  # noqa: BLE001  (dois cadastros ao mesmo tempo com o mesmo apelido)
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return None, f"O apelido @{u} já está em uso. Escolha outro.", ""
        raise
    return buscar(u), "Conta criada.", codigo


def bloqueio_restante(usuario: str) -> int:
    """Segundos que faltam do bloqueio por senhas erradas (0 = liberado)."""
    r = _q("SELECT bloqueado_ate FROM sa_tentativas WHERE usuario = %s", (normalizar_usuario(usuario),), "one")
    return max(0, int(r["bloqueado_ate"]) - int(time.time())) if r else 0


def _registrar_falha(usuario: str) -> None:
    u = normalizar_usuario(usuario)
    r = _q("SELECT falhas FROM sa_tentativas WHERE usuario = %s", (u,), "one")
    falhas = (int(r["falhas"]) if r else 0) + 1
    bloq = int(time.time()) + BLOQUEIO_S if falhas >= MAX_FALHAS else 0
    if r:
        _q("UPDATE sa_tentativas SET falhas = %s, bloqueado_ate = %s WHERE usuario = %s", (0 if bloq else falhas, bloq, u))
    else:
        _q("INSERT INTO sa_tentativas (usuario, falhas, bloqueado_ate) VALUES (%s,%s,%s)", (u, 0 if bloq else falhas, bloq))


def autenticar(usuario: str, senha: str) -> dict | None:
    """Confere apelido e senha. Depois de 5 senhas erradas a conta fica bloqueada por 5 min,
    em qualquer aba ou aparelho (a contagem fica no banco, não na sessão)."""
    u = normalizar_usuario(usuario)
    if bloqueio_restante(u):
        return None
    r = _q("SELECT id, usuario, senha_hash, senha_sal, tutorial_visto FROM sa_usuarios WHERE usuario = %s", (u,), "one")
    if not r or not hmac.compare_digest(_hash(senha or "", r["senha_sal"]), r["senha_hash"]):
        if r:
            _registrar_falha(u)
        return None
    _q("DELETE FROM sa_tentativas WHERE usuario = %s", (u,))
    _q("UPDATE sa_usuarios SET ultimo_acesso = CURRENT_TIMESTAMP, acessos = acessos + 1 WHERE id = %s", (r["id"],))
    return {"id": r["id"], "usuario": r["usuario"], "tutorial_visto": r["tutorial_visto"]}


def conferir_codigo(usuario: str, codigo: str) -> bool:
    r = _q("SELECT rec_hash, rec_sal FROM sa_usuarios WHERE usuario = %s", (normalizar_usuario(usuario),), "one")
    return bool(r and r["rec_hash"] and hmac.compare_digest(_hash(_norm_codigo(codigo), r["rec_sal"]), r["rec_hash"]))


def redefinir_senha(usuario: str, senha: str) -> tuple[bool, str]:
    erro = validar_senha(senha)
    if erro:
        return False, erro
    h, s = _novo_hash(senha)
    _q("UPDATE sa_usuarios SET senha_hash = %s, senha_sal = %s WHERE usuario = %s", (h, s, normalizar_usuario(usuario)))
    _q("DELETE FROM sa_tentativas WHERE usuario = %s", (normalizar_usuario(usuario),))
    return True, "Senha nova cadastrada."


def marcar_tutorial(uid: int) -> None:
    _q("UPDATE sa_usuarios SET tutorial_visto = 1 WHERE id = %s", (uid,))


def listar_usuarios(exceto_id: int | None = None, limite: int = 60) -> list[str]:
    """Apelidos cadastrados (os mais recentes primeiro), para a lista de Pix entre contas."""
    rows = _q("SELECT id, usuario FROM sa_usuarios ORDER BY ultimo_acesso DESC LIMIT %s", (limite,), "all") or []
    return [r["usuario"] for r in rows if r["id"] != exceto_id]


# ----------------------------------------------------------------------------- estado da conta
def _enc(o):
    if isinstance(o, pd.DataFrame):
        return {"__df": [_enc(r) for r in o.to_dict("records")], "__cols": list(o.columns)}
    if isinstance(o, (datetime, pd.Timestamp)):
        return {"__dt": o.isoformat()}
    if isinstance(o, date):
        return {"__d": o.isoformat()}
    if isinstance(o, set):
        return {"__set": sorted((_enc(x) for x in o), key=str)}
    if isinstance(o, dict):
        return {str(k): _enc(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_enc(x) for x in o]
    if hasattr(o, "item"):  # números do numpy/pandas
        try:
            return o.item()
        except Exception:  # noqa: BLE001
            pass
    if isinstance(o, float) and o != o:  # NaN
        return None
    return o


def _dec(o):
    if isinstance(o, dict):
        if "__df" in o:
            return pd.DataFrame([_dec(r) for r in o["__df"]], columns=o.get("__cols"))
        if "__dt" in o:
            return datetime.fromisoformat(o["__dt"])
        if "__d" in o:
            return date.fromisoformat(o["__d"])
        if "__set" in o:
            return {_dec(x) for x in o["__set"]}
        return {k: _dec(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_dec(x) for x in o]
    return o


def serializar(estado: dict) -> str:
    return json.dumps(_enc(estado), ensure_ascii=False, sort_keys=True)


def salvar_estado(uid: int, texto_json: str, versao: int) -> int | None:
    """Grava se ninguém gravou desde a versão que esta sessão conhece. Devolve a versão nova, ou None se
    outro aparelho gravou antes (aí a sessão recarrega a conta em vez de apagar o que o outro fez)."""
    r = _q("UPDATE sa_estado SET estado = %s, versao = versao + 1, atualizado_em = CURRENT_TIMESTAMP "
           "WHERE usuario_id = %s AND versao = %s RETURNING versao", (texto_json, uid, versao), "one")
    if r:
        return int(r["versao"])
    r = _q("INSERT INTO sa_estado (usuario_id, estado, versao) VALUES (%s, %s, 1) "
           "ON CONFLICT (usuario_id) DO NOTHING RETURNING versao", (uid, texto_json), "one")
    return int(r["versao"]) if r else None


def versao_estado(uid: int) -> int:
    r = _q("SELECT versao FROM sa_estado WHERE usuario_id = %s", (uid,), "one")
    return int(r["versao"]) if r else 0


def carregar_estado(uid: int) -> tuple[dict | None, int]:
    r = _q("SELECT estado, versao FROM sa_estado WHERE usuario_id = %s", (uid,), "one")
    if not r:
        return None, 0
    bruto = r["estado"]
    return _dec(json.loads(bruto) if isinstance(bruto, str) else bruto), int(r["versao"])


# ----------------------------------------------------------------------------- Pix entre contas
def enviar_pix(de_id: int, de_usuario: str, para_usuario: str, valor: float, mensagem: str = "") -> dict | None:
    """Registra o Pix para a outra conta. Recusa (None) valor menor que R$ 0,01, não numérico, acima do teto
    ou acima do saldo gravado de quem envia, apelido inexistente e Pix para si mesmo.
    O app só debita o saldo de quem envia depois que este registro dá certo."""
    try:
        valor = round(float(valor), 2)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(valor) or valor < 0.01 or valor > PIX_MAX:
        return None
    alvo = buscar(para_usuario)
    if not alvo or alvo["id"] == de_id:
        return None
    est, _ = carregar_estado(de_id)          # saldo gravado de quem envia (antes do débito desta operação)
    if est is not None and valor > round(float(est.get("saldo", 0) or 0), 2) + 0.005:
        return None
    _q("INSERT INTO sa_pix (de_id, para_id, de_usuario, para_usuario, valor, mensagem, criado_ts) "
       "VALUES (%s,%s,%s,%s,%s,%s,%s)",
       (de_id, alvo["id"], de_usuario, alvo["usuario"], round(float(valor), 2), (mensagem or "")[:140], int(time.time())))
    return alvo


def pix_pendentes(uid: int) -> int:
    r = _q("SELECT count(*) AS n FROM sa_pix WHERE para_id = %s AND recebido = 0", (uid,), "one")
    return int(r["n"]) if r else 0


def pix_repetido(de_id: int, para_usuario: str, valor: float, segundos: int = 600) -> int | None:
    """Há quantos segundos esta conta mandou o mesmo valor para o mesmo @apelido (None se não mandou)."""
    r = _q("SELECT max(criado_ts) AS ts FROM sa_pix WHERE de_id = %s AND para_usuario = %s AND valor = %s "
           "AND criado_ts > %s", (de_id, normalizar_usuario(para_usuario), round(float(valor), 2),
                                  int(time.time()) - segundos), "one")
    return int(time.time()) - int(r["ts"]) if r and r.get("ts") else None


def receber_pix(uid: int) -> list[dict]:
    """Pix que chegaram para esta conta e ainda não entraram no saldo (marca como recebidos)."""
    rows = _q("UPDATE sa_pix SET recebido = 1 WHERE para_id = %s AND recebido = 0 "
              "RETURNING id, de_usuario, valor, mensagem, criado_em", (uid,), "all") or []
    for r in rows:
        r["valor"] = float(r["valor"])
    return sorted(rows, key=lambda r: r["id"])


# ----------------------------------------------------------------------------- sessão lembrada
HORAS_SESSAO = 12


def criar_sessao(uid: int, senha_sal: str, senha_hash: str) -> str:
    """Token guardado num cookie do navegador; no banco fica só o hash dele."""
    token = secrets.token_urlsafe(24)
    _q("DELETE FROM sa_sessoes WHERE expira_ts < %s", (int(time.time()),))
    _q("INSERT INTO sa_sessoes (token_hash, usuario_id, senha_sal, senha_hash, expira_ts) VALUES (%s,%s,%s,%s,%s)",
       (hashlib.sha256(token.encode()).hexdigest(), uid, senha_sal, senha_hash, int(time.time()) + HORAS_SESSAO * 3600))
    return token


def sessao_valida(token: str) -> dict | None:
    if not token:
        return None
    r = _q("SELECT u.id, u.usuario, u.tutorial_visto, s.senha_sal, s.senha_hash FROM sa_sessoes s "
           "JOIN sa_usuarios u ON u.id = s.usuario_id WHERE s.token_hash = %s AND s.expira_ts > %s",
           (hashlib.sha256(token.encode()).hexdigest(), int(time.time())), "one")
    return r


def encerrar_sessao(token: str) -> None:
    if token:
        _q("DELETE FROM sa_sessoes WHERE token_hash = %s", (hashlib.sha256(token.encode()).hexdigest(),))


# ----------------------------------------------------------------------------- números para o grupo
def metricas() -> dict:
    """Contas criadas, ativas e Pix entre contas — métricas reais de aquisição e retenção."""
    try:
        u = _q("SELECT count(*) AS n, sum(CASE WHEN acessos > 1 THEN 1 ELSE 0 END) AS voltaram FROM sa_usuarios",
               (), "one") or {}
        p = _q("SELECT count(*) AS n, coalesce(sum(valor), 0) AS total FROM sa_pix", (), "one") or {}
        return {"contas": int(u.get("n") or 0), "voltaram": int(u.get("voltaram") or 0),
                "pix": int(p.get("n") or 0), "pix_total": float(p.get("total") or 0)}
    except Exception as e:  # noqa: BLE001
        return {"erro": str(e)}


def listar_contas_admin() -> pd.DataFrame:
    return pd.DataFrame(_q("SELECT usuario, criado_em, ultimo_acesso, acessos FROM sa_usuarios ORDER BY criado_em DESC",
                           (), "all") or [])


def listar_pix_admin(limite: int = 100) -> pd.DataFrame:
    df = pd.DataFrame(_q("SELECT id, criado_em, de_usuario, para_usuario, valor, recebido FROM sa_pix ORDER BY id DESC LIMIT %s",
                         (limite,), "all") or [])
    if not df.empty:
        df["valor"] = df["valor"].astype(float)
        df["recebido"] = df["recebido"].map({1: "sim", 0: "aguardando a pessoa abrir o app"})
    return df
