# Estimacion de implementacion - Cidade Social + NMF + OneSignal

Este documento resume consideraciones necesarias para que otra universidad implemente el stack y la integracion de recomendaciones/notificaciones.

## Prerrequisitos

- Docker y Docker Compose en el host.
- PostgreSQL con tablas de usuarios, intereses y clases/ofertas.
- Keycloak configurado si se usa autenticacion/autorizacion.
- Credenciales de OneSignal (App ID y API Key).
- Fuentes de datos para entrenamiento (oferta de actividades/vacantes e información sobre la inscripción o equivalente).

## Pipeline externo a la app

La app no define el pipeline de validacion. Se asume un flujo externo que:

1. Valida ofertas de actividades (fuente oficial).
2. Gestiona inscripciones por fuera de la app (sistema academico o portal propio).

La API de recomendaciones consume ese estado y no reemplaza el flujo academico: resuelve la difusión de las propuestas a potenciales interesados. Clasifica un corpus de ofertas en tematicas usando algoritmos y devuelve esas tematicas para que los usuarios indiquen intereses. Luego, para una oferta dada detecta los intereses asociados, busca usuarios que los hayan declarado y les envia notificaciones sobre esas ofertas.

## Integracion de datos

- `interest.id` debe coincidir con `tag_id` del modelo.
- `class_interest` enlaza ofertas con intereses (tabla puente).
- `user_cs_interests_list` enlaza usuarios con intereses.
- `user_cs.id` se usa como `external_user_id` en OneSignal.

## Volumen de datos y performance

- Entrenamiento inicial: depende del numero de ofertas y del texto total.
- Reentrenos: recomendados fuera de horario pico. Son opcionales; se puede solo clasificar lo nuevo con lo preexistente (como en la prueba piloto). Si se reentrena, hay que resolver el mapeo.
- Notificaciones por oferta: el costo principal es resolver usuarios por intereses.

Regla simple:

- Menos de 50k usuarios: query directa es suficiente.
- Mas de 50k usuarios: considerar materializar usuarios por interes o usar batch.

## Requerimientos de servidores (referencia)

Ambientes de prueba:

- 1 VM: 2-4 vCPU, 8-16 GB RAM, 30-50 GB disco.

Ambientes productivos (linea base):

- API + NMF: 2-4 vCPU, 8-16 GB RAM.
- Postgres dedicado: 2-4 vCPU, 8-16 GB RAM.
- Keycloak: 1-2 vCPU, 2-4 GB RAM.
- Elastic/Kibana (si se usa): 2-4 vCPU, 8-16 GB RAM.

Escalado por usuarios (regla simple):

- Cada +10k usuarios activos/mes: sumar 1 vCPU y 2-4 GB RAM a API/DB.
- Cada +50k usuarios activos/mes: considerar separar servicios y agregar cache.

## Operacion recomendada

- Reentreno bajo demanda o programado.
- Dedupe de notificaciones por `(class_id, user_id)`.
- Monitoreo basico de errores en API y DB.

## Como correr todos los microservicios

Desde la carpeta `cidade-social-compose/`:

```bash
docker compose up --build -d
```

Para ver logs de un servicio:

```bash
docker compose logs -f csgateway
```

Para apagar todo:

```bash
docker compose down
```

Si se necesita limpiar datos persistidos:

```bash
docker compose down -v
```
