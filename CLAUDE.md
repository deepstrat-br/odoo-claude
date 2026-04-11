# Odoo ERP — Deepstrat

Helper CLI + modulo Python para o Odoo da Deepstrat via XML-RPC.

## Conexao

| Param | Origem |
|---|---|
| URL | `ODOO_URL` no `.env` |
| DB | `ODOO_DB` no `.env` |
| Login | `ODOO_LOGIN` no `.env` |
| API Key | `ODOO_KEY` no `.env` |

Credenciais carregadas automaticamente pelo `odoo.py`. Cada usuario configura seu proprio `.env`.

**Moeda: BRL (R$).** A Deepstrat opera no Brasil. A moeda base do Odoo é BRL (Real brasileiro). Nunca assumir USD, EUR ou outra moeda sem verificar `currency_id`.

**Regra de moeda em consultas financeiras.**
Faturas e POs podem estar em moeda estrangeira (USD, EUR, etc.). Ao buscar registros financeiros, sempre inclua os campos abaixo e trate-os corretamente:

| Campo | Moeda | Uso |
|---|---|---|
| `currency_id` | — | Moeda original do documento |
| `amount_total` / `amount_residual` | moeda original | Valor na moeda do documento |
| `amount_total_signed` / `amount_residual_signed` | BRL | Valor convertido pelo Odoo (taxa da data da fatura) |

**Quando exibir valores monetários, sempre informe:**
- Valor original (ex: USD 1.200,00)
- Equivalente BRL (ex: BRL 6.000,00)
- Taxa usada (ex: taxa 5,0000 — calculada como `amount_total_signed / amount_total`)

Se `currency_id` for BRL, `amount_total == amount_total_signed` (sem conversão).
Se for moeda estrangeira, use `amount_total_signed` para somar com outros valores BRL.

---

## Principios de desenvolvimento

**Scripts genericos, dados descartaveis.**
Nunca criar um script para um caso especifico (ex: "criar PO do fulano"). Sempre desenvolver o script generico e parametrizavel primeiro. Os arquivos de dados (`data/`) sao temporarios — criados na hora, usados, descartados.

**Resolver para campos relacionais.**
Todo script que cria ou atualiza registros com campos `many2one`/`many2many` deve usar a classe `Resolver` de `odoo.py`. Ela resolve nomes para IDs com cache, evitando duplicacao de logica entre scripts.

```python
from odoo import OdooClient, Resolver

odoo = OdooClient()
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
odoo-deepstrat/
├── odoo.py                          # cliente XML-RPC + Resolver (lib core)
├── mcp_server.py                    # servidor MCP (Model Context Protocol)
├── scripts/
│   ├── project/
│   │   └── import_tasks.py          # criacao em lote de tarefas via YAML
│   └── purchase/
│       └── import_po.py             # criacao de PO + linhas via YAML
├── integrations/
│   └── clockify.py                  # Clockify <-> account.analytic.line
├── reports/
│   ├── dre.py                       # gerador de Demonstrativos Financeiros (DRE) em Excel + CLI
│   └── fluxo_caixa.py               # gerador da aba DFC (Fluxo de Caixa) — consumido por dre.py
├── data/                            # entradas temporarias (nao versionadas)
│   ├── tasks/
│   └── purchase/
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

## Demonstrativos Financeiros — reports/dre.py

Gera **Demonstrativos Financeiros (DRE + DFC)** em Excel com ate 6 abas:
- **DRE {ano} — Competencia** (por `invoice_date`)
- **DRE {ano} — Caixa** (por `invoice_date_due`)
- **DFC {ano}** — Demonstrativo do Fluxo de Caixa real por `account.payment`
  (so quando `clients/<slug>.yaml` tem `cash_flow.credit_cards`)
- **Detalhamento Receitas**, **Detalhamento Despesas**
- **Detalhamento Fluxo de Caixa** (so com DFC)

Categoriza cada linha de despesa pela **conta analitica** (prioritario) ou pela
**conta do plano de contas contabil** (fallback). A aba de detalhamento mostra
as duas colunas para auditoria.

**Prefira o CLI** — a tool MCP `gerar-demonstrativos-financeiros` pode sofrer timeout em anos com muitas faturas.

```bash
# CLI (sem timeout, recomendado)
python reports/dre.py 2026
python reports/dre.py 2026 --slug deepstrat              # habilita DFC via YAML
python reports/dre.py 2026 --output /tmp/demonstrativos_2026.xlsx
python reports/dre.py 2026 --mapeamento data/mapeamento.json
```

```json
// Exemplo data/mapeamento.json
{
  "Pessoal / Servicos Profissionais": ["Pessoal", "RH", "Honorarios"],
  "Terceirizacao / Subcontratacao": ["Subcontratacao", "Terceiros"],
  "Impostos e Taxas": ["SEFAZ", "ISS", "Simples", "INSS"]
}
```

**Logica de categorizacao** (por linha de fatura):
1. Verifica `analytic_distribution` — resolve ID para nome da conta analitica
2. Tenta match do nome analitico com os termos do mapeamento
3. Se nao encontrar, tenta match do nome da conta contabil (`account_id`)
4. Fallback: `"Software / SaaS / Infraestrutura"`

**Categorias de despesa** (`reports/dre.py::CATEGORIAS_DESPESA`):

| Categoria | Uso tipico |
|---|---|
| `Pessoal / Servicos Profissionais` | Folha, MEIs, honorarios |
| `Terceirizacao / Subcontratacao` | Servicos de terceiros |
| `Impostos e Taxas` | SEFAZ, Prefeitura, guias |
| `Software / SaaS / Infraestrutura` | Default para nao mapeados |

**Regras (DRE):**
- Inclui faturas `posted` (Efetivo) e `draft` (Provisorio) — coluna Obs indica o status
- Granularidade por linha de fatura, nao por cabecalho
- Faturas em moeda estrangeira sao convertidas pelo Odoo pela taxa da data da fatura

### Fluxo de Caixa (DFC) — `reports/fluxo_caixa.py`

O DFC usa `account.payment` (estados `posted`/`paid`) em vez de
`account.move` — ou seja, olha o que **efetivamente saiu/entrou** do caixa
ou banco. Cada `journal_id` listado em `cash_flow.credit_cards` e tratado
como cartao de credito: suas compras sao deferidas para a data de
vencimento da fatura usando `closing_day`/`due_day`.

**Regra do cartao:**
- Compra ate `closing_day` → entra na fatura que fecha neste mes, paga no
  `due_day` do mes seguinte.
- Compra apos `closing_day` → entra na fatura do proximo mes, paga no
  `due_day` do mes subsequente.
- Compras de nov/dez do ano anterior cujo vencimento cai no ano atual
  aparecem na linha **"Ajuste: faturas de cartao do ano anterior"**.
- Compras do ano atual cujo vencimento cai no ano seguinte vao para o
  rodape **"Faturas de cartao diferidas para {ano+1}"** (nao entram nas
  colunas mensais).

**Config no `clients/<slug>.yaml`:**

```yaml
cash_flow:
  saldo_inicial_por_ano:
    2026: 0.00
  credit_cards:
    - name: "Cartao Itau Black"    # substring do account.journal.name
      id: null                      # opcional: prevalece sobre name
      closing_day: 25
      due_day: 5
```

Sem `cash_flow.credit_cards`, a aba DFC nao e gerada (arquivo sai so com as abas de DRE).

**Outros detalhes:**
- Saida padrao: `reports/demonstrativos_financeiros_{ano}.xlsx` na raiz do projeto
- Dependencias: `pip install openpyxl pyyaml`

---

## Modulo Python

```python
from odoo import OdooClient
odoo = OdooClient()

odoo.search('modelo', filters=[[...]], fields=['campo1', 'campo2'], limit=20)
odoo.get('modelo', record_id, fields=[...])
odoo.count('modelo', filters=[[...]])
odoo.create('modelo', {'campo': 'valor'})
odoo.update('modelo', record_id, {'campo': 'novo_valor'})
odoo.delete('modelo', record_id)
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
