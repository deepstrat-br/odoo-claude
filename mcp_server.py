"""
MCP Server for Odoo — Deepstrat
Expoe o Odoo XML-RPC como tools do Model Context Protocol.
"""

import json
import re
from datetime import date, datetime
from mcp.server.fastmcp import FastMCP
from odoo import OdooClient, Resolver

mcp = FastMCP(
    "odoo-deepstrat",
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
    """Retorna leads novos que ainda nao foram qualificados/enriquecidos.

    Leads pendentes sao aqueles com priority='0' e sem pesquisa na descricao.
    Retorna os dados do lead junto com a metodologia de qualificacao resumida.

    Para cada lead retornado, voce deve:
    1. Pesquisar a empresa online (Google, redes sociais, CNPJ)
    2. Avaliar potencial e definir prioridade (0-3 estrelas)
    3. Chamar qualificar_lead() para aplicar a atualizacao

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
    """Aplica a qualificacao em um lead do CRM.

    Atualiza prioridade, nomes, descricao com pesquisa.
    Acoes automaticas por prioridade:
    - Prioridade 3: envia WhatsApp de abordagem (template 17) + cria atividade Call.
    - Prioridade 2: cria atividade de revisao manual (To Do).
    - Prioridade 0-1: apenas atualiza dados, sem acao adicional.

    Args:
        lead_id: ID do lead no Odoo.
        prioridade: 0 (spam/baixo), 1 (pouco potencial), 2 (medio), 3 (alto).
        nome_contato: Nome do contato corrigido (Title Case). None = nao alterar.
        empresa: Nome da empresa corrigido. None = nao alterar.
        titulo: Titulo do lead. None = gerar automaticamente como 'Lead Odoo: Nome — Empresa'.
        pesquisa: Texto da pesquisa sobre a empresa (sera adicionado ao campo descricao).
        potencial: Avaliacao do potencial (ex: 'Alto. E-commerce com produto real.').
        website: URL do site da empresa. None = nao alterar.
        nota_atividade: Nota HTML para a atividade (Call ou To Do). Recomendado para prioridade 2 e 3.
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
    """Lista templates de WhatsApp disponiveis no Odoo.

    Args:
        modelo: Filtrar por modelo vinculado (ex: 'crm.lead', 'account.move'). None = todos.
        apenas_aprovados: Se True, retorna apenas templates com status 'approved'.
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
    """Envia uma mensagem de WhatsApp usando um template aprovado do Odoo.

    O template ja esta vinculado a um modelo (ex: crm.lead, account.move).
    O registro_id deve ser um ID valido desse modelo.
    Variaveis do tipo 'field' sao preenchidas automaticamente pelo Odoo a partir do registro.
    Variaveis do tipo 'free_text' devem ser passadas via textos_livres.

    ATENCAO: Esta acao envia uma mensagem real via WhatsApp. Confirme com o usuario antes de executar.

    Args:
        template_id: ID do template de WhatsApp (use listar_templates_whatsapp para ver opcoes).
        registro_id: ID do registro no modelo vinculado ao template.
        telefone: Numero de telefone (override). None = usa o telefone do registro.
        textos_livres: Valores para variaveis free_text, ex: {"1": "Joao", "2": "14:00"}.
                       As chaves sao os numeros das variaveis (sem chaves duplas).
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
    """Gera um preview da mensagem WhatsApp SEM enviar.

    Util para verificar como a mensagem ficara antes de confirmar o envio.

    Args:
        template_id: ID do template de WhatsApp.
        registro_id: ID do registro no modelo vinculado ao template.
        telefone: Numero de telefone (override). None = usa o telefone do registro.
        textos_livres: Valores para variaveis free_text.
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


# ─── Entrypoint ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
