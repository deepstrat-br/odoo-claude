# Odoo MCP — Multi-cliente

Cliente Python XML-RPC + servidor MCP (Model Context Protocol) para Odoo ERP, com suporte a multiplos clientes via YAML. Permite que agentes LLM (Claude Code, etc.) e scripts interajam diretamente com o ERP — buscar, criar, atualizar registros, qualificar leads, enviar WhatsApp, lancar horas e mais.

> **Moeda:** Cada documento no Odoo (fatura, pedido, oportunidade) tem seu proprio `currency_id`. As tools financeiras sempre retornam a moeda real de cada registro, sem assumir uma moeda padrao.

---

## Quick Start

```bash
# 1. Clone
git clone <url-do-seu-fork>.git
cd odoo-claude

# 2. Instale dependencias
pip install pyyaml python-dotenv

# 3. Configure um cliente (veja secao Configuracao)
cp .env.example .env
# Edite .env com suas credenciais
# Crie clients/<slug>.yaml com URL, DB e IDs do cliente

# 4. Teste a conexao
export ODOO_CLIENT=<slug>
python odoo.py projetos
```

---

## Configuracao

### Multi-cliente (recomendado)

Cada cliente tem um arquivo YAML em `clients/<slug>.yaml` com URL, DB, IDs de atividades,
templates WhatsApp e config de CRM. Selecione o cliente ativo via:

```bash
export ODOO_CLIENT=acme    # ou --client acme no CLI
```

Exemplo de `clients/acme.yaml`:

```yaml
slug: acme
nome: ACME Corp
moeda: BRL

odoo:
  url: https://acme.odoo.com
  db: acme_production
  login: ""   # fallback para ACME_ODOO_LOGIN env
  key: ""     # fallback para ACME_ODOO_KEY env

activity_types:
  call: 2
  todo: 4

whatsapp:
  template_abordagem_leads: null   # null = desabilita envio automatico

crm:
  stage_novos: "Novos"
  metodologia: |
    Texto da metodologia de qualificacao de leads...
```

Credenciais (login/key) ficam no `.env` como `{SLUG}_ODOO_LOGIN` e `{SLUG}_ODOO_KEY`
(slug em maiusculas) — **nunca** no YAML commitado.

### Fallback (sem YAML)

Se `ODOO_CLIENT` nao estiver definido, le diretamente do `.env`:

```env
ODOO_URL=https://instance.odoo.com
ODOO_DB=database_name
ODOO_LOGIN=seu-email@empresa.com
ODOO_KEY=sua-api-key-aqui

# Opcional — so necessario para integracao Clockify
CLOCKIFY_KEY=sua-clockify-api-key
```

> **API Key do Odoo:** Settings > My Profile > Account Security > API Keys

### Configuracao pessoal (CLAUDE.local.md)

Para quem usa Claude Code, crie um `CLAUDE.local.md` na raiz do projeto com seus IDs de referencia pessoais (UID, projetos, etapas, funcionarios). Este arquivo ja esta no `.gitignore` e e carregado automaticamente pelo Claude Code junto com o `CLAUDE.md`.

Veja o exemplo no `CLAUDE.md` (secao "Configuracao local").

---

## Estrutura do Projeto

```
odoo-claude/
├── odoo.py                          # Cliente XML-RPC + Resolver + load_client_config
├── mcp_server.py                    # Servidor MCP para agentes LLM
│
├── clients/                         # Configs por cliente (YAML, nao versionados)
│   └── <slug>.yaml
│
├── scripts/                         # Scripts de automacao por modulo Odoo
│   ├── project/
│   │   └── import_tasks.py          # Criacao em lote de tarefas via YAML
│   └── purchase/
│       └── import_po.py             # Criacao de PO + linhas via YAML
│
├── integrations/                    # Integracoes com sistemas externos
│   └── clockify.py                  # Clockify <-> account.analytic.line
│
├── data/                            # Entradas temporarias (nao versionadas)
│   ├── tasks/
│   └── purchase/
│
├── CLAUDE.md                        # Instrucoes para o Claude Code (versionado)
├── CLAUDE.local.md                  # Config pessoal do dev (nao versionado)
├── .env.example                     # Template de credenciais
└── .env                             # Credenciais locais (nao versionado)
```

---

## MCP Server

O `mcp_server.py` expoe o Odoo como tools via [Model Context Protocol](https://modelcontextprotocol.io), permitindo que agentes LLM interajam com o ERP.

### Tools disponiveis

| Categoria              | Tools                                                                                                                            |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **CRUD generico**      | `buscar`, `contar`, `ler_registro`, `criar_registro`, `atualizar_registro`, `deletar_registro`, `listar_campos`, `resolver_nome` |
| **Projetos & Tarefas** | `listar_projetos`, `listar_tarefas`, `criar_tarefa`, `mover_tarefa`, `lancar_horas`                                              |
| **CRM**                | `pipeline_crm`, `leads_pendentes_qualificacao`, `qualificar_lead`                                                                |
| **Financeiro**         | `resumo_financeiro`                                                                                                              |
| **WhatsApp**           | `listar_templates_whatsapp`, `enviar_whatsapp`, `preview_whatsapp`                                                               |
| **Multi-cliente**      | `listar_clientes`, `trocar_cliente`                                                                                              |

### Como usar com Claude Code

Adicione ao seu `claude_desktop_config.json` ou configure via `claude mcp add`:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": ["caminho/para/mcp_server.py"],
      "env": {
        "ODOO_CLIENT": "acme"
      }
    }
  }
}
```

---

## CLI

```bash
python odoo.py projetos                                          # Listar projetos ativos
python odoo.py --client acme projetos                            # Especificar cliente
python odoo.py tarefas <id_ou_nome>                              # Tarefas de um projeto
python odoo.py financeiro                                        # Resumo financeiro
python odoo.py busca res.partner "name,email,city" "customer_rank>0" 10  # Busca generica
python odoo.py criar-tarefa <proj_id> "Nome da Tarefa" 4.0      # Criar tarefa
python odoo.py campos account.move                               # Inspecionar campos de um modelo
```

---

## Scripts de Automacao

### Importacao de Tarefas em Lote

```bash
python scripts/project/import_tasks.py data/tasks/cliente.yaml
python scripts/project/import_tasks.py data/tasks/cliente.yaml --dry-run
python scripts/project/import_tasks.py data/tasks/cliente.yaml --projeto "Nome"
```

**Formato YAML:**

```yaml
project: "Nome do Projeto" # nome ou ID

tasks:
  - name: "Titulo da tarefa"
    stage: "Backlog" # nome ou ID
    milestone: "Marco 1" # nome ou ID
    hours: 4.0
    deadline: "2026-05-01"
    tags: [Planejamento, CRM]
    assignees: [usuario@email.com]
    description:
      - Item 1
      - Item 2
```

### Importacao de Pedido de Compra

```bash
python scripts/purchase/import_po.py data/purchase/contrato.yaml
python scripts/purchase/import_po.py data/purchase/contrato.yaml --dry-run
```

**Formato YAML:**

```yaml
partner: "Nome do Fornecedor"

header:
  date_planned: "2026-09-12"
  notes: "<p>Descricao do escopo...</p>"

lines:
  - section: "Titulo da Secao"
  - product: "Service on Timesheets"
    uom: "Hours"
    qty: 10.0
    price: 150.0
    date: "2026-06-30"
    analytic:
      "Conta Analitica": 100.0
    name: |
      Descricao linha 1
      Descricao linha 2
```

---

## Integracao Clockify

Compara entradas do Clockify com timesheets do Odoo para fechamento mensal.

```bash
python integrations/clockify.py workspaces                        # Listar workspaces
python integrations/clockify.py projetos                          # Listar projetos
python integrations/clockify.py entradas 2026-04-01 2026-04-30   # Entradas do periodo
python integrations/clockify.py comparar 2026-04-01 2026-04-30   # Comparar Clockify x Odoo
```

---

## Modulo Python

```python
from odoo import OdooClient, Resolver, load_client_config

config = load_client_config("acme")   # le clients/acme.yaml + credenciais do .env
odoo = OdooClient(**config["odoo"])

# CRUD basico
odoo.search('res.partner', filters=[["customer_rank", ">", 0]], fields=['name', 'email'], limit=10)
odoo.get('res.partner', 42, fields=['name', 'email'])
odoo.count('res.partner', filters=[["customer_rank", ">", 0]])
odoo.create('res.partner', {'name': 'Novo Cliente', 'email': 'novo@email.com'})
odoo.update('res.partner', 42, {'phone': '+55 11 99999-0000'})
odoo.delete('res.partner', 42)
odoo.fields('res.partner')

# Resolver — converte nomes para IDs automaticamente
r = Resolver(odoo)
r.project("Meu Projeto")              # project.project -> int
r.partner("Nome do Cliente")          # res.partner -> int
r.users(["user@empresa.com"])         # res.users -> [int]
r.tags(["CRM", "Vendas"])            # project.tags -> [(6, 0, [ids])]
```

---

## Modelos Odoo mais usados

| Modelo                  | Descricao                         |
| ----------------------- | --------------------------------- |
| `res.partner`           | Contatos (clientes, fornecedores) |
| `sale.order`            | Pedidos de venda                  |
| `purchase.order`        | Pedidos de compra                 |
| `account.move`          | Faturas e lancamentos contabeis   |
| `project.project`       | Projetos                          |
| `project.task`          | Tarefas                           |
| `account.analytic.line` | Timesheets (horas lancadas)       |
| `crm.lead`              | Leads e oportunidades CRM         |
| `hr.employee`           | Funcionarios                      |
| `whatsapp.template`     | Templates de WhatsApp Business    |
| `whatsapp.message`      | Mensagens WhatsApp enviadas       |

---

## Documentacao

Veja [CLAUDE.md](CLAUDE.md) para referencia completa — modelos, campos, Resolver, dicas de uso.
