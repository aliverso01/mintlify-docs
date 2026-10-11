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

| Pasta | Conteúdo |
|-------|----------|
| `arquitetura/` | visão geral, fluxos, ambientes, integrações externas, convenções |
| `backend/` | `backend-miggo` (Django): instalação, configuração, estrutura, modelo de dados, autenticação, comandos, tarefas agendadas, testes, deploy, referência de API |
| `backend/apps/` | uma página por app Django (`account`, `client`, `post`, `media`, `subscription`, `brandkit`, `webhooks`, …) |
| `frontend/` | `frontend-miggo` (React 19 + Vite + TS): estrutura, roteamento, páginas, componentes, contextos, hooks, services, área admin, tema, qualidade, build |
| `miggoai/` | serviço de IA: arquitetura, modelo de dados, prompts, workflows, integração OpenAI, referência de API |
| `snippets/` | trechos reutilizáveis (hoje vazio) |

São 55 páginas. **Veja se a página já existe antes de criar outra** — prefira
editar a duplicar.

## Frontmatter

Siga o padrão das páginas existentes: três campos, nesta ordem.

```mdx
---
title: "Suíte de testes"
description: "Como rodar os testes automatizados do backend-miggo e o que cada app cobre"
icon: "flask-conical"
---
```

- `title`: curto, substantivo, sem o nome do repo quando a pasta já diz.
- `description`: uma frase dizendo o que a página resolve. É o subtítulo no site.
- `icon`: nome de ícone [Lucide](https://lucide.dev) (ex.: `flask-conical`).

## `docs.json` — navegação

Página nova **só é alcançável se entrar na navegação**. As abas são *Visão geral*
(com os grupos "Comece por aqui" e "Arquitetura"), *Backend*, *Frontend* e
*MiggoAI*. Os caminhos nas `pages` são sem extensão (`backend/testes`).

- Acrescentar uma entrada ao grupo certo: ok, é o fluxo normal.
- Mudar tema, cores, nome do site, domínio ou reordenar abas: **só por pedido
  explícito.** Um erro ali derruba a navegação de todo o site.

**Pendência conhecida (verificada em 08/10/2026):** a navegação lista 58 páginas,
mas **três não têm arquivo** — `arquitetura/glossario`, `miggoai/frontend` e
`miggoai/deploy`. São links quebrados no site. Ou crie a página, ou remova a
entrada; não deixe como está. Nenhum `.mdx` do repo está fora da navegação, então
o inverso (página órfã) não é um problema hoje — mantenha assim.

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
`EOFError`), então roda com sqlite em memória via um settings do workspace:

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
