# Estimacao de implementacao - Cidade Social + NMF + OneSignal

Este documento resume consideracoes necessarias para que outra universidade implemente o stack e a integracao de recomendacoes/notificacoes.

## Prerrequisitos

- Docker e Docker Compose no host.
- PostgreSQL com tabelas de usuarios, interesses e classes/ofertas.
- Keycloak configurado se usar autenticacao/autorizacao.
- Credenciais do OneSignal (App ID e API Key).
- Fontes de dados para treinamento (ofertas de atividades/vacantes e informacao sobre inscricao ou equivalente).

## Pipeline externo a app

A app nao define o pipeline de validacao. Assume-se um fluxo externo que:

1. Valida ofertas de atividades (fonte oficial).
2. Gerencia inscricoes fora da app (sistema academico ou portal proprio).

A API de recomendacoes consome esse estado e nao substitui o fluxo academico, resolve a difusao das propostas a potenciais interessados. Classifica um corpus de ofertas em tematicas usando algoritmos e devolve essas tematicas para que usuarios indiquem interesses. Depois, para uma oferta dada, detecta os interesses associados, busca usuarios que os declararam e envia notificacoes sobre essas ofertas.

## Integracao de dados

- `interest.id` deve coincidir com `tag_id` do modelo.
- `class_interest` liga ofertas a interesses (tabela ponte).
- `user_cs_interests_list` liga usuarios a interesses.
- `user_cs.id` e usado como `external_user_id` no OneSignal.

## Volume de dados e performance

- Treinamento inicial: depende do numero de ofertas e do texto total.
- Re-treinos: recomendados fora do horario de pico. Sao opcionais; pode-se apenas classificar o novo com o modelo existente (como na prova piloto). Se re-treinar, e preciso resolver o mapeamento.
- Notificacoes por oferta: o custo principal e resolver usuarios por interesses.

Regra simples:

- Menos de 50k usuarios: query direta e suficiente.
- Mais de 50k usuarios: considerar materializar usuarios por interesse ou usar batch.

## Requisitos de servidores (referencia)

Ambientes de teste:

- 1 VM: 2-4 vCPU, 8-16 GB RAM, 30-50 GB disco.

Ambientes de producao (linha base):

- API + NMF: 2-4 vCPU, 8-16 GB RAM.
- Postgres dedicado: 2-4 vCPU, 8-16 GB RAM.
- Keycloak: 1-2 vCPU, 2-4 GB RAM.
- Elastic/Kibana (se usar): 2-4 vCPU, 8-16 GB RAM.

Escalonamento por usuarios (regra simples):

- A cada +10k usuarios ativos/mes: somar 1 vCPU e 2-4 GB RAM a API/DB.
- A cada +50k usuarios ativos/mes: considerar separar servicos e adicionar cache.

## Operacao recomendada

- Re-treino sob demanda ou programado.
- Dedupe de notificacoes por `(class_id, user_id)`.
- Monitoramento basico de erros na API e DB.

## Como rodar todos os microservicos

A partir da pasta `cidade-social-compose/`:

```bash
docker compose up --build -d
```

Para ver logs de um servico:

```bash
docker compose logs -f csgateway
```

Para desligar tudo:

```bash
docker compose down
```

Se precisar limpar dados persistidos:

```bash
docker compose down -v
```
