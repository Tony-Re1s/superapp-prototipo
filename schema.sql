-- Tabelas do protótipo (o app cria sozinho na 1ª execução; aqui só para referência)

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
