# -*- coding: utf-8 -*-
from odoo import OdooClient
import json

odoo = OdooClient()

# IDs
THIAGO_PARTNER = 188
PRODUCT_TIMESHEETS = 4   # "Service on Timesheets" - billed by Hours
UOM_HOURS = 4
ANALYTIC_PROJ = {'97': 100.0}  # Projeto Sudoeste Ambiental

# Create the Purchase Order (draft)
po_id = odoo.create('purchase.order', {
    'partner_id': THIAGO_PARTNER,
    'date_planned': '2026-09-12 18:00:00',
    'notes': (
        '<p><strong>Escopo de Trabalho — PMO / Gestão de Projeto</strong></p>'
        '<p>Contratação de Thiago Monteiro para atuação como PMO no projeto de implantação Odoo '
        'da Sudoeste Ambiental (Ulysses Codognotto), referente ao pedido S00103.</p>'
        '<p><strong>Período:</strong> 13/04/2026 a 12/09/2026 (5 meses)</p>'
        '<p><strong>Responsabilidades:</strong></p>'
        '<ul>'
        '<li>Coordenação geral do cronograma e marcos do projeto</li>'
        '<li>Facilitação de reuniões de kickoff, revisão de marco e retrospectivas</li>'
        '<li>Gestão de riscos, impedimentos e dependências</li>'
        '<li>Elaboração e envio de status reports ao cliente</li>'
        '<li>Suporte ao go-live e estabilização</li>'
        '</ul>'
    ),
})

print(f'PO created: ID {po_id}')

# Build PO lines
lines = [
    # Section header
    {
        'order_id': po_id,
        'display_type': 'line_section',
        'name': 'Escopo por Marco — Projeto Sudoeste Ambiental',
        'sequence': 10,
        'product_qty': 0.0,
    },
    # M1
    {
        'order_id': po_id,
        'product_id': PRODUCT_TIMESHEETS,
        'product_uom_id': UOM_HOURS,
        'product_qty': 5.0,
        'price_unit': 0.0,
        'date_planned': '2026-05-02 18:00:00',
        'analytic_distribution': ANALYTIC_PROJ,
        'sequence': 20,
        'name': (
            'M1 — Planejamento e Kickoff (13/04 a 02/05)\n'
            '- Reunião de kickoff com stakeholders e levantamento de requisitos\n'
            '- Definição de cronograma, responsáveis e critérios de aceite\n'
            '- Configuração do projeto no Odoo (estrutura, etapas, milestones)\n'
            '- Status report inicial'
        ),
    },
    # M2
    {
        'order_id': po_id,
        'product_id': PRODUCT_TIMESHEETS,
        'product_uom_id': UOM_HOURS,
        'product_qty': 3.0,
        'price_unit': 0.0,
        'date_planned': '2026-05-30 18:00:00',
        'analytic_distribution': ANALYTIC_PROJ,
        'sequence': 30,
        'name': (
            'M2 — Acompanhamento: Vendas e CRM (05/05 a 30/05)\n'
            '- Acompanhamento do progresso e resolução de impedimentos\n'
            '- Facilitação de homologação com o cliente\n'
            '- Status report e revisão de marco'
        ),
    },
    # M3
    {
        'order_id': po_id,
        'product_id': PRODUCT_TIMESHEETS,
        'product_uom_id': UOM_HOURS,
        'product_qty': 4.0,
        'price_unit': 0.0,
        'date_planned': '2026-07-03 18:00:00',
        'analytic_distribution': ANALYTIC_PROJ,
        'sequence': 40,
        'name': (
            'M3 — Acompanhamento: Finanças (01/06 a 03/07)\n'
            '- Acompanhamento do módulo financeiro e conciliação\n'
            '- Gestão de riscos fiscais e de integração\n'
            '- Status report e revisão de marco'
        ),
    },
    # M4
    {
        'order_id': po_id,
        'product_id': PRODUCT_TIMESHEETS,
        'product_uom_id': UOM_HOURS,
        'product_qty': 3.0,
        'price_unit': 0.0,
        'date_planned': '2026-07-31 18:00:00',
        'analytic_distribution': ANALYTIC_PROJ,
        'sequence': 50,
        'name': (
            'M4 — Acompanhamento: Cadeia de Suprimentos (06/07 a 31/07)\n'
            '- Acompanhamento de estoque, compras e frotas\n'
            '- Coordenação de testes e treinamento\n'
            '- Status report e revisão de marco'
        ),
    },
    # M5
    {
        'order_id': po_id,
        'product_id': PRODUCT_TIMESHEETS,
        'product_uom_id': UOM_HOURS,
        'product_qty': 4.0,
        'price_unit': 0.0,
        'date_planned': '2026-08-29 18:00:00',
        'analytic_distribution': ANALYTIC_PROJ,
        'sequence': 60,
        'name': (
            'M5 — Acompanhamento: RH, Serviços e Canais Digitais (03/08 a 29/08)\n'
            '- Acompanhamento de RH, helpdesk, website e marketing\n'
            '- Gestão de dependências entre módulos\n'
            '- Status report e revisão de marco'
        ),
    },
    # M6
    {
        'order_id': po_id,
        'product_id': PRODUCT_TIMESHEETS,
        'product_uom_id': UOM_HOURS,
        'product_qty': 5.0,
        'price_unit': 0.0,
        'date_planned': '2026-09-12 18:00:00',
        'analytic_distribution': ANALYTIC_PROJ,
        'sequence': 70,
        'name': (
            'M6 — Go-Live e Encerramento (01/09 a 12/09)\n'
            '- Coordenação da validação final e auditoria\n'
            '- Suporte ao go-live e monitoramento inicial\n'
            '- Encerramento formal: documentação, relatório final e lições aprendidas'
        ),
    },
]

print(f'Creating {len(lines)} PO lines...')
for line in lines:
    lid = odoo.create('purchase.order.line', line)
    label = line.get('name', '').split('\n')[0]
    print(f'  Line {lid}: {label}')

# Verify PO
po = odoo.get('purchase.order', po_id, fields=['name', 'partner_id', 'state', 'amount_total', 'date_planned'])
print(f'\nPO Summary:')
print(json.dumps(po, indent=2, default=str))
