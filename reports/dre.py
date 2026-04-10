"""
Gerador de DRE (Demonstracao do Resultado do Exercicio) em Excel (.xlsx).

Produz planilha profissional com 3 abas:
- "DRE {ano}": demonstrativo mensal com formulas Excel reais
- "Detalhamento Receitas": todas as faturas de venda por mes
- "Detalhamento Despesas": todas as faturas de compra categorizadas

Agnostico de empresa — nome da empresa e mapeamento de fornecedores para
categorias de despesa sao recebidos como parametros.

Moeda: todos os valores na moeda da empresa (amount_total_signed).
Faturas em moedas estrangeiras sao convertidas pelo Odoo pela taxa do dia.
"""

import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# ─── Constantes ──────────────────────────────────────────────────────────────

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
         "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

CATEGORIAS_DESPESA = [
    "Pessoal / Serviços Profissionais",
    "Terceirização / Subcontratação",
    "Software / SaaS / Infraestrutura",
    "Impostos e Taxas",
]

CATEGORIA_DEFAULT = "Software / SaaS / Infraestrutura"

# ─── Estilos ─────────────────────────────────────────────────────────────────

FMT_BRL = '#,##0.00;(#,##0.00);"-"'
FMT_PCT = "0.0%"

_S_TITULO = {
    "font": Font(name="Arial", size=14, bold=True, color="FFFFFF"),
    "fill": PatternFill("solid", fgColor="1F3864"),
}
_S_SUBTITULO = {
    "font": Font(name="Arial", size=9, italic=True, color="FFFFFF"),
    "fill": PatternFill("solid", fgColor="2F5496"),
}
_S_HEADER = {
    "font": Font(name="Arial", size=12, bold=True, color="FFFFFF"),
    "fill": PatternFill("solid", fgColor="2F5496"),
}
_S_SECAO = {
    "font": Font(name="Arial", size=10, bold=True),
    "fill": PatternFill("solid", fgColor="E2EFDA"),
}
_S_DADO = {
    "font": Font(name="Arial", size=10),
}
_S_TOTAL = {
    "font": Font(name="Arial", size=10, bold=True),
    "fill": PatternFill("solid", fgColor="FFF2CC"),
}
_S_RESULT = {
    "font": Font(name="Arial", size=11, bold=True, color="1F3864"),
    "fill": PatternFill("solid", fgColor="BDD7EE"),
}
_S_FINAL = {
    "font": Font(name="Arial", size=12, bold=True, color="FFFFFF"),
    "fill": PatternFill("solid", fgColor="1F3864"),
}
_S_MARGEM = {
    "font": Font(name="Arial", size=9, italic=True, color="666666"),
}
_S_OBS = Font(name="Arial", size=9, color="666666")

_F_EFETIVO = Font(name="Arial", size=10, color="006100")
_F_PROVISORIO = Font(name="Arial", size=10, color="C65911")


# ─── Funcoes publicas ────────────────────────────────────────────────────────


def categorizar_por_conta(
    analitica_nome: str,
    conta_nome: str,
    mapeamento: dict[str, list[str]],
) -> str:
    """Categoriza despesa pela conta analitica (prioritario) ou conta contabil (fallback).

    Compara os nomes de forma case-insensitive e por substring.

    Args:
        analitica_nome: Nome da conta analitica resolvida (vazio se nao houver distribuicao).
        conta_nome: Nome da conta do plano de contas (account_id[1] do Odoo).
        mapeamento: {categoria: [termos]} para classificar. Se vazio, retorna CATEGORIA_DEFAULT.

    Returns:
        Nome da categoria de despesa.
    """
    def _match(nome: str) -> str | None:
        n = nome.lower()
        for cat, termos in mapeamento.items():
            if any(t.lower() in n for t in termos):
                return cat
        return None

    if analitica_nome:
        cat = _match(analitica_nome)
        if cat:
            return cat
    if conta_nome:
        cat = _match(conta_nome)
        if cat:
            return cat
    return CATEGORIA_DEFAULT


def obs_from_states(states: set) -> str:
    """Retorna 'Efetivo', 'Provisorio' ou 'Efet+Prov' com base nos estados das faturas."""
    if not states:
        return ""
    has_posted = "posted" in states
    has_draft = "draft" in states
    if has_posted and has_draft:
        return "Efet+Prov"
    if has_posted:
        return "Efetivo"
    if has_draft:
        return "Provisorio"
    return ""


def gerar_excel_dre(*, ano, hoje, empresa, moeda, receita, imposto, despesa,
                    receita_obs, imposto_obs, despesa_obs,
                    vendas, linhas_compra, output_path):
    """Gera o arquivo Excel completo do DRE e salva em output_path.

    Args:
        ano: Ano fiscal.
        hoje: Data de geracao (str YYYY-MM-DD).
        empresa: Nome da empresa (ex: 'Minha Empresa Ltda').
        moeda: Simbolo da moeda base da empresa (ex: 'BRL', 'USD').
        receita: dict {1..12: float} receita bruta mensal.
        imposto: dict {1..12: float} impostos sobre receita mensal.
        despesa: dict {categoria: {1..12: float}} despesas mensais por categoria.
        receita_obs, imposto_obs: str com estado das faturas.
        despesa_obs: dict {categoria: str} com estado por categoria.
        vendas: lista de faturas de venda (dicts do Odoo).
        linhas_compra: lista de linhas de compra enriquecidas com categoria, conta e analitica.
                       Cada item: {mes, fornecedor, fatura, categoria, analitica, conta, valor, status}.
        output_path: caminho para salvar o .xlsx.

    Returns:
        Caminho do arquivo salvo (str).
    """
    wb = Workbook()
    _build_dre_sheet(wb, ano, hoje, empresa, moeda, receita, imposto, despesa,
                     receita_obs, imposto_obs, despesa_obs)
    _build_receitas_sheet(wb, ano, vendas, moeda)
    _build_despesas_sheet(wb, ano, linhas_compra, moeda)
    wb.save(output_path)
    return output_path


# ─── Helpers internos ────────────────────────────────────────────────────────


def _fill_row(ws, row, fill, col_start=1, col_end=15):
    for ci in range(col_start, col_end + 1):
        ws.cell(row=row, column=ci).fill = fill


def _write_data_row(ws, row, data, obs, style):
    """Escreve dados mensais (C-N) + SUM no TOTAL (O)."""
    font = style["font"]
    fill = style.get("fill")
    ws.cell(row=row, column=1).font = font
    if obs:
        ws.cell(row=row, column=2, value=obs).font = _S_OBS
    if fill:
        _fill_row(ws, row, fill)
    for m in range(1, 13):
        c = ws.cell(row=row, column=m + 2, value=round(data[m], 2))
        c.font = font
        c.number_format = FMT_BRL
    c = ws.cell(row=row, column=15, value=f"=SUM(C{row}:N{row})")
    c.font = font
    c.number_format = FMT_BRL


def _write_formula_row(ws, row, tmpl, style, fmt=FMT_BRL):
    """Escreve formula para colunas C-O. tmpl usa {c} como placeholder."""
    font = style["font"]
    fill = style.get("fill")
    ws.cell(row=row, column=1).font = font
    if fill:
        _fill_row(ws, row, fill)
    for ci in range(3, 16):
        cl = get_column_letter(ci)
        c = ws.cell(row=row, column=ci, value="=" + tmpl.replace("{c}", cl))
        c.font = font
        c.number_format = fmt
        if fill:
            c.fill = fill


# ─── Aba 1: DRE ─────────────────────────────────────────────────────────────


def _build_dre_sheet(wb, ano, hoje, empresa, moeda, receita, imposto, despesa,
                     receita_obs, imposto_obs, despesa_obs):
    ws = wb.active
    ws.title = f"DRE {ano}"

    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 12
    for ci in range(3, 16):
        ws.column_dimensions[get_column_letter(ci)].width = 15

    # Row 1: Titulo
    ws.merge_cells("A1:O1")
    c = ws["A1"]
    c.value = f"{empresa} \u2014 DRE (Demonstra\u00e7\u00e3o do Resultado) \u2014 {ano}"
    c.font = _S_TITULO["font"]
    c.alignment = Alignment(horizontal="center", vertical="center")
    _fill_row(ws, 1, _S_TITULO["fill"])

    # Row 2: Subtitulo
    ws.merge_cells("A2:O2")
    c = ws["A2"]
    c.value = (
        f"Extra\u00eddo do Odoo em {hoje} | Valores em {moeda} | "
        "Moedas estrangeiras convertidas pela taxa do Odoo na data da fatura"
    )
    c.font = _S_SUBTITULO["font"]
    c.alignment = Alignment(horizontal="center")
    _fill_row(ws, 2, _S_SUBTITULO["fill"])

    # Row 4: Headers
    headers = ["Descri\u00e7\u00e3o", "Obs"] + MESES + [f"TOTAL {ano}"]
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=4, column=i, value=h)
        c.font = _S_HEADER["font"]
        c.fill = _S_HEADER["fill"]
        c.alignment = Alignment(horizontal="center")

    # ── RECEITA ──
    ws.cell(row=6, column=1, value="RECEITA OPERACIONAL BRUTA").font = _S_SECAO["font"]
    _fill_row(ws, 6, _S_SECAO["fill"])

    ws.cell(row=7, column=1, value="Receita de Servi\u00e7os (Faturamento)")
    _write_data_row(ws, 7, receita, receita_obs, _S_DADO)

    ws.cell(row=8, column=1, value="TOTAL RECEITA BRUTA")
    _write_formula_row(ws, 8, "{c}7", _S_TOTAL)

    # ── DEDUCOES ──
    ws.cell(row=10, column=1, value="(-) DEDU\u00c7\u00d5ES DA RECEITA").font = _S_SECAO["font"]
    _fill_row(ws, 10, _S_SECAO["fill"])

    ws.cell(row=11, column=1, value="(-) Impostos sobre Servi\u00e7os")
    _write_data_row(ws, 11, imposto, imposto_obs, _S_DADO)

    ws.cell(row=12, column=1, value="TOTAL DEDU\u00c7\u00d5ES")
    _write_formula_row(ws, 12, "-{c}11", _S_TOTAL)

    # ── RECEITA LIQUIDA ──
    ws.cell(row=14, column=1, value="RECEITA OPERACIONAL L\u00cdQUIDA")
    _write_formula_row(ws, 14, "{c}8+{c}12", _S_RESULT)

    # ── CSP ──
    ws.cell(row=16, column=1, value="(-) CUSTOS DOS SERVI\u00c7OS PRESTADOS").font = _S_SECAO["font"]
    _fill_row(ws, 16, _S_SECAO["fill"])

    ws.cell(row=17, column=1, value="(-) Pessoal / Servi\u00e7os Profissionais")
    _write_data_row(ws, 17,
                    despesa["Pessoal / Servi\u00e7os Profissionais"],
                    despesa_obs["Pessoal / Servi\u00e7os Profissionais"],
                    _S_DADO)

    ws.cell(row=18, column=1, value="(-) Terceiriza\u00e7\u00e3o / Subcontrata\u00e7\u00e3o")
    _write_data_row(ws, 18,
                    despesa["Terceiriza\u00e7\u00e3o / Subcontrata\u00e7\u00e3o"],
                    despesa_obs["Terceiriza\u00e7\u00e3o / Subcontrata\u00e7\u00e3o"],
                    _S_DADO)

    ws.cell(row=19, column=1, value="TOTAL CSP")
    _write_formula_row(ws, 19, "-({c}17+{c}18)", _S_TOTAL)

    # ── LUCRO BRUTO ──
    ws.cell(row=21, column=1, value="LUCRO BRUTO")
    _write_formula_row(ws, 21, "{c}14+{c}19", _S_RESULT)

    ws.cell(row=22, column=1, value="Margem Bruta %").font = _S_MARGEM["font"]
    _write_formula_row(ws, 22, "IF({c}14=0,0,{c}21/{c}14)", _S_MARGEM, FMT_PCT)

    # ── DESPESAS OPERACIONAIS ──
    ws.cell(row=24, column=1, value="(-) DESPESAS OPERACIONAIS").font = _S_SECAO["font"]
    _fill_row(ws, 24, _S_SECAO["fill"])

    ws.cell(row=25, column=1, value="(-) Software / SaaS / Infraestrutura")
    _write_data_row(ws, 25,
                    despesa["Software / SaaS / Infraestrutura"],
                    despesa_obs["Software / SaaS / Infraestrutura"],
                    _S_DADO)

    ws.cell(row=26, column=1, value="(-) Impostos e Taxas")
    _write_data_row(ws, 26,
                    despesa["Impostos e Taxas"],
                    despesa_obs["Impostos e Taxas"],
                    _S_DADO)

    ws.cell(row=28, column=1, value="TOTAL DESPESAS OPERACIONAIS")
    _write_formula_row(ws, 28, "-({c}25+{c}26)", _S_TOTAL)

    # ── EBITDA ──
    ws.cell(row=30, column=1, value="EBITDA (Resultado Operacional)")
    _write_formula_row(ws, 30, "{c}21+{c}28", _S_RESULT)

    ws.cell(row=31, column=1, value="Margem EBITDA %").font = _S_MARGEM["font"]
    _write_formula_row(ws, 31, "IF({c}14=0,0,{c}30/{c}14)", _S_MARGEM, FMT_PCT)

    # ── RESULTADO ──
    ws.cell(row=33, column=1, value="RESULTADO L\u00cdQUIDO DO EXERC\u00cdCIO")
    _write_formula_row(ws, 33, "{c}30", _S_FINAL)

    ws.cell(row=34, column=1, value="Margem L\u00edquida %").font = _S_MARGEM["font"]
    _write_formula_row(ws, 34, "IF({c}14=0,0,{c}33/{c}14)", _S_MARGEM, FMT_PCT)

    ws.freeze_panes = "C5"


# ─── Aba 2: Detalhamento Receitas ────────────────────────────────────────────


def _build_receitas_sheet(wb, ano, vendas, moeda):
    ws = wb.create_sheet(title="Detalhamento Receitas")

    ws.merge_cells("A1:H1")
    c = ws["A1"]
    c.value = f"Detalhamento de Receitas \u2014 {ano}"
    c.font = _S_TITULO["font"]
    c.fill = _S_TITULO["fill"]
    c.alignment = Alignment(horizontal="center")
    _fill_row(ws, 1, _S_TITULO["fill"], 1, 8)

    headers = ["M\u00eas", "Cliente", "Moeda Original", f"L\u00edquido ({moeda})",
               f"Impostos ({moeda})", f"Total ({moeda})", "Status", "Fatura"]
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=2, column=i, value=h)
        c.font = _S_HEADER["font"]
        c.fill = _S_HEADER["fill"]
        c.alignment = Alignment(horizontal="center")

    for i, w in enumerate([8, 35, 14, 16, 16, 16, 12, 18], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    row = 3
    for v in vendas:
        mes_num = int(v["invoice_date"].split("-")[1])
        moeda_orig = v["currency_id"][1] if v["currency_id"] else moeda
        total_brl = v["amount_total_signed"]
        untaxed_brl = v.get("amount_untaxed_signed", total_brl)
        tax_brl = total_brl - untaxed_brl
        status = "Efetivo" if v["state"] == "posted" else "Provis\u00f3rio"

        ws.cell(row=row, column=1, value=MESES[mes_num - 1])
        ws.cell(row=row, column=2, value=v["partner_id"][1] if v["partner_id"] else "")
        ws.cell(row=row, column=3, value=moeda_orig)

        for col, val in [(4, untaxed_brl), (5, tax_brl), (6, total_brl)]:
            c = ws.cell(row=row, column=col, value=round(val, 2))
            c.number_format = FMT_BRL

        sc = ws.cell(row=row, column=7, value=status)
        sc.font = _F_EFETIVO if v["state"] == "posted" else _F_PROVISORIO

        ws.cell(row=row, column=8, value=v["name"])
        row += 1

    ws.freeze_panes = "A3"


# ─── Aba 3: Detalhamento Despesas ────────────────────────────────────────────


def _build_despesas_sheet(wb, ano, linhas_compra, moeda):
    ws = wb.create_sheet(title="Detalhamento Despesas")

    n_cols = 8
    ws.merge_cells(f"A1:{get_column_letter(n_cols)}1")
    c = ws["A1"]
    c.value = f"Detalhamento de Despesas \u2014 {ano}"
    c.font = _S_TITULO["font"]
    c.fill = _S_TITULO["fill"]
    c.alignment = Alignment(horizontal="center")
    _fill_row(ws, 1, _S_TITULO["fill"], 1, n_cols)

    headers = [
        "M\u00eas", "Fornecedor", "Fatura", "Categoria",
        "Conta Anal\u00edtica", "Conta Cont\u00e1bil", f"Valor ({moeda})", "Status",
    ]
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=2, column=i, value=h)
        c.font = _S_HEADER["font"]
        c.fill = _S_HEADER["fill"]
        c.alignment = Alignment(horizontal="center")

    for i, w in enumerate([8, 28, 18, 32, 25, 30, 16, 12], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    row = 3
    for linha in linhas_compra:
        status_posted = linha["status"] == "posted"
        ws.cell(row=row, column=1, value=MESES[linha["mes"] - 1])
        ws.cell(row=row, column=2, value=linha["fornecedor"])
        ws.cell(row=row, column=3, value=linha["fatura"])
        ws.cell(row=row, column=4, value=linha["categoria"])
        ws.cell(row=row, column=5, value=linha["analitica"])
        ws.cell(row=row, column=6, value=linha["conta"])
        c = ws.cell(row=row, column=7, value=round(linha["valor"], 2))
        c.number_format = FMT_BRL
        sc = ws.cell(row=row, column=8, value="Efetivo" if status_posted else "Provis\u00f3rio")
        sc.font = _F_EFETIVO if status_posted else _F_PROVISORIO
        row += 1

    ws.freeze_panes = "A3"
