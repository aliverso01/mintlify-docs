"""Pós-processa um spec OpenAPI gerado pelo drf-spectacular para o portal.

O drf-spectacular marca com uma tag genérica (`api`, `webhooks`) ou com o
primeiro segmento do caminho (`generations`, `prompts`) toda view que não
declara `@extend_schema(tags=[...])`, não gera `summary` e copia a docstring
da view (com número de card, caminho repetido e docstring de classe base) para
a `description`. No Mintlify, cada tag vira um grupo da navegação e o `summary`
vira o título da página do endpoint.

Este script:
1. troca a tag genérica (ou ausente) por uma tag derivada do prefixo do caminho,
   traduz para pt-BR as tags que o código declara em inglês e reagrupa as tags
   grandes demais ou com uma operação só;
2. gera um `summary` em pt-BR para cada operação (método + recurso do caminho);
3. limpa a `description`: tira número de card (`MIG-nnn`), a linha que só repete
   verbo e caminho, citação de arquivo `.py` e docstring genérica de classe base;
4. declara os esquemas de segurança (JWT Bearer e Api-Key) e os aplica;
5. grava a lista `tags` (com descrição) no topo do spec, em ordem alfabética;
6. fixa `info` e `servers` do perfil (o que o settings do repo não define).

Uso (da raiz do repo de doc):

    python scripts/openapi_tags.py api-reference/backend-miggo/openapi.json --perfil plataforma
    python scripts/openapi_tags.py api-reference/miggoai/openapi.json --perfil miggoai

É idempotente: rodar duas vezes dá o mesmo arquivo. Grava sempre em UTF-8 com
fim de linha LF. Se sobrar caminho sem regra de tag, operação sem `summary` ou
tag sem descrição, sai com código 1 e não grava nada.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}

# Tags que não dizem nada sobre o recurso.
TAGS_GENERICAS = {"api", "webhooks"}

# (regex do caminho, tag) para operação com tag genérica ou sem tag.
# A primeira que casar vence: do mais específico ao mais geral.
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
    (r"^/api/v1/integration/", "Log de integrações"),
    (r"^/api/v1/media/", "Mídia"),
    (r"^/api/v1/notification/", "Notificações"),
    (r"^/api/v1/onboarding/", "Onboarding"),
    (r"^/api/v1/post/insights/", "Posts - Insights"),
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
    "Integration": "Log de integrações",
    "Integrações": "Log de integrações",
    "Platform Integration": "Integrações - Plataformas",
    "WhatsApp Integration": "Integrações - Plataformas",
    "Social Network": "Integrações - Plataformas",
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

# (regex do caminho, tag) que vale por cima da tag do código: divide as tags
# grandes demais e junta as de uma operação só no grupo do assunto.
REAGRUPAMENTO: list[tuple[str, str]] = [
    # backend-miggo
    (r"^/webhooks/", "Webhooks"),
    (r"^/api/v1/post/webhook-", "Webhooks"),
    (r"^/api/v1/account/support/jira-webhook/", "Webhooks"),
    (r"^/api/v1/onboarding/(signup|verify|validate-profile|plan|referral|resume|state|summary|complete)/", "Onboarding - Cadastro"),
    (r"^/api/v1/onboarding/(brand-source|logo|identity|photos|media|analysis-status|review)/", "Onboarding - Marca"),
    (r"^/api/v1/onboarding/(strategy|calendar)/", "Onboarding - Estratégia e calendário"),
    (r"^/api/v1/onboarding/(grid|first-content)/", "Onboarding - Grid e primeiro conteúdo"),
    (r"^/api/v1/agency/(me|context|plans|subscription)/", "Agência - Painel da agência"),
    (r"^/api/v1/agency/", "Agência - Gestão Miggo"),
    (r"^/api/v1/client/trials/", "Clientes - Trials"),
    (r"^/api/v1/client/(allowed-social-networks|media-preference|signature-preference|miggoai-workflow|miggoai-generate-now|onboarding-skip|onboarding-status|onboarding-step)/", "Clientes - Preferências e onboarding"),
    (r"^/api/v1/email-marketing/campaign/", "E-mail marketing - Campanhas"),
    (r"^/api/v1/email-marketing/segment/", "E-mail marketing - Segmentos"),
    (r"^/api/v1/subscription/(anomalies|billing-identities|deduplicate-subscriptions|duplicate-subscriptions|financial-stats|gateway-search|orphan-charges|resolve-unmatched|sync-stripe|sync-subscription-status-invoices|unlinked-active-subscriptions)/", "Assinaturas - Conciliação"),
    (r"^/api/v1/subscription/\{[^}]+\}/gateway-link/", "Assinaturas - Conciliação"),
    (r"^/api/v1/brandkit/ingestion-job/", "Brandkit - Importação de referências"),
    (r"^/api/v1/post/(media-view/|\{[^}]+\}/media-link/)", "Mídia - Link público"),
    (r"^/api/v1/post/(platform-integration|social-network)/", "Integrações - Plataformas"),
    # miggoai
    (r"^/api/generations/(gerar-agora|gerar-card|production|test)/", "Gerações - Disparo"),
    (r"^/api/generations/(grid|perfil)/", "Gerações - Grid e perfil"),
    (r"^/api/prompts/workflows/", "Prompts - Workflows"),
]

# Uma frase por tag (vira a descrição do grupo).
DESCRICOES_TAGS = {
    # backend-miggo
    "Acervo Miggo": "Banco de fotos interno da Miggo (`StockPhoto`), usado quando o cliente não tem foto própria.",
    "Agência - Gestão Miggo": "Cadastro de agências pela equipe Miggo: dados, marca, domínios, usuários e clientes vinculados.",
    "Agência - Painel da agência": "O que a própria agência vê e edita: contexto, marca, membros, clientes e assinatura.",
    "Agenda": "Eventos da agenda do cliente e limites de uso.",
    "Assinaturas": "Assinatura do cliente: criação, checkout, troca de plano, cancelamento e consulta.",
    "Assinaturas - Conciliação": "Ferramentas da gestão para conciliar assinaturas e cobranças com o gateway.",
    "Assinaturas - Faturas": "Faturas das assinaturas.",
    "Autenticação": "Emissão e renovação de token, login, logout, Google e redefinição de senha.",
    "Benefícios": "Benefícios do clube oferecidos aos clientes e envio de novos benefícios.",
    "Benefícios - Admin": "Cadastro e moderação de benefícios pela equipe Miggo.",
    "Brandkit": "Brandkit do cliente: identidade visual e referências usadas na geração.",
    "Brandkit - Arquivos": "Arquivos da marca guardados no brandkit.",
    "Brandkit - Cores": "Paleta de cores do brandkit.",
    "Brandkit - Grid": "Grid de posts do brandkit: geração, aprovação e status.",
    "Brandkit - Importação de referências": "Importação de referências a partir de link ou arquivo e acompanhamento do job.",
    "Brandkit - Logo": "Logos do brandkit e reanálise por IA.",
    "Brandkit - Referência de texto": "Textos de referência do cliente, com busca e transmutação.",
    "Brandkit - Referência visual": "Imagens de referência visual e reanálise por IA.",
    "Brandkit - Tipografia": "Fontes do brandkit.",
    "Calendário editorial": "Calendário editorial do cliente.",
    "Calendário editorial - Catálogo": "Catálogos usados para montar o calendário: estilos, CTAs e regras por formato.",
    "Clientes": "Cadastro, ativação e consulta de clientes.",
    "Clientes - Materiais da marca": "Materiais da marca enviados pelo cliente.",
    "Clientes - Metadados": "Metadados chave-valor do cliente (`ClientMeta`).",
    "Clientes - Preferências e onboarding": "Preferências do cliente (redes, mídia, assinatura, workflow do MiggoAI) e controle do onboarding.",
    "Clientes - Trials": "Painel de trials e funil de vendas.",
    "Contas": "Usuários, equipe e módulos de acesso.",
    "Contas - Metadados": "Metadados chave-valor do usuário (`UserMeta`).",
    "Contas - Suporte": "Chat de suporte e tickets integrados ao Jira.",
    "Conversas": "Conversas do WhatsApp via ManyChat, automações e flows.",
    "E-mail marketing": "Configurações, arquivos e histórico de envios do e-mail marketing.",
    "E-mail marketing - Campanhas": "Campanhas de e-mail: criação, público, prévia e envio de teste.",
    "E-mail marketing - Segmentos": "Segmentos de clientes usados como público das campanhas.",
    "Histórico": "Histórico de ações e relatórios do painel de gestão.",
    "Integrações - Perfis de plataforma": "Configuração de perfil por rede social (`PlatformProfileConfig`) e correção por IA.",
    "Integrações - Plataformas": "Contas de redes sociais e WhatsApp conectadas ao cliente (`PlatformIntegration`).",
    "Log de integrações": "Registro das chamadas a serviços externos (app `integration`).",
    "Mídia": "Galeria de mídia do cliente: upload, análise por IA e limites.",
    "Mídia - Link público": "Visualização e download de mídia por link público, sem login.",
    "Mídia - Posts": "Vínculo entre mídia e post.",
    "Notificações": "Notificações do usuário.",
    "Onboarding - Cadastro": "Cadastro, verificação de WhatsApp, plano e estado do onboarding.",
    "Onboarding - Estratégia e calendário": "Geração e aprovação da estratégia e do calendário no onboarding.",
    "Onboarding - Grid e primeiro conteúdo": "Grid de estilos e primeiro conteúdo do onboarding.",
    "Onboarding - Marca": "Coleta da marca no onboarding: fonte, logo, fotos, análise e revisão.",
    "Planos": "Planos de assinatura.",
    "Planos - Metadados": "Metadados chave-valor dos planos.",
    "Planos - Preços": "Preços dos planos por gateway e intervalo.",
    "Planos - Recursos": "Recursos incluídos em cada plano.",
    "Posts": "Posts do cliente: criação, aprovação, publicação e regeneração pelo MiggoAI.",
    "Posts - Formatos": "Formatos de post.",
    "Posts - Insights": "Métricas das redes sociais.",
    "Posts - Status": "Status de post.",
    "Webhooks": "Rotas chamadas por serviços externos (Stripe, Asaas, Zernio, ManyChat e Jira).",
    # miggoai
    "Custos": "Custo das chamadas pagas à OpenAI: painel, log, preços e cotações.",
    "Gerações": "Gerações registradas: lista, detalhe, resumo e regeneração.",
    "Gerações - Disparo": "Disparo de geração de conteúdo para um cliente.",
    "Gerações - Grid e perfil": "Grid do onboarding e peças de perfil (bio, banner, destaques).",
    "Prompts": "Prompts editáveis, versões e variáveis.",
    "Prompts - Workflows": "Workflows de geração e sua configuração.",
}

DESCRICOES_TAGS_POR_PERFIL = {
    "miggoai": {
        "Autenticação": "Emissão e renovação do token local do MiggoAI.",
        "Clientes": "Clientes lidos da Plataforma, com predefinições e variáveis salvas.",
        "Posts": "Posts lidos da Plataforma, com formatos e status.",
    },
}

# Segmento de caminho -> (singular, plural). Plural None = recurso único.
NOMES: dict[str, tuple[str, str | None]] = {
    # backend-miggo
    "account": ("usuário", "usuários"),
    "acervo": ("foto do acervo", "fotos do acervo"),
    "admin": ("benefício", "benefícios"),
    "admin-dashboard": ("painel de gestão", None),
    "agency": ("agência", "agências"),
    "agenda": ("evento da agenda", "eventos da agenda"),
    "allowed-social-networks": ("redes sociais permitidas", None),
    "analysis-status": ("progresso da análise", None),
    "anomalies": ("anomalias de cobrança", None),
    "approval": ("aprovação do grid", None),
    "asset": ("arquivo", "arquivos"),
    "audience": ("público da campanha", None),
    "autofill": ("preenchimento automático da revisão", None),
    "automations": ("automação", "automações"),
    "benefits": ("benefício", "benefícios"),
    "billing-identities": ("identidade de cobrança", "identidades de cobrança"),
    "board": ("quadro de preços", None),
    "brand": ("marca", None),
    "brand-materials": ("material da marca", "materiais da marca"),
    "brandkit": ("brandkit", "brandkits"),
    "calendar": ("calendário", None),
    "campaign": ("campanha", "campanhas"),
    "candidates": ("logos candidatos", None),
    "channels": ("canais do funil de vendas", None),
    "charts": ("gráficos do painel de gestão", None),
    "client": ("cliente", "clientes"),
    "client-meta": ("metadado do cliente", "metadados do cliente"),
    "color": ("cor", "cores"),
    "content-styles": ("estilos de conteúdo", None),
    "context": ("contexto", None),
    "conversation": ("conversa", "conversas"),
    "copy-reference": ("referência de texto", "referências de texto"),
    "correction": ("correção do perfil", None),
    "coverage": ("cobertura da galeria", None),
    "cta-categories": ("categorias de CTA", None),
    "daily-metrics": ("métricas diárias", None),
    "design-reference": ("referência visual", "referências visuais"),
    "dispatch": ("envios de e-mail", None),
    "domains": ("domínio", "domínios"),
    "duplicate-subscriptions": ("assinaturas duplicadas", None),
    "editorial-calendar": ("calendário editorial", "calendários editoriais"),
    "elegiveis": ("fotos elegíveis do acervo", None),
    "financial-stats": ("indicadores financeiros", None),
    "first-content": ("primeiro conteúdo", None),
    "flows": ("flow", "flows"),
    "follower-stats": ("estatísticas de seguidores", None),
    "fontes": ("fontes externas do acervo", None),
    "format": ("formato de post", "formatos de post"),
    "format-intervals": ("intervalos por formato", None),
    "format-style-rules": ("regras de estilo por formato", None),
    "gateway-link": ("vínculo com o gateway", None),
    "grid": ("grid", "grids"),
    "history": ("registro de histórico", "registros de histórico"),
    "insights": ("insight", "insights"),
    "integration": ("registro de integração", "registros de integração"),
    "invoice": ("fatura", "faturas"),
    "limits": ("limites", None),
    "logo": ("logo", "logos"),
    "media": ("mídia", "mídias"),
    "media-post": ("vínculo de mídia com post", "vínculos de mídia com post"),
    "media-preference": ("preferência de mídia", None),
    "members": ("membro", "membros"),
    "messages": ("mensagens", None),
    "metadata": ("metadado de post", "metadados de post"),
    "miggoai-workflow": ("workflow do MiggoAI do cliente", None),
    "modules": ("módulos", None),
    "nichos": ("nichos do acervo", None),
    "notification": ("notificação", "notificações"),
    "onboarding-status": ("status do onboarding", None),
    "onboarding-step": ("etapa do onboarding", None),
    "options": ("opções", None),
    "orphan-charges": ("cobrança órfã", "cobranças órfãs"),
    "photos": ("fotos", None),
    "plan": ("plano", "planos"),
    "plan-feature": ("recurso do plano", "recursos do plano"),
    "plan-meta": ("metadado do plano", "metadados do plano"),
    "plan-price": ("preço do plano", "preços dos planos"),
    "plans": ("planos", None),
    "platform-integration": ("integração de plataforma", "integrações de plataforma"),
    "platform-profile-config": ("configuração de perfil", "configurações de perfil"),
    "post": ("post", "posts"),
    "posts": ("post", "posts"),
    "publication": ("publicação", "publicações"),
    "reference-import": ("importação de referências", "importações de referências"),
    "report": ("relatório", None),
    "review": ("revisão", None),
    "sales-funnel": ("funil de vendas", None),
    "segment": ("segmento", "segmentos"),
    "settings": ("configurações", None),
    "signature-preference": ("preferência de assinatura", None),
    "social-network": ("rede social", "redes sociais"),
    "state": ("estado do onboarding", None),
    "status": ("status", None),
    "strategy": ("estratégia", None),
    "styles": ("estilos do grid", None),
    "subscription": ("assinatura", "assinaturas"),
    "summary": ("resumo do onboarding", None),
    "team": ("membro da equipe", "membros da equipe"),
    "tickets": ("ticket", "tickets"),
    "timeline": ("linha do tempo", None),
    "trials": ("trial", "trials"),
    "typography": ("tipografia", "tipografias"),
    "unlinked-active-subscriptions": ("assinaturas ativas sem vínculo", None),
    "user-meta": ("metadado do usuário", "metadados do usuário"),
    "users": ("usuário", "usuários"),
    "variables": ("variáveis", None),
    # miggoai
    "chamadas": ("chamada paga", "chamadas pagas"),
    "clients": ("cliente", "clientes"),
    "cotacoes": ("cotação", "cotações"),
    "dashboard": ("painel de custos", None),
    "execucoes": ("execução", "execuções"),
    "formats": ("formato", "formatos"),
    "generations": ("geração", "gerações"),
    "linhas": ("linha de geração", "linhas de geração"),
    "precos": ("preço", "preços"),
    "presets": ("predefinições", None),
    "prompts": ("prompt", "prompts"),
    "resumo": ("resumo das gerações", None),
    "statuses": ("status", "status"),
    "versions": ("versão", "versões"),
    "workflows": ("workflow", "workflows"),
}

# Último segmento que nomeia a operação, não o recurso: o recurso é o anterior.
SEGMENTOS_DE_CRUD = {
    "list": "listar",
    "create": "criar",
    "update": "atualizar",
    "edit": "obter",
    "delete": "remover",
    "destroy": "remover",
    "retrieve": "obter",
    "detail": "obter",
}

# Último segmento que é ação. `{o}` = singular do recurso anterior no caminho.
ACOES: dict[str, str] = {
    "activate": "Ativar {o}",
    "analyze": "Analisar {o} com IA",
    "approve": "Aprovar {o}",
    "busca": "Buscar fotos numa fonte externa",
    "check-status": "Verificar status da {o}",
    "complete": "Concluir {o}",
    "continue": "Avançar etapa ({o})",
    "deactivate": "Desativar {o}",
    "deduplicate": "Deduplicar {o}",
    "detect-variables": "Detectar variáveis do {o}",
    "download": "Baixar mídia por link público",
    "feedback": "Enviar feedback sobre {o}",
    "import-website": "Importar arquivos de um site",
    "importar": "Importar fotos de uma fonte externa",
    "info": "Consultar dados da mídia por link público",
    "moderate": "Moderar {o}",
    "preview": "Pré-visualizar {o}",
    "read": "Marcar {o} como lida",
    "reanalyze": "Reanalisar {o}",
    "regenerate": "Regenerar {o}",
    "reply": "Responder {o}",
    "resolve": "Resolver {o}",
    "retry": "Tentar de novo a {o}",
    "search": "Buscar {o}",
    "send": "Enviar mensagem na {o}",
    "sync": "Sincronizar {o}",
    "sync-gateway": "Sincronizar {o} com o gateway",
    "upload": "Enviar {o}",
    "usable": "Marcar {o} como utilizável",
    "verify": "Verificar {o}",
}

# Operações que a regra genérica não nomeia bem: "MÉTODO caminho" -> summary.
RESUMOS_FIXOS = {
    # backend-miggo
    "POST /api/v1/account/create/": "Criar usuário (gestão)",
    "POST /api/v1/account/register/": "Cadastrar usuário",
    "POST /api/v1/account/google/": "Entrar com Google",
    "POST /api/v1/account/login/": "Entrar (sessão com cookie)",
    "POST /api/v1/account/logout/": "Sair",
    "POST /api/v1/account/token/": "Obter token JWT",
    "POST /api/v1/account/token/refresh/": "Renovar token JWT",
    "GET /api/v1/account/modules/": "Listar módulos de acesso",
    "PUT /api/v1/account/team/{id}/modules/": "Definir módulos do membro da equipe",
    "POST /api/v1/account/password-reset/request/": "Pedir redefinição de senha",
    "POST /api/v1/account/password-reset/confirm/": "Confirmar redefinição de senha",
    "POST /api/v1/account/verify-email/send/": "Enviar e-mail de verificação",
    "POST /api/v1/account/verify-email/confirm/": "Confirmar e-mail",
    "POST /api/v1/account/support/chat/": "Conversar com o suporte",
    "POST /api/v1/account/support/ticket/": "Abrir ticket de suporte",
    "PATCH /api/v1/account/support/tickets/": "Atualizar tickets em lote",
    "GET /api/v1/account/support/tickets/{id}/jira-status/": "Consultar status do ticket no Jira",
    "POST /api/v1/account/support/tickets/{id}/jira-sync/": "Sincronizar ticket com o Jira",
    "POST /api/v1/account/support/jira-webhook/": "Receber atualização de ticket do Jira",
    "GET /api/v1/agency/context/": "Consultar contexto de agência do usuário",
    "GET /api/v1/agency/me/": "Consultar a própria agência",
    "GET /api/v1/agency/me/brand/": "Consultar marca da própria agência",
    "PATCH /api/v1/agency/me/brand/": "Atualizar marca da própria agência",
    "POST /api/v1/agency/me/clients/": "Criar cliente da agência",
    "GET /api/v1/agency/me/members/": "Listar membros da agência",
    "POST /api/v1/agency/me/members/": "Criar membro da agência",
    "PATCH /api/v1/agency/me/members/{id}/": "Atualizar membro da agência",
    "DELETE /api/v1/agency/me/members/{id}/": "Desativar membro da agência",
    "PUT /api/v1/agency/me/members/{id}/modules/": "Definir módulos do membro da agência",
    "PUT /api/v1/agency/{id}/users/{uid}/modules/": "Definir módulos do usuário da agência",
    "GET /api/v1/agency/plans/": "Listar planos para agência",
    "GET /api/v1/agency/subscription/": "Consultar assinatura da agência",
    "POST /api/v1/agency/subscription/checkout/": "Abrir checkout da assinatura da agência",
    "POST /api/v1/agency/subscription/portal/": "Abrir portal de cobrança da agência",
    "POST /api/v1/agency/{id}/clients/link/": "Vincular clientes à agência",
    "GET /api/v1/agency/{id}/brand/": "Consultar marca da agência",
    "PATCH /api/v1/agency/{id}/brand/": "Atualizar marca da agência",
    "POST /api/v1/agency/{id}/domains/{did}/verify/": "Verificar domínio da agência",
    "GET /api/v1/benefits/": "Listar benefícios publicados",
    "GET /api/v1/benefits/admin/": "Listar todos os benefícios",
    "POST /api/v1/benefits/admin/": "Criar benefício",
    "GET /api/v1/benefits/mine/": "Listar meus benefícios enviados",
    "GET /api/v1/benefits/options/": "Listar opções do formulário de benefício",
    "POST /api/v1/benefits/submit/": "Enviar benefício para análise",
    "GET /api/v1/brandkit/asset/client/{client_id}/": "Listar arquivos da marca do cliente",
    "GET /api/v1/brandkit/client/{client_id}/": "Obter brandkit do cliente",
    "POST /api/v1/brandkit/copy-reference/transmute/": "Transmutar referência de texto",
    "POST /api/v1/brandkit/design-reference/upload/": "Enviar referência visual",
    "GET /api/v1/brandkit/grid/approval/": "Consultar aprovação do grid",
    "POST /api/v1/brandkit/grid/approval/approve/": "Aprovar grid",
    "POST /api/v1/brandkit/grid/approval/feedback/": "Enviar feedback sobre o grid",
    "POST /api/v1/brandkit/grid/approval/retry/": "Tentar de novo a aprovação do grid",
    "POST /api/v1/brandkit/grid/send-approval/": "Enviar grid para aprovação",
    "GET /api/v1/brandkit/grid/status/": "Consultar status do grid",
    "GET /api/v1/brandkit/ingestion-job/{job_id}/": "Consultar job de ingestão",
    "POST /api/v1/brandkit/reference-import/{id}/copy-draft/": "Gerar rascunho de texto da importação",
    "POST /api/v1/brandkit/reference-import/{id}/visual/": "Gerar referência visual da importação",
    "POST /api/v1/client/activate-account/{id}/": "Ativar conta do cliente",
    "POST /api/v1/client/briefing/apply/": "Aplicar briefing ao cliente",
    "POST /api/v1/client/create-bio-agent/": "Criar cliente pelo agente de bio",
    "GET /api/v1/client/generate-activation-code/{id}/": "Gerar código de ativação",
    "POST /api/v1/client/instagram-scrape/": "Ler perfil do Instagram",
    "POST /api/v1/client/miggoai-generate-now/{id}/": "Pedir geração imediata ao MiggoAI",
    "DELETE /api/v1/client/miggoai-generate-now/{id}/": "Cancelar geração imediata no MiggoAI",
    "PUT /api/v1/client/miggoai-workflow/{id}/": "Definir workflow do MiggoAI do cliente",
    "POST /api/v1/client/onboarding-skip/{id}/": "Pular onboarding do cliente",
    "POST /api/v1/client/send-generic-password/": "Enviar senha provisória",
    "PATCH /api/v1/client/toggle-active/{id}/": "Ativar ou desativar cliente",
    "POST /api/v1/client/verify-code/{id}/": "Verificar código de ativação",
    "GET /api/v1/client/trials/": "Listar trials",
    "POST /api/v1/client/trials/{id}/grid-retry/": "Tentar de novo o grid do trial",
    "GET /api/v1/history/report/clients/": "Gerar relatório de clientes",
    "GET /api/v1/history/report/posts/": "Gerar relatório de posts",
    "DELETE /api/v1/media/{id}/": "Remover mídia (galeria)",
    "POST /api/v1/media/analyze-pending/": "Analisar mídias pendentes",
    "POST /api/v1/media/upload-chunk/": "Enviar mídia em partes",
    "POST /api/v1/media/acervo/uso/": "Registrar uso de foto do acervo",
    "PATCH /api/v1/notification/mark-all-read/": "Marcar todas as notificações como lidas",
    "GET /api/v1/notification/history/": "Listar histórico de notificações",
    "GET /api/v1/email-marketing/campaign/options/": "Listar opções de campanha",
    "POST /api/v1/email-marketing/campaign/render/": "Renderizar campanha",
    "POST /api/v1/email-marketing/campaign/send-test/": "Enviar teste da campanha",
    "POST /api/v1/email-marketing/segment/count/": "Contar clientes do segmento",
    "GET /api/v1/email-marketing/asset/": "Listar arquivos do e-mail marketing",
    "POST /api/v1/email-marketing/asset/": "Enviar arquivo do e-mail marketing",
    "POST /api/v1/onboarding/brand-source/": "Informar fonte da marca",
    "POST /api/v1/onboarding/brand-source/preview/": "Pré-visualizar fonte da marca",
    "POST /api/v1/onboarding/analysis-status/": "Reiniciar análise da marca",
    "POST /api/v1/onboarding/complete/": "Concluir onboarding",
    "POST /api/v1/onboarding/first-content/request-change/": "Pedir ajuste no primeiro conteúdo",
    "POST /api/v1/onboarding/identity/continue/": "Confirmar identidade visual",
    "POST /api/v1/onboarding/identity/select-logo/": "Escolher logo",
    "GET /api/v1/onboarding/identity/candidates/": "Listar logos candidatos",
    "POST /api/v1/onboarding/logo/": "Enviar logo",
    "GET /api/v1/onboarding/media/": "Listar fotos enviadas no onboarding",
    "POST /api/v1/onboarding/media/": "Enviar fotos no onboarding",
    "DELETE /api/v1/onboarding/media/": "Remover foto do onboarding",
    "POST /api/v1/onboarding/media/continue/": "Concluir etapa de fotos",
    "GET /api/v1/onboarding/photos/": "Listar fotos do perfil",
    "POST /api/v1/onboarding/photos/": "Enviar fotos do perfil",
    "DELETE /api/v1/onboarding/photos/": "Remover foto do perfil",
    "POST /api/v1/onboarding/plan/": "Escolher plano",
    "POST /api/v1/onboarding/referral/": "Informar como conheceu a Miggo",
    "POST /api/v1/onboarding/resume/": "Retomar onboarding",
    "GET /api/v1/onboarding/review/autofill/": "Consultar preenchimento automático da revisão",
    "POST /api/v1/onboarding/review/autofill/": "Gerar preenchimento automático da revisão",
    "PUT /api/v1/onboarding/review/autofill/": "Salvar preenchimento automático da revisão",
    "POST /api/v1/onboarding/signup/": "Criar conta (cadastro)",
    "POST /api/v1/onboarding/signup/complete-social/": "Concluir cadastro por login social",
    "POST /api/v1/onboarding/strategy/approve-item/": "Aprovar item da estratégia",
    "POST /api/v1/onboarding/strategy/generate/": "Gerar estratégia",
    "POST /api/v1/onboarding/strategy/item/regenerate/": "Regenerar item da estratégia",
    "POST /api/v1/onboarding/validate-profile/": "Validar perfil do Instagram",
    "POST /api/v1/onboarding/verify/": "Verificar código do WhatsApp",
    "PATCH /api/v1/onboarding/verify/change-number/": "Trocar número do WhatsApp",
    "POST /api/v1/onboarding/verify/resend/": "Reenviar código do WhatsApp",
    "GET /api/v1/onboarding/grid/styles/": "Listar estilos do grid",
    "POST /api/v1/onboarding/grid/styles/": "Escolher estilos do grid",
    "POST /api/v1/post/create-posts/": "Criar posts em lote",
    "POST /api/v1/post/insights/sync/": "Sincronizar insights",
    "POST /api/v1/post/miggoai/regenerate/": "Regenerar post no MiggoAI",
    "GET /api/v1/post/miggoai/regenerate/status/": "Consultar regeneração no MiggoAI",
    "GET /api/v1/post/platform-integration/retrieve/{client}/": "Obter integrações do cliente",
    "POST /api/v1/post/platform-integration/whatsapp/create/": "Conectar WhatsApp",
    "POST /api/v1/post/platform-integration/whatsapp/verify/": "Verificar WhatsApp",
    "POST /api/v1/post/platform-profile-config/{id}/correction/": "Pedir correção do perfil por IA",
    "GET /api/v1/post/platform-profile-config/{id}/correction/{job_id}/": "Consultar correção do perfil",
    "POST /api/v1/post/publish/": "Publicar post",
    "POST /api/v1/post/schedule-review/": "Agendar revisão de posts",
    "POST /api/v1/post/send-post-whatsapp/": "Enviar post pelo WhatsApp",
    "GET /api/v1/post/{post_id}/media-link/": "Gerar link público da mídia",
    "GET /api/v1/post/media-view/{token}/": "Ver mídia por link público",
    "POST /api/v1/post/webhook-account-connected/": "Receber conta conectada (legado)",
    "POST /api/v1/post/webhook-update-post/": "Receber atualização de post (legado)",
    "POST /api/v1/subscription/billing-portal/": "Abrir portal de cobrança",
    "POST /api/v1/subscription/cancel/": "Cancelar assinatura",
    "POST /api/v1/subscription/change-plan/": "Trocar plano",
    "POST /api/v1/subscription/create-checkout-session/": "Abrir checkout da Stripe",
    "POST /api/v1/subscription/create-subscription/": "Criar assinatura no gateway",
    "POST /api/v1/subscription/deduplicate-subscriptions/": "Deduplicar assinaturas",
    "GET /api/v1/subscription/gateway-search/": "Buscar no gateway",
    "POST /api/v1/subscription/orphan-charges/{id}/resolve/": "Resolver cobrança órfã",
    "POST /api/v1/subscription/resolve-unmatched/": "Resolver cobranças sem vínculo",
    "GET /api/v1/subscription/retrieve/{client}/": "Obter assinatura do cliente",
    "POST /api/v1/subscription/start-trial/": "Iniciar trial",
    "POST /api/v1/subscription/sync-stripe/": "Sincronizar com a Stripe",
    "POST /api/v1/subscription/sync-subscription-status-invoices/": "Sincronizar status e faturas",
    "POST /api/v1/subscription/sync-subscription-status-invoices/async/": "Sincronizar status e faturas em segundo plano",
    "GET /api/v1/subscription/sync-subscription-status-invoices/status/{job_id}/": "Consultar sincronização em segundo plano",
    "POST /api/v1/subscription/plan-price/bulk-destroy/": "Remover preços em lote",
    "POST /webhooks/": "Receber evento da Stripe",
    "POST /webhooks/asaas/": "Receber evento do Asaas",
    "POST /webhooks/asas/": "Receber evento do Asaas (rota alternativa)",
    "POST /webhooks/zernio/account/": "Receber conta conectada no Zernio",
    "POST /webhooks/zernio/status/": "Receber status de publicação do Zernio",
    "POST /webhooks/manychat/": "Receber evento do ManyChat",
    "POST /webhooks/manychat/dynamic-block/continue/": "Continuar bloco dinâmico do ManyChat",
    "POST /api/v1/conversation/{id}/automation/": "Disparar automação na conversa",
    "GET /api/v1/conversation/{id}/posts/": "Listar posts da conversa",
    "GET /api/v1/conversation/flows/variables/": "Listar variáveis de flow",
    "GET /api/v1/conversation/{id}/messages/": "Listar mensagens da conversa",
    "GET /api/v1/editorial-calendar/options/": "Listar opções do calendário editorial",
    "GET /api/v1/agenda/limits/": "Consultar limites da agenda",
    "GET /api/v1/media/limits/": "Consultar limites de upload",
    "GET /api/v1/onboarding/grid/": "Consultar grid do onboarding",
    "POST /api/v1/onboarding/grid/feedback/": "Enviar feedback sobre o grid",
    "POST /api/v1/onboarding/strategy/feedback/": "Enviar feedback sobre a estratégia",
    # miggoai
    "POST /api/token/": "Obter token local",
    "POST /api/token/refresh/": "Renovar token local",
    "GET /api/generations/context/": "Pré-visualizar contexto da geração",
    "POST /api/generations/gerar-agora/": "Gerar o próximo card agora",
    "POST /api/generations/gerar-card/": "Gerar um card",
    "POST /api/generations/grid/": "Gerar grid do onboarding",
    "GET /api/generations/grid/by-key/{idempotency_key}/": "Consultar grid pela chave",
    "POST /api/generations/perfil/banner/": "Gerar banner do LinkedIn",
    "POST /api/generations/perfil/bio/": "Gerar bio do perfil",
    "POST /api/generations/perfil/destaques/": "Gerar capas de destaques",
    "GET /api/generations/perfil/by-key/{idempotency_key}/": "Consultar peça de perfil pela chave",
    "POST /api/generations/production/": "Gerar peça (produção)",
    "POST /api/generations/production/complete/": "Gerar post completo (produção)",
    "POST /api/generations/test/": "Gerar peça (teste)",
    "POST /api/generations/test/complete/": "Gerar post completo (teste)",
    "POST /api/generations/regenerate/": "Regenerar peça de um post",
    "GET /api/generations/regenerate/status/": "Consultar regeneração",
    "POST /api/prompts/{id}/versions/{version}/restore/": "Restaurar versão do prompt",
    "GET /api/prompts/{id}/variables/": "Listar variáveis do prompt",
    "POST /api/prompts/{id}/variables/": "Criar variável do prompt",
    "PUT /api/prompts/variables/{id}/": "Atualizar variável de prompt",
    "DELETE /api/prompts/variables/{id}/": "Remover variável de prompt",
    "PUT /api/clients/{client_id}/variables/": "Salvar variáveis do cliente",
    "DELETE /api/clients/{client_id}/variables/{key}/": "Remover variável salva do cliente",
    "GET /api/clients/{client_id}/variables/": "Listar variáveis salvas do cliente",
}

# Docstring de classe base: o drf-spectacular a copia para toda view filha.
DESCRICOES_DE_BASE = (
    "View genérica que só enxerga e só grava recurso de cliente visível.",
    "Recurso que pertence a um brandkit: o dono é o cliente do brandkit",
    "Escopo de leitura/edição/exclusão de uma view de meta.",
    "Além do post, a mídia vinculada também tem de ser de cliente visível",
    "Base para os endpoints de teste/produção",
    "Base pros endpoints de geração COMPLETA",
)

VERBOS = "GET|POST|PUT|PATCH|DELETE"
RE_LINHA_DE_ROTA = re.compile(rf"^\s*(?:{VERBOS})(?:\s*[/,]\s*(?:{VERBOS}))*\s+/\S*\s*(?P<resto>.*)$")
RE_CARD_EM_PARENTESES = re.compile(r"\s*\((?:[^()]*?,\s*)?MIG-\d+[^()]*\)")
RE_CARD_NO_INICIO = re.compile(r"^(?:MIG-\d+(?:\s*\([^)]*\))?\s*[—–:.-]\s*)+")
RE_CARD_SOLTO = re.compile(r"\s*[—–]\s*MIG-\d+(?:\s*\([^)]*\))?\.?")
RE_CARD_ARTIGO = re.compile(r"\b[oa] MIG-\d+")
RE_CARD = re.compile(r",?\s*MIG-\d+")
RE_CITA_PY = re.compile(r"\s*(?:[—–-]\s*)?(?:ver\s+)?\(?`[^`]*\.py`\)?(?:\s+para [^.\n]*)?")

SEGURANCA = {
    "jwtAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Access token JWT (RS256) emitido em `POST /api/v1/account/token/`. Header `Authorization: Bearer <token>`.",
    },
    "apiKeyAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": (
            "Chave de serviço para chamadas entre a Plataforma e o MiggoAI, gerada no admin do Django. "
            "Header `Authorization: Api-Key <chave>`. Na Plataforma, algumas rotas recusam a chave "
            "(ex.: acervo e rotas só da gestão): a permissão da view decide."
        ),
    },
}

PERFIS = {
    "plataforma": {
        "info": {
            "title": "Plataforma Miggo (backend-miggo)",
            "description": (
                "API REST da Plataforma Miggo. Autenticação por JWT (Bearer) "
                "emitido em /api/v1/account/token/; chamadas entre serviços usam Api-Key."
            ),
        },
        "servers": [
            {"url": "https://api.miggomkt.com.br", "description": "Produção"},
            {"url": "https://test-api.miggomkt.com.br", "description": "Homologação"},
        ],
        "descricao_jwt": SEGURANCA["jwtAuth"]["description"],
    },
    "miggoai": {
        "info": {
            "title": "MiggoAI (backend)",
            "description": (
                "API do serviço de IA da Miggo. Aceita o JWT da Plataforma (RS256) "
                "para a gestão Miggo e Api-Key para chamadas entre serviços."
            ),
        },
        "servers": [
            {"url": "https://backend-ai.miggomkt.com.br", "description": "Produção"},
            {"url": "https://backend-test-ai.miggomkt.com.br", "description": "Homologação"},
        ],
        "descricao_jwt": (
            "Access token JWT (RS256) da Plataforma, ou o token local de `POST /api/token/`. "
            "Header `Authorization: Bearer <token>`."
        ),
    },
}


def operacoes(spec: dict):
    for caminho, itens in spec.get("paths", {}).items():
        for metodo, operacao in itens.items():
            if metodo in HTTP_METHODS and isinstance(operacao, dict):
                yield caminho, metodo, operacao


def tag_por_regra(regras: list[tuple[str, str]], caminho: str) -> str | None:
    for padrao, tag in regras:
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
    """Ajusta as tags de cada operação e devolve as operações sem regra."""
    sem_regra: list[str] = []
    for caminho, metodo, operacao in operacoes(spec):
        novas: list[str] = []
        for tag in operacao.get("tags") or [""]:
            if not tag or eh_generica(tag, caminho):
                tag = tag_por_regra(REGRAS_POR_CAMINHO, caminho) or ""
                if not tag:
                    sem_regra.append(f"{metodo.upper()} {caminho}")
                    continue
            tag = TRADUCOES.get(tag, tag)
            if tag not in novas:
                novas.append(tag)
        reagrupada = tag_por_regra(REAGRUPAMENTO, caminho)
        if reagrupada:
            novas = [reagrupada]
        if novas:
            operacao["tags"] = novas
    return sem_regra


def nome(segmento: str) -> tuple[str, str | None]:
    return NOMES.get(segmento, (segmento.replace("-", " "), segmento.replace("-", " ")))


def resumo(metodo: str, caminho: str, metodos_do_caminho: set[str]) -> str:
    fixo = RESUMOS_FIXOS.get(f"{metodo.upper()} {caminho}")
    if fixo:
        return fixo
    partes = [p for p in caminho.split("/") if p and p not in ("api", "v1")]
    termina_em_parametro = partes[-1].startswith("{")
    segmentos = [p for p in partes if not p.startswith("{")]
    ultimo = segmentos[-1]
    anterior = segmentos[-2] if len(segmentos) > 1 else ultimo

    if ultimo in ACOES:
        return ACOES[ultimo].format(o=nome(anterior)[0])

    if ultimo in SEGMENTOS_DE_CRUD:
        acao = SEGMENTOS_DE_CRUD[ultimo]
        singular, plural = nome(anterior)
        if acao == "listar":
            return f"Listar {plural or singular}"
        if acao == "atualizar" and metodo == "put" and "patch" in metodos_do_caminho:
            acao = "substituir"
        return f"{acao.capitalize()} {singular}"

    singular, plural = nome(ultimo)
    if metodo == "get":
        if termina_em_parametro:
            return f"Obter {singular}"
        return f"Listar {plural}" if plural else f"Consultar {singular}"
    if metodo == "post":
        return f"Criar {singular}"
    if metodo == "put":
        return f"Substituir {singular}" if "patch" in metodos_do_caminho else f"Atualizar {singular}"
    if metodo == "patch":
        return f"Atualizar {singular}"
    if metodo == "delete":
        return f"Remover {singular}"
    return f"{metodo.upper()} {singular}"


def limpar_linha(linha: str) -> str | None:
    """Devolve a linha sem número de card nem caminho repetido; None = descartar."""
    rota = RE_LINHA_DE_ROTA.match(linha)
    if rota:
        linha = rota.group("resto").strip()
        linha = re.sub(r"^[—–:-]\s*", "", linha)
        if not linha:
            return None
    linha = RE_CARD_EM_PARENTESES.sub("", linha)
    linha = RE_CARD_NO_INICIO.sub("", linha)
    linha = RE_CARD_SOLTO.sub("", linha)
    linha = RE_CARD_ARTIGO.sub("a mudança", linha)
    linha = RE_CARD.sub("", linha)
    linha = RE_CITA_PY.sub("", linha)
    linha = re.sub(r"^[.,;:]\s*", "", linha)
    if rota or linha != linha.lstrip():
        linha = linha.strip()
    if linha and linha[0].islower() and rota:
        linha = linha[0].upper() + linha[1:]
    return linha


def limpar_descricao(texto: str) -> str:
    if texto.startswith(DESCRICOES_DE_BASE):
        return ""
    linhas = [limpar_linha(linha) for linha in texto.split("\n")]
    texto = "\n".join(linha for linha in linhas if linha is not None)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    if re.fullmatch(r"[\s.,;:—–-]*", texto):
        return ""
    return texto


def limpar_textos(no):
    """Tira número de card das descrições dos schemas (components)."""
    if isinstance(no, dict):
        for chave, valor in no.items():
            if chave == "description" and isinstance(valor, str):
                no[chave] = limpar_descricao(valor)
            else:
                limpar_textos(valor)
    elif isinstance(no, list):
        for item in no:
            limpar_textos(item)


def aplicar_seguranca(spec: dict, perfil: dict) -> None:
    esquemas = json.loads(json.dumps(SEGURANCA))
    esquemas["jwtAuth"]["description"] = perfil["descricao_jwt"]
    spec.setdefault("components", {})["securitySchemes"] = esquemas
    for _, _, operacao in operacoes(spec):
        atual = operacao.get("security")
        if not atual:
            # Rota pública ou com autenticação própria (webhook, token).
            operacao["security"] = [{}]
            continue
        exige_jwt = any("jwtAuth" in item for item in atual)
        anonimo = any(item == {} for item in atual)
        if not exige_jwt:
            continue
        novo = [{"jwtAuth": []}, {"apiKeyAuth": []}]
        if anonimo:
            novo.append({})
        operacao["security"] = novo


def listar_tags(spec: dict, perfil: str) -> tuple[list[dict], list[str]]:
    usadas = {tag for _, _, operacao in operacoes(spec) for tag in operacao.get("tags", [])}
    descricoes = {**DESCRICOES_TAGS, **DESCRICOES_TAGS_POR_PERFIL.get(perfil, {})}
    sem_descricao = sorted(tag for tag in usadas if not descricoes.get(tag))
    tags = [{"name": tag, "description": descricoes.get(tag, "")} for tag in sorted(usadas, key=str.casefold)]
    return tags, sem_descricao


def processar(spec: dict, perfil_nome: str, versao: str | None) -> list[str]:
    """Aplica todo o pós-processamento e devolve a lista de problemas."""
    perfil = PERFIS[perfil_nome]
    spec.setdefault("info", {}).update(perfil["info"])
    if versao:
        spec["info"]["version"] = versao
    spec["servers"] = perfil["servers"]

    problemas = [f"sem regra de tag: {item}" for item in retaguear(spec)]

    for caminho, metodo, operacao in operacoes(spec):
        metodos = {m for m in spec["paths"][caminho] if m in HTTP_METHODS}
        operacao["summary"] = resumo(metodo, caminho, metodos)
        descricao = limpar_descricao(operacao.get("description", ""))
        if descricao:
            operacao["description"] = descricao
        else:
            operacao.pop("description", None)
    limpar_textos(spec.get("components", {}).get("schemas", {}))
    aplicar_seguranca(spec, perfil)

    vistos: dict[tuple[str, str], str] = {}
    for caminho, metodo, operacao in operacoes(spec):
        chave = (operacao["tags"][0], operacao["summary"])
        if chave in vistos:
            problemas.append(f"summary repetido em '{chave[0]}': '{chave[1]}' ({vistos[chave]} e {metodo.upper()} {caminho})")
        vistos[chave] = f"{metodo.upper()} {caminho}"

    restos = re.findall(r"MIG-\d+", json.dumps(spec, ensure_ascii=False))
    if restos:
        problemas.append(f"número de card que sobrou: {sorted(set(restos))}")

    spec["tags"], sem_descricao = listar_tags(spec, perfil_nome)
    problemas += [f"tag sem descrição em DESCRICOES_TAGS: {tag}" for tag in sem_descricao]
    return problemas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec", type=Path, help="caminho do openapi.json gerado")
    parser.add_argument("--perfil", choices=sorted(PERFIS), required=True)
    parser.add_argument("--versao", help="versão exibida em info.version (ex.: 2.3.0)")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    problemas = processar(spec, args.perfil, args.versao)
    if problemas:
        print(f"{args.spec}: nada foi gravado. Corrija no script e rode de novo:")
        for item in problemas:
            print(f"  {item}")
        return 1

    with args.spec.open("w", encoding="utf-8", newline="\n") as arquivo:
        arquivo.write(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
    print(f"{args.spec}: {len(spec['paths'])} caminhos, {len(spec['tags'])} tags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
