# Odoo Deepstrat — MCP Server, CLI & Automations

Cliente Python XML-RPC + servidor MCP (Model Context Protocol) para o Odoo ERP da Deepstrat. Permite que agentes LLM (Claude Code, etc.) e scripts interajam diretamente com o ERP — buscar, criar, atualizar registros, qualificar leads, enviar WhatsApp, lancar horas e mais.

> **Moeda:** Todos os valores monetarios estao em **BRL (R$)**, salvo quando `currency_id` indicar outra moeda.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/deepstrat-br/odoo-claude.git
cd odoo-deepstrat

# 2. Instale dependencias
pip install pyyaml python-dotenv openpyxl

# 3. Configure suas credenciais
cp .env.example .env
# Edite o .env com seus dados (veja secao Configuracao abaixo)

# 4. Teste a conexao
python odoo.py projetos
```

---

## Configuracao

### Credenciais (.env)

Cada dev cria seu proprio `.env` na raiz do projeto (ja esta no `.gitignore`):

```env
ODOO_URL=https://deepstrat.odoo.com
ODOO_DB=deepstrat
ODOO_LOGIN=seu-email@deepstrat.com.br
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
odoo-deepstrat/
├── odoo.py                          # Cliente XML-RPC + Resolver (lib core)
├── mcp_server.py                    # Servidor MCP para agentes LLM
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
├── reports/                         # Geradores de relatorios
│   └── dre.py                       # DRE (Demonstracao do Resultado) em Excel
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
| **CRUD generico**      | `buscar`, `contar`, `ler_registro`, `criar_registro`, `atualizar_registro`, `deletar_registro`, `listar_campos`, `resolver_nome` |
| **Projetos & Tarefas** | `listar_projetos`, `listar_tarefas`, `criar_tarefa`, `mover_tarefa`, `lancar_horas`                                              |
| **CRM**                | `pipeline_crm`, `leads_pendentes_qualificacao`, `qualificar_lead`                                                                |
| **Financeiro**         | `resumo_financeiro`, `gerar_dre`                                                                                                 |
| **WhatsApp**           | `listar_templates_whatsapp`, `enviar_whatsapp`, `preview_whatsapp`                                                               |

### Como usar com Claude Code

Adicione ao seu `claude_desktop_config.json` ou configure via `claude mcp add`:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": ["caminho/para/mcp_server.py"]
    }
  }
}
```

---

## CLI

```bash
python odoo.py projetos                                          # Listar projetos ativos
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

## Relatorios Financeiros

### DRE (Demonstracao do Resultado do Exercicio)

Gera planilha Excel (.xlsx) com 3 abas: **DRE mensal**, **Detalhamento Receitas** e **Detalhamento Despesas**.

**Via MCP (Claude Code):**

```
gerar_dre(ano=2025)
```

Com mapeamento de termos de contas analiticas ou contabeis para categorias:

```
gerar_dre(
  ano=2025,
  mapeamento_categorias={
    "Pessoal / Servicos Profissionais": ["Pessoal", "RH", "Honorarios"],
    "Terceirizacao / Subcontratacao": ["Subcontratacao", "Terceiros"],
    "Impostos e Taxas": ["SEFAZ", "ISS", "Simples", "INSS"]
  }
)
```

**Logica de categorizacao** por linha de fatura:
1. Conta analitica (`analytic_distribution`) — prioritario
2. Conta do plano de contas (`account_id`) — fallback
3. Default: `"Software / SaaS / Infraestrutura"`

Categorias de despesa disponíveis:

| Categoria | Descricao |
|---|---|
| `Pessoal / Servicos Profissionais` | Folha, MEIs, honorarios |
| `Terceirizacao / Subcontratacao` | Servicos de terceiros |
| `Impostos e Taxas` | SEFAZ, Prefeitura, taxas |
| `Software / SaaS / Infraestrutura` | Default para nao mapeados |

O arquivo e salvo em `reports/dre_{ano}.xlsx`. A aba "Detalhamento Despesas" exibe a conta analitica e conta contabil de cada linha para auditoria. Faturas em rascunho aparecem como "Provisorio"; faturas confirmadas como "Efetivo".

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
from odoo import OdooClient, Resolver

odoo = OdooClient()  # le credenciais do .env

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
