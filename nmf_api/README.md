# Recomendaciones con NMF

API sencilla para etiquetar ofertas con temas generados por NMF y recomendar segun intereses declarados.

## Requisitos

- Python 3.10+

## Instalacion rapida

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Datos de entrada

Por defecto se usan ambos archivos: [../classes.json](../classes.json) y [../vacantes.json](../vacantes.json). Si queres usar otro JSON o varios JSON, define:

```bash
export OFFER_DATA_PATH="/ruta/al/archivo.json"
# o varios archivos separados por coma
export OFFER_DATA_PATHS="/ruta/a/clases.json,/ruta/a/vacantes.json"
```

El JSON debe ser una lista de objetos (una oferta por elemento). Si se cargan varios archivos, las ofertas se combinan por `id_acao` (o por `id_anuncio_*` si no existe), y los campos faltantes se completan sin pisar valores ya existentes.

## Correr la API

```bash
uvicorn app.main:app --reload --port 8000
```

Si estas usando un venv en el repo:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker

Build de la imagen:

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

Levantar API + Postgres:

```bash
docker compose up --build
```

Notas:

- Usa `../classes.json` y `../vacantes.json` como volumenes en `/data`.
- Ajusta las credenciales y variables en `docker-compose.yml`.

## Endpoints principales

- `GET /tags` -> lista de etiquetas detectadas
- `POST /recommend` -> ofertas recomendadas segun etiquetas
- `POST /recommend/serendipity` -> recomendaciones con diversidad/novedad
- `POST /recommend/user` -> recomendaciones segun intereses del usuario (fuente de verdad en el back)
- `POST /train` -> reentrenar con nuevos parametros
- `GET /offers` -> lista ofertas con tags
- `GET /offers/active` -> lista ofertas activas con tags
- `GET /offers/normalized` -> lista ofertas con modelo de salida normalizado
- `GET /offers/brief` -> lista ofertas con titulo y descripcion
- `POST /tag-offers` -> etiquetar ofertas nuevas con el modelo actual
- `POST /notifications/offers/brief` -> enviar notificacion con ofertas brief
- `POST /notifications/send` -> envio general a OneSignal
- `POST /notifications/offers/class` -> notificar usuarios segun intereses de la oferta
- `POST /notifications/offers/auto` -> taggear oferta y notificar usuarios

## Endpoints de notificaciones (detalle)

### POST /notifications/offers/brief

Que hace:

- Obtiene los intereses del usuario desde la base.
- Recomienda ofertas y arma un mensaje breve con titulo/descripcion.
- Envia la notificacion a OneSignal usando `external_user_id` = `user_id`.

Recibe:

```json
{
  "user_id": 123,
  "limit": 5,
  "min_score": 0.0,
  "active_only": false,
  "require_tag_match": true,
  "heading": "Nuevas ofertas",
  "dry_run": false
}
```

Devuelve:

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

Que hace:

- Envia una notificacion generica a OneSignal.
- Requiere al menos uno de `external_user_ids`, `included_segments` o `filters`.

Recibe:

```json
{
  "external_user_ids": ["123"],
  "included_segments": ["All"],
  "filters": [{"field": "tag", "key": "vip", "relation": "=", "value": "1"}],
  "headings": {"es": "Titulo"},
  "contents": {"es": "Mensaje"},
  "data": {"url": "https://..."},
  "dry_run": false
}
```

Devuelve:

```json
{"onesignal": {"id": "..."}}
```

### POST /notifications/offers/class

Que hace:

- Busca `interest_id` de la oferta en `class_interest`.
- Resuelve usuarios en `user_cs_interests_list`.
- Aplica dedupe por `(class_id, user_id)` usando `notifications_sent`.
- Envia OneSignal a esos usuarios usando `user_cs.id` como `external_user_id`.
- Si no recibe `heading`/`content`, arma el brief con `extension_class`.

Recibe:

```json
{
  "class_id": 999,
  "heading": "Nueva oferta",
  "content": "Se abrio una oferta...",
  "interest_ids": [1, 2, 3],
  "data": {"class_id": 999},
  "dry_run": false
}
```

Devuelve:

```json
{
  "total_users": 42,
  "interest_ids": [1, 2, 3],
  "onesignal": {"id": "..."}
}
```

### POST /notifications/offers/auto

Que hace:

- Calcula tags de la oferta si no se pasan `interest_ids`.
- Persiste `class_interest` (opcional).
- Resuelve usuarios por intereses y aplica dedupe.
- Envia OneSignal con brief automatico si no se envia texto.

Recibe:

```json
{
  "class_id": 999,
  "offer": {"id_acao": "A1", "titulo": "...", "descricao": "..."},
  "heading": null,
  "content": null,
  "interest_ids": null,
  "persist_interests": true,
  "data": {"class_id": 999},
  "dry_run": false
}
```

Devuelve:

```json
{
  "total_users": 42,
  "interest_ids": [1, 2, 3],
  "tags": [1, 2, 3],
  "onesignal": {"id": "..."}
}
```

## Estructura del proyecto

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

Resumen rapido:

- `app/main.py`: crea la app e incluye routers.
- `app/routes/`: endpoints HTTP.
- `app/services/`: logica de negocio (modelo, intereses).
- `app/nmf_classifier.py`: entrenamiento y scoring NMF.
- `app/data_loader.py`: carga y merge de datos.
- `app/schemas.py`: modelos Pydantic.

## Ejemplos

Listar etiquetas:

```bash
curl http://localhost:8000/tags
```

Recomendar ofertas usando etiquetas 0 y 2:

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"tag_ids": [0, 2], "limit": 5, "active_only": true, "require_tag_match": true}'
```

Recomendar por usuario (intereses en el back):

```bash
curl -X POST http://localhost:8000/recommend/user \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123, "limit": 5, "active_only": true}'
```

Recomendar con serendipity (diversidad):

```bash
curl -X POST http://localhost:8000/recommend/serendipity \
  -H "Content-Type: application/json" \
  -d '{"tag_ids": [0, 2], "limit": 5, "active_only": true, "diversity_lambda": 0.7}'
```

Reentrenar con 10 temas:

```bash
curl -X POST http://localhost:8000/train \
  -H "Content-Type: application/json" \
  -d '{"n_topics": 10, "max_features": 6000, "active_only": true}'
```

## Como dialoga el train con el modelo

- El modelo se carga en el arranque con los datos actuales.
- `POST /train` recalcula temas y actualiza en memoria el modelo y todas las etiquetas.
- Si queres mantener etiquetas fijas para los usuarios, evita reentrenar y usa el mismo modelo para etiquetar nuevas ofertas.
- Si reentrenas, las etiquetas pueden cambiar (ids y terminos) y deberias versionarlas.

### Parametros del entrenamiento inicial

El entrenamiento inicial usa los defaults de `TaggerConfig` en [app/nmf_classifier.py](recomendaciones/nmf_api/app/nmf_classifier.py),
invocados en `startup_model` de [app/services/model_service.py](recomendaciones/nmf_api/app/services/model_service.py).
Para cambiarlos en runtime, usa `POST /train` con esos mismos parametros.

Impacto por parametro (a mayor valor / a menor valor):

- `n_topics`: mas temas = mayor granularidad, mas etiquetas; menos temas = etiquetas mas generales.
- `max_features`: mas vocabulario = mas detalle, mayor costo; menos vocabulario = mas ruido filtrado, menor detalle.
- `min_df`: mas alto = elimina terminos raros, mas estabilidad; mas bajo = conserva terminos raros, mas ruido.
- `max_df`: mas bajo = elimina terminos muy frecuentes, mas foco; mas alto = deja terminos comunes, menos discriminacion.
- `ngram_range`: incluir bigramas mejora frases, pero sube costo y sparsity.
- `top_terms`: mas terminos por tema = etiquetas mas largas; menos terminos = etiquetas mas cortas.
- `topic_threshold`: mas alto = menos tags por oferta; mas bajo = mas tags por oferta.
- `top_k`: mas alto = mas tags cuando no hay umbral; mas bajo = menos tags forzados.

## Etiquetar ofertas nuevas sin reentrenar

Para mantener las etiquetas fijas, usa el mismo modelo y etiqueta solo las ofertas nuevas con `POST /tag-offers`.

1. Extrae las ofertas nuevas desde tu fuente.
2. Envia esas ofertas al endpoint `/tag-offers`.
3. Guarda `tags` y `tag_labels` en tu base.

Ejemplo:

```bash
curl -X POST http://localhost:8000/tag-offers \
  -H "Content-Type: application/json" \
  -d '{"items": [{"id_acao": "ABC", "titulo": "Oferta nueva", "resumo": "Texto"}]}'
```

## Ingesta a base de datos

Una forma simple de poblar la base es consumir `GET /offers/normalized` y hacer upsert por `offer_id`:

1. Llamar a `/offers/normalized?limit=200&offset=0`
2. Guardar campos normalizados y `tags`
3. Repetir con `offset` hasta completar

Ejemplo con paginado:

```bash
curl "http://localhost:8000/offers/normalized?limit=200&offset=0"
```

Si queres almacenar etiquetas, guarda `tags` y (opcional) `is_active` en la tabla de ofertas.

Listar ofertas activas (inscripciones vigentes):

```bash
curl "http://localhost:8000/offers/active?limit=20&offset=0"
```

Listar ofertas normalizadas:

```bash
curl "http://localhost:8000/offers/normalized?limit=20&offset=0&tag_ids=2&tag_ids=5"
```

Listar titulo y descripcion:

```bash
curl "http://localhost:8000/offers/brief?limit=20&offset=0&tag_ids=2&tag_ids=5"
```

## Notas sobre el algoritmo

- Se arma un corpus con campos como `titulo`, `resumo`, `descricao`, `objetivos` y areas.
- Se genera una matriz TF-IDF y se entrena un modelo NMF.
- Cada tema se resume con sus terminos mas relevantes y se usa como etiqueta.
- Para cada oferta se seleccionan temas con peso alto; si no hay, se usan los top-K.

## Reentrenos programados

Para reentrenar con nuevas ofertas sin bloquear la API, podes programar un job externo que llame a `POST /train`.
Ejemplo cron diario a las 03:00:

```bash
0 3 * * * curl -X POST http://localhost:8000/train -H "Content-Type: application/json" -d '{"n_topics": 20, "active_only": true}'
```

Si queres mantener estables las etiquetas para los usuarios, evita reentrenar y usa el mismo modelo para etiquetar ofertas nuevas.

## Intereses de usuario (fuente de verdad en el back)

El back calcula los intereses consultando la base y transforma esos intereses a `tag_ids`.
El endpoint `POST /recommend/user` usa ese listado y llama al mismo motor que `POST /recommend`.

Se asume una tabla `interests` con `id` y `tag_id` (FK a los ids de tags del modelo).
La relacion usuario-interes se guarda en `user_cs_interests_list`:

- `user_cs`: usuarios, clave `id`.
- `user_cs_interests_list`: `entity_user_id`, `interests_list_id`.
- `interests`: `id`, `tag_id`.

Consulta por defecto (configurable con `USER_INTERESTS_SQL`):

```sql
SELECT i.tag_id
FROM user_cs_interests_list u
JOIN interests i ON i.id = u.interests_list_id
WHERE u.entity_user_id = %s
```

Para activar el lookup hay que definir `DATABASE_URL` (Postgres). Si usan otro motor,
reemplaza la funcion `fetch_user_tag_ids` y/o el SQL por la version correspondiente.

### Postgres y porque no conviene mandar intereses desde el front

Si el motor es Postgres, lo ideal es que el back sea la fuente de verdad de intereses:

- Evitas que el front tenga que conocer ids internos de intereses y tags.
- Centralizas validacion y versionado de etiquetas en el back.
- Evitas inconsistencias si el front envia intereses desactualizados.

Si aun queres soportar que el front envie intereses, podes usar `POST /recommend` con `tag_ids`,
pero perdes trazabilidad y consistencia con la base. Recomendado: mantener `POST /recommend/user`
como camino principal y usar `POST /recommend` solo para pruebas.

## Checklist de integracion para dejarlo operativo

### Datos y tablas

- Tabla `user_cs`: existe `id` como PK.
- Tabla `user_cs_interests_list`: `entity_user_id`, `interests_list_id`.
- Tabla `interests`: `id`, `tag_id` (FK a ids de tags del modelo).
- `tag_id` debe mapear a los ids actuales del modelo; si se reentrena, versionar o actualizar.

### Pipeline de datos

- Mantener el modelo estable si los usuarios ya tienen intereses asignados a tags.
- Si se reentrena, recalcular `tag_id` en `interests` o versionar tags.
- Al cargar ofertas nuevas, usar `POST /tag-offers` para mantener tags consistentes.

### API y configuracion

- Implementar `fetch_user_tag_ids` con Postgres y definir credenciales/DSN.
- Ajustar `USER_INTERESTS_SQL` si el esquema difiere.
- Ajustar `CLASS_INTERESTS_SQL` y `USERS_BY_INTERESTS_SQL` si el esquema difiere.
- Asegurar que la API tenga acceso de lectura a las tablas de intereses.

### Validaciones recomendadas

- Verificar que todos los `tag_id` de `interests` existan en `/tags`.
- Si un usuario no tiene intereses, devolver lista vacia sin error.
- Mantener `require_tag_match=true` para coherencia entre intereses y resultados.

## OneSignal (notificaciones)

Estado actual:

- Implementado `POST /notifications/offers/brief`.
- Implementado `POST /notifications/send`.

Pendientes:

- Definir `external_user_id`.
- Configurar credenciales de OneSignal.
- Definir modelo de datos para dispositivos.
- Definir dedupe.
- Considerar rate limits.

Variables de entorno esperadas:

- `ONESIGNAL_APP_ID`
- `ONESIGNAL_API_KEY`
- `ONESIGNAL_API_URL` (opcional, default del provider)
- `ONESIGNAL_DRY_RUN` (opcional)
- `ONESIGNAL_LANG` (opcional)
- `NOTIFICATIONS_DEDUPE_SQL` (opcional)

### Endpoint de envio general

La info que compartiste sirve como referencia de flujo: validar payload, enviar a OneSignal,
y luego persistir/registrar en base. En este proyecto se implementa el endpoint
`POST /notifications/send` que acepta:

- `headings` y `contents` (por idioma)
- `external_user_ids` o `included_segments` o `filters` (al menos uno)
- `data` opcional (para deep links o metadata)

Y devuelve la respuesta de OneSignal. Si queres persistir/auditar, hay que sumar
una tabla y registrar el envio.

### Notificacion por intereses de una oferta

`POST /notifications/offers/class` toma `class_id` y consulta `class_interest` para
obtener los `interest_id` (que son los `tag_id` del modelo). Luego consulta
`user_cs_interests_list` para resolver usuarios y envia OneSignal usando `user_cs.id`
como `external_user_id`. Si no se envia `heading`/`content`, se arma con el brief
de la oferta via `CLASS_BRIEF_SQL`.

Dedupe (recomendado): crear la tabla `notifications_sent` con clave unica `(class_id, user_id)`
y usar el insert con `ON CONFLICT DO NOTHING` para evitar reenvios.

DDL sugerido en [db/notifications_sent.sql](recomendaciones/nmf_api/db/notifications_sent.sql).

Variables SQL opcionales:

- `CLASS_INTERESTS_SQL`
- `USERS_BY_INTERESTS_SQL`
- `NOTIFICATIONS_DEDUPE_SQL`
- `CLASS_BRIEF_SQL`
- `CLASS_INTERESTS_INSERT_SQL`
