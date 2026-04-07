#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_po.py — Criacao de Pedido de Compra (PO) no Odoo a partir de um arquivo YAML.

Uso (da raiz do projeto):
  python scripts/purchase/import_po.py data/purchase/contrato.yaml
  python scripts/purchase/import_po.py data/purchase/contrato.yaml --dry-run

Formato do YAML:
  partner: nome ou ID do fornecedor/prestador

  header:
    date_planned: "YYYY-MM-DD"        # data de entrega prevista
    notes: "<html>"                   # notas internas (HTML ou texto)

  lines:
    - section: "Titulo da Secao"      # linha de secao (sem produto)

    - product: "Nome do Produto"      # nome ou ID do produto
      uom: "Horas"                    # nome ou ID da unidade (opcional)
      qty: 5.0                        # quantidade
      price: 150.0                    # preco unitario (default 0)
      date: "YYYY-MM-DD"             # data de entrega da linha (opcional)
      analytic:                       # distribuicao analitica (opcional)
        "Nome da Conta": 100.0        # nome ou ID da conta: percentual
      name: |                         # descricao da linha (texto livre)
        Linha 1
        Linha 2
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    import yaml
except ImportError:
    print("Dependencia ausente: pip install pyyaml")
    sys.exit(1)

from odoo import OdooClient, Resolver


# ─── Build ────────────────────────────────────────────────────────────────────

def build_header(raw_header, partner_id):
    vals = {'partner_id': partner_id}
    if not raw_header:
        return vals
    if 'date_planned' in raw_header:
        d = str(raw_header['date_planned'])
        vals['date_planned'] = d if 'T' in d or ' ' in d else f"{d} 18:00:00"
    if 'notes' in raw_header:
        vals['notes'] = str(raw_header['notes'])
    return vals


def build_line(raw, po_id, seq, resolver):
    if 'section' in raw:
        return {
            'order_id': po_id,
            'display_type': 'line_section',
            'name': raw['section'],
            'sequence': seq,
            'product_qty': 0.0,
        }

    if 'product' not in raw:
        raise ValueError(f"Linha sem 'product' ou 'section': {raw}")

    vals = {
        'order_id': po_id,
        'sequence': seq,
        'product_id': resolver.product(raw['product']),
        'product_qty': float(raw.get('qty', 1.0)),
        'price_unit': float(raw.get('price', 0.0)),
    }

    if 'uom' in raw:
        vals['product_uom_id'] = resolver.uom(raw['uom'])
    if 'date' in raw:
        d = str(raw['date'])
        vals['date_planned'] = d if 'T' in d or ' ' in d else f"{d} 18:00:00"
    if 'analytic' in raw:
        vals['analytic_distribution'] = resolver.analytic_distribution(raw['analytic'])
    if 'name' in raw:
        vals['name'] = str(raw['name']).strip()

    return vals


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Cria um Pedido de Compra no Odoo a partir de um arquivo YAML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('arquivo', help='Arquivo YAML com o PO')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simula sem gravar no Odoo')
    args = parser.parse_args()

    with open(args.arquivo, encoding='utf-8') as f:
        data = yaml.safe_load(f)

    odoo = OdooClient()
    resolver = Resolver(odoo)

    if 'partner' not in data:
        print("Erro: campo 'partner' e obrigatorio no YAML")
        sys.exit(1)

    partner_id = resolver.partner(data['partner'])
    raw_lines = data.get('lines', [])

    prefix = '[DRY RUN] ' if args.dry_run else ''
    print(f"Parceiro: ID {partner_id} ({data['partner']})")
    print(f"{prefix}PO com {len(raw_lines)} linha(s)...\n")

    if args.dry_run:
        total_qty = 0.0
        total_value = 0.0
        for i, raw in enumerate(raw_lines, 1):
            if 'section' in raw:
                print(f"  --  {raw['section']}")
            else:
                qty = float(raw.get('qty', 1.0))
                price = float(raw.get('price', 0.0))
                prod = raw.get('product', '?')
                label = str(raw.get('name', '')).split('\n')[0][:60]
                print(f"  [{i:02d}] {qty:5.1f} x {price:8.2f}  {prod:<30}  {label}")
                total_qty += qty
                total_value += qty * price
        print(f"\n  Total: {total_qty:.1f} unidades | R$ {total_value:,.2f}")
        return

    header_vals = build_header(data.get('header', {}), partner_id)
    po_id = odoo.create('purchase.order', header_vals)
    print(f"PO criado: ID {po_id}")

    errors = []
    for i, raw in enumerate(raw_lines, 1):
        seq = i * 10
        try:
            line_vals = build_line(raw, po_id, seq, resolver)
            lid = odoo.create('purchase.order.line', line_vals)
            label = line_vals.get('name', line_vals.get('display_type', '')).split('\n')[0][:60]
            print(f"  [{i:02d}] ID {lid:<6}  {label}")
        except Exception as e:
            errors.append((i, str(e)))
            print(f"  [{i:02d}] ERRO: {e}")

    po = odoo.get('purchase.order', po_id, fields=['name', 'partner_id', 'state', 'amount_total'])
    print(f"\nPO {po['name']} | {po['partner_id'][1]} | R$ {po['amount_total']:,.2f}")
    if errors:
        print(f"\n{len(errors)} erro(s):")
        for idx, err in errors:
            print(f"  [{idx:02d}] {err}")
        sys.exit(1)


if __name__ == '__main__':
    main()
