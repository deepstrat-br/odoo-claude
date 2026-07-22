# Odoo — MCP Server, CLI & Automations (Multi-cliente)

Cliente Python XML-RPC + servidor MCP (Model Context Protocol) para Odoo ERP, com suporte a **multiplos clientes** (um YAML por cliente em `clients/`). Permite que agentes LLM (Claude Code, etc.) e scripts interajam diretamente com o ERP — buscar, criar, atualizar registros, qualificar leads, enviar WhatsApp, lancar horas e mais.

O servidor MCP atende varios clientes **simultaneamente**: toda tool aceita o parametro opcional `cliente` (slug), e as conexoes ficam em pool por slug — sessoes paralelas operando em clientes diferentes nao interferem umas nas outras.

> **Moeda:** Nunca assuma uma moeda especifica. Cada documento no Odoo (fatura, pedido, oportunidade) tem seu proprio `currency_id`, e as tools financeiras retornam a moeda real de cada registro.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/deepstrat-br/odoo-claude.git
cd odoo-deepstrat

# 2. Instale dependencias
pip install pyyaml python-dotenv

# 3. Configure suas credenciais
cp .env.example .env
# Edite o .env com seus dados (veja secao Configuracao abaixo)

# 4. Teste a conexao (escolha o cliente pelo slug)
python odoo.py --client deepstrat projetos
```

---

## Configuracao

### Clientes (clients/<slug>.yaml)

Cada cliente Odoo tem um YAML versionado em `clients/` com URL, DB, IDs de atividades,
templates WhatsApp e config de CRM (ex: `clients/deepstrat.yaml`, `clients/fenix.yaml`,
`clients/sudoeste.yaml`). Para adicionar um cliente novo, copie um YAML existente e
ajuste slug/nome/IDs.

Credenciais (login/key) **nunca** vao no YAML — ficam no `.env` ou em variaveis de
ambiente, com prefixo do slug:

```env
# Credenciais por cliente: <SLUG>_ODOO_LOGIN / <SLUG>_ODOO_KEY
DEEPSTRAT_ODOO_LOGIN=seu-email@deepstrat.com.br
DEEPSTRAT_ODOO_KEY=sua-api-key
FENIX_ODOO_LOGIN=...
FENIX_ODOO_KEY=...

# Fallback sem YAML (modo mono-cliente legado)
ODOO_URL=https://deepstrat.odoo.com
ODOO_DB=deepstrat
ODOO_LOGIN=seu-email@deepstrat.com.br
ODOO_KEY=sua-api-key-aqui

# Opcional — so necessario para integracao Clockify
CLOCKIFY_KEY=sua-clockify-api-key
```

> **API Key do Odoo:** Settings > My Profile > Account Security > API Keys

### Selecionar o cliente

- **MCP:** parametro `cliente` em cada tool (recomendado), ou `ODOO_CLIENT` no env do servidor como padrao
- **CLI:** `python odoo.py --client <slug> <comando>` ou env `ODOO_CLIENT=<slug>`
- **Python:** `load_client_config("<slug>")`

### Configuracao pessoal (CLAUDE.local.md)

Para quem usa Claude Code, crie um `CLAUDE.local.md` na raiz do projeto com seus IDs de referencia pessoais (UID, projetos, etapas, funcionarios). Este arquivo ja esta no `.gitignore` e e carregado automaticamente pelo Claude Code junto com o `CLAUDE.md`.

Veja o exemplo no `CLAUDE.md` (secao "Configuracao local").

---

## Estrutura do Projeto

```
odoo-deepstrat/
├── odoo.py                          # Cliente XML-RPC + Resolver + load_client_config (lib core)
├── mcp_server.py                    # Servidor MCP para agentes LLM (multi-cliente)
│
├── clients/                         # Configs de clientes (YAML, versionados)
│   ├── deepstrat.yaml
│   ├── fenix.yaml
│   └── sudoeste.yaml
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
├── docs/                            # Documentacao de processos e fluxos
│   ├── projetos-timesheets.md
│   ├── clockify.md
│   └── qualificacao-leads.md
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
| **Clientes**           | `listar_clientes`, `trocar_cliente`                                                                                              |
| **CRUD generico**      | `buscar`, `contar`, `ler_registro`, `criar_registro`, `atualizar_registro`, `deletar_registro`, `listar_campos`, `resolver_nome` |
| **Projetos & Tarefas** | `listar_projetos`, `listar_tarefas`, `criar_tarefa`, `mover_tarefa`, `lancar_horas`                                              |
| **CRM**                | `pipeline_crm`, `leads_pendentes_qualificacao`, `qualificar_lead`                                                                |
| **Financeiro**         | `resumo_financeiro`                                                                                                              |
| **WhatsApp**           | `listar_templates_whatsapp`, `enviar_whatsapp`, `preview_whatsapp`                                                               |

### Multi-cliente: como o servidor seleciona o cliente

Toda tool (exceto as de gerenciamento) aceita o parametro opcional **`cliente`** (slug):

```
contar(modelo="res.partner", cliente="sudoeste")
listar_projetos(cliente="fenix")
```

- Com `cliente` explicito, a chamada opera naquele cliente **sem afetar as demais** —
  as conexoes ficam em pool por slug, permitindo varios clientes simultaneos
  (inclusive em sessoes paralelas do Claude).
- Sem `cliente`, vale o **padrao da sessao**: env `ODOO_CLIENT` no startup do servidor,
  alteravel via `trocar_cliente(slug)` (que muda apenas o padrao, sem derrubar conexoes).
- `listar_clientes()` mostra os slugs disponiveis e o `cliente_padrao` atual.

> Em projetos/sessoes dedicados a um unico cliente, prefira **sempre passar o
> `cliente` explicito** nas chamadas — e imune a mudancas de padrao feitas em paralelo.

### Como usar com Claude Code

Adicione ao seu `claude_desktop_config.json` ou configure via `claude mcp add`:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": ["caminho/para/mcp_server.py"],
      "env": { "ODOO_CLIENT": "deepstrat" }
    }
  }
}
```

O `env.ODOO_CLIENT` define o cliente padrao do servidor (opcional — chamadas com
`cliente` explicito nao dependem dele).

As chamadas XML-RPC rodam em thread pool com timeout de socket (default 30s,
configuravel via env `ODOO_TIMEOUT`), entao requisicoes concorrentes nao travam
o servidor.

---

## CLI

```bash
# Selecione o cliente com --client <slug> (ou env ODOO_CLIENT=<slug>)
python odoo.py --client deepstrat projetos                       # Listar projetos ativos
python odoo.py --client deepstrat tarefas <id_ou_nome>           # Tarefas de um projeto
python odoo.py --client deepstrat financeiro                     # Resumo financeiro
python odoo.py --client deepstrat busca res.partner "name,email,city" "customer_rank>0" 10
python odoo.py --client deepstrat criar-tarefa <proj_id> "Nome da Tarefa" 4.0
python odoo.py --client deepstrat campos account.move            # Inspecionar campos de um modelo
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
python integrations/clockify.py comparar-rti 2026-04-01 2026-04-30
```

---

## Modulo Python

```python
from odoo import OdooClient, Resolver, load_client_config

config = load_client_config("deepstrat")  # ou usa env ODOO_CLIENT
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
r.users(["user@deepstrat.com.br"])    # res.users -> [int]
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

| Documento                                                  | Conteudo                                               |
| ---------------------------------------------------------- | ------------------------------------------------------ |
| [CLAUDE.md](CLAUDE.md)                                     | Referencia completa — modelos, campos, Resolver, dicas |
| [docs/projetos-timesheets.md](docs/projetos-timesheets.md) | Fluxo de etapas, convencoes de timesheet, metricas     |
| [docs/clockify.md](docs/clockify.md)                       | Integracao Clockify x Odoo, fechamento mensal          |
| [docs/qualificacao-leads.md](docs/qualificacao-leads.md)   | Metodologia de enriquecimento e priorizacao de leads   |
