> Para conhecimento de produto da Mintlify (componentes, configuração, padrões
> de escrita), instale a skill: `npx skills add https://mintlify.com/docs`

# Instruções do projeto de documentação técnica

## Sobre este projeto

- Documentação **técnica interna** dos repositórios do workspace Miggo:
  `backend-miggo`, `frontend-miggo` e `miggoai-2.0/miggoai_v2`.
- Público-alvo: **a equipe de desenvolvimento e os agentes de IA do workspace**.
  Não é documentação de cliente final — essa é a `miggo-docs/`, um repo separado.
- Site em [Mintlify](https://mintlify.com). Páginas são arquivos MDX com
  frontmatter YAML; a configuração e a navegação ficam em `docs.json`.
- Todo o conteúdo é em **português do Brasil**.
- Preview local: `npx -y mint dev --port 3002` (já roda no terminal `Docs Interna`
  do canvas Maestri). A `miggo-docs` usa a 3001 — não confunda as duas.

## Não confunda com a doc pública

A `miggo-docs/` tem uma tabela de terminologia que **troca o nome técnico pelo
nome do menu** ("Meus conteúdos" em vez de Kanban, "Minha marca" em vez de
brandkit). **Aqui é o contrário:** este repo documenta o sistema para quem mexe
no código, então use o nome real — app `brandkit`, modelo `PlatformProfileConfig`,
`CustomUser`, endpoint `/api/v1/account/token/`. Nomear coisas pelo rótulo da
interface aqui torna a página inútil para quem precisa achar o código.

Quando a página precisar citar o que o usuário vê, diga os dois: *o módulo
`brandkit` (na interface, "Minha marca")*.

## Estrutura

Uma aba por software, cada uma no formato Diátaxis: comece aqui → guias → conceitos/domínios → referência de API → operação.

| Pasta | Aba | Conteúdo |
|-------|-----|----------|
| `index.mdx`, `quickstart.mdx`, `arquitetura/` | Visão geral | arquitetura, fluxos, integrações externas, ambientes, glossário, convenções |
| `plataforma/` | Plataforma (`backend-miggo`) | rodar localmente, variáveis, autenticação, estrutura, guias (`guias/`), filas, crons, comandos, testes, deploy, introdução à API |
| `plataforma/apps/` | Plataforma → Domínios | uma página por app Django: propósito, models principais, regras, integrações, onde fica no código |
| `web/` | Web app (`frontend-miggo`) | rodar localmente, estrutura, autenticação, guias (`guias/`), roteamento, estado e dados, áreas (`/app`, `/admin`, painel de IA), qualidade, build e deploy |
| `miggoai/` | MiggoAI (só o backend de `miggoai_v2`) | rodar localmente, variáveis, autenticação, arquitetura, guias (`guias/`), workflows, prompts, OpenAI, custos, modelo de dados, introdução à API, testes, deploy |
| `releases/` | Changelog | uma entrada por release; versionamento |
| `api-reference/<software>/openapi.json` | Referência de API | specs gerados do código; viram as páginas de endpoint |
| `scripts/openapi_tags.py` | — | pós-processa os specs (tags por recurso, em pt-BR) |
| `snippets/` | — | trechos reutilizáveis (hoje vazio) |

O frontend próprio do `miggoai_v2` e o protótipo `modules/` **não** são documentados: a interface de IA é o painel do `/admin` no `frontend-miggo` (`web/painel-de-ia`).

**Veja se a página já existe antes de criar outra** — prefira editar a duplicar.

### O que não entra nas páginas

- Número de card (`MIG-nnn`): só no changelog.
- `arquivo.py:linha`: cite o caminho do arquivo ou `modulo.py::simbolo`, nunca a linha.
- Tabela manual de rotas, parâmetros e respostas: a referência OpenAPI cobre. A página de domínio linka para a introdução da API (`plataforma/api-referencia`).
- Narração de processo do time, passos de Jira, seções "Pontos de atenção" e dívida técnica (isso é backlog). Fica só aviso que muda o uso (`<Warning>`).
- O que está "planejado": a doc descreve a `main`.

## Frontmatter

Três campos, nesta ordem:

```mdx
---
title: "Testes da Plataforma"
description: "Como rodar a suíte do backend-miggo e o que fazer quando o banco de teste não sobe."
icon: "flask-conical"
---
```

- `title`: curto, sentence case, distinguível na busca (evite três páginas chamadas só "Configuração").
- `description`: uma frase com ponto final dizendo o que a página resolve.
- `icon`: nome de ícone [Lucide](https://lucide.dev/icons) (o `docs.json` declara `"icons": {"library": "lucide"}`). Não use nomes do Font Awesome.

## `docs.json` — navegação

Página nova **só é alcançável se entrar na navegação**. As abas são *Visão geral*, *Plataforma*, *Web app*, *MiggoAI* e *Changelog*. Os caminhos nas `pages` são sem extensão (`plataforma/testes`).

- Os endpoints vêm dos grupos com `"openapi"` (`Endpoints da Plataforma`, `Endpoints do MiggoAI`); cada tag do spec vira um subgrupo. Não liste endpoint à mão.
- Acrescentar uma entrada ao grupo certo: ok, é o fluxo normal.
- **Renomeou ou removeu uma página? Acrescente o `redirects`** do caminho antigo para o novo. Link compartilhado não pode quebrar.
- Nenhuma entrada sem arquivo e nenhum `.mdx` fora da navegação. Antes de commitar: `npx -y mint broken-links`.
- Mudar tema, cores, nome do site, domínio ou reordenar abas: **só por pedido explícito.**
- A versão no `navbar` acompanha a última release do changelog.

## Referência de API (OpenAPI)

Os specs em `api-reference/` são gerados do código da `main` com `drf-spectacular` e passam pelo `scripts/openapi_tags.py`. O passo a passo para regenerar está no `README.md`. Regenere a cada release que mexer em rota ou serializer e atualize `--versao`. Prefixo de caminho novo sem regra faz o script sair com código 1 e listar o caminho: acrescente a regra em `REGRAS_POR_CAMINHO`.

## Verifique no código antes de escrever

Documentar o que você supõe que o sistema faz é pior que não documentar. Antes de
afirmar comportamento, confirme no repo correspondente — `Grep` para achar o
ponto, `Read` só no trecho. Fatos úteis já verificados do workspace:

| | Valor |
|---|---|
| Raiz do workspace | `D:\Projetos\Miggo` (não é repo git; cada repo tem o seu) |
| Venv do backend | `backend-miggo/venv/Scripts/python.exe` |
| Venv do miggoai | `miggoai-2.0/miggoai_v2/backend/venv/Scripts/python.exe` |
| Backend local | `python manage.py runserver 8000` · settings `core.settings` · Django 5.2.7 |
| Frontend local | `npm run dev` → 5173 (Vite 6) |
| Auth da API | JWT (`rest_framework_simplejwt`); access 30 min em memória, refresh 7 dias em cookie httpOnly; `POST /api/v1/account/token/` |
| Modelo de usuário | `account.CustomUser` (login por e-mail, campo `role`: `admin`/`client`) |

**Suíte do backend:** o Postgres local não cria o DB de teste (morre com
`EOFError`), então roda com sqlite em memória via um settings do workspace
(documentado em `plataforma/testes`):

```bash
PYTHONPATH=D:/Projetos/Miggo/.maestri \
  backend-miggo/venv/Scripts/python.exe backend-miggo/manage.py test \
  --settings=test_settings
```

São ~854 testes, ~165s. Três falhas são **pré-existentes na `develop`** e não são
regressão: `app.media.tests_galeria.SaneamentoTests.test_arte_de_post_no_acervo_volta_para_fora`,
`app.post.tests.PostListViewTests.test_has_post_format_true_filters_posts_without_raising_error`
e o erro de loader do `test_grid.py` da raiz. Se documentar a página de testes,
registre isso — já custou tempo a mais de uma pessoa.

**Frontend:** nenhum dos dois frontends tem test runner (sem vitest, jest,
playwright ou cypress). A verificação automatizada é `npm run lint` (ESLint;
`oxlint` no miggoai) + `npm run build` (`tsc -b`). Não documente teste que não
existe.

## Git e publicação

- Trabalhe em branch: `git -C mintlify-docs checkout -b docs/<assunto>`.
- **Commit sim, push não.** Um hook `pre-push` recusa push em `main`, `master` e
  `develop` neste repo — não tente contornar com `--no-verify`. Terminado,
  reporte: branch, páginas tocadas e o que ficou pendente.
- Não commite segredo, token, `.env` ou dump com dado de cliente real.

## Estilo

- Mudança mínima no assunto pedido. Nada de reescrever página inteira para
  "melhorar" — refator de doc fora de escopo não entra.
- Prefira tabela a parágrafo quando o conteúdo é um mapa de nomes para valores.
- Caminho de arquivo, comando, nome de classe e de endpoint sempre em `código`.
- Não prometa roadmap nem descreva o que está "planejado": esta doc descreve o
  que existe hoje no código.
