"""
MCP Server for Odoo — Deepstrat

Expoe o Odoo ERP (deepstrat.odoo.com) via XML-RPC como ferramentas MCP.

Tools genericas (CRUD): buscar, contar, ler_registro, criar_registro,
    atualizar_registro, deletar_registro, listar_campos.
Tools especializadas: listar_projetos, listar_tarefas, criar_tarefa, mover_tarefa,
    lancar_horas, resumo_financeiro, pipeline_crm, resolver_nome.
Tools de CRM/leads: leads_pendentes_qualificacao, qualificar_lead.
Tools de WhatsApp: listar_templates_whatsapp, preview_whatsapp, enviar_whatsapp.
Tools de Relatorios: gerar_dre.

MOEDA PADRAO: Todos os valores monetarios estao em BRL (Real brasileiro).
Nunca assuma USD, EUR ou outra moeda — o padrao e sempre R$.
"""

import json
import re
from datetime import date, datetime
from mcp.server.fastmcp import FastMCP
from odoo import OdooClient, Resolver

mcp = FastMCP(
    "MCP Server for Odoo - by Deepstrat",
    instructions=(
        "Servidor MCP para o Odoo ERP da Deepstrat (deepstrat.odoo.com). "
        "Permite buscar, criar, atualizar e deletar registros, "
        "alem de operacoes especializadas para projetos, tarefas, CRM, financeiro e WhatsApp. "
        "IMPORTANTE — MOEDA: A empresa Deepstrat opera no Brasil. "
        "A moeda base do Odoo é BRL (Real brasileiro, simbolo R$). "
        "Todos os valores monetarios retornados estao em BRL, salvo quando "
        "o campo 'moeda' ou 'currency_id' indicar explicitamente outra moeda. "
        "NUNCA assuma USD, EUR ou outra moeda — o padrao é SEMPRE R$ (BRL). "
        "QUALIFICACAO DE LEADS: Use leads_pendentes_qualificacao() para obter leads novos "
        "e a metodologia de qualificacao. Pesquise cada empresa online e use qualificar_lead() "
        "para aplicar. Para leads com prioridade 3, crie atividade de ligacao."
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
    """Busca multiplos registros no Odoo com filtros. Use ler_registro() para buscar um unico ID.

    Returns JSON array com os registros encontrados.
    Campos many2one retornam [id, "nome"]; use [0] para ID e [1] para nome.

    Args:
        modelo: Modelo Odoo (ex: 'res.partner', 'sale.order', 'project.task').
        filtros: Domain Odoo [[campo, operador, valor], ...].
                 Operadores: '=', '!=', '>', '<', '>=', '<=', 'in', 'not in', 'ilike', 'like'.
                 Ex: [["state", "=", "posted"], ["amount_total", ">", 1000]].
                 None = sem filtro (retorna ate o limite).
        campos: Campos a incluir. None = todos (pode ser volumoso — prefira listar apenas o necessario).
                Ex: ["id", "name", "email_from", "stage_id"].
        limite: Maximo de registros (default 20; use ate 200 para lotes).
        ordem: Ordenacao SQL. Ex: 'name asc', 'create_date desc'.
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
    """Conta registros que atendem ao filtro, sem retornar os dados. Mais rapido que buscar().

    Use quando precisar apenas da quantidade (ex: quantas faturas em aberto?).

    Returns inteiro com o total de registros.

    Args:
        modelo: Modelo Odoo.
        filtros: Domain Odoo. None = contar todos. Ex: [["state", "=", "posted"]].
    """
    return get_odoo().count(modelo, filters=filtros or [])


@mcp.tool()
def ler_registro(modelo: str, id: int, campos: list[str] | None = None) -> str:
    """Le um unico registro pelo ID. Mais eficiente que buscar() para registros individuais.

    Returns JSON do registro, ou {"erro": "..."} se nao encontrado.

    Args:
        modelo: Modelo Odoo.
        id: ID do registro.
        campos: Campos a retornar. None = todos.
    """
    record = get_odoo().get(modelo, id, fields=campos)
    if not record:
        return json.dumps({"erro": f"Registro {id} nao encontrado em {modelo}"})
    return json.dumps(record, default=serialize, ensure_ascii=False)


@mcp.tool()
def criar_registro(modelo: str, valores: dict) -> str:
    """Cria um novo registro no Odoo. Para tarefas de projeto, prefira criar_tarefa() (mais ergonomico).

    Returns JSON {"id": <novo_id>, "modelo": ..., "status": "criado"}.

    ATENCAO: Alguns modelos exigem campos obrigatorios. Use listar_campos() para verificar
    ou consulte a documentacao do modelo antes de criar.

    Args:
        modelo: Modelo Odoo.
        valores: Campos e valores do registro.
                 Campos many2one aceitam ID inteiro (ex: "project_id": 9).
                 Many2many usam comandos Odoo: [(6, 0, [ids])] para substituir lista.
                 Ex: {"name": "Nova Tarefa", "project_id": 9, "user_ids": [2]}.
    """
    record_id = get_odoo().create(modelo, valores)
    return json.dumps({"id": record_id, "modelo": modelo, "status": "criado"})


@mcp.tool()
def atualizar_registro(modelo: str, id: int, valores: dict) -> str:
    """Atualiza campos de um registro existente no Odoo (update parcial).

    Returns JSON {"id": ..., "modelo": ..., "status": "atualizado"}.

    Args:
        modelo: Modelo Odoo.
        id: ID do registro.
        valores: Apenas os campos a modificar — nao precisa enviar todos os campos.
                 Ex: {"priority": "1"} para marcar como urgente.
    """
    get_odoo().update(modelo, id, valores)
    return json.dumps({"id": id, "modelo": modelo, "status": "atualizado"})


@mcp.tool()
def deletar_registro(modelo: str, id: int) -> str:
    """DESTRUTIVO — Deleta permanentemente um registro do Odoo. Acao irreversivel.

    Confirme com o usuario antes de executar.
    Para tarefas e leads, prefira arquivar (atualizar_registro com {"active": False})
    em vez de deletar, pois preserva o historico.

    Returns JSON {"id": ..., "modelo": ..., "status": "deletado"}.

    Args:
        modelo: Modelo Odoo.
        id: ID do registro a deletar permanentemente.
    """
    get_odoo().delete(modelo, id)
    return json.dumps({"id": id, "modelo": modelo, "status": "deletado"})


@mcp.tool()
def listar_campos(modelo: str) -> str:
    """Lista todos os campos de um modelo com nome tecnico, label em portugues e tipo.

    Use antes de criar/atualizar registros para conhecer campos disponiveis.
    Returns JSON objeto {campo: {label, tipo}} ordenado alfabeticamente.
    Tipos comuns: char, text, integer, float, boolean, date, datetime,
                  many2one, many2many, one2many, selection.

    Args:
        modelo: Modelo Odoo (ex: 'sale.order', 'crm.lead', 'project.task').
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
    """Lista todos os projetos ativos com ID, nome, cliente, total de tarefas e prazo.

    Retorna apenas projetos com active=True. Para projetos arquivados,
    use buscar('project.project', [['active', '=', False]]).

    Returns JSON array [{id, nome, cliente, tarefas, prazo}, ...] ordenado por nome.
    """
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
    """Lista tarefas de um projeto com etapa, horas planejadas/gastas, prazo e prioridade.

    Returns JSON array [{id, nome, etapa, horas_planejadas, horas_gastas, prazo, prioridade}, ...].

    Args:
        projeto: Nome ou ID do projeto (ex: 'Projeto Interno' ou 9).
        etapa: Nome exato da etapa para filtrar (ex: 'Em andamento', 'Backlog'). None = todas.
        incluir_inativas: True para incluir tarefas arquivadas. Default False.
        limite: Maximo de tarefas a retornar (default 50).
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
    """Cria uma tarefa em um projeto. Prefira esta tool a criar_registro() — faz resolucao de nomes automaticamente.

    Returns JSON {"id": <novo_id>, "nome", "projeto", "status": "criada"}.

    Args:
        projeto: Nome ou ID do projeto (ex: 'Projeto Interno' ou 9).
        nome: Titulo da tarefa.
        horas: Horas planejadas em allocated_hours (ex: 2.5 = 2h30min). Default 0.
        etapa: Nome da etapa (ex: 'Backlog', 'A fazer', 'Em andamento'). None = etapa padrao do projeto.
        responsaveis: Lista de emails ou nomes (ex: ['vagner@deepstrat.com.br']). None = usuario logado.
        prazo: Data limite no formato YYYY-MM-DD.
        descricao: Descricao da tarefa (HTML aceito ou texto simples).
        tags: Lista de nomes de tags existentes (ex: ['CRM', 'Vendas']).
        prioridade: 'normal' (default) ou 'urgente'.
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
    """Move uma tarefa para outra etapa. Equivale a arrastar o card no Kanban.

    Returns JSON {"id": ..., "etapa": ..., "status": "movida"}.

    Args:
        tarefa_id: ID da tarefa.
        etapa: Nome exato da etapa destino (ex: 'Em andamento', 'Concluido', 'Cancelado').
    """
    r = get_resolver()
    stage_id = r.stage(etapa)
    get_odoo().update("project.task", tarefa_id, {"stage_id": stage_id})
    return json.dumps({"id": tarefa_id, "etapa": etapa, "status": "movida"})


@mcp.tool()
def resumo_financeiro() -> str:
    """Retorna painel financeiro: faturas a receber/vencidas, contas a pagar e pedidos de venda abertos.

    Todos os valores monetarios estao em BRL (Real brasileiro).

    Returns JSON {data, moeda, faturas_em_aberto, faturas_vencidas, total_a_receber_BRL,
                  pedidos_venda_abertos, contas_a_pagar, total_a_pagar_BRL}.
    """
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
    """Lista oportunidades do CRM com receita esperada, probabilidade e etapa.

    Use leads_pendentes_qualificacao() para ver leads novos nao qualificados.
    Valores monetarios em BRL.

    Returns JSON array [{id, nome, cliente, etapa, receita_esperada, moeda,
                        probabilidade, prazo, responsavel}, ...] ordenado por receita desc.

    Args:
        etapa: Nome da etapa CRM (ex: 'Qualificados', 'Negociacao', 'Won'). None = todas.
        responsavel: Email ou nome do responsavel. None = todos os responsaveis.
        limite: Maximo de oportunidades (default 20).
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
    """Lanca uma entrada de timesheet (account.analytic.line) em um projeto ou tarefa.

    Returns JSON {"id": <id_da_linha>, "horas", "projeto", "status": "lancado"}.

    Args:
        projeto: Nome ou ID do projeto.
        tarefa: Nome ou ID da tarefa dentro do projeto. None = timesheet sem tarefa especifica.
        horas: Horas a lancar (ex: 1.5 = 1h30min).
        descricao: Descricao da atividade realizada.
        data: Data no formato YYYY-MM-DD. None = data de hoje.
        funcionario: Nome ou ID do funcionario. None = funcionario do usuario logado.
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
    """Resolve um nome textual para ID numerico no Odoo (busca exata, depois ilike).

    Use para descobrir IDs antes de usa-los em filtros ou campos de outros modelos.

    Returns JSON {"modelo", "nome", "id"}.

    Args:
        modelo: Modelo Odoo (ex: 'res.partner', 'product.product', 'project.task.type').
        nome: Nome a buscar. Aceita nome parcial via ilike como fallback.
    """
    r = get_resolver()
    record_id = r._resolve(modelo, nome)
    return json.dumps({"modelo": modelo, "nome": nome, "id": record_id})


# ─── Qualificacao de Leads ───────────────────────────────────────────────────

# Metodologia completa em docs/qualificacao-leads.md
_METODOLOGIA_RESUMO = (
    "METODOLOGIA DE QUALIFICACAO:\n"
    "1. Para cada lead, pesquise a empresa online (Google, Instagram, site, CNPJ).\n"
    "2. Analise sinais: site proprio (+), email corporativo (+), presenca digital (+), "
    "email .edu.br (-), nome sem sentido (-), telefone incompleto (-).\n"
    "3. Classifique: 3=empresa real confirmada com necessidade ERP, "
    "2=provavelmente real mas sem confirmacao, 1=pouca info/micro, 0=spam/bot/academico.\n"
    "4. Atualize: capitalizar nomes, preencher empresa, adicionar pesquisa na descricao, "
    "definir prioridade, adicionar website se encontrado.\n"
    "5. Para leads prioridade 3: enviar WhatsApp de abordagem (auto) + criar atividade Call.\n"
    "   Para leads prioridade 2: criar atividade de revisao manual (To Do).\n"
    "6. Titulo padrao: 'Lead Odoo: Nome do Contato — Empresa'.\n"
    "Detalhes completos: docs/qualificacao-leads.md"
)


@mcp.tool()
def leads_pendentes_qualificacao(limite: int = 30) -> str:
    """Retorna leads novos nao qualificados (stage=Novos, priority=0, sem pesquisa na descricao).

    Inclui a metodologia de qualificacao na resposta para guiar o processo.
    Apos obter a lista, pesquise cada empresa online e chame qualificar_lead() para cada um.

    Returns JSON {total_pendentes, leads: [{id, nome_lead, contato, empresa_informada,
                  telefone, email, website, cidade, estado, criado_em, descricao_raw}],
                  metodologia}.

    Args:
        limite: Maximo de leads a retornar (default 30).
    """
    odoo = get_odoo()
    records = odoo.search(
        "crm.lead",
        filters=[
            ["type", "=", "lead"],
            ["priority", "=", "0"],
            ["stage_id.name", "=", "Novos"],
        ],
        fields=[
            "id", "name", "contact_name", "partner_name",
            "phone", "email_from", "website",
            "description", "city", "state_id", "country_id",
            "create_date",
        ],
        limit=limite,
        order="create_date desc",
    )

    # Filtrar apenas leads sem pesquisa na descricao
    pendentes = []
    for r in records:
        desc = r.get("description") or ""
        if "<b>Pesquisa:</b>" not in desc:
            # Extrair "Company:" da descricao se existir
            company = ""
            if "Company:" in desc:
                try:
                    company = desc.split("Company:")[1].split("<")[0].strip()
                except (IndexError, AttributeError):
                    pass
            pendentes.append({
                "id": r["id"],
                "nome_lead": r["name"],
                "contato": r["contact_name"] or "",
                "empresa_informada": r["partner_name"] or company or "",
                "telefone": r["phone"] or "",
                "email": r["email_from"] or "",
                "website": r["website"] or "",
                "cidade": r["city"] or "",
                "estado": r["state_id"][1] if r["state_id"] else "",
                "criado_em": r["create_date"],
                "descricao_raw": desc,
            })

    return json.dumps({
        "total_pendentes": len(pendentes),
        "leads": pendentes,
        "metodologia": _METODOLOGIA_RESUMO,
    }, default=serialize, ensure_ascii=False)


@mcp.tool()
def qualificar_lead(
    lead_id: int,
    prioridade: int,
    nome_contato: str | None = None,
    empresa: str | None = None,
    titulo: str | None = None,
    pesquisa: str = "",
    potencial: str = "",
    website: str | None = None,
    nota_atividade: str | None = None,
) -> str:
    """Aplica qualificacao em um lead: atualiza prioridade, nomes, pesquisa e executa acoes automaticas.

    Acoes automaticas por nivel de prioridade:
    - 3 (alto): envia WhatsApp template 17 (Abordagem Leads) + cria atividade Call para hoje.
    - 2 (medio): cria atividade To Do de revisao para hoje.
    - 0-1: apenas atualiza dados, sem acao adicional.

    Returns JSON {id, prioridade, status, atividade_id?, atividade?, whatsapp?}.

    Args:
        lead_id: ID do lead (crm.lead).
        prioridade: 0=spam/bot, 1=micro/pouca info, 2=medio potencial, 3=alto potencial confirmado.
        nome_contato: Nome do contato em Title Case. None = manter atual.
        empresa: Nome da empresa em Title Case. None = manter atual.
        titulo: Titulo do lead. None = gerar automaticamente como 'Lead Odoo: Nome — Empresa'.
        pesquisa: Texto resumindo a pesquisa online sobre a empresa (salvo na descricao do lead).
        potencial: Avaliacao curta do potencial (ex: 'Alto. E-commerce com produto real.').
        website: URL do site encontrado na pesquisa. None = nao alterar.
        nota_atividade: HTML para a nota da atividade criada. Recomendado para prioridade 2 e 3.
    """
    odoo = get_odoo()

    # Buscar lead atual
    lead = odoo.get("crm.lead", lead_id,
                     fields=["id", "description", "contact_name", "partner_name", "phone"])
    if not lead:
        return json.dumps({"erro": f"Lead {lead_id} nao encontrado"})

    vals = {"priority": str(prioridade)}

    if nome_contato:
        vals["contact_name"] = nome_contato
    if empresa:
        vals["partner_name"] = empresa

    # Gerar titulo automaticamente se nao fornecido
    if titulo:
        vals["name"] = titulo
    else:
        nome = nome_contato or lead.get("contact_name") or ""
        emp = empresa or lead.get("partner_name") or ""
        if nome and emp:
            vals["name"] = f"Lead Odoo: {nome} \u2014 {emp}"
        elif nome:
            vals["name"] = f"Lead Odoo: {nome}"

    # Montar descricao com pesquisa
    if pesquisa:
        desc_atual = lead.get("description") or ""
        # Preservar Source/Company original
        source_block = ""
        if "Source:" in desc_atual:
            try:
                source_block = desc_atual.split("</p>")[0] + "</p>"
            except (IndexError, AttributeError):
                source_block = desc_atual

        desc_nova = source_block
        desc_nova += f"<p><b>Pesquisa:</b> {pesquisa}</p>"
        if potencial:
            desc_nova += f"<p><b>Potencial:</b> {potencial}</p>"
        vals["description"] = desc_nova

    if website:
        vals["website"] = website

    odoo.update("crm.lead", lead_id, vals)

    resultado = {
        "id": lead_id,
        "prioridade": prioridade,
        "status": "qualificado",
    }

    nome_display = nome_contato or lead.get("contact_name") or ""
    emp_display = empresa or lead.get("partner_name") or ""

    # Buscar model_id de crm.lead (cacheado internamente pelo Odoo)
    model_rec = odoo.search("ir.model", [["model", "=", "crm.lead"]], ["id"], limit=1)
    model_id = model_rec[0]["id"] if model_rec else 618

    # === PRIORIDADE 3: WhatsApp automatico + atividade Call ===
    if prioridade >= 3:
        # 1) Enviar WhatsApp de abordagem (template 17 = "Abordagem Leads enviados pela Odoo")
        phone = lead.get("phone") or ""
        if phone and len(phone.replace(" ", "").replace("-", "").replace("+", "")) >= 12:
            try:
                composer_vals = {
                    "wa_template_id": 17,
                    "res_model": "crm.lead",
                    "res_ids": str([lead_id]),
                }
                context = {"active_model": "crm.lead", "active_ids": [lead_id]}
                composer_id = odoo._call(
                    "whatsapp.composer", "create",
                    [composer_vals], {"context": context},
                )
                odoo._call(
                    "whatsapp.composer", "action_send_whatsapp_template",
                    [[composer_id]], {"context": context},
                )
                resultado["whatsapp"] = f"Enviado para {phone}"
            except Exception as e:
                resultado["whatsapp_erro"] = str(e)
        else:
            resultado["whatsapp"] = f"Nao enviado — telefone invalido ou incompleto: {phone}"

        # 2) Criar atividade Call
        act_vals = {
            "res_model_id": model_id,
            "res_model": "crm.lead",
            "res_id": lead_id,
            "activity_type_id": 2,  # Call
            "summary": f"Ligar para {nome_display} ({emp_display})",
            "date_deadline": str(date.today()),
            "user_id": odoo.uid,
        }
        if nota_atividade:
            act_vals["note"] = nota_atividade

        act_id = odoo.create("mail.activity", act_vals)
        resultado["atividade_id"] = act_id
        resultado["atividade"] = f"Call agendada: {nome_display} ({emp_display})"

    # === PRIORIDADE 2: atividade de revisao manual ===
    elif prioridade == 2:
        note = nota_atividade or (
            f"<p>Lead qualificado automaticamente com prioridade 2 (media).</p>"
            f"<p><b>Empresa:</b> {emp_display}</p>"
            f"<p><b>Pesquisa:</b> {pesquisa[:300]}{'...' if len(pesquisa) > 300 else ''}</p>"
            f"<p><b>Decisao necessaria:</b> Avaliar se vale abordar via WhatsApp/ligacao "
            f"ou arquivar o lead.</p>"
        )
        act_vals = {
            "res_model_id": model_id,
            "res_model": "crm.lead",
            "res_id": lead_id,
            "activity_type_id": 4,  # To Do
            "summary": f"Revisar lead: {nome_display} ({emp_display})",
            "date_deadline": str(date.today()),
            "user_id": odoo.uid,
            "note": note,
        }
        act_id = odoo.create("mail.activity", act_vals)
        resultado["atividade_id"] = act_id
        resultado["atividade"] = f"Revisao agendada: {nome_display} ({emp_display})"

    return json.dumps(resultado, default=serialize, ensure_ascii=False)


# ─── WhatsApp ────────────────────────────────────────────────────────────────


@mcp.tool()
def listar_templates_whatsapp(
    modelo: str | None = None,
    apenas_aprovados: bool = True,
) -> str:
    """Lista templates de WhatsApp com corpo, variaveis e modelo vinculado.

    Use antes de enviar_whatsapp() ou preview_whatsapp() para obter o template_id correto.

    Returns JSON array [{id, nome, template_name, modelo, corpo, header, footer, conta,
                        variaveis: [{placeholder, tipo, campo, exemplo}]}, ...].
    Variaveis tipo 'field' sao preenchidas automaticamente; tipo 'free_text' devem ser passadas manualmente.

    Args:
        modelo: Filtrar por modelo Odoo vinculado (ex: 'crm.lead', 'account.move'). None = todos.
        apenas_aprovados: True (default) retorna apenas templates aprovados pelo Meta/WhatsApp.
    """
    odoo = get_odoo()
    filters = []
    if apenas_aprovados:
        filters.append(["status", "=", "approved"])
    if modelo:
        filters.append(["model", "=", modelo])

    templates = odoo.search(
        "whatsapp.template",
        filters=filters,
        fields=[
            "id", "name", "template_name", "status", "body",
            "header_type", "header_text", "footer_text",
            "template_type", "model", "phone_field",
            "variable_ids", "wa_account_id",
        ],
        limit=50,
        order="name asc",
    )

    # Enriquecer com info das variaveis
    all_var_ids = []
    for t in templates:
        all_var_ids.extend(t["variable_ids"])

    vars_map = {}
    if all_var_ids:
        variables = odoo.search(
            "whatsapp.template.variable",
            filters=[["id", "in", all_var_ids]],
            fields=["id", "name", "line_type", "field_type", "field_name", "demo_value", "wa_template_id"],
            limit=200,
        )
        for v in variables:
            tmpl_id = v["wa_template_id"][0]
            vars_map.setdefault(tmpl_id, []).append({
                "placeholder": v["name"],
                "tipo": v["field_type"],
                "campo": v["field_name"] or None,
                "exemplo": v["demo_value"] or None,
            })

    rows = []
    for t in templates:
        rows.append({
            "id": t["id"],
            "nome": t["name"],
            "template_name": t["template_name"],
            "modelo": t["model"],
            "corpo": t["body"],
            "header": t["header_text"] or None,
            "footer": t["footer_text"] or None,
            "conta": t["wa_account_id"][1] if t["wa_account_id"] else None,
            "variaveis": vars_map.get(t["id"], []),
        })

    return json.dumps(rows, default=serialize, ensure_ascii=False)


@mcp.tool()
def enviar_whatsapp(
    template_id: int,
    registro_id: int,
    telefone: str | None = None,
    textos_livres: dict[str, str] | None = None,
) -> str:
    """ACAO REAL — Envia mensagem WhatsApp via template aprovado. Acao irreversivel.

    SEMPRE use preview_whatsapp() primeiro para confirmar o conteudo da mensagem.
    SEMPRE confirme com o usuario antes de executar este envio.

    Variaveis tipo 'field' sao preenchidas automaticamente a partir do registro.
    Variaveis tipo 'free_text' devem ser passadas via textos_livres.

    Returns JSON {status, template, modelo, registro_id, mensagem_id, telefone, estado}.

    Args:
        template_id: ID do template (use listar_templates_whatsapp() para listar disponiveis).
        registro_id: ID do registro no modelo vinculado ao template (ex: ID do crm.lead).
        telefone: Telefone em formato internacional (ex: '+5541999999999'). None = usa o do registro.
        textos_livres: Valores para variaveis free_text, ex: {"1": "Joao", "2": "14:00"}.
                       As chaves sao os numeros das variaveis sem as chaves duplas.
    """
    odoo = get_odoo()

    # Buscar o template para saber o modelo vinculado
    template = odoo.get("whatsapp.template", template_id,
                        fields=["model", "status", "name"])
    if not template:
        return json.dumps({"erro": f"Template {template_id} nao encontrado"})
    if template["status"] != "approved":
        return json.dumps({"erro": f"Template '{template['name']}' nao esta aprovado (status: {template['status']})"})

    res_model = template["model"]

    # Verificar se o registro existe
    record = odoo.get(res_model, registro_id, fields=["id"])
    if not record:
        return json.dumps({"erro": f"Registro {registro_id} nao encontrado em {res_model}"})

    # Montar valores do composer
    composer_vals = {
        "wa_template_id": template_id,
        "res_model": res_model,
        "res_ids": str([registro_id]),
    }
    if telefone:
        composer_vals["phone"] = telefone

    # Preencher textos livres
    if textos_livres:
        for key, value in textos_livres.items():
            field_name = f"free_text_{key}"
            composer_vals[field_name] = value

    context = {
        "active_model": res_model,
        "active_ids": [registro_id],
    }

    # Criar o composer
    composer_id = odoo._call(
        "whatsapp.composer", "create",
        [composer_vals],
        {"context": context},
    )

    # Enviar
    try:
        result = odoo._call(
            "whatsapp.composer", "action_send_whatsapp_template",
            [[composer_id]],
            {"context": context},
        )
    except Exception as e:
        return json.dumps({"erro": f"Falha ao enviar: {str(e)}", "composer_id": composer_id})

    # Buscar a mensagem criada para confirmar
    msgs = odoo.search(
        "whatsapp.message",
        filters=[["create_uid", "=", odoo.uid]],
        fields=["id", "mobile_number", "state", "wa_template_id"],
        limit=1,
        order="id desc",
    )

    msg_info = msgs[0] if msgs else {}

    return json.dumps({
        "status": "enviado",
        "template": template["name"],
        "modelo": res_model,
        "registro_id": registro_id,
        "mensagem_id": msg_info.get("id"),
        "telefone": msg_info.get("mobile_number"),
        "estado": msg_info.get("state"),
    }, default=serialize, ensure_ascii=False)


@mcp.tool()
def preview_whatsapp(
    template_id: int,
    registro_id: int,
    telefone: str | None = None,
    textos_livres: dict[str, str] | None = None,
) -> str:
    """Gera preview da mensagem WhatsApp SEM enviar. Sem efeito colateral.

    Use SEMPRE antes de enviar_whatsapp() para verificar o conteudo final da mensagem.
    Cria um composer temporario, le o preview e o descarta sem enviar.

    Returns JSON {template, telefone, preview} com o texto final da mensagem ja interpolado.

    Args:
        template_id: ID do template de WhatsApp.
        registro_id: ID do registro no modelo vinculado ao template.
        telefone: Override de telefone. None = usa o do registro.
        textos_livres: Valores para variaveis free_text, no mesmo formato de enviar_whatsapp().
    """
    odoo = get_odoo()

    template = odoo.get("whatsapp.template", template_id,
                        fields=["model", "name", "body"])
    if not template:
        return json.dumps({"erro": f"Template {template_id} nao encontrado"})

    res_model = template["model"]

    composer_vals = {
        "wa_template_id": template_id,
        "res_model": res_model,
        "res_ids": str([registro_id]),
    }
    if telefone:
        composer_vals["phone"] = telefone
    if textos_livres:
        for key, value in textos_livres.items():
            composer_vals[f"free_text_{key}"] = value

    context = {
        "active_model": res_model,
        "active_ids": [registro_id],
    }

    composer_id = odoo._call(
        "whatsapp.composer", "create",
        [composer_vals],
        {"context": context},
    )

    composer = odoo.get("whatsapp.composer", composer_id,
                        fields=["phone", "preview_whatsapp"])

    # Limpar HTML do preview para texto legivel
    preview_html = composer.get("preview_whatsapp", "")
    # Extrair texto do HTML de forma simples
    text = re.sub(r"<[^>]+>", "", preview_html)
    text = re.sub(r"\s+", " ", text).strip()

    # Deletar o composer (nao enviar)
    odoo.delete("whatsapp.composer", composer_id)

    return json.dumps({
        "template": template["name"],
        "telefone": composer.get("phone"),
        "preview": text,
    }, default=serialize, ensure_ascii=False)


# ─── Relatorios ──────────────────────────────────────────────────────────────


@mcp.tool()
def gerar_dre(
    ano: int,
    mapeamento_categorias: dict | None = None,
    output_path: str | None = None,
) -> str:
    """Gera DRE (Demonstracao do Resultado do Exercicio) em Excel para o ano especificado.

    Busca faturas de venda (receita) e linhas de compra (despesas) no Odoo.
    Categoriza cada linha de despesa pela conta analitica (prioritario) ou pela
    conta do plano de contas contabil (fallback). Gera planilha .xlsx com 3 abas:
    DRE mensal com formulas, detalhamento de receitas e detalhamento de despesas.

    Categorias de despesa disponíveis:
    - "Pessoal / Servicos Profissionais"
    - "Terceirizacao / Subcontratacao"
    - "Impostos e Taxas"
    - "Software / SaaS / Infraestrutura" (default para nao mapeados)

    Args:
        ano: Ano fiscal (ex: 2025).
        mapeamento_categorias: {categoria: ["termo analitico ou contabil", ...]} para classificar.
                               Prioridade: nome da conta analitica; fallback: nome da conta contabil.
                               Nao obrigatorio — linhas nao mapeadas vao para
                               "Software / SaaS / Infraestrutura".
                               Exemplo: {"Pessoal / Servicos Profissionais": ["Pessoal", "RH"],
                                         "Impostos e Taxas": ["SEFAZ", "ISS", "Simples"]}
        output_path: Caminho do arquivo .xlsx a gerar. Default: "reports/dre_{ano}.xlsx".

    Returns: JSON com caminho do arquivo, resumo financeiro e linhas processadas.
    """
    import os
    from reports.dre import (
        gerar_excel_dre, categorizar_por_conta, obs_from_states,
        CATEGORIAS_DESPESA, CATEGORIA_DEFAULT,
    )

    odoo = get_odoo()
    hoje = str(date.today())
    mapeamento = mapeamento_categorias or {}

    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "reports", f"dre_{ano}.xlsx"
        )

    # Info da empresa
    company = odoo.search("res.company", [], fields=["name", "currency_id"], limit=1)
    empresa = company[0]["name"] if company else "Empresa"
    moeda_raw = company[0]["currency_id"][1] if company and company[0].get("currency_id") else "BRL"
    moeda = moeda_raw.split()[0].strip("[]") if moeda_raw else "BRL"

    campos_fatura = [
        "name", "invoice_date", "move_type", "state",
        "partner_id", "currency_id",
        "amount_total_signed", "amount_untaxed_signed",
    ]
    data_ini = f"{ano}-01-01"
    data_fim = f"{ano}-12-31"

    vendas = odoo.search("account.move", [
        ["move_type", "=", "out_invoice"],
        ["state", "in", ["posted", "draft"]],
        ["invoice_date", ">=", data_ini],
        ["invoice_date", "<=", data_fim],
    ], fields=campos_fatura, limit=500)

    compras = odoo.search("account.move", [
        ["move_type", "=", "in_invoice"],
        ["state", "in", ["posted", "draft"]],
        ["invoice_date", ">=", data_ini],
        ["invoice_date", "<=", data_fim],
    ], fields=campos_fatura, limit=500)

    # Agrega receita e impostos por mes
    receita = {m: 0.0 for m in range(1, 13)}
    imposto = {m: 0.0 for m in range(1, 13)}
    receita_states: set = set()

    for v in vendas:
        if not v.get("invoice_date"):
            continue
        mes = int(v["invoice_date"].split("-")[1])
        total = v.get("amount_total_signed") or 0.0
        untaxed = v.get("amount_untaxed_signed") or total
        receita[mes] += untaxed
        imposto[mes] += total - untaxed
        receita_states.add(v["state"])

    # Busca linhas das faturas de compra para categorizar por conta analitica / contabil
    compras_by_id = {c["id"]: c for c in compras}
    compra_ids = list(compras_by_id.keys())

    linhas_odoo = []
    if compra_ids:
        linhas_odoo = odoo.search("account.move.line", [
            ["move_id", "in", compra_ids],
            ["display_type", "not in", ["line_section", "line_note"]],
            ["tax_line_id", "=", False],
            ["price_subtotal", "!=", 0],
        ], fields=[
            "move_id", "name", "account_id", "analytic_distribution", "price_subtotal",
        ], limit=2000)

    # Resolve nomes das contas analiticas em lote
    analytic_ids: set = set()
    for l in linhas_odoo:
        if l.get("analytic_distribution"):
            analytic_ids.update(int(k) for k in l["analytic_distribution"].keys())

    analiticas: dict = {}
    if analytic_ids:
        aa = odoo.search("account.analytic.account", [
            ["id", "in", list(analytic_ids)],
        ], fields=["id", "name"], limit=len(analytic_ids))
        analiticas = {r["id"]: r["name"] for r in aa}

    # Monta linhas de compra enriquecidas e agrega despesa por categoria/mes
    despesa = {cat: {m: 0.0 for m in range(1, 13)} for cat in CATEGORIAS_DESPESA}
    despesa_states: dict = {cat: set() for cat in CATEGORIAS_DESPESA}
    linhas_compra = []

    for l in linhas_odoo:
        move_id = l["move_id"][0] if isinstance(l["move_id"], list) else l["move_id"]
        compra = compras_by_id.get(move_id)
        if not compra or not compra.get("invoice_date"):
            continue

        mes = int(compra["invoice_date"].split("-")[1])

        # Conta analitica: pega a de maior percentual
        analitica_nome = ""
        if l.get("analytic_distribution"):
            top_id = max(l["analytic_distribution"], key=lambda k: l["analytic_distribution"][k])
            analitica_nome = analiticas.get(int(top_id), "")

        conta_nome = l["account_id"][1] if l.get("account_id") else ""
        cat = categorizar_por_conta(analitica_nome, conta_nome, mapeamento)
        if cat not in despesa:
            cat = CATEGORIA_DEFAULT

        valor = abs(l.get("price_subtotal") or 0.0)
        despesa[cat][mes] += valor
        despesa_states[cat].add(compra["state"])

        linhas_compra.append({
            "mes": mes,
            "fornecedor": compra["partner_id"][1] if compra.get("partner_id") else "",
            "fatura": compra.get("name", ""),
            "categoria": cat,
            "analitica": analitica_nome,
            "conta": conta_nome,
            "valor": valor,
            "status": compra["state"],
        })

    receita_obs = obs_from_states(receita_states)
    imposto_obs = obs_from_states(receita_states)
    despesa_obs = {cat: obs_from_states(despesa_states[cat]) for cat in CATEGORIAS_DESPESA}

    path = gerar_excel_dre(
        ano=ano,
        hoje=hoje,
        empresa=empresa,
        moeda=moeda,
        receita=receita,
        imposto=imposto,
        despesa=despesa,
        receita_obs=receita_obs,
        imposto_obs=imposto_obs,
        despesa_obs=despesa_obs,
        vendas=vendas,
        linhas_compra=linhas_compra,
        output_path=output_path,
    )

    total_receita = sum(receita.values())
    total_despesa = sum(sum(v.values()) for v in despesa.values())

    return json.dumps({
        "arquivo": path,
        "ano": ano,
        "empresa": empresa,
        "moeda": moeda,
        "total_faturas_venda": len(vendas),
        "total_faturas_compra": len(compras),
        "total_linhas_despesa": len(linhas_compra),
        "receita_bruta_total": round(total_receita, 2),
        "despesas_total": round(total_despesa, 2),
        "resultado_liquido": round(total_receita - total_despesa, 2),
    }, default=serialize, ensure_ascii=False)


# ─── Entrypoint ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
