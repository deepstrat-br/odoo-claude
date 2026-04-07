#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_tasks.py — Criacao em lote de tarefas no Odoo a partir de um arquivo YAML.

Uso (da raiz do projeto):
  python scripts/project/import_tasks.py data/tasks/sudoeste_ambiental.yaml
  python scripts/project/import_tasks.py data/tasks/meu_cliente.yaml --dry-run
  python scripts/project/import_tasks.py data/tasks/meu_cliente.yaml --projeto "Projeto X"

Formato do YAML (ver data/tasks/sudoeste_ambiental.yaml como referencia):
  project: nome ou ID do projeto (pode ser sobrescrito com --projeto)
  tasks:
    - name: "Nome da Tarefa"       # obrigatorio
      stage: "Backlog"             # nome da etapa (ou ID numerico)
      milestone: "Marco 1"         # nome ou ID do milestone
      hours: 4.0                   # horas planejadas
      deadline: "2026-05-10"       # prazo (YYYY-MM-DD)
      tags: [Vendas, CRM]          # nomes das tags (ou IDs)
      assignees: [vagner@...]      # login, nome ou ID dos usuarios
      description:                 # lista de itens -> <ul><li>...</li></ul>
        - "Item 1"
        - "Item 2"
"""

import sys
import os
import argparse

# Garante que odoo.py (raiz do projeto) seja encontrado independente de onde o script e chamado
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    import yaml
except ImportError:
    print("Dependencia ausente: pip install pyyaml")
    sys.exit(1)

from odoo import OdooClient


# ─── Helpers ──────────────────────────────────────────────────────────────────

def html_list(items):
    lines = ''.join(f'<li>{i}</li>' for i in items)
    return f'<ul>{lines}</ul>'


def coerce_id(value):
    """Converte valor para int se possivel, senao retorna None."""
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ─── Resolver ─────────────────────────────────────────────────────────────────

class Resolver:
    """Resolve nomes para IDs no Odoo com cache por sessao."""

    def __init__(self, odoo):
        self.odoo = odoo
        self._tags = {}        # name -> id
        self._stages = {}      # name -> id  (globais no Odoo)
        self._milestones = {}  # (project_id, name) -> id
        self._users = {}       # login/name -> id

    def project(self, name_or_id):
        pid = coerce_id(name_or_id)
        if pid:
            return pid
        r = self.odoo.search('project.project', [['name', '=', name_or_id]], ['id'], limit=1)
        if not r:
            r = self.odoo.search('project.project', [['name', 'ilike', name_or_id]], ['id'], limit=1)
        if not r:
            raise ValueError(f"Projeto nao encontrado: {name_or_id!r}")
        return r[0]['id']

    def tags(self, names):
        if not names:
            return [(6, 0, [])]
        ids = []
        for name in names:
            pid = coerce_id(name)
            if pid:
                ids.append(pid)
                continue
            if name not in self._tags:
                r = self.odoo.search('project.tags', [['name', '=', name]], ['id'], limit=1)
                if not r:
                    raise ValueError(f"Tag nao encontrada: {name!r}")
                self._tags[name] = r[0]['id']
            ids.append(self._tags[name])
        return [(6, 0, ids)]

    def stage(self, name_or_id):
        if name_or_id is None:
            return None
        sid = coerce_id(name_or_id)
        if sid:
            return sid
        if name_or_id not in self._stages:
            r = self.odoo.search('project.task.type', [['name', '=', name_or_id]], ['id'], limit=1)
            if not r:
                r = self.odoo.search('project.task.type', [['name', 'ilike', name_or_id]], ['id'], limit=1)
            if not r:
                raise ValueError(f"Etapa nao encontrada: {name_or_id!r}")
            self._stages[name_or_id] = r[0]['id']
        return self._stages[name_or_id]

    def milestone(self, project_id, name_or_id):
        if name_or_id is None:
            return None
        mid = coerce_id(name_or_id)
        if mid:
            return mid
        key = (project_id, name_or_id)
        if key not in self._milestones:
            r = self.odoo.search('project.milestone', [
                ['project_id', '=', project_id],
                ['name', '=', name_or_id],
            ], ['id'], limit=1)
            if not r:
                r = self.odoo.search('project.milestone', [
                    ['project_id', '=', project_id],
                    ['name', 'ilike', name_or_id],
                ], ['id'], limit=1)
            if not r:
                raise ValueError(f"Milestone nao encontrado: {name_or_id!r}")
            self._milestones[key] = r[0]['id']
        return self._milestones[key]

    def users(self, names_or_ids):
        if not names_or_ids:
            return []
        ids = []
        for n in names_or_ids:
            uid = coerce_id(n)
            if uid:
                ids.append(uid)
                continue
            if n not in self._users:
                r = self.odoo.search('res.users', [['login', '=', n]], ['id'], limit=1)
                if not r:
                    r = self.odoo.search('res.users', [['name', 'ilike', n]], ['id'], limit=1)
                if not r:
                    raise ValueError(f"Usuario nao encontrado: {n!r}")
                self._users[n] = r[0]['id']
            ids.append(self._users[n])
        return ids


# ─── Build ────────────────────────────────────────────────────────────────────

def build_task_vals(raw, project_id, resolver):
    if 'name' not in raw:
        raise ValueError("Campo 'name' e obrigatorio em cada tarefa")

    vals = {'project_id': project_id, 'name': raw['name']}

    if 'stage' in raw:
        vals['stage_id'] = resolver.stage(raw['stage'])
    if 'milestone' in raw:
        vals['milestone_id'] = resolver.milestone(project_id, raw['milestone'])
    if 'tags' in raw:
        vals['tag_ids'] = resolver.tags(raw['tags'])
    if 'assignees' in raw:
        vals['user_ids'] = resolver.users(raw['assignees'])
    if 'hours' in raw:
        vals['allocated_hours'] = float(raw['hours'])
    if 'deadline' in raw:
        vals['date_deadline'] = str(raw['deadline'])
    if 'priority' in raw:
        vals['priority'] = str(raw['priority'])
    if 'description' in raw:
        desc = raw['description']
        vals['description'] = html_list(desc) if isinstance(desc, list) else str(desc)

    return vals


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Cria tarefas no Odoo a partir de um arquivo YAML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('arquivo', help='Arquivo YAML com as tarefas')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simula a criacao sem gravar no Odoo')
    parser.add_argument('--projeto', metavar='NOME_OU_ID',
                        help='Sobrescreve o projeto definido no YAML')
    args = parser.parse_args()

    with open(args.arquivo, encoding='utf-8') as f:
        data = yaml.safe_load(f)

    odoo = OdooClient()
    resolver = Resolver(odoo)

    project_ref = args.projeto or data.get('project')
    if not project_ref:
        print("Erro: defina 'project' no YAML ou use --projeto <nome_ou_id>")
        sys.exit(1)

    project_id = resolver.project(project_ref)
    raw_tasks = data.get('tasks', [])

    prefix = '[DRY RUN] ' if args.dry_run else ''
    print(f"Projeto ID: {project_id}")
    print(f"{prefix}Processando {len(raw_tasks)} tarefas...\n")

    total_hours = 0.0
    errors = []

    for i, raw in enumerate(raw_tasks, 1):
        try:
            vals = build_task_vals(raw, project_id, resolver)
            hours = vals.get('allocated_hours', 0.0)
            total_hours += hours

            ms_label = str(raw.get('milestone', '—'))[:22]
            name_label = vals['name'][:50]

            if args.dry_run:
                print(f"  [{i:02d}] {hours:4.0f}h  {ms_label:<22}  {name_label}")
            else:
                tid = odoo.create('project.task', vals)
                print(f"  [{i:02d}] ID {tid:<6} {hours:4.0f}h  {name_label}")

        except Exception as e:
            errors.append((i, raw.get('name', '?'), str(e)))
            print(f"  [{i:02d}] ERRO: {e}")

    status = 'simuladas' if args.dry_run else 'criadas'
    print(f"\nTotal: {len(raw_tasks) - len(errors)} tarefas {status} | {total_hours:.0f}h planejadas")
    if errors:
        print(f"\n{len(errors)} erro(s):")
        for idx, name, err in errors:
            print(f"  [{idx:02d}] {name}: {err}")
        sys.exit(1)


if __name__ == '__main__':
    main()
