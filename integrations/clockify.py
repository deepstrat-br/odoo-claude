"""
Clockify Helper — Deepstrat
Uso: python integrations/clockify.py <comando> [args]

Comandos:
  workspaces                        Lista workspaces
  projetos                          Lista projetos do workspace
  entradas <from> <to>              Entradas de tempo (YYYY-MM-DD)
  usuario                           Dados do usuario autenticado
  comparar <from> <to>              Compara horas Clockify x Odoo (por projeto)
  comparar-rti <from> <to>          Compara RTI SOW#7 x Odoo por usuario
"""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# .env fica na raiz do projeto (dois niveis acima de integrations/)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

CLOCKIFY_KEY = os.environ.get("CLOCKIFY_KEY", "")
CLOCKIFY_BASE = "https://api.clockify.me/api/v1"
CLOCKIFY_REPORTS = "https://reports.api.clockify.me/v1"


class ClockifyClient:
    def __init__(self):
        if not CLOCKIFY_KEY:
            raise ValueError("CLOCKIFY_KEY nao configurado no .env")
        self.headers = {
            "X-Api-Key": CLOCKIFY_KEY,
            "Content-Type": "application/json",
        }
        user = self.get_user()
        self.user_id = user["id"]
        self.user_name = user.get("name", "")
        self.email = user.get("email", "")
        # workspace padrao = primeiro da lista
        workspaces = self.get_workspaces()
        self.workspace_id = workspaces[0]["id"]
        self.workspace_name = workspaces[0]["name"]

    def _get(self, url, params=None):
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"
        req = Request(url, headers=self.headers)
        with urlopen(req) as resp:
            return json.loads(resp.read())

    def _post(self, url, body):
        data = json.dumps(body).encode()
        req = Request(url, data=data, headers=self.headers, method="POST")
        with urlopen(req) as resp:
            return json.loads(resp.read())

    def get_user(self):
        return self._get(f"{CLOCKIFY_BASE}/user")

    def get_workspaces(self):
        return self._get(f"{CLOCKIFY_BASE}/workspaces")

    def get_projects(self, archived=False):
        params = {"archived": str(archived).lower(), "page-size": 500}
        return self._get(
            f"{CLOCKIFY_BASE}/workspaces/{self.workspace_id}/projects", params
        )

    def get_time_entries(self, start, end, user_id=None, project_id=None, page_size=500):
        """
        start / end: strings YYYY-MM-DD ou datetime ISO
        Retorna lista de entradas de tempo do usuario.
        """
        uid = user_id or self.user_id
        # Clockify exige ISO 8601 com Z
        start_iso = _to_iso(start)
        end_iso = _to_iso(end, end_of_day=True)
        params = {
            "start": start_iso,
            "end": end_iso,
            "page-size": page_size,
        }
        if project_id:
            params["project"] = project_id
        return self._get(
            f"{CLOCKIFY_BASE}/workspaces/{self.workspace_id}/user/{uid}/time-entries",
            params,
        )

    def detailed_report(self, start, end, project_ids=None):
        """
        Usa a Reports API para obter relatorio detalhado por projeto/tarefa.
        Requer permissao de relatorios no plano.
        """
        body = {
            "dateRangeStart": _to_iso(start),
            "dateRangeEnd": _to_iso(end, end_of_day=True),
            "detailedFilter": {"page": 1, "pageSize": 1000},
        }
        if project_ids:
            body["projects"] = {"ids": project_ids, "contains": "CONTAINS"}
        return self._post(
            f"{CLOCKIFY_REPORTS}/workspaces/{self.workspace_id}/reports/detailed",
            body,
        )

    def summary_by_project(self, start, end):
        """Agrupa entradas de tempo por projeto (usando time-entries do usuario)."""
        entries = self.get_time_entries(start, end)
        projects = {p["id"]: p["name"] for p in self.get_projects()}

        summary = {}
        for e in entries:
            pid = (e.get("projectId") or "sem_projeto")
            pname = projects.get(pid, pid)
            dur = _parse_duration(e.get("timeInterval", {}).get("duration", "PT0S"))
            summary.setdefault(pname, 0.0)
            summary[pname] += dur

        return dict(sorted(summary.items(), key=lambda x: x[1], reverse=True))


# ── helpers ────────────────────────────────────────────────────────────────────

def _to_iso(date_str, end_of_day=False):
    """Converte YYYY-MM-DD para ISO 8601 UTC com Z."""
    if "T" in str(date_str):
        return date_str if date_str.endswith("Z") else date_str + "Z"
    suffix = "T23:59:59Z" if end_of_day else "T00:00:00Z"
    return f"{date_str}{suffix}"


def _parse_duration(iso_dur):
    """Converte duração ISO 8601 (PT1H30M) para horas decimais."""
    if not iso_dur or iso_dur == "PT0S":
        return 0.0
    import re
    h = int(re.search(r"(\d+)H", iso_dur).group(1)) if "H" in iso_dur else 0
    m = int(re.search(r"(\d+)M", iso_dur).group(1)) if "M" in iso_dur else 0
    s = int(re.search(r"(\d+)S", iso_dur).group(1)) if "S" in iso_dur else 0
    return h + m / 60 + s / 3600


def _fmt_h(h):
    return f"{h:.2f}h"


# ── CLI ────────────────────────────────────────────────────────────────────────

def cmd_workspaces(args):
    c = ClockifyClient()
    for w in c.get_workspaces():
        print(f"  {w['id']}  {w['name']}")


def cmd_usuario(args):
    c = ClockifyClient()
    print(f"  Nome:      {c.user_name}")
    print(f"  Email:     {c.email}")
    print(f"  User ID:   {c.user_id}")
    print(f"  Workspace: {c.workspace_name} ({c.workspace_id})")


def cmd_projetos(args):
    c = ClockifyClient()
    projects = c.get_projects()
    print(f"{'Nome':<40} {'ID'}")
    print("-" * 70)
    for p in projects:
        status = " [arquivado]" if p.get("archived") else ""
        print(f"  {p['name']:<38} {p['id']}{status}")


def cmd_entradas(args):
    if len(args) < 2:
        print("Uso: python clockify.py entradas <from YYYY-MM-DD> <to YYYY-MM-DD>")
        return
    start, end = args[0], args[1]
    c = ClockifyClient()
    entries = c.get_time_entries(start, end)
    projects = {p["id"]: p["name"] for p in c.get_projects()}

    print(f"{'Data':<12} {'Projeto':<35} {'Descricao':<40} {'Horas':>7}")
    print("-" * 100)
    total = 0.0
    for e in entries:
        pid = e.get("projectId", "")
        pname = projects.get(pid, "—")
        desc = (e.get("description") or "")[:39]
        dur = _parse_duration(e.get("timeInterval", {}).get("duration", "PT0S"))
        start_dt = (e.get("timeInterval", {}).get("start", "")[:10])
        print(f"  {start_dt:<10} {pname:<35} {desc:<40} {dur:>6.2f}h")
        total += dur
    print("-" * 100)
    print(f"  {'TOTAL':>88} {total:>6.2f}h")


def cmd_comparar(args):
    """Compara horas lancadas no Clockify com timesheets do Odoo, por projeto."""
    if len(args) < 2:
        print("Uso: python clockify.py comparar <from YYYY-MM-DD> <to YYYY-MM-DD>")
        return
    start, end = args[0], args[1]

    # --- Clockify ---
    c = ClockifyClient()
    clockify_summary = c.summary_by_project(start, end)

    # --- Odoo ---
    import xmlrpc.client
    ODOO_URL = os.environ.get("ODOO_URL", "https://deepstrat.odoo.com")
    ODOO_DB = os.environ.get("ODOO_DB", "deepstrat")
    ODOO_LOGIN = os.environ.get("ODOO_LOGIN", "")
    ODOO_KEY = os.environ.get("ODOO_KEY", "")

    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_LOGIN, ODOO_KEY, {})
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

    timesheets = models.execute_kw(
        ODOO_DB, uid, ODOO_KEY,
        "account.analytic.line", "search_read",
        [[["date", ">=", start], ["date", "<=", end], ["project_id", "!=", False]]],
        {"fields": ["project_id", "unit_amount"], "limit": 5000}
    )

    odoo_summary = {}
    for ts in timesheets:
        pname = ts["project_id"][1]
        odoo_summary.setdefault(pname, 0.0)
        odoo_summary[pname] += ts["unit_amount"]

    # --- Comparativo ---
    all_projects = sorted(set(list(clockify_summary) + list(odoo_summary)))

    print(f"\nPeriodo: {start} a {end}")
    print(f"{'Projeto':<40} {'Clockify':>10} {'Odoo':>10} {'Diff':>10}")
    print("-" * 75)

    total_cf = total_od = 0.0
    for p in all_projects:
        cf = clockify_summary.get(p, 0.0)
        od = odoo_summary.get(p, 0.0)
        diff = cf - od
        flag = " !" if abs(diff) > 0.25 else ""
        print(f"  {p:<38} {cf:>9.2f}h {od:>9.2f}h {diff:>+9.2f}h{flag}")
        total_cf += cf
        total_od += od

    print("-" * 75)
    diff_total = total_cf - total_od
    print(f"  {'TOTAL':<38} {total_cf:>9.2f}h {total_od:>9.2f}h {diff_total:>+9.2f}h")


def cmd_comparar_rti(args):
    """Compara RTI SOW#7 (Clockify) vs RTI Staffing Model (Odoo) por usuario."""
    if len(args) < 2:
        print("Uso: python clockify.py comparar-rti <from YYYY-MM-DD> <to YYYY-MM-DD>")
        return
    start, end = args[0], args[1]

    c = ClockifyClient()
    RTI_CF_PROJECT = "68cc2795436bab22d09d1cd9"
    RTI_ODOO_PROJECT = 20

    # Mapeamento Odoo employee -> Clockify user ID
    team = [
        ("Vagner Kogikoski Jr.", "Vagner Kogikoski",   "6870160f154d994d47964b94"),
        ("Carlos Gottardi",      "Carlos Gottardi",    "698668b02b4755a9290cfc31"),
        ("Thiago Monteiro",      "Thiago Monteiro",    "68dc33814749ad1b8775c0ef"),
        ("Vinay Jain",           "Vinay jain",         "69b873636ceaf91e50e0ae8d"),
        ("Stefano Tavanielli",   "Stefano Tavanielli", "69c576158be1757f0a869bac"),
    ]

    # Clockify por usuario
    cf_hours = {}
    for _, cf_name, cf_uid in team:
        url = (
            f"{CLOCKIFY_BASE}/workspaces/{c.workspace_id}/user/{cf_uid}/time-entries"
            f"?project={RTI_CF_PROJECT}&start={_to_iso(start)}&end={_to_iso(end, end_of_day=True)}&page-size=500"
        )
        entries = c._get(url)
        cf_hours[cf_name] = sum(
            _parse_duration(e.get("timeInterval", {}).get("duration", "PT0S"))
            for e in entries
        )

    # Odoo por funcionario
    import xmlrpc.client
    ODOO_URL = os.environ.get("ODOO_URL")
    ODOO_DB  = os.environ.get("ODOO_DB")
    ODOO_LOGIN = os.environ.get("ODOO_LOGIN")
    ODOO_KEY   = os.environ.get("ODOO_KEY")
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_LOGIN, ODOO_KEY, {})
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    ts = models.execute_kw(ODOO_DB, uid, ODOO_KEY,
        "account.analytic.line", "search_read",
        [[["project_id", "=", RTI_ODOO_PROJECT],
          ["date", ">=", start], ["date", "<=", end]]],
        {"fields": ["employee_id", "unit_amount"], "limit": 2000})

    odoo_hours = {}
    for t in ts:
        emp = t["employee_id"][1]
        odoo_hours[emp] = odoo_hours.get(emp, 0.0) + t["unit_amount"]

    print(f"\nRTI SOW#7 (Clockify) vs RTI Staffing Model (Odoo) | {start} a {end}")
    print("%-25s %10s %10s %10s  %s" % ("Usuario", "Clockify", "Odoo", "Diff", ""))
    print("-" * 65)
    total_cf = total_od = 0.0
    for odoo_n, cf_n, _ in team:
        cf = cf_hours.get(cf_n, 0.0)
        od = odoo_hours.get(odoo_n, 0.0)
        diff = cf - od
        flag = "DIVERGE !" if abs(diff) > 0.01 else "OK"
        print("  %-23s %9.2fh %9.2fh %+9.2fh  %s" % (odoo_n, cf, od, diff, flag))
        total_cf += cf
        total_od += od
    print("-" * 65)
    diff = total_cf - total_od
    flag = "DIVERGE !" if abs(diff) > 0.01 else "OK"
    print("  %-23s %9.2fh %9.2fh %+9.2fh  %s" % ("TOTAL", total_cf, total_od, diff, flag))


COMMANDS = {
    "workspaces": cmd_workspaces,
    "usuario": cmd_usuario,
    "projetos": cmd_projetos,
    "entradas": cmd_entradas,
    "comparar": cmd_comparar,
    "comparar-rti": cmd_comparar_rti,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
