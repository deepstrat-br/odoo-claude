# Odoo ERP — Multi-cliente

Helper CLI + modulo Python para o Odoo via XML-RPC, com suporte a multiplos clientes.

## Conexao

### Configuracao por cliente (recomendado)

Cada cliente tem um arquivo YAML em `clients/<slug>.yaml` com URL, DB, IDs de atividades,
templates WhatsApp e config de CRM. Selecione o cliente ativo via:

```bash
export ODOO_CLIENT=deepstrat    # ou --client deepstrat no CLI
```

Credenciais (login/key) ficam no `.env` ou variaveis de ambiente — nunca no YAML commitado.

### Fallback (sem YAML)

Se `ODOO_CLIENT` nao estiver definido, usa diretamente as variaveis do `.env`:

| Param | Origem |
|---|---|
| URL | `ODOO_URL` no `.env` |
| DB | `ODOO_DB` no `.env` |
| Login | `ODOO_LOGIN` no `.env` |
| API Key | `ODOO_KEY` no `.env` |

**Moeda:** Nunca assumir uma moeda especifica. Cada documento no Odoo (fatura, pedido, oportunidade) tem seu proprio `currency_id`. As tools financeiras sempre retornam a moeda real de cada registro.

---

## Principios de desenvolvimento

**Scripts genericos, dados descartaveis.**
Nunca criar um script para um caso especifico (ex: "criar PO do fulano"). Sempre desenvolver o script generico e parametrizavel primeiro. Os arquivos de dados (`data/`) sao temporarios — criados na hora, usados, descartados.

**Resolver para campos relacionais.**
Todo script que cria ou atualiza registros com campos `many2one`/`many2many` deve usar a classe `Resolver` de `odoo.py`. Ela resolve nomes para IDs com cache, evitando duplicacao de logica entre scripts.

```python
from odoo import OdooClient, Resolver, load_client_config

config = load_client_config()  # usa ODOO_CLIENT env, ou load_client_config("slug")
odoo = OdooClient(**config["odoo"])
r = Resolver(odoo)

r.project("Meu Projeto")              # project.project -> int
r.stage("Backlog")                    # project.task.type -> int
r.milestone(project_id, "Marco 1")   # project.milestone -> int
r.tags(["CRM", "Vendas"])            # project.tags -> [(6, 0, [ids])]
r.users(["user@deepstrat.com.br"])  # res.users -> [int]
r.partner("Nome do Cliente")         # res.partner -> int
r.product("Service on Timesheets")   # product.product -> int
r.uom("Hours")                       # uom.uom -> int
r.analytic_distribution({"Proj X": 100.0})  # -> {str(id): float}
r.crm_stage("Qualificados")          # crm.stage -> int
r.employee("Nome do Funcionario")    # hr.employee -> int
```

Todos os metodos aceitam nome (string) ou ID (int) — se for ID, retorna direto sem consultar.

**Scripts especializados existem para workflows repetitivos.**
Para operacoes pontuais, Claude gera Python usando `OdooClient` diretamente, sem criar script.

---

## Estrutura do projeto

```
odoo-claude/
├── odoo.py                          # cliente XML-RPC + Resolver + load_client_config (lib core)
├── mcp_server.py                    # servidor MCP (Model Context Protocol)
├── clients/                         # configs de clientes (YAML, versionados)
│   └── deepstrat.yaml              # config Deepstrat: IDs, templates, CRM
├── scripts/
│   ├── project/
│   │   └── import_tasks.py          # criacao em lote de tarefas via YAML
│   └── purchase/
│       └── import_po.py             # criacao de PO + linhas via YAML
├── integrations/
│   └── clockify.py                  # Clockify <-> account.analytic.line
├── data/                            # entradas temporarias (nao versionadas)
│   ├── tasks/
│   └── purchase/
└── docs/
    ├── projetos-timesheets.md
    ├── clockify.md
    └── qualificacao-leads.md
```

---

## CLI — odoo.py

```bash
python odoo.py projetos                                          # usa ODOO_CLIENT env
python odoo.py --client deepstrat projetos                       # especifica cliente
python odoo.py tarefas <id_ou_nome>
python odoo.py financeiro
python odoo.py busca res.partner "name,email,city" "customer_rank>0" 10
python odoo.py criar-tarefa <proj_id> "Nome da Tarefa" 4.0
python odoo.py campos account.move
```

## CLI — scripts

```bash
# Tarefas em lote
python scripts/project/import_tasks.py data/tasks/cliente.yaml
python scripts/project/import_tasks.py data/tasks/cliente.yaml --dry-run
python scripts/project/import_tasks.py data/tasks/cliente.yaml --projeto "Nome"

# Pedido de Compra
python scripts/purchase/import_po.py data/purchase/contrato.yaml
python scripts/purchase/import_po.py data/purchase/contrato.yaml --dry-run
```

## CLI — integrations/clockify.py

```bash
python integrations/clockify.py entradas 2026-04-01 2026-04-30
python integrations/clockify.py comparar 2026-04-01 2026-04-30
python integrations/clockify.py comparar-rti 2026-04-01 2026-04-30
```

---

## Modulo Python

```python
from odoo import OdooClient, load_client_config

config = load_client_config()  # usa ODOO_CLIENT env
odoo = OdooClient(**config["odoo"])

odoo.search('modelo', filters=[[...]], fields=['campo1', 'campo2'], limit=20)
odoo.get('modelo', record_id, fields=[...])
odoo.count('modelo', filters=[[...]])
odoo.create('modelo', {'campo': 'valor'})
odoo.update('modelo', record_id, {'campo': 'novo_valor'})
odoo.delete('modelo', record_id)
odoo.fields('modelo')
```

---

## Configuracao multi-cliente (`clients/`)

Cada cliente tem um YAML em `clients/<slug>.yaml` com:

```yaml
slug: meu_cliente
nome: Nome do Cliente
moeda: BRL                    # moeda padrao (informativo)

odoo:
  url: https://instance.odoo.com
  db: database_name
  login: ""                   # fallback para ODOO_LOGIN env
  key: ""                     # fallback para ODOO_KEY env

activity_types:               # IDs variam por instancia Odoo
  call: 2
  todo: 4

whatsapp:
  template_abordagem_leads: 17  # null = desabilita envio automatico

crm:
  stage_novos: "Novos"
  metodologia: |
    Texto da metodologia de qualificacao...
```

**Para adicionar um novo cliente:** copiar `clients/deepstrat.yaml`, ajustar slug/nome/IDs, configurar credenciais no `.env`.

**Selecionar cliente ativo:**
- Env var: `ODOO_CLIENT=slug`
- CLI: `python odoo.py --client slug <comando>`
- Python: `load_client_config("slug")`

---

## Referencia rapida — Modelos e campos

### account.move (Faturas)

| Campo | Tipo | Descricao |
|---|---|---|
| `name` | char | Numero do documento |
| `partner_id` | m2o | Cliente/fornecedor |
| `move_type` | sel | `out_invoice` / `in_invoice` / `entry` |
| `state` | sel | `draft` / `posted` / `cancel` |
| `payment_state` | sel | `not_paid` / `in_payment` / `paid` / `partial` / `reversed` |
| `invoice_date` | date | Emissao |
| `invoice_date_due` | date | Vencimento |
| `amount_total` | float | Total com impostos |
| `amount_residual` | float | Saldo em aberto |
| `ref` | char | Referencia |
| `journal_id` | m2o | Diario contabil |

### sale.order (Vendas)

| Campo | Tipo | Descricao |
|---|---|---|
| `name` | char | Numero (ex: S00123) |
| `partner_id` | m2o | Cliente |
| `state` | sel | `draft` / `sent` / `sale` / `cancel` |
| `date_order` | datetime | Data do pedido |
| `amount_total` | float | Total |
| `invoice_status` | sel | `nothing` / `to invoice` / `invoiced` / `upselling` |
| `user_id` | m2o | Vendedor |
| `order_line` | o2m | Linhas do pedido |

### purchase.order (Compras)

| Campo | Tipo | Descricao |
|---|---|---|
| `name` | char | Numero (ex: P00045) |
| `partner_id` | m2o | Fornecedor |
| `state` | sel | `draft` / `sent` / `to approve` / `purchase` / `cancel` |
| `date_planned` | datetime | Entrega prevista |
| `amount_total` | float | Total |
| `invoice_status` | sel | `nothing` / `to invoice` / `invoiced` |

### project.task (Tarefas)

| Campo | Tipo | Descricao |
|---|---|---|
| `name` | char | Titulo |
| `project_id` | m2o | Projeto |
| `stage_id` | m2o | Etapa |
| `user_ids` | m2m | Responsaveis (lista!) |
| `allocated_hours` | float | Horas planejadas (usar este, NAO `planned_hours`) |
| `effective_hours` | float | Horas lancadas |
| `remaining_hours` | float | Horas restantes |
| `date_deadline` | date | Prazo |
| `priority` | sel | `0` normal / `1` urgente |
| `description` | html | Descricao |

### crm.lead (CRM)

| Campo | Tipo | Descricao |
|---|---|---|
| `name` | char | Titulo |
| `partner_id` | m2o | Cliente |
| `type` | sel | `lead` / `opportunity` |
| `stage_id` | m2o | Etapa do funil |
| `expected_revenue` | float | Receita esperada |
| `probability` | float | Probabilidade (0-100) |
| `date_deadline` | date | Prazo de fechamento |
| `priority` | sel | `0` / `1` quente / `2` muito quente |
| `user_id` | m2o | Responsavel |

### account.analytic.line (Timesheets)

| Campo | Tipo | Descricao |
|---|---|---|
| `date` | date | Data |
| `employee_id` | m2o | Funcionario |
| `project_id` | m2o | Projeto |
| `task_id` | m2o | Tarefa |
| `name` | char | Descricao da atividade |
| `unit_amount` | float | Horas |
| `validated` | bool | Aprovado pelo gestor |

### whatsapp.template (Templates WhatsApp)

| Campo | Tipo | Descricao |
|---|---|---|
| `name` | char | Nome do template |
| `template_name` | char | Nome tecnico (slug) |
| `status` | sel | `approved` / `pending` / `rejected` |
| `body` | text | Corpo da mensagem (com placeholders {{1}}, {{2}}...) |
| `model` | char | Modelo vinculado (ex: `crm.lead`, `account.move`) |
| `phone_field` | char | Campo de telefone no modelo |
| `variable_ids` | o2m | Variaveis do template |
| `wa_account_id` | m2o | Conta WhatsApp Business |

### whatsapp.message (Mensagens WhatsApp)

| Campo | Tipo | Descricao |
|---|---|---|
| `mobile_number` | char | Numero destino |
| `state` | sel | `outgoing` / `sent` / `delivered` / `read` / `error` / `cancel` |
| `wa_template_id` | m2o | Template utilizado |
| `failure_reason` | char | Motivo da falha |

---

## Documentacao detalhada

- [Projetos & Timesheets](docs/projetos-timesheets.md) — fluxo de etapas, convencoes de timesheet, metricas de saude
- [Clockify](docs/clockify.md) — integracao Clockify x Odoo, mapeamento de projetos/usuarios, fechamento mensal
- [Qualificacao de Leads](docs/qualificacao-leads.md) — metodologia de enriquecimento e priorizacao de leads CRM

Ler `projetos-timesheets.md` antes de criar/mover tarefas, lancar horas ou avaliar saude de projeto.
Ler `clockify.md` antes de comparar horas ou fechar o mes no projeto RTI.
Ler `qualificacao-leads.md` antes de qualificar leads ou usar as tools `leads_pendentes_qualificacao` / `qualificar_lead`.

---

## Configuracao local — CLAUDE.local.md

Informacoes pessoais (login, UID, IDs de referencia) **nao devem** estar neste arquivo.
Cada usuario cria seu proprio `CLAUDE.local.md` na raiz do projeto (ja esta no `.gitignore`).

O Claude Code carrega automaticamente ambos os arquivos (`CLAUDE.md` + `CLAUDE.local.md`).

Exemplo de conteudo para `CLAUDE.local.md`:

```markdown
# Configuracao pessoal

## Conexao
| Param | Valor |
|---|---|
| Login | `seu-email@deepstrat.com.br` |
| UID | `2` |

## IDs de referencia
(tabelas de projetos, funcionarios, etapas, etc.)
```

---

## Dicas

- Campos `many2one` retornam `[id, 'nome']` — use `[0]` para ID, `[1]` para nome
- Ao criar tarefas: `'user_ids': [uid]` (lista), nao `'user_id'`
- Datas como string `YYYY-MM-DD`; datetimes como `YYYY-MM-DD HH:MM:SS`
- Sempre `default=str` no `json.dumps()`
- O UID do usuario logado vem de `odoo.uid` (autenticado via `.env`)
