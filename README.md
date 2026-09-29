# Superapp — protótipo de banco digital centrado no cliente

Protótipo do **Tech Challenge FIAP — Fase 03** (iti no Superapp Itaú: do diagnóstico
estratégico ao modelo de negócio centrado no cliente). Banco fictício, dados fictícios,
cores laranja/azul. Cada tela responde a uma dor levantada na pesquisa de campo
*"Você e seu banco"* (n=56).

| Tela | Dor da pesquisa que endereça |
|---|---|
| Início (atalhos por perfil, alertas da IA) | Excesso de telas e menus (19 menções) |
| Pix (2 toques, confirmação reforçada fora do padrão) | Confusão no menu do Pix; medo de golpe (18) |
| Cartão (fatura, limite, bloqueio, cartão virtual, pagar fatura) | Informação completa em um lugar |
| Pagar (contas, boleto com antifraude, agendamento) | Conta recorrente esquecida |
| Extrato (filtros, busca, gráfico, CSV) | Autosserviço |
| Investir (carteira, aplicar/resgatar, simulador) | Autosserviço |
| Gastos (categorização automática, previsão, sugestões) | Persona Lucas |
| Avisos (preferências, ofertas silenciadas por padrão) | Propaganda não solicitada (20) e notificações demais (13) |
| Assistente (IA que executa ações e escala para humano) | **Atendimento robótico que não resolve (36)** |
| Segurança (golpe, celular perdido, verificador de mensagem) | Persona Marisa |
| Avalie (NPS + nota por módulo + perfil) | Fonte de dados para os OKRs |

Sem biometria (LGPD): a confirmação reforçada usa uma senha fictícia de 4 dígitos.

## Rodar no seu PC

```bash
pip install -r requirements.txt
streamlit run app.py
```

Sem `secrets.toml` o app funciona igual, só que: o assistente usa o motor por regras
(sem API) e as avaliações vão para `dados_local/avaliacoes.csv`.

Painel de resultados do grupo: abra a URL do app com `?admin=1` no final
(senha padrão `fiap2026`, troque nos secrets).

## Publicar (mesmo fluxo do CRM)

### 1. GitHub
1. Crie um repositório (público ou privado, tanto faz), ex.: `superapp-prototipo`.
2. No GitHub Desktop, copie **todo o conteúdo desta pasta** para o repositório
   (inclusive `.streamlit/config.toml` e `.gitignore`). Nunca copie `secrets.toml`.
3. Commit to main → Push origin.

### 2. Supabase (grava as avaliações)
1. New project → região **South America (São Paulo)** → anote a senha do banco.
2. Project Settings → Database → **Connect** → escolha **Session pooler** (porta 5432).
   Copie a URI; ela fica no formato
   `postgresql://postgres.<project_ref>:<senha>@aws-0-sa-east-1.pooler.supabase.com:5432/postgres`.
   *Não use a conexão direta: ela só responde em IPv6 e o Streamlit Cloud não a alcança.*
3. As tabelas `avaliacoes` e `eventos_uso` são criadas pelo app na primeira execução
   (`schema.sql` só documenta). RLS fica ligado; o app acessa direto pelo Postgres.

### 3. Streamlit Community Cloud
1. share.streamlit.io → New app → repositório, branch `main`, arquivo `app.py`.
2. Deixe o app **público** (a vaga de app privado é 1 por conta; público é ilimitado e
   é o que a pesquisa precisa: qualquer pessoa com o link avalia).
3. Advanced settings → **Secrets** → cole o conteúdo de `.streamlit/secrets.example.toml`
   preenchido:
   - `[supabase] url` — a URI do Session pooler.
   - `[anthropic] api_key` — chave da API (console.anthropic.com). Sem ela o assistente
     usa regras.
   - `[admin] senha` — senha do painel de resultados.
4. Deploy. Atualizações: substitua a pasta inteira no GitHub Desktop → Commit → Push;
   o Streamlit republica sozinho.

### Custo
Tudo gratuito, exceto a API: com o modelo Haiku 4.5, cada mensagem do chat custa
cerca de US$ 0,002 (≈ US$ 1 a cada 500 mensagens). Coloque um limite de gasto na
conta da API para não ter surpresa.

### Limites do gratuito que importam
- Streamlit: o app dorme após alguns dias sem acesso (acorda em ~30 s no próximo clique).
- Supabase Free: banco pausa após 7 dias sem uso (reativa com um clique no painel);
  sem backup automático → baixe o CSV pelo painel `?admin=1` de tempos em tempos.

## Estrutura

```
app.py                      entrada e navegação
superapp/dados.py           personas (Marisa/Lucas), extrato, fatura, contas, investimentos
superapp/estilo.py          identidade visual (laranja/azul) e componentes
superapp/telas.py           todas as telas
superapp/ia.py              assistente: API Claude + regras + escalonamento humano
superapp/db.py              Supabase (Session pooler) com fallback em CSV
schema.sql                  referência das tabelas
.streamlit/config.toml      tema
.streamlit/secrets.example.toml  modelo dos secrets
```
