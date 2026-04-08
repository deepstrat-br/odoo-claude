"""
MCP Server for Odoo — Deepstrat
Expoe o Odoo XML-RPC como tools do Model Context Protocol.
"""

import json
from datetime import date, datetime
from mcp.server.fastmcp import FastMCP
from odoo import OdooClient, Resolver

mcp = FastMCP(
    "odoo-deepstrat",
    instructions=(
        "Servidor MCP para o Odoo ERP da Deepstrat (deepstrat.odoo.com). "
        "Permite buscar, criar, atualizar e deletar registros, "
        "alem de operacoes especializadas para projetos, tarefas, CRM e financeiro. "
        "IMPORTANTE — MOEDA: A empresa Deepstrat opera no Brasil. "
        "A moeda base do Odoo é BRL (Real brasileiro, simbolo R$). "
        "Todos os valores monetarios retornados estao em BRL, salvo quando "
        "o campo 'moeda' ou 'currency_id' indicar explicitamente outra moeda. "
        "NUNCA assuma USD, EUR ou outra moeda — o padrao é SEMPRE R$ (BRL)."
    ),
)

# Conexao lazy — inicializa apenas no primeiro uso
_odoo = None
_resolver = None


def get_odoo():
    global _odoo
    if _odoo is None:
        _odoo = OdooClient()
    return _odoo


def get_resolver():
    global _resolver
    if _resolver is None:
        _resolver = Resolver(get_odoo())
    return _resolver


def serialize(obj):
    """Converte objetos nao-serializaveis para JSON."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return str(obj)


# ─── Tools genericas (CRUD) ──────────────────────────────────────────────────


@mcp.tool()
def buscar(
    modelo: str,
    filtros: list | None = None,
    campos: list[str] | None = None,
    limite: int = 20,
    ordem: str | None = None,
) -> str:
    """Busca registros no Odoo via search_read.

    Args:
        modelo: Nome do modelo Odoo (ex: 'res.partner', 'sale.order')
        filtros: Domain filters no formato Odoo [[campo, op, valor], ...]. None = sem filtro.
        campos: Lista de campos a retornar. None = todos.
        limite: Maximo de registros (default 20).
        ordem: Ordenacao (ex: 'name asc', 'date desc').
    """
    odoo = get_odoo()
    records = odoo.search(
        modelo,
        filters=filtros or [],
        fields=campos,
        limit=limite,
        order=ordem,
    )
    return json.dumps(records, default=serialize, ensure_ascii=False)


@mcp.tool()
def contar(modelo: str, filtros: list | None = None) -> int:
    """Conta registros que atendem ao filtro.

    Args:
        modelo: Nome do modelo Odoo.
        filtros: Domain filters. None = sem filtro.
    """
    return get_odoo().count(modelo, filters=filtros or [])


@mcp.tool()
def ler_registro(modelo: str, id: int, campos: list[str] | None = None) -> str:
    """Le um unico registro pelo ID.

    Args:
        modelo: Nome do modelo Odoo.
        id: ID do registro.
        campos: Lista de campos. None = todos.
    """
    record = get_odoo().get(modelo, id, fields=campos)
    if not record:
        return json.dumps({"erro": f"Registro {id} nao encontrado em {modelo}"})
    return json.dumps(record, default=serialize, ensure_ascii=False)


@mcp.tool()
def criar_registro(modelo: str, valores: dict) -> str:
    """Cria um registro no Odoo.

    Args:
        modelo: Nome do modelo Odoo.
        valores: Dicionario de campos e valores.
    """
    record_id = get_odoo().create(modelo, valores)
    return json.dumps({"id": record_id, "modelo": modelo, "status": "criado"})


@mcp.tool()
def atualizar_registro(modelo: str, id: int, valores: dict) -> str:
    """Atualiza um registro existente.

    Args:
        modelo: Nome do modelo Odoo.
        id: ID do registro.
        valores: Campos a atualizar.
    """
    get_odoo().update(modelo, id, valores)
    return json.dumps({"id": id, "modelo": modelo, "status": "atualizado"})


@mcp.tool()
def deletar_registro(modelo: str, id: int) -> str:
    """Deleta um registro.

    Args:
        modelo: Nome do modelo Odoo.
        id: ID do registro a deletar.
    """
    get_odoo().delete(modelo, id)
    return json.dumps({"id": id, "modelo": modelo, "status": "deletado"})


@mcp.tool()
def listar_campos(modelo: str) -> str:
    """Lista todos os campos de um modelo com tipo e label.

    Args:
        modelo: Nome do modelo Odoo.
    """
    fields = get_odoo().fields(modelo)
    result = {
        k: {"label": v["string"], "tipo": v["type"]}
        for k, v in sorted(fields.items())
    }
    return json.dumps(result, ensure_ascii=False)


# ─── Tools especializadas ────────────────────────────────────────────────────


@mcp.tool()
def listar_projetos() -> str:
    """Lista todos os projetos ativos com ID, nome, cliente, qtd de tarefas e prazo."""
    odoo = get_odoo()
    records = odoo.search(
        "project.project",
        filters=[["active", "=", True]],
        fields=["id", "name", "partner_id", "task_count", "date"],
        order="name asc",
    )
    rows = [
        {
            "id": r["id"],
            "nome": r["name"],
            "cliente": r["partner_id"][1] if r["partner_id"] else None,
            "tarefas": r["task_count"],
            "prazo": r["date"] or None,
        }
        for r in records
    ]
    return json.dumps(rows, default=serialize, ensure_ascii=False)


@mcp.tool()
def listar_tarefas(
    projeto: str | int,
    etapa: str | None = None,
    incluir_inativas: bool = False,
    limite: int = 50,
) -> str:
    """Lista tarefas de um projeto.

    Args:
        projeto: Nome ou ID do projeto.
        etapa: Filtrar por etapa (ex: 'Em andamento'). None = todas.
        incluir_inativas: Incluir tarefas arquivadas.
        limite: Maximo de tarefas.
    """
    r = get_resolver()
    project_id = r.project(projeto)

    filters = [["project_id", "=", project_id]]
    if incluir_inativas:
        filters.append(["active", "in", [True, False]])
    if etapa:
        filters.append(["stage_id", "=", r.stage(etapa)])

    records = get_odoo().search(
        "project.task",
        filters=filters,
        fields=["id", "name", "stage_id", "allocated_hours", "effective_hours", "user_ids", "date_deadline", "priority"],
        limit=limite,
        order="name asc",
    )
    rows = [
        {
            "id": t["id"],
            "nome": t["name"],
            "etapa": t["stage_id"][1] if t["stage_id"] else None,
            "horas_planejadas": t["allocated_hours"],
            "horas_gastas": t["effective_hours"],
            "prazo": t["date_deadline"] or None,
            "prioridade": "urgente" if t["priority"] == "1" else "normal",
        }
        for t in records
    ]
    return json.dumps(rows, default=serialize, ensure_ascii=False)


@mcp.tool()
def criar_tarefa(
    projeto: str | int,
    nome: str,
    horas: float = 0.0,
    etapa: str | None = None,
    responsaveis: list[str] | None = None,
    prazo: str | None = None,
    descricao: str | None = None,
    tags: list[str] | None = None,
    prioridade: str = "normal",
) -> str:
    """Cria uma tarefa em um projeto.

    Args:
        projeto: Nome ou ID do projeto.
        nome: Titulo da tarefa.
        horas: Horas planejadas (allocated_hours).
        etapa: Nome da etapa (ex: 'Backlog', 'Em andamento'). None = padrao do projeto.
        responsaveis: Lista de emails ou nomes dos responsaveis. None = usuario logado.
        prazo: Data limite no formato YYYY-MM-DD.
        descricao: Descricao da tarefa (HTML aceito).
        tags: Lista de nomes de tags.
        prioridade: 'normal' ou 'urgente'.
    """
    r = get_resolver()
    vals = {
        "project_id": r.project(projeto),
        "name": nome,
        "allocated_hours": horas,
        "priority": "1" if prioridade == "urgente" else "0",
    }

    if etapa:
        vals["stage_id"] = r.stage(etapa)
    if responsaveis:
        vals["user_ids"] = r.users(responsaveis)
    else:
        vals["user_ids"] = [get_odoo().uid]
    if prazo:
        vals["date_deadline"] = prazo
    if descricao:
        vals["description"] = descricao
    if tags:
        vals["tag_ids"] = r.tags(tags)

    task_id = get_odoo().create("project.task", vals)
    return json.dumps({"id": task_id, "nome": nome, "projeto": str(projeto), "status": "criada"})


@mcp.tool()
def mover_tarefa(tarefa_id: int, etapa: str) -> str:
    """Move uma tarefa para outra etapa.

    Args:
        tarefa_id: ID da tarefa.
        etapa: Nome da etapa destino (ex: 'Em andamento', 'Concluido').
    """
    r = get_resolver()
    stage_id = r.stage(etapa)
    get_odoo().update("project.task", tarefa_id, {"stage_id": stage_id})
    return json.dumps({"id": tarefa_id, "etapa": etapa, "status": "movida"})


@mcp.tool()
def resumo_financeiro() -> str:
    """Retorna resumo financeiro: faturas em aberto, vencidas e pedidos de venda."""
    odoo = get_odoo()
    hoje = str(date.today())

    faturas_abertas = odoo.count("account.move", [
        ["move_type", "=", "out_invoice"],
        ["payment_state", "!=", "paid"],
        ["state", "=", "posted"],
    ])

    faturas_vencidas = odoo.count("account.move", [
        ["move_type", "=", "out_invoice"],
        ["payment_state", "!=", "paid"],
        ["state", "=", "posted"],
        ["invoice_date_due", "<", hoje],
    ])

    vendas_abertas = odoo.count("sale.order", [
        ["state", "in", ["draft", "sent", "sale"]],
    ])

    contas_pagar = odoo.count("account.move", [
        ["move_type", "=", "in_invoice"],
        ["payment_state", "!=", "paid"],
        ["state", "=", "posted"],
    ])

    # Totais monetarios (a receber e a pagar)
    faturas_rec = odoo.search("account.move", [
        ["move_type", "=", "out_invoice"],
        ["payment_state", "!=", "paid"],
        ["state", "=", "posted"],
    ], fields=["amount_residual", "currency_id"], limit=200)
    total_receber = sum(f["amount_residual"] for f in faturas_rec)

    faturas_pag = odoo.search("account.move", [
        ["move_type", "=", "in_invoice"],
        ["payment_state", "!=", "paid"],
        ["state", "=", "posted"],
    ], fields=["amount_residual", "currency_id"], limit=200)
    total_pagar = sum(f["amount_residual"] for f in faturas_pag)

    return json.dumps({
        "data": hoje,
        "moeda": "BRL",
        "faturas_em_aberto": faturas_abertas,
        "faturas_vencidas": faturas_vencidas,
        "total_a_receber_BRL": round(total_receber, 2),
        "pedidos_venda_abertos": vendas_abertas,
        "contas_a_pagar": contas_pagar,
        "total_a_pagar_BRL": round(total_pagar, 2),
    })


@mcp.tool()
def pipeline_crm(
    etapa: str | None = None,
    responsavel: str | None = None,
    limite: int = 20,
) -> str:
    """Lista oportunidades do CRM.

    Args:
        etapa: Filtrar por etapa (ex: 'Qualificados', 'Negociacao'). None = todas.
        responsavel: Email ou nome do responsavel. None = todos.
        limite: Maximo de oportunidades.
    """
    r = get_resolver()
    filters = [["type", "=", "opportunity"]]

    if etapa:
        filters.append(["stage_id", "=", r.crm_stage(etapa)])
    if responsavel:
        user_ids = r.users([responsavel])
        filters.append(["user_id", "=", user_ids[0]])

    records = get_odoo().search(
        "crm.lead",
        filters=filters,
        fields=["id", "name", "partner_id", "stage_id", "expected_revenue", "probability", "date_deadline", "user_id", "company_currency"],
        limit=limite,
        order="expected_revenue desc",
    )

    rows = [
        {
            "id": o["id"],
            "nome": o["name"],
            "cliente": o["partner_id"][1] if o["partner_id"] else None,
            "etapa": o["stage_id"][1] if o["stage_id"] else None,
            "receita_esperada": o["expected_revenue"],
            "moeda": o["company_currency"][1] if o.get("company_currency") else "BRL",
            "probabilidade": o["probability"],
            "prazo": o["date_deadline"] or None,
            "responsavel": o["user_id"][1] if o["user_id"] else None,
        }
        for o in records
    ]
    return json.dumps(rows, default=serialize, ensure_ascii=False)


@mcp.tool()
def lancar_horas(
    projeto: str | int,
    tarefa: str | int | None = None,
    horas: float = 0.0,
    descricao: str = "",
    data: str | None = None,
    funcionario: str | int | None = None,
) -> str:
    """Lanca horas (timesheet) em um projeto/tarefa.

    Args:
        projeto: Nome ou ID do projeto.
        tarefa: Nome ou ID da tarefa. None = sem tarefa.
        horas: Quantidade de horas.
        descricao: Descricao da atividade.
        data: Data no formato YYYY-MM-DD. None = hoje.
        funcionario: Nome ou ID do funcionario. None = usuario logado.
    """
    r = get_resolver()
    odoo = get_odoo()

    project_id = r.project(projeto)
    vals = {
        "project_id": project_id,
        "unit_amount": horas,
        "name": descricao or "/",
        "date": data or str(date.today()),
    }

    if tarefa:
        if isinstance(tarefa, int):
            vals["task_id"] = tarefa
        else:
            # Busca tarefa pelo nome dentro do projeto
            tasks = odoo.search(
                "project.task",
                filters=[["project_id", "=", project_id], ["name", "ilike", tarefa]],
                fields=["id"],
                limit=1,
            )
            if not tasks:
                return json.dumps({"erro": f"Tarefa '{tarefa}' nao encontrada no projeto"})
            vals["task_id"] = tasks[0]["id"]

    if funcionario:
        emp_id = r.employee(funcionario)
        vals["employee_id"] = emp_id
    else:
        # Busca employee do usuario logado
        emps = odoo.search("hr.employee", [["user_id", "=", odoo.uid]], ["id"], limit=1)
        if emps:
            vals["employee_id"] = emps[0]["id"]

    line_id = odoo.create("account.analytic.line", vals)
    return json.dumps({"id": line_id, "horas": horas, "projeto": str(projeto), "status": "lancado"})


@mcp.tool()
def resolver_nome(modelo: str, nome: str) -> str:
    """Resolve um nome para ID no Odoo (busca exata, depois ilike).

    Args:
        modelo: Nome do modelo Odoo (ex: 'res.partner', 'product.product').
        nome: Nome a buscar.
    """
    r = get_resolver()
    record_id = r._resolve(modelo, nome)
    return json.dumps({"modelo": modelo, "nome": nome, "id": record_id})


# ─── Entrypoint ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
