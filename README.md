# odoo-claude

Python client layer for Claude AI to interact with any Odoo instance via XML-RPC.

Built as a foundation for Claude-powered automation — works with any Odoo database you have credentials for.

---

## Setup

**1. Clone and install dependencies**

```bash
git clone https://github.com/deepstrat-br/odoo-claude.git
cd odoo-claude
pip install python-dotenv  # optional, .env is loaded natively
```

No external dependencies required — uses Python's built-in `xmlrpc.client`.

**2. Configure your Odoo instance**

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
ODOO_URL=https://your-instance.odoo.com
ODOO_DB=your-database-name
ODOO_LOGIN=your-email@company.com
ODOO_KEY=your-api-key-here
```

> **Where to find your API key:** Odoo → Settings → My Profile → Account Security → API Keys

The `.env` file is loaded automatically — no need to set environment variables manually. You can also point Claude to a different `.env` file per project to switch between Odoo instances.

---

## CLI

```bash
python odoo.py projetos
python odoo.py tarefas 26
python odoo.py tarefas "Marketing"
python odoo.py financeiro
python odoo.py busca res.partner "name,email,city" "customer_rank>0" 10
python odoo.py criar-tarefa 26 "Task name" 4.0
python odoo.py campos account.move
```

| Command | Description |
|---|---|
| `projetos` | List active projects |
| `tarefas <id\|name>` | List tasks for a project (by ID or name) |
| `financeiro` | Quick financial summary (open invoices, overdue, sales orders) |
| `busca <model> <fields> [filter] [limit]` | Generic record search |
| `criar-tarefa <proj_id> <name> [hours]` | Create a task |
| `campos <model>` | Inspect all fields of a model |

---

## Python Module

Import `OdooClient` to build your own automations:

```python
from odoo import OdooClient

odoo = OdooClient()  # reads credentials from .env automatically

# Search
odoo.search('model', filters=[[...]], fields=['field1', 'field2'], limit=20)

# Read single record
odoo.get('model', record_id, fields=['field1', 'field2'])

# Count
odoo.count('model', filters=[[...]])

# Create
odoo.create('model', {'field': 'value'})

# Update
odoo.update('model', record_id, {'field': 'new_value'})

# Delete
odoo.delete('model', record_id)

# Inspect fields
odoo.fields('model')
```

### Examples

```python
from odoo import OdooClient
odoo = OdooClient()

# Open invoices
invoices = odoo.search('account.move', filters=[
    ['move_type', '=', 'out_invoice'],
    ['payment_state', '!=', 'paid'],
    ['state', '=', 'posted'],
], fields=['name', 'partner_id', 'amount_residual', 'invoice_date_due'])

# Tasks in progress
tasks = odoo.search('project.task', filters=[
    ['stage_id.name', 'ilike', 'progress']
], fields=['name', 'project_id', 'user_ids', 'allocated_hours'])

# Create a timesheet entry
odoo.create('account.analytic.line', {
    'date': '2025-01-15',
    'project_id': 26,
    'task_id': 123,
    'name': 'Development work',
    'unit_amount': 2.5,
})
```

---

## Switching between Odoo instances

Each `.env` file points to one Odoo instance. To work with multiple databases:

```
project-a/.env   → ODOO_URL=https://client-a.odoo.com, ODOO_DB=client_a
project-b/.env   → ODOO_URL=https://client-b.odoo.com, ODOO_DB=client_b
```

The client loads the `.env` from the same directory as `odoo.py`. Place or symlink `odoo.py` into each project folder, or set the env vars explicitly before running:

```bash
ODOO_URL=https://other.odoo.com ODOO_DB=other ODOO_LOGIN=me@other.com ODOO_KEY=xxx python odoo.py projetos
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

Use `python odoo.py campos <model>` to explore fields on any model.

---

## Additional integrations

- [`clockify.py`](clockify.py) — Clockify time tracking integration (compare hours vs Odoo timesheets)
