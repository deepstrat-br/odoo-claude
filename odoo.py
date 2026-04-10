"""
Odoo Helper — XML-RPC client for Claude automation

Biblioteca central para acesso ao Odoo via XML-RPC.
Exporta OdooClient (operacoes CRUD), Resolver (resolucao de nomes para IDs com cache)
e load_client_config (configuracao multi-cliente via YAML).

Uso como biblioteca:
    from odoo import OdooClient, Resolver, load_client_config
    config = load_client_config("deepstrat")
    odoo = OdooClient(**config["odoo"])
    r = Resolver(odoo)

Uso como CLI:
    python odoo.py projetos
    python odoo.py --client deepstrat projetos
    python odoo.py tarefas <id_ou_nome>
    python odoo.py busca <modelo> <campos> [filtro] [limite]
    python odoo.py criar-tarefa <proj_id> "Nome" [horas]
    python odoo.py campos <modelo>
    python odoo.py financeiro

Credenciais: YAML do cliente (clients/<slug>.yaml) > variaveis de ambiente > .env.
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

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_client_config(slug=None):
    """Carrega configuracao do cliente a partir de clients/<slug>.yaml.

    Prioridade para slug: argumento > env ODOO_CLIENT > None.
    Se nenhum slug definido ou arquivo nao encontrado, retorna config
    padrao usando variaveis de ambiente (compatibilidade retroativa).

    Credenciais no YAML sao opcionais — valores vazios fazem fallback
    para as variaveis de ambiente ODOO_URL, ODOO_DB, ODOO_LOGIN, ODOO_KEY.

    Returns:
        Dict com chaves: slug, nome, moeda, odoo, activity_types, whatsapp, crm.
    """
    slug = slug or os.environ.get("ODOO_CLIENT", "")

    # Config padrao (fallback para .env puro)
    default = {
        "slug": "",
        "nome": "",
        "moeda": "",
        "odoo": {
            "url": ODOO_URL,
            "db": ODOO_DB,
            "login": ODOO_LOGIN,
            "key": ODOO_KEY,
        },
        "activity_types": {},
        "whatsapp": {},
        "crm": {},
    }

    if not slug:
        return default

    yaml_path = os.path.join(_BASE_DIR, "clients", f"{slug}.yaml")
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(
            f"Config do cliente nao encontrada: {yaml_path}"
        )

    try:
        import yaml
    except ImportError:
        raise ImportError("Dependencia ausente: pip install pyyaml")

    with open(yaml_path) as f:
        data = yaml.safe_load(f) or {}

    odoo_cfg = data.get("odoo", {})
    config = {
        "slug": data.get("slug", slug),
        "nome": data.get("nome", slug),
        "moeda": data.get("moeda", ""),
        "odoo": {
            "url": odoo_cfg.get("url") or ODOO_URL,
            "db": odoo_cfg.get("db") or ODOO_DB,
            "login": odoo_cfg.get("login") or ODOO_LOGIN,
            "key": odoo_cfg.get("key") or ODOO_KEY,
        },
        "activity_types": data.get("activity_types", {}),
        "whatsapp": data.get("whatsapp", {}),
        "crm": data.get("crm", {}),
    }
    return config


class OdooClient:
    """Cliente XML-RPC para o Odoo ERP.

    Encapsula as chamadas execute_kw da API XML-RPC do Odoo com metodos
    de alto nivel para search_read, read, create, write e unlink.

    Aceita credenciais explicitas ou faz fallback para variaveis de ambiente
    ODOO_URL, ODOO_DB, ODOO_LOGIN e ODOO_KEY (carregadas do .env).

    Attributes:
        uid: ID do usuario autenticado (int). Disponivel apos __init__.
    """

    def __init__(self, url=None, db=None, login=None, key=None):
        url = url or ODOO_URL
        db = db or ODOO_DB
        login = login or ODOO_LOGIN
        key = key or ODOO_KEY

        if not all([url, db, login, key]):
            raise ConnectionError(
                "Credenciais incompletas. Configure via clients/<slug>.yaml ou .env."
            )

        self._db = db
        self._key = key
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        self.uid = common.authenticate(db, login, key, {})
        if not self.uid:
            raise ConnectionError("Falha na autenticacao. Verifique as credenciais.")
        self._models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    def _call(self, model, method, args, kwargs=None):
        """Chama execute_kw diretamente. Use para metodos nao cobertos pela API publica."""
        return self._models.execute_kw(
            self._db, self.uid, self._key, model, method, args, kwargs or {}
        )

    def search(self, model, filters=None, fields=None, limit=80, order=None):
        """Busca registros com search_read.

        Args:
            model: Modelo Odoo (ex: 'res.partner').
            filters: Domain Odoo [[campo, op, valor], ...]. None = sem filtro.
            fields: Campos a retornar. None = todos.
            limit: Maximo de registros (default 80).
            order: Ordenacao SQL (ex: 'name asc').

        Returns:
            Lista de dicionarios com os registros encontrados.
        """
        kwargs = {"limit": limit}
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order
        return self._call(model, "search_read", [filters or []], kwargs)

    def count(self, model, filters=None):
        """Conta registros sem retornar dados. Mais eficiente que len(search(...)).

        Returns:
            Inteiro com o total de registros que atendem ao filtro.
        """
        return self._call(model, "search_count", [filters or []])

    def get(self, model, record_id, fields=None):
        """Le um unico registro pelo ID.

        Returns:
            Dicionario do registro, ou None se nao encontrado.
        """
        kwargs = {}
        if fields:
            kwargs["fields"] = fields
        result = self._call(model, "read", [[record_id]], kwargs)
        return result[0] if result else None

    def create(self, model, values):
        """Cria um registro e retorna o ID criado (int)."""
        return self._call(model, "create", [values])

    def update(self, model, record_id, values):
        """Atualiza campos de um registro existente (write parcial). Retorna True."""
        return self._call(model, "write", [[record_id], values])

    def delete(self, model, record_id):
        """Deleta permanentemente um registro (unlink). Acao irreversivel. Retorna True."""
        return self._call(model, "unlink", [[record_id]])

    def fields(self, model):
        """Retorna metadados dos campos do modelo: {campo: {string, type}}."""
        return self._call(model, "fields_get", [], {"attributes": ["string", "type"]})


# ─── Resolver ─────────────────────────────────────────────────────────────────

def coerce_id(value):
    """Converte valor para int se possivel, senao retorna None."""
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


class Resolver:
    """Resolve nomes para IDs no Odoo com cache por sessao.

    Aceita nome (str) ou ID (int) em todos os metodos — se for ID, retorna direto sem consultar.
    Busca primeiro por correspondencia exata ('='), depois por ilike como fallback.
    Resultados sao cacheados para evitar chamadas repetidas na mesma sessao.

    Uso:
        from odoo import OdooClient, Resolver
        odoo = OdooClient()
        r = Resolver(odoo)

        r.project("Meu Projeto")                    # project.project -> int
        r.stage("Backlog")                          # project.task.type -> int
        r.milestone(project_id, "Marco 1")          # project.milestone -> int
        r.tags(["CRM", "Vendas"])                   # project.tags -> [(6, 0, [ids])]
        r.users(["user@deepstrat.com.br"])          # res.users -> [int]
        r.partner("Nome do Cliente")                # res.partner -> int
        r.product("Service on Timesheets")          # product.product -> int
        r.uom("Hours")                              # uom.uom -> int
        r.analytic_distribution({"Proj X": 100.0}) # -> {str(id): float}
        r.crm_stage("Qualificados")                 # crm.stage -> int
        r.employee("Nome do Funcionario")           # hr.employee -> int
    """

    def __init__(self, odoo):
        self.odoo = odoo
        self._cache = {}

    def _resolve(self, model, name_or_id, extra_domain=None):
        """Busca ID de um registro pelo nome com cache. Tenta '=' exato, depois 'ilike'.

        Raises:
            ValueError: Se o nome nao for encontrado no modelo.
        """
        id_ = coerce_id(name_or_id)
        if id_:
            return id_
        key = (model, str(name_or_id), str(extra_domain))
        if key not in self._cache:
            domain = [['name', '=', name_or_id]] + (extra_domain or [])
            r = self.odoo.search(model, domain, ['id'], limit=1)
            if not r:
                domain[0][1] = 'ilike'
                r = self.odoo.search(model, domain, ['id'], limit=1)
            if not r:
                raise ValueError(f"{model}: '{name_or_id}' nao encontrado")
            self._cache[key] = r[0]['id']
        return self._cache[key]

    # ── Projetos ──────────────────────────────────────────────────────────────
    def project(self, name_or_id):
        """Resolve nome ou ID de projeto (project.project) -> int."""
        return self._resolve('project.project', name_or_id)

    def stage(self, name_or_id):
        """Resolve etapa de tarefa (project.task.type) -> int. Escopo global no Odoo."""
        if name_or_id is None:
            return None
        return self._resolve('project.task.type', name_or_id)

    def milestone(self, project_id, name_or_id):
        """Resolve marco de projeto (project.milestone) filtrado pelo project_id -> int."""
        if name_or_id is None:
            return None
        return self._resolve('project.milestone', name_or_id, [['project_id', '=', project_id]])

    def tags(self, names):
        """Resolve lista de nomes de tags (project.tags) -> [(6, 0, [ids])] para campo many2many."""
        if not names:
            return [(6, 0, [])]
        return [(6, 0, [self._resolve('project.tags', n) for n in names])]

    def users(self, names_or_ids):
        """Resolve lista de emails ou nomes de usuarios (res.users) -> [int].

        Busca primeiro por login (email exato), depois por nome ilike.
        """
        if not names_or_ids:
            return []
        result = []
        for n in names_or_ids:
            id_ = coerce_id(n)
            if id_:
                result.append(id_)
                continue
            key = ('res.users:login', str(n))
            if key not in self._cache:
                r = self.odoo.search('res.users', [['login', '=', n]], ['id'], limit=1)
                if not r:
                    r = self.odoo.search('res.users', [['name', 'ilike', n]], ['id'], limit=1)
                if not r:
                    raise ValueError(f"res.users: '{n}' nao encontrado")
                self._cache[key] = r[0]['id']
            result.append(self._cache[key])
        return result

    # ── Compras / Vendas / Financeiro ─────────────────────────────────────────
    def partner(self, name_or_id):
        """Resolve nome ou ID de parceiro/cliente/fornecedor (res.partner) -> int."""
        return self._resolve('res.partner', name_or_id)

    def product(self, name_or_id):
        """Resolve nome ou ID de produto (product.product) -> int."""
        return self._resolve('product.product', name_or_id)

    def uom(self, name_or_id):
        """Resolve unidade de medida (uom.uom) -> int. Ex: 'Hours', 'Units'."""
        if name_or_id is None:
            return None
        return self._resolve('uom.uom', name_or_id)

    def analytic_distribution(self, analytic_dict):
        """Converte {nome_ou_id: pct} -> {str(id): float} para o campo analytic_distribution.

        Valida que os percentuais somam exatamente 100%.

        Raises:
            ValueError: Se a soma dos percentuais diferir de 100%.
        """
        if not analytic_dict:
            return {}
        result = {
            str(self._resolve('account.analytic.account', k)): float(v)
            for k, v in analytic_dict.items()
        }
        total = sum(result.values())
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"analytic_distribution soma {total:.1f}% (esperado 100%)")
        return result

    # ── CRM ───────────────────────────────────────────────────────────────────
    def crm_stage(self, name_or_id):
        """Resolve etapa do CRM (crm.stage) -> int. Ex: 'Qualificados', 'Negociacao'."""
        if name_or_id is None:
            return None
        return self._resolve('crm.stage', name_or_id)

    # ── RH ────────────────────────────────────────────────────────────────────
    def employee(self, name_or_id):
        """Resolve nome ou ID de funcionario (hr.employee) -> int."""
        return self._resolve('hr.employee', name_or_id)


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
Uso: python odoo.py [--client <slug>] <comando> [args]

Opcoes:
  --client <slug>   Carrega config de clients/<slug>.yaml (ou use ODOO_CLIENT env)

Comandos:
  projetos                          Lista projetos ativos
  tarefas <id_ou_nome>              Lista tarefas de um projeto
  busca <modelo> <campos> [filtro]  Busca generica
  criar-tarefa <proj_id> <nome> [h] Cria uma tarefa
  campos <modelo>                   Lista campos de um modelo
  financeiro                        Resumo financeiro rapido
"""

if __name__ == "__main__":
    argv = sys.argv[1:]

    # Extrair --client flag
    client_slug = None
    if len(argv) >= 2 and argv[0] == "--client":
        client_slug = argv[1]
        argv = argv[2:]

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(HELP)
        sys.exit(0)

    cmd = argv[0]
    args = argv[1:]

    if cmd not in COMMANDS:
        print(f"Comando desconhecido: '{cmd}'\n{HELP}")
        sys.exit(1)

    try:
        config = load_client_config(client_slug)
        c = config["odoo"]
        odoo = OdooClient(url=c["url"], db=c["db"], login=c["login"], key=c["key"])
        COMMANDS[cmd](odoo, args)
    except ConnectionError as e:
        print(f"Erro de conexao: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)
