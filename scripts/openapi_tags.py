"""Pós-processa um spec OpenAPI gerado pelo drf-spectacular para o portal.

O drf-spectacular marca com uma tag genérica (`api`, `webhooks`) ou com o
primeiro segmento do caminho (`generations`, `prompts`) toda view que não
declara `@extend_schema(tags=[...])`. No Mintlify, cada tag vira um grupo da
navegação, então tag genérica joga dezenas de endpoints num grupo sem sentido.

Este script:
1. troca a tag genérica (ou ausente) por uma tag derivada do prefixo do caminho;
2. traduz para pt-BR as tags que o código declara em inglês;
3. grava a lista `tags` no topo do spec, em ordem alfabética;
4. fixa `info` e `servers` do perfil (o que o settings do repo não define).

Uso (da raiz do repo de doc):

    python scripts/openapi_tags.py api-reference/backend-miggo/openapi.json --perfil plataforma
    python scripts/openapi_tags.py api-reference/miggoai/openapi.json --perfil miggoai

É idempotente: rodar duas vezes dá o mesmo arquivo.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}

# Tags que não dizem nada sobre o recurso.
TAGS_GENERICAS = {"api", "webhooks"}

# (regex do caminho, tag). A primeira que casar vence: do mais específico ao mais geral.
REGRAS_POR_CAMINHO: list[tuple[str, str]] = [
    # backend-miggo
    (r"^/webhooks/", "Webhooks"),
    (r"^/api/v1/post/webhook-", "Webhooks"),
    (r"^/api/v1/account/password-reset/", "Autenticação"),
    (r"^/api/v1/account/", "Contas"),
    (r"^/api/v1/agency/", "Agência"),
    (r"^/api/v1/agenda/", "Agenda"),
    (r"^/api/v1/benefits/", "Benefícios"),
    (r"^/api/v1/brandkit/", "Brandkit"),
    (r"^/api/v1/client/", "Clientes"),
    (r"^/api/v1/conversation/", "Conversas"),
    (r"^/api/v1/editorial-calendar/", "Calendário editorial"),
    (r"^/api/v1/email-marketing/", "E-mail marketing"),
    (r"^/api/v1/history/", "Histórico"),
    (r"^/api/v1/integration/", "Integrações"),
    (r"^/api/v1/media/", "Mídia"),
    (r"^/api/v1/notification/", "Notificações"),
    (r"^/api/v1/onboarding/", "Onboarding"),
    (r"^/api/v1/post/insights/", "Posts - Insights"),
    (r"^/api/v1/post/(media-view/|\{[^}]+\}/media-link/)", "Mídia - Posts"),
    (r"^/api/v1/post/", "Posts"),
    (r"^/api/v1/subscription/", "Assinaturas"),
    # miggoai
    (r"^/api/token/", "Autenticação"),
    (r"^/api/generations/", "Gerações"),
    (r"^/api/prompts/", "Prompts"),
    (r"^/api/custos/", "Custos"),
    (r"^/api/clients/", "Clientes"),
    (r"^/api/posts/", "Posts"),
]

# Tags que o código declara em inglês, com o nome usado no portal.
TRADUCOES = {
    "Account": "Contas",
    "Account Meta": "Contas - Metadados",
    "Authentication": "Autenticação",
    "Support": "Contas - Suporte",
    "Benefits": "Benefícios",
    "Benefits - Admin": "Benefícios - Admin",
    "Brandkit - Assets": "Brandkit - Arquivos",
    "Brandkit - Colors": "Brandkit - Cores",
    "Brandkit - Typography": "Brandkit - Tipografia",
    "Brandkit - Copy Reference": "Brandkit - Referência de texto",
    "Brandkit - Design Reference": "Brandkit - Referência visual",
    "Brandkit - Reference Import": "Brandkit - Importação de referências",
    "Client": "Clientes",
    "Client Meta": "Clientes - Metadados",
    "Client - Materiais da marca": "Clientes - Materiais da marca",
    "Trials": "Clientes - Trials",
    "Conversations": "Conversas",
    "Editorial Calendar": "Calendário editorial",
    "Editorial Calendar Catalog": "Calendário editorial - Catálogo",
    "Email Marketing": "E-mail marketing",
    "History": "Histórico",
    "Integration": "Integrações",
    "Platform Integration": "Integrações - Plataformas",
    "WhatsApp Integration": "Integrações - WhatsApp",
    "Social Network": "Integrações - Redes sociais",
    "Platform Profile Config": "Integrações - Perfis de plataforma",
    "Media": "Mídia",
    "Media Post": "Mídia - Posts",
    "Notifications": "Notificações",
    "Plan": "Planos",
    "Plan Feature": "Planos - Recursos",
    "Plan Meta": "Planos - Metadados",
    "Plan Price": "Planos - Preços",
    "Post": "Posts",
    "Post Format": "Posts - Formatos",
    "Post Insights": "Posts - Insights",
    "Post Status": "Posts - Status",
    "Subscription": "Assinaturas",
    "Invoice": "Assinaturas - Faturas",
    "Webhooks": "Webhooks",
}

PERFIS = {
    "plataforma": {
        "info": {
            "title": "Plataforma Miggo (backend-miggo)",
            "description": (
                "API REST da plataforma Miggo. Autenticação por JWT (Bearer) "
                "emitido em /api/v1/account/token/."
            ),
        },
        "servers": [
            {"url": "https://api.miggomkt.com.br", "description": "Produção"},
            {"url": "https://test-api.miggomkt.com.br", "description": "Homologação"},
        ],
    },
    "miggoai": {
        "info": {
            "title": "MiggoAI (backend)",
            "description": (
                "API do serviço de IA da Miggo. Aceita o JWT da plataforma (RS256) "
                "para a gestão Miggo e Api-Key para chamadas entre serviços."
            ),
        },
        "servers": [{"url": "https://backend-ai.miggomkt.com.br", "description": "Produção"}],
    },
}


def tag_por_caminho(caminho: str) -> str | None:
    for padrao, tag in REGRAS_POR_CAMINHO:
        if re.search(padrao, caminho):
            return tag
    return None


def eh_generica(tag: str, caminho: str) -> bool:
    """Genérica = nome vazio de sentido ou o segmento do caminho em minúsculas."""
    if tag.lower() in TAGS_GENERICAS:
        return True
    segmentos = [s for s in caminho.split("/") if s]
    return tag == tag.lower() and tag in segmentos


def retaguear(spec: dict) -> list[str]:
    """Ajusta as tags de cada operação e devolve os caminhos sem regra."""
    sem_regra: list[str] = []
    for caminho, operacoes in spec.get("paths", {}).items():
        for metodo, operacao in operacoes.items():
            if metodo not in HTTP_METHODS or not isinstance(operacao, dict):
                continue
            tags = operacao.get("tags") or []
            novas: list[str] = []
            for tag in tags or [""]:
                if not tag or eh_generica(tag, caminho):
                    tag = tag_por_caminho(caminho) or ""
                    if not tag:
                        sem_regra.append(f"{metodo.upper()} {caminho}")
                        continue
                tag = TRADUCOES.get(tag, tag)
                if tag not in novas:
                    novas.append(tag)
            if novas:
                operacao["tags"] = novas
    return sem_regra


def listar_tags(spec: dict) -> list[dict]:
    usadas = {
        tag
        for operacoes in spec.get("paths", {}).values()
        for metodo, operacao in operacoes.items()
        if metodo in HTTP_METHODS and isinstance(operacao, dict)
        for tag in operacao.get("tags", [])
    }
    return [{"name": tag} for tag in sorted(usadas, key=str.casefold)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec", type=Path, help="caminho do openapi.json gerado")
    parser.add_argument("--perfil", choices=sorted(PERFIS), required=True)
    parser.add_argument("--versao", help="versão exibida em info.version (ex.: 2.3.0)")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    perfil = PERFIS[args.perfil]

    spec.setdefault("info", {}).update(perfil["info"])
    if args.versao:
        spec["info"]["version"] = args.versao
    spec["servers"] = perfil["servers"]

    sem_regra = retaguear(spec)
    spec["tags"] = listar_tags(spec)

    args.spec.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{args.spec}: {len(spec['paths'])} caminhos, {len(spec['tags'])} tags")
    if sem_regra:
        print("Sem regra de tag (acrescente em REGRAS_POR_CAMINHO):")
        for item in sem_regra:
            print(f"  {item}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
