# Odoo ERP — Deepstrat

Helper CLI + modulo Python para o Odoo da Deepstrat via XML-RPC.

## Conexao

| Param | Valor |
|---|---|
| URL | `https://deepstrat.odoo.com` |
| DB | `deepstrat` |
| Login | `vagner@deepstrat.com.br` |
| UID | `2` |

Credenciais completas no `.env` (carregadas automaticamente pelo `odoo.py`).

## Estrutura do projeto

```
odoo-deepstrat/
├── odoo.py                          # cliente XML-RPC (lib core)
├── scripts/
│   ├── project/
│   │   └── import_tasks.py          # criacao em lote de tarefas via YAML
│   └── purchase/                    # (futuro: pedidos de compra, etc.)
├── integrations/
│   └── clockify.py                  # Clockify ↔ account.analytic.line
├── data/
│   └── tasks/                       # YAMLs de tarefas por cliente
│       └── sudoeste_ambiental.yaml
└── docs/
    ├── projetos-timesheets.md
    └── clockify.md
```

## CLI — odoo.py (raiz)

```bash
python odoo.py projetos
python odoo.py tarefas 26
python odoo.py financeiro
python odoo.py busca res.partner "name,email,city" "customer_rank>0" 10
python odoo.py criar-tarefa 26 "Nome da Tarefa" 4.0
python odoo.py campos account.move
```

## CLI — scripts/project/import_tasks.py

```bash
# Criacao em lote de tarefas a partir de YAML
python scripts/project/import_tasks.py data/tasks/<cliente>.yaml
python scripts/project/import_tasks.py data/tasks/<cliente>.yaml --dry-run
python scripts/project/import_tasks.py data/tasks/<cliente>.yaml --projeto "Nome do Projeto"
```

## CLI — integrations/clockify.py

```bash
python integrations/clockify.py workspaces
python integrations/clockify.py entradas 2026-04-01 2026-04-30
python integrations/clockify.py comparar 2026-04-01 2026-04-30
python integrations/clockify.py comparar-rti 2026-04-01 2026-04-30
```

## Modulo Python

```python
from odoo import OdooClient
odoo = OdooClient()

odoo.search('modelo', filters=[[...]], fields=['campo1','campo2'], limit=20)
odoo.create('modelo', {'campo': 'valor'})
odoo.update('modelo', record_id, {'campo': 'novo_valor'})
odoo.delete('modelo', record_id)
odoo.count('modelo', filters=[[...]])
odoo.get('modelo', record_id, fields=[...])
odoo.fields('modelo')
```

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

---

## IDs de referencia

### Etapas de tarefas (project.task → stage_id)

| ID | Etapa |
|---|---|
| 43 | Backlog |
| 71 | A fazer |
| 59 | Em andamento |
| 37 | Aguardando |
| 36 | QA/QC |
| 79 | Concluido |
| 80 | Bloqueado |
| 12 | Cancelado |

### Etapas CRM (crm.lead → stage_id)

| ID | Etapa |
|---|---|
| 1 | Novos |
| 2 | Qualificados |
| 3 | Proposition |
| 10 | Negociacao |
| 4 | Won |
| 9 | Arquivadas |

### Projetos (project.project)

| ID | Projeto |
|---|---|
| 17 | Assessoria Empresarial Fenix |
| 22 | Projeto Sudoeste Ambiental |
| 24 | Plano de Marketing |
| 25 | Parceria Microsoft |
| 26 | Localizacao Odoo (OCA) |
| 9 | Projeto Interno |

### Funcionarios (hr.employee)

| ID | Nome |
|---|---|
| 1 | Vagner Kogikoski Jr. |
| 2 | Carlos Gottardi |
| 4 | Thiago Monteiro |
| 7 | Stefano Tavanielli |

---

## Documentacao detalhada

- [Projetos & Timesheets](docs/projetos-timesheets.md) — principios de gestao de projetos, fluxo de etapas, convencoes de lancamento de horas e metricas de saude
- [Clockify](docs/clockify.md) — integracao com Clockify (Ryse), comandos CLI, mapeamento de projetos/usuarios e fluxo de fechamento mensal

Ler `projetos-timesheets.md` antes de:
- Criar ou mover tarefas (fluxo de etapas e convencoes)
- Lancar, corrigir ou validar horas (regras de timesheet)
- Avaliar saude de um projeto (metricas e sinais de atencao)
- Responder perguntas sobre processo — nao apenas sobre dados

Ler `clockify.md` antes de:
- Comparar horas Clockify x Odoo
- Usar o script `integrations/clockify.py`
- Fechar o mes no projeto RTI ou qualquer projeto Ryse

## Dicas

- Campos `many2one` retornam `[id, 'nome']` — use `[1]` para nome, `[0]` para ID
- Ao criar tarefas: `'user_ids': [uid]` (lista), nao `'user_id'`
- Datas como string `YYYY-MM-DD`
- Sempre `default=str` no `json.dumps()`
- UID 2 = Vagner (usuario logado)
