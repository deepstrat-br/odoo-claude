# odoo-deepstrat

Python client + automation scripts for Odoo via XML-RPC, built for Claude-powered workflows.

---

## Setup

**1. Clone and install dependencies**

```bash
git clone https://github.com/deepstrat-br/odoo-claude.git
cd odoo-deepstrat
pip install pyyaml  # required for import scripts
```

**2. Configure credentials**

```bash
cp .env.example .env
```

```env
ODOO_URL=https://your-instance.odoo.com
ODOO_DB=your-database-name
ODOO_LOGIN=your-email@company.com
ODOO_KEY=your-api-key-here
CLOCKIFY_KEY=your-clockify-api-key
```

> **Odoo API key:** Settings → My Profile → Account Security → API Keys

---

## Project structure

```
odoo-deepstrat/
│
├── odoo.py                          # XML-RPC client (core lib)
│
├── scripts/                         # generic automation scripts by Odoo module
│   ├── project/
│   │   └── import_tasks.py          # bulk task creation from YAML
│   └── purchase/
│       └── import_po.py             # purchase order creation from YAML
│
├── integrations/                    # external systems ↔ Odoo
│   └── clockify.py                  # Clockify ↔ account.analytic.line
│
├── data/                            # temporary input files (not versioned)
│   ├── tasks/
│   └── purchase/
│
└── docs/
    ├── projetos-timesheets.md
    └── clockify.md
```

---

## CLI — odoo.py

```bash
python odoo.py projetos
python odoo.py tarefas <id_ou_nome>
python odoo.py financeiro
python odoo.py busca res.partner "name,email,city" "customer_rank>0" 10
python odoo.py criar-tarefa <proj_id> "Task name" 4.0
python odoo.py campos account.move
```

| Command | Description |
|---|---|
| `projetos` | List active projects |
| `tarefas <id\|name>` | List tasks for a project |
| `financeiro` | Quick financial summary |
| `busca <model> <fields> [filter] [limit]` | Generic record search |
| `criar-tarefa <proj_id> <name> [hours]` | Create a single task |
| `campos <model>` | Inspect fields of any model |

---

## Scripts

### scripts/project/import_tasks.py

Bulk task creation from a YAML file. Resolves project, stage, milestone, tags and assignees by name or ID.

```bash
python scripts/project/import_tasks.py data/tasks/client.yaml
python scripts/project/import_tasks.py data/tasks/client.yaml --dry-run
python scripts/project/import_tasks.py data/tasks/client.yaml --projeto "Project Name"
```

**YAML format:**
```yaml
project: "Project Name"  # or numeric ID

tasks:
  - name: "Task title"
    stage: "Backlog"           # name or ID
    milestone: "Marco 1"       # name or ID
    hours: 4.0
    deadline: "2026-05-01"
    tags: [Planejamento, CRM]  # names or IDs
    assignees: [user@email.com]
    description:
      - Item 1
      - Item 2
```

---

### scripts/purchase/import_po.py

Purchase order creation from a YAML file. Resolves partner, product, UOM and analytic accounts by name or ID. Supports section headers and analytic distribution.

```bash
python scripts/purchase/import_po.py data/purchase/contract.yaml
python scripts/purchase/import_po.py data/purchase/contract.yaml --dry-run
```

**YAML format:**
```yaml
partner: "Supplier Name"  # or numeric ID

header:
  date_planned: "2026-09-12"
  notes: "<p>Scope description...</p>"

lines:
  - section: "Section Title"

  - product: "Service on Timesheets"  # or ID
    uom: "Hours"
    qty: 10.0
    price: 150.0
    date: "2026-06-30"
    analytic:
      "Project Account": 100.0   # name or ID: percentage
    name: |
      Description line 1
      Description line 2
```

---

## integrations/clockify.py

Compares Clockify time entries with Odoo timesheets.

```bash
python integrations/clockify.py workspaces
python integrations/clockify.py projetos
python integrations/clockify.py entradas 2026-04-01 2026-04-30
python integrations/clockify.py comparar 2026-04-01 2026-04-30
python integrations/clockify.py comparar-rti 2026-04-01 2026-04-30
```

---

## Python module

```python
from odoo import OdooClient

odoo = OdooClient()  # reads credentials from .env

odoo.search('model', filters=[[...]], fields=['f1', 'f2'], limit=20)
odoo.get('model', record_id, fields=['f1'])
odoo.count('model', filters=[[...]])
odoo.create('model', {'field': 'value'})
odoo.update('model', record_id, {'field': 'new_value'})
odoo.delete('model', record_id)
odoo.fields('model')
```

---

## Common Odoo models

| Model | Description |
|---|---|
| `res.partner` | Contacts (customers, suppliers) |
| `sale.order` | Sales orders |
| `purchase.order` | Purchase orders |
| `account.move` | Invoices and journal entries |
| `project.project` | Projects |
| `project.task` | Tasks |
| `account.analytic.line` | Timesheets |
| `crm.lead` | CRM leads and opportunities |
| `hr.employee` | Employees |
| `product.product` | Products |
| `stock.quant` | Inventory |
