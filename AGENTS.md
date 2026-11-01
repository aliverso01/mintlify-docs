> Para conhecimento de produto da Mintlify (componentes, configuração, padrões
> de escrita), instale a skill: `npx skills add https://mintlify.com/docs`

# Instruções do projeto de documentação técnica

## Sobre este projeto

- Portal de desenvolvedor da Miggo, publicado em `developer.miggomkt.com.br`:
  documentação técnica de `backend-miggo`, `frontend-miggo` e `miggoai-2.0/miggoai_v2`.
- Público-alvo: **quem escreve código nos três softwares** (time e agentes de IA).
  O portal é público: nada de segredo, caminho de máquina local, processo interno do
  time ou dado de cliente. A doc de cliente final é a `miggo-docs/`
  (`ajuda.miggomkt.com.br`), um repo separado.
- Site em [Mintlify](https://mintlify.com). Páginas são arquivos MDX com
  frontmatter YAML; a configuração e a navegação ficam em `docs.json`.
- Todo o conteúdo é em **português do Brasil**.
- Preview local: `npx -y mint dev --port 3002`. A `miggo-docs` usa a 3001 — não confunda as duas.

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

Uma aba por software. As abas Plataforma, Web app e MiggoAI usam o mesmo molde de grupos, nesta ordem: **Comece aqui** (rodar localmente, variáveis, autenticação) → **Guias** (tarefa com objetivo, pré-requisitos, passos e resultado verificável) → **Conceitos** (na Plataforma, com o subgrupo *Domínios*) → **Referência** (introdução à API, endpoints do OpenAPI, modelo de dados, comandos, rotas) → **Operação** (agendamentos, testes, deploy). A Visão geral usa Comece aqui → Conceitos → Referência.

| Pasta | Aba | Conteúdo |
|-------|-----|----------|
| `index.mdx`, `quickstart.mdx`, `arquitetura/` | Visão geral | arquitetura, fluxos, integrações externas, ambientes, glossário, convenções |
| `plataforma/` | Plataforma (`backend-miggo`) | rodar localmente, variáveis, autenticação, guias (`guias/`), estrutura, ciclo do conteúdo, filas, introdução à API, modelo de dados, comandos, tarefas agendadas, testes, deploy |
| `plataforma/apps/` | Plataforma → Domínios | uma página por app Django: propósito, models principais, regras, integrações, onde fica no código |
| `web/` | Web app (`frontend-miggo`) | rodar localmente, variáveis (`configuracao`), sessão e login, guias (`guias/`), estrutura, roteamento, estado e dados, áreas (`/admin`, `/agency`, painel de IA), telas e rotas, qualidade, build e deploy |
| `miggoai/` | MiggoAI (só o backend de `miggoai_v2`) | rodar localmente, variáveis, autenticação, guias (`guias/`), arquitetura, workflows, prompts, OpenAI, custos, integração com a Plataforma, introdução à API, modelo de dados, testes, deploy |
| `releases/` | Changelog | uma entrada por release; versionamento |
| `api-reference/<software>/openapi.json` | Referência de API | specs gerados do código; viram as páginas de endpoint |
| `scripts/openapi_tags.py` | — | pós-processa os specs: tags, `summary` em pt-BR, limpeza das descrições, segurança, `info` e `servers` |

O frontend próprio do `miggoai_v2` e o protótipo `modules/` **não** são documentados nem citados (nem no changelog): a interface de IA é o painel do `/admin` no `frontend-miggo` (`web/painel-de-ia`).

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

- `title`: curto, sentence case, distinguível na busca. Nas abas de software, título genérico leva o nome do software ("Testes da Plataforma", "Rodar o Web app localmente", "Deploy do MiggoAI"); página de domínio com nome próprio ("Brandkit") não precisa. Escreva "Plataforma" e "Web app" com maiúscula quando forem o nome do software.
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

Os specs em `api-reference/` são gerados do código da `main` com `drf-spectacular` e passam pelo `scripts/openapi_tags.py`. O passo a passo para regenerar está no `README.md`. Regenere a cada release que mexer em rota ou serializer e atualize `--versao`.

O script é idempotente, grava em LF e **não grava nada** quando sobra problema: caminho sem regra de tag (acrescente em `REGRAS_POR_CAMINHO`), `summary` repetido na mesma tag (acrescente em `RESUMOS_FIXOS` ou em `NOMES`), tag sem descrição (`DESCRICOES_TAGS`) ou `MIG-nnn` que a limpeza não tirou. Tag grande demais ou de uma operação só se ajusta em `REAGRUPAMENTO`.

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

**Suíte do backend:** quando o Postgres local não cria o DB de teste, a suíte
roda com sqlite em memória por um `test_settings.py` fora do repo. A página
`plataforma/testes` mostra o arquivo e o comando com caminho genérico; mantenha
assim (nada de caminho da sua máquina). Falhas conhecidas da suíte mudam a cada
release: não as registre no portal.

**Frontend:** nenhum dos dois frontends tem test runner (sem vitest, jest,
playwright ou cypress). A verificação automatizada é `npm run lint` (ESLint;
`oxlint` no miggoai) + `npm run build` (`tsc -b`). Não documente teste que não
existe.

## Git e publicação

- Trabalhe em branch: `git -C mintlify-docs checkout -b docs/<assunto>`.
- **Commit sim, push não**, salvo na publicação. Um hook `pre-push` recusa push em
  `main`, `master` e `develop` neste repo. A publicação na `main` (deploy automático)
  acontece só quando o card chega a *Em produção*, por quem conduz a release, com
  `git push --no-verify origin <branch>:main` deliberado (fast-forward, nunca force).
  Fora disso, não contorne o hook. Terminado, reporte: branch, páginas tocadas e o
  que ficou pendente.
- Não commite segredo, token, `.env` ou dump com dado de cliente real.

## Estilo

- Mudança mínima no assunto pedido. Nada de reescrever página inteira para
  "melhorar" — refator de doc fora de escopo não entra.
- Prefira tabela a parágrafo quando o conteúdo é um mapa de nomes para valores.
- Caminho de arquivo, comando, nome de classe e de endpoint sempre em `código`.
- Não prometa roadmap nem descreva o que está "planejado": esta doc descreve o
  que existe hoje no código.
