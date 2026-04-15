# Recomendacoes com NMF

API simples para etiquetar ofertas com temas gerados por NMF e recomendar conforme interesses declarados.

## Requisitos

- Python 3.10+

## Instalacao rapida

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Dados de entrada

Por padrao sao usados ambos arquivos: [../classes.json](../classes.json) e [../vacantes.json](../vacantes.json). Se quiser usar outro JSON ou varios JSON, defina:

```bash
export OFFER_DATA_PATH="/caminho/para/arquivo.json"
# ou varios arquivos separados por virgula
export OFFER_DATA_PATHS="/caminho/para/clases.json,/caminho/para/vacantes.json"
```

O JSON deve ser uma lista de objetos (uma oferta por elemento). Se forem carregados varios arquivos, as ofertas sao combinadas por `id_acao` (ou por `id_anuncio_*` se nao existir), e os campos faltantes sao completados sem sobrescrever valores existentes.

## Rodar a API

```bash
uvicorn app.main:app --reload --port 8000
```

Se voce estiver usando um venv no repo:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker

Build da imagem:

```bash
docker build -t nmf-api .
```

Run:

```bash
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e ONESIGNAL_APP_ID="..." \
  -e ONESIGNAL_API_KEY="..." \
  nmf-api
```

## Docker Compose

Subir API + Postgres:

```bash
docker compose up --build
```

Notas:

- Usa `../classes.json` y `../vacantes.json` como volumes em `/data`.
- Ajuste credenciais e variaveis em `docker-compose.yml`.

## Endpoints principais

- `GET /tags` -> lista de etiquetas detectadas
- `POST /recommend` -> ofertas recomendadas conforme etiquetas
- `POST /recommend/serendipity` -> recomendacoes com diversidade/novidade
- `POST /recommend/user` -> recomendacoes conforme interesses do usuario (fonte de verdade no back)
- `POST /train` -> reentrenar com novos parametros
- `GET /offers` -> lista ofertas com tags
- `GET /offers/active` -> lista ofertas ativas com tags
- `GET /offers/normalized` -> lista ofertas com modelo de saida normalizado
- `GET /offers/brief` -> lista ofertas com titulo e descricao
- `POST /tag-offers` -> etiquetar novas ofertas com o modelo atual
- `POST /notifications/offers/brief` -> enviar notificacao com ofertas brief
- `POST /notifications/send` -> envio geral para OneSignal
- `POST /notifications/offers/class` -> notificar usuarios pelos interesses da oferta

## Endpoints de notificacoes (detalhe)

### POST /notifications/offers/brief

O que faz:

- Busca interesses do usuario na base.
- Recomenda ofertas e monta mensagem breve com titulo/descricao.
- Envia OneSignal usando `external_user_id` = `user_id`.

Recebe:

```json
{
  "user_id": 123,
  "limit": 5,
  "min_score": 0.0,
  "active_only": false,
  "require_tag_match": true,
  "heading": "Novas ofertas",
  "dry_run": false
}
```

Retorna:

```json
{
  "total": 2,
  "items": [
    {"offer_id": "A1", "title": "...", "description": "..."}
  ],
  "onesignal": {"id": "..."}
}
```

### POST /notifications/send

O que faz:

- Envia uma notificacao generica para OneSignal.
- Exige pelo menos um de `external_user_ids`, `included_segments` ou `filters`.

Recebe:

```json
{
  "external_user_ids": ["123"],
  "included_segments": ["All"],
  "filters": [{"field": "tag", "key": "vip", "relation": "=", "value": "1"}],
  "headings": {"es": "Titulo"},
  "contents": {"es": "Mensagem"},
  "data": {"url": "https://..."},
  "dry_run": false
}
```

Retorna:

```json
{"onesignal": {"id": "..."}}
```

### POST /notifications/offers/class

O que faz:

- Busca `interest_id` da oferta em `class_interest`.
- Resolve usuarios em `user_cs_interests_list`.
- Aplica dedupe por `(class_id, user_id)` usando `notifications_sent`.
- Envia OneSignal usando `user_cs.id` como `external_user_id`.
- Se nao receber `heading`/`content`, monta o brief com `extension_class`.

Recebe:

```json
{
  "class_id": 999,
  "heading": "Nova oferta",
  "content": "Abriu uma oferta...",
  "interest_ids": [1, 2, 3],
  "data": {"class_id": 999},
  "dry_run": false
}
```

Retorna:

```json
{
  "total_users": 42,
  "interest_ids": [1, 2, 3],
  "onesignal": {"id": "..."}
}
```

## Estrutura do projeto

```
recomendaciones/nmf_api/
  app/
    routes/
      health.py
      offers.py
      recommendations.py
    services/
      interests_service.py
      model_service.py
    data_loader.py
    deps.py
    main.py
    nmf_classifier.py
    schemas.py
    state.py
  README.md
  README.pt.md
  requirements.txt
```

Resumo rapido:

- `app/main.py`: cria a app e inclui routers.
- `app/routes/`: endpoints HTTP.
- `app/services/`: logica de negocio (modelo, interesses).
- `app/nmf_classifier.py`: treino e scoring NMF.
- `app/data_loader.py`: carga e merge de dados.
- `app/schemas.py`: modelos Pydantic.

## Exemplos

Listar etiquetas:

```bash
curl http://localhost:8000/tags
```

Recomendar ofertas usando etiquetas 0 e 2:

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"tag_ids": [0, 2], "limit": 5, "active_only": true, "require_tag_match": true}'
```

Recomendar por usuario (interesses no back):

```bash
curl -X POST http://localhost:8000/recommend/user \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123, "limit": 5, "active_only": true}'
```

Recomendar com serendipity (diversidade):

```bash
curl -X POST http://localhost:8000/recommend/serendipity \
  -H "Content-Type: application/json" \
  -d '{"tag_ids": [0, 2], "limit": 5, "active_only": true, "diversity_lambda": 0.7}'
```

Reentrenar com 10 temas:

```bash
curl -X POST http://localhost:8000/train \
  -H "Content-Type: application/json" \
  -d '{"n_topics": 10, "max_features": 6000, "active_only": true}'
```

## Como o train conversa com o modelo

- O modelo e carregado na inicializacao com os dados atuais.
- `POST /train` recalcula temas e atualiza em memoria o modelo e todas as etiquetas.
- Se voce quiser manter etiquetas fixas para usuarios, evite reentrenar e use o mesmo modelo para etiquetar novas ofertas.
- Se reentrenar, as etiquetas podem mudar (ids e termos) e voce deve versiona-las.

### Parametros do treino inicial

O treino inicial usa os defaults de `TaggerConfig` em [app/nmf_classifier.py](recomendaciones/nmf_api/app/nmf_classifier.py),
chamados em `startup_model` de [app/services/model_service.py](recomendaciones/nmf_api/app/services/model_service.py).
Para mudar em runtime, use `POST /train` com esses mesmos parametros.

Impacto por parametro (aumentando / diminuindo):

- `n_topics`: mais temas = maior granularidade, mais etiquetas; menos temas = etiquetas mais gerais.
- `max_features`: mais vocabulario = mais detalhe, maior custo; menos vocabulario = menos detalhe.
- `min_df`: mais alto = remove termos raros, mais estabilidade; mais baixo = mantem termos raros, mais ruido.
- `max_df`: mais baixo = remove termos muito frequentes, mais foco; mais alto = deixa termos comuns, menos discriminacao.
- `ngram_range`: incluir bigramas melhora frases, mas aumenta custo e sparsity.
- `top_terms`: mais termos por tema = etiquetas mais longas; menos termos = etiquetas mais curtas.
- `topic_threshold`: mais alto = menos tags por oferta; mais baixo = mais tags por oferta.
- `top_k`: mais alto = mais tags quando nao ha limiar; mais baixo = menos tags forzadas.

## Etiquetar novas ofertas sem reentrenar

Para manter as etiquetas fixas, use o mesmo modelo e etiquete apenas novas ofertas com `POST /tag-offers`.

1. Extraia as novas ofertas da sua fonte.
2. Envie essas ofertas para o endpoint `/tag-offers`.
3. Salve `tags` e `tag_labels` na sua base.

Exemplo:

```bash
curl -X POST http://localhost:8000/tag-offers \
  -H "Content-Type: application/json" \
  -d '{"items": [{"id_acao": "ABC", "titulo": "Oferta nova", "resumo": "Texto"}]}'
```

## Ingestao para base de dados

Uma forma simples de popular a base e consumir `GET /offers/normalized` e fazer upsert por `offer_id`:

1. Chamar `/offers/normalized?limit=200&offset=0`
2. Salvar campos normalizados e `tags`
3. Repetir com `offset` ate completar

Exemplo com paginacao:

```bash
curl "http://localhost:8000/offers/normalized?limit=200&offset=0"
```

Se quiser armazenar etiquetas, salve `tags` e (opcional) `is_active` na tabela de ofertas.

Listar ofertas ativas (inscricoes vigentes):

```bash
curl "http://localhost:8000/offers/active?limit=20&offset=0"
```

Listar ofertas normalizadas:

```bash
curl "http://localhost:8000/offers/normalized?limit=20&offset=0&tag_ids=2&tag_ids=5"
```

Listar titulo e descricao:

```bash
curl "http://localhost:8000/offers/brief?limit=20&offset=0&tag_ids=2&tag_ids=5"
```

## Notas sobre o algoritmo

- Monta-se um corpus com campos como `titulo`, `resumo`, `descricao`, `objetivos` e areas.
- Gera-se uma matriz TF-IDF e treina-se um modelo NMF.
- Cada tema e resumido pelos termos mais relevantes e usado como etiqueta.
- Para cada oferta, selecionam-se temas com peso alto; se nao houver, usam-se os top-K.

## Reentrenos programados

Para reentrenar com novas ofertas sem bloquear a API, voce pode programar um job externo que chame `POST /train`.
Exemplo cron diario as 03:00:

```bash
0 3 * * * curl -X POST http://localhost:8000/train -H "Content-Type: application/json" -d '{"n_topics": 20, "active_only": true}'
```

Se quiser manter as etiquetas estaveis para usuarios, evite reentrenar e use o mesmo modelo para etiquetar novas ofertas.

## Interesses de usuario (fonte de verdade no back)

O back calcula os interesses consultando a base e transforma esses interesses em `tag_ids`.
O endpoint `POST /recommend/user` usa essa lista e chama o mesmo motor que `POST /recommend`.

Assume-se uma tabela `interests` com `id` e `tag_id` (FK para os ids de tags do modelo).
A relacao usuario-interesse e guardada em `user_cs_interests_list`:

- `user_cs`: usuarios, chave `id`.
- `user_cs_interests_list`: `entity_user_id`, `interests_list_id`.
- `interests`: `id`, `tag_id`.

Consulta padrao (configuravel com `USER_INTERESTS_SQL`):

```sql
SELECT i.tag_id
FROM user_cs_interests_list u
JOIN interests i ON i.id = u.interests_list_id
WHERE u.entity_user_id = %s
```

Para ativar o lookup e necessario definir `DATABASE_URL` (Postgres). Se usar outro motor,
substitua a funcao `fetch_user_tag_ids` e/ou o SQL pela versao correspondente.

### Postgres e por que nao convem mandar interesses pelo front

Se o motor e Postgres, o ideal e que o back seja a fonte de verdade dos interesses:

- Evita que o front tenha que conhecer ids internos de interesses e tags.
- Centraliza validacao e versionamento de etiquetas no back.
- Evita inconsistencias se o front enviar interesses desatualizados.

Se voce ainda quiser suportar que o front envie interesses, pode usar `POST /recommend` com `tag_ids`,
mas perde rastreabilidade e consistencia com a base. Recomendado: manter `POST /recommend/user`
como caminho principal e usar `POST /recommend` apenas para testes.

## Checklist de integracao para deixar operacional

### Dados e tabelas

- Tabela `user_cs`: existe `id` como PK.
- Tabela `user_cs_interests_list`: `entity_user_id`, `interests_list_id`.
- Tabela `interests`: `id`, `tag_id` (FK para ids de tags do modelo).
- `tag_id` deve mapear para os ids atuais do modelo; se reentrenar, versionar ou atualizar.

### Pipeline de dados

- Manter o modelo estavel se os usuarios ja possuem interesses associados a tags.
- Se reentrenar, recalcular `tag_id` em `interests` ou versionar tags.
- Ao carregar novas ofertas, usar `POST /tag-offers` para manter tags consistentes.

### API e configuracao

- Implementar `fetch_user_tag_ids` com Postgres e definir credenciais/DSN.
- Ajustar `USER_INTERESTS_SQL` se o esquema diferir.
- Ajustar `CLASS_INTERESTS_SQL` e `USERS_BY_INTERESTS_SQL` se o esquema diferir.
- Garantir que a API tenha acesso de leitura as tabelas de interesses.

### Validacoes recomendadas

- Verificar se todos os `tag_id` de `interests` existem em `/tags`.
- Se um usuario nao tiver interesses, devolver lista vazia sem erro.
- Manter `require_tag_match=true` para coerencia entre interesses e resultados.

## OneSignal (notificacoes)

Estado atual:

- Implementado `POST /notifications/offers/brief`.
- Implementado `POST /notifications/send`.

Pendentes:

- Definir `external_user_id`.
- Configurar credenciais do OneSignal.
- Definir modelo de dados para dispositivos.
- Definir dedupe.
- Considerar rate limits.

Variaveis de ambiente esperadas:

- `ONESIGNAL_APP_ID`
- `ONESIGNAL_API_KEY`
- `ONESIGNAL_API_URL` (opcional, default do provider)
- `ONESIGNAL_DRY_RUN` (opcional)
- `ONESIGNAL_LANG` (opcional)
- `NOTIFICATIONS_DEDUPE_SQL` (opcional)

### Endpoint de envio geral

A informacao que voce compartilhou serve como referencia de fluxo: validar payload, enviar ao OneSignal,
e depois persistir/registrar na base. Neste projeto o endpoint
`POST /notifications/send` foi implementado e aceita:

- `headings` e `contents` (por idioma)
- `external_user_ids` ou `included_segments` ou `filters` (pelo menos um)
- `data` opcional (para deep links ou metadata)

E retorna a resposta do OneSignal. Se quiser persistir/auditar, e preciso somar
uma tabela e registrar o envio.

### Notificacao por interesses de uma oferta

`POST /notifications/offers/class` recebe `class_id` e consulta `class_interest`
para obter `interest_id` (que sao os `tag_id` do modelo). Depois consulta
`user_cs_interests_list` para resolver usuarios e envia OneSignal usando `user_cs.id`
como `external_user_id`. Se nao enviar `heading`/`content`, monta com o brief
da oferta via `CLASS_BRIEF_SQL`.

Dedupe (recomendado): criar a tabela `notifications_sent` com chave unica `(class_id, user_id)`
e usar insert com `ON CONFLICT DO NOTHING` para evitar reenvios.

Variaveis SQL opcionais:

- `CLASS_INTERESTS_SQL`
- `USERS_BY_INTERESTS_SQL`
- `NOTIFICATIONS_DEDUPE_SQL`
- `CLASS_BRIEF_SQL`
