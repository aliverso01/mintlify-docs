# Portal de desenvolvedor da Miggo

Fonte do [developer.miggomkt.com.br](https://developer.miggomkt.com.br), feito em
[Mintlify](https://mintlify.com). Documenta os três softwares da Miggo para quem
mexe no código: a Plataforma (`backend-miggo`), o Web app (`frontend-miggo`) e o
MiggoAI (`miggoai_v2/backend`). Regras de escrita e de navegação: [`AGENTS.md`](AGENTS.md).

## Estrutura

| Caminho | Aba |
|---|---|
| `index.mdx`, `quickstart.mdx`, `arquitetura/` | Visão geral |
| `plataforma/` | Plataforma (`backend-miggo`) |
| `web/` | Web app (`frontend-miggo`) |
| `miggoai/` | MiggoAI (backend do serviço de IA) |
| `releases/` | Changelog |
| `api-reference/<software>/openapi.json` | specs OpenAPI usados pela Referência de API |
| `scripts/openapi_tags.py` | pós-processamento dos specs (tags, `summary`, limpeza das descrições, segurança, `info`, `servers`) |
| `docs.json` | navegação, redirects e tema |

## Preview local

```bash
npx -y mint dev --port 3002
npx -y mint broken-links   # antes de commitar
```

## Regenerar a Referência de API

Os specs são gerados do código da `main` de cada repo com o `drf-spectacular`
e pós-processados pelo `scripts/openapi_tags.py`, que:

- troca tags genéricas (`api`, `generations`) por tags por recurso em pt-BR e
  reagrupa as grandes demais ou de uma operação só (cada tag vira um grupo na
  navegação);
- gera o `summary` de cada operação (título da página do endpoint);
- tira das descrições o número de card, a linha que repete verbo e caminho,
  citação de arquivo `.py` e docstring de classe base;
- declara os esquemas `jwtAuth` (Bearer) e `apiKeyAuth` (`Authorization: Api-Key`);
- fixa `info` e `servers` (produção e homologação) de cada perfil.

O `settings.py` dos dois repos exige variáveis na importação. Valores fictícios
bastam: o comando só importa URLs e views, não conecta no banco nem chama
serviço externo. Nunca use o `.env` de um ambiente real para isso.

**Plataforma** (no checkout da `main` do `backend-miggo`; mesmas variáveis do
`manage.py check` do CI em `.github/workflows/docker-ecr.yml`):

```bash
export DEBUG=False SECURE_SSL_REDIRECT=False
export DB_NAME=ci DB_USER=ci DB_PASSWORD=ci DB_HOST=localhost DB_PORT=5432
export EMAIL_HOST=localhost EMAIL_PORT=25 EMAIL_HOST_USER=ci EMAIL_HOST_PASSWORD=ci
export MIGGO_API_KEY=ci JWT_PRIVATE_KEY="$(openssl genrsa 2048 2>/dev/null)"
./venv/Scripts/python.exe manage.py spectacular --format openapi-json --file <repo-de-doc>/api-reference/backend-miggo/openapi.json
```

**MiggoAI** (em `miggoai_v2/backend`, na `main`):

```bash
openssl genrsa -out /tmp/k.pem 2048 && openssl rsa -in /tmp/k.pem -pubout -out /tmp/k.pub
export SECRET_KEY=ci DEBUG=False
export DB_NAME=ci DB_USER=ci DB_PASSWORD=ci DB_HOST=localhost DB_PORT=5432
export MIGGO_API_KEY=ci MIGGO_API_BASE_URL=http://localhost:8000
export MIGGO_JWT_PUBLIC_KEY="$(cat /tmp/k.pub)"
./venv/Scripts/python.exe manage.py spectacular --format openapi-json --file <repo-de-doc>/api-reference/miggoai/openapi.json
```

Se o settings passar a exigir outra variável, o comando falha com
`UndefinedValueError` dizendo qual: acrescente um valor fictício.

Depois, na raiz deste repo:

```bash
python scripts/openapi_tags.py api-reference/backend-miggo/openapi.json --perfil plataforma --versao 2.3.0
python scripts/openapi_tags.py api-reference/miggoai/openapi.json --perfil miggoai --versao 2.3.0
```

Se sobrar problema, o script sai com código `1`, lista o que falta e **não grava**
o arquivo: caminho sem regra (`REGRAS_POR_CAMINHO`), `summary` repetido na mesma
tag (`RESUMOS_FIXOS` ou `NOMES`), tag sem descrição (`DESCRICOES_TAGS`) ou número
de card que a limpeza não tirou. Tag nova em inglês declarada no código entra em
`TRADUCOES`. Rodar de novo sobre o arquivo já processado não muda nada.

## Publicação

O deploy é automático no push da `main`. Trabalhe em branch e não faça push
direto: veja [`AGENTS.md`](AGENTS.md).
