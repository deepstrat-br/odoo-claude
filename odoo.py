"""
Odoo Helper — XML-RPC client for Claude automation
Uso: python odoo.py <comando> [args]
"""

import xmlrpc.client
import json
import os
import sys

# Carrega .env se existir (mesmo diretorio do script)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

ODOO_URL   = os.environ.get("ODOO_URL", "")
ODOO_DB    = os.environ.get("ODOO_DB", "")
ODOO_LOGIN = os.environ.get("ODOO_LOGIN", "")
ODOO_KEY   = os.environ.get("ODOO_KEY", "")


class OdooClient:
    def __init__(self):
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        self.uid = common.authenticate(ODOO_DB, ODOO_LOGIN, ODOO_KEY, {})
        if not self.uid:
            raise ConnectionError("Falha na autenticacao. Verifique as credenciais.")
        self._models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

    def _call(self, model, method, args, kwargs=None):
        return self._models.execute_kw(
            ODOO_DB, self.uid, ODOO_KEY, model, method, args, kwargs or {}
        )

    def search(self, model, filters=None, fields=None, limit=80, order=None):
        kwargs = {"limit": limit}
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order
        return self._call(model, "search_read", [filters or []], kwargs)

    def count(self, model, filters=None):
        return self._call(model, "search_count", [filters or []])

    def get(self, model, record_id, fields=None):
        kwargs = {}
        if fields:
            kwargs["fields"] = fields
        result = self._call(model, "read", [[record_id]], kwargs)
        return result[0] if result else None

    def create(self, model, values):
        return self._call(model, "create", [values])

    def update(self, model, record_id, values):
        return self._call(model, "write", [[record_id], values])

    def delete(self, model, record_id):
        return self._call(model, "unlink", [[record_id]])

    def fields(self, model):
        return self._call(model, "fields_get", [], {"attributes": ["string", "type"]})


# ─── CLI ──────────────────────────────────────────────────────────────────────

def print_table(records, cols=None):
    if not records:
        print("Nenhum registro encontrado.")
        return
    if cols is None:
        cols = list(records[0].keys())
    widths = {c: max(len(str(c)), max(len(str(r.get(c, ""))) for r in records)) for c in cols}
    header = "  ".join(str(c).ljust(widths[c]) for c in cols)
    sep = "  ".join("-" * widths[c] for c in cols)
    print(header)
    print(sep)
    for r in records:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))
    print(f"\n{len(records)} registro(s)")


def cmd_projetos(odoo, args):
    records = odoo.search(
        "project.project",
        filters=[["active", "=", True]],
        fields=["id", "name", "partner_id", "task_count", "date"],
        order="name asc",
    )
    rows = [
        {
            "ID": r["id"],
            "Projeto": r["name"][:40],
            "Cliente": (r["partner_id"][1] if r["partner_id"] else "—")[:25],
            "Tarefas": r["task_count"],
            "Prazo": r["date"] or "—",
        }
        for r in records
    ]
    print_table(rows, ["ID", "Projeto", "Cliente", "Tarefas", "Prazo"])


def cmd_tarefas(odoo, args):
    if not args:
        print("Uso: python odoo.py tarefas <project_id ou nome>")
        return

    arg = args[0]
    if arg.isdigit():
        filters = [["project_id", "=", int(arg)], ["active", "in", [True, False]]]
    else:
        filters = [["project_id.name", "ilike", arg], ["active", "in", [True, False]]]

    records = odoo.search(
        "project.task",
        filters=filters,
        fields=["id", "name", "stage_id", "allocated_hours", "effective_hours", "user_ids"],
        limit=50,
        order="name asc",
    )
    rows = [
        {
            "ID": r["id"],
            "Tarefa": r["name"][:45],
            "Etapa": (r["stage_id"][1] if r["stage_id"] else "—")[:20],
            "Plan.h": r["allocated_hours"],
            "Gasto.h": r["effective_hours"],
        }
        for r in records
    ]
    print_table(rows, ["ID", "Tarefa", "Etapa", "Plan.h", "Gasto.h"])


def cmd_busca(odoo, args):
    if len(args) < 2:
        print("Uso: python odoo.py busca <modelo> <campos> [filtro] [limite]")
        print('Exemplo: python odoo.py busca res.partner "name,email,city" "customer_rank>0" 10')
        return

    model = args[0]
    fields = [f.strip() for f in args[1].split(",")]
    limit = int(args[3]) if len(args) > 3 else 20
    filters = []

    if len(args) > 2 and args[2]:
        # Parse simples de filtro: "campo>valor" ou "campo=valor"
        for op in [">", "<", ">=", "<=", "!=", "="]:
            if op in args[2]:
                campo, valor = args[2].split(op, 1)
                try:
                    valor = int(valor)
                except ValueError:
                    pass
                filters = [[campo.strip(), op, valor]]
                break

    records = odoo.search(model, filters=filters, fields=fields, limit=limit)

    if not records:
        print("Nenhum registro encontrado.")
        return

    rows = []
    for r in records:
        row = {}
        for f in fields:
            val = r.get(f, "")
            if isinstance(val, list) and len(val) == 2:
                val = val[1]  # many2one: pega o nome
            row[f] = str(val)[:40]
        rows.append(row)
    print_table(rows, fields)


def cmd_criar_tarefa(odoo, args):
    if len(args) < 2:
        print("Uso: python odoo.py criar-tarefa <project_id> <nome> [horas]")
        return
    project_id = int(args[0])
    name = args[1]
    hours = float(args[2]) if len(args) > 2 else 0.0

    task_id = odoo.create("project.task", {
        "name": name,
        "project_id": project_id,
        "allocated_hours": hours,
        "user_ids": [odoo.uid],
    })
    print(f"Tarefa criada: ID {task_id} — '{name}' ({hours}h) no projeto {project_id}")


def cmd_campos(odoo, args):
    if not args:
        print("Uso: python odoo.py campos <modelo>")
        return
    fields = odoo.fields(args[0])
    rows = [{"Campo": k, "Label": v["string"], "Tipo": v["type"]} for k, v in sorted(fields.items())]
    print_table(rows, ["Campo", "Label", "Tipo"])


def cmd_financeiro(odoo, args):
    from datetime import date
    mes = date.today().strftime("%Y-%m")

    # Faturas em aberto
    faturas_abertas = odoo.count("account.move", [
        ["move_type", "=", "out_invoice"],
        ["payment_state", "!=", "paid"],
        ["state", "=", "posted"],
    ])

    # Faturas vencidas
    faturas_vencidas = odoo.count("account.move", [
        ["move_type", "=", "out_invoice"],
        ["payment_state", "!=", "paid"],
        ["state", "=", "posted"],
        ["invoice_date_due", "<", str(date.today())],
    ])

    # Pedidos de venda abertos
    vendas_abertas = odoo.count("sale.order", [
        ["state", "in", ["draft", "sent", "sale"]],
    ])

    print(f"=== Resumo Financeiro ===")
    print(f"Faturas em aberto:  {faturas_abertas}")
    print(f"Faturas vencidas:   {faturas_vencidas}")
    print(f"Pedidos de venda:   {vendas_abertas}")


COMMANDS = {
    "projetos":     cmd_projetos,
    "tarefas":      cmd_tarefas,
    "busca":        cmd_busca,
    "criar-tarefa": cmd_criar_tarefa,
    "campos":       cmd_campos,
    "financeiro":   cmd_financeiro,
}

HELP = """
Uso: python odoo.py <comando> [args]

Comandos:
  projetos                          Lista projetos ativos
  tarefas <id_ou_nome>              Lista tarefas de um projeto
  busca <modelo> <campos> [filtro]  Busca generica
  criar-tarefa <proj_id> <nome> [h] Cria uma tarefa
  campos <modelo>                   Lista campos de um modelo
  financeiro                        Resumo financeiro rapido
"""

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(HELP)
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd not in COMMANDS:
        print(f"Comando desconhecido: '{cmd}'\n{HELP}")
        sys.exit(1)

    try:
        odoo = OdooClient()
        COMMANDS[cmd](odoo, args)
    except ConnectionError as e:
        print(f"Erro de conexao: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)
