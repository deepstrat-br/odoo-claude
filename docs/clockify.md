# Clockify — Integracao e Comparacao com Odoo

Como a Deepstrat usa o Clockify para registro de horas em projetos Ryse, e como comparar esses lancamentos com os timesheets do Odoo.

---

## Contexto

O Clockify e o sistema oficial de timesheet da **Ryse Technologies**. Todos os membros da equipe Deepstrat alocados em projetos Ryse lancam horas la. O Odoo e o sistema interno da Deepstrat — as mesmas horas precisam ser replicadas la para controle financeiro e faturamento.

A comparacao entre os dois sistemas garante que nada ficou de fora antes de emitir faturas.

---

## Configuracao

### API Key

Adicione sua chave no arquivo `.env` na raiz do projeto:

```
CLOCKIFY_KEY=sua_chave_aqui
```

Para obter a chave: **Clockify > Preferencias de perfil > API > Gerar API Key**

### Workspace

O workspace padrao e detectado automaticamente (primeiro da lista). O workspace atual e **Ryse** (`60217438c804cc7e0bac0f1a`).

---

## CLI — Comandos disponiveis

```bash
python clockify.py <comando> [args]
```

### `usuario`
Exibe dados do usuario autenticado e workspace ativo.

```bash
python clockify.py usuario
```

```
Nome:      Vagner Kogikoski
Email:     vagner.kogikoski@rysetechnologies.com
Workspace: Ryse (60217438c804cc7e0bac0f1a)
```

---

### `workspaces`
Lista todos os workspaces disponiveis para a conta.

```bash
python clockify.py workspaces
```

---

### `projetos`
Lista os projetos do workspace ativo.

```bash
python clockify.py projetos
```

```
Nome                                     ID
----------------------------------------------------------------------
  HCG Danos SOW#X SQL DB Cloud Migration 699749b967dd31067dcf35cb
  RTI SOW#7 Fabric Staffing Prediction   68cc2795436bab22d09d1cd9
  Ryse XIAD Training                     686fc6a28f248e4e26968c14
```

---

### `entradas <from> <to>`
Lista todas as entradas de tempo do usuario autenticado no periodo.

```bash
python clockify.py entradas 2026-03-01 2026-03-31
```

Mostra: data, projeto, descricao e horas por entrada, com total ao final.

---

### `comparar <from> <to>`
Compara horas do usuario autenticado no Clockify com os timesheets do Odoo, agrupado por projeto.

```bash
python clockify.py comparar 2026-03-01 2026-03-31
```

> Nota: os nomes de projeto diferem entre os sistemas (ex: "RTI SOW#7 Fabric Staffing" no Clockify vs "RTI Staffing Model" no Odoo). Use `comparar-rti` para uma comparacao precisa do projeto RTI.

---

### `comparar-rti <from> <to>`
Comparacao especializada do projeto RTI: cruza horas do **RTI SOW#7** (Clockify) com o projeto **RTI Staffing Model** (Odoo #20), **por usuario**.

> **Importante:** ao consultar `account.analytic.line` para comparacao de timesheets, sempre filtrar `['employee_id', '!=', False]`. Registros sem `employee_id` sao lancamentos de outros tipos (custos, servicos de terceiros) e nao devem ser incluidos na comparacao com o Clockify.

```bash
python clockify.py comparar-rti 2026-03-01 2026-03-31
```

Exemplo de saida:

```
RTI SOW#7 (Clockify) vs RTI Staffing Model (Odoo) | 2026-03-01 a 2026-03-31
Usuario                     Clockify       Odoo       Diff
-----------------------------------------------------------------
  Vagner Kogikoski Jr.        10.50h     10.50h     +0.00h  OK
  Carlos Gottardi             38.50h     38.50h     +0.00h  OK
  Thiago Monteiro              5.00h      5.00h     +0.00h  OK
  Vinay Jain                  13.75h     13.75h     +0.00h  OK
  Stefano Tavanielli           1.00h      1.00h     +0.00h  OK
-----------------------------------------------------------------
  TOTAL                       68.75h     68.75h     +0.00h  OK
```

Qualquer linha marcada como `DIVERGE !` indica diferenca superior a 0,01h entre os sistemas.

---

## Modulo Python

O `ClockifyClient` pode ser usado diretamente em scripts:

```python
from clockify import ClockifyClient

c = ClockifyClient()

# Projetos do workspace
projetos = c.get_projects()

# Entradas de tempo (usuario autenticado)
entradas = c.get_time_entries("2026-03-01", "2026-03-31")

# Resumo de horas por projeto
resumo = c.summary_by_project("2026-03-01", "2026-03-31")
# { "RTI SOW#7 ...": 22.17, "Ryse XIAD Training": 27.0, ... }
```

### API disponivel

| Metodo | Descricao |
|---|---|
| `get_user()` | Dados do usuario autenticado |
| `get_workspaces()` | Lista de workspaces |
| `get_projects(archived=False)` | Projetos do workspace |
| `get_time_entries(start, end, user_id, project_id)` | Entradas de tempo |
| `summary_by_project(start, end)` | Total de horas por projeto |

---

## Mapeamento de projetos (Clockify x Odoo)

| Projeto Clockify | Projeto Odoo | ID Odoo |
|---|---|---|
| RTI SOW#7 Fabric Staffing Prediction Modeling | RTI Staffing Model | 20 |
| Ryse XIAD Training | — | (lancado direto na fatura) |
| HCG Danos SOW#X SQL DB Cloud Migration | — | (projeto HCG, sem Odoo ainda) |

---

## Mapeamento de usuarios (Clockify x Odoo)

| Nome Odoo | Nome Clockify | Clockify User ID | Odoo Employee ID |
|---|---|---|---|
| Vagner Kogikoski Jr. | Vagner Kogikoski | `6870160f154d994d47964b94` | 1 |
| Carlos Gottardi | Carlos Gottardi | `698668b02b4755a9290cfc31` | 2 |
| Thiago Monteiro | Thiago Monteiro | `68dc33814749ad1b8775c0ef` | 4 |
| Vinay Jain | Vinay jain | `69b873636ceaf91e50e0ae8d` | 6 |
| Stefano Tavanielli | Stefano Tavanielli | `69c576158be1757f0a869bac` | 7 |

---

## Mapeamento de tarefas e papeis — RTI SOW#7

Cada membro da equipe tem um papel de faturamento fixo que determina qual tarefa e linha do pedido usar no Odoo, independente do sub-task do Clockify.

| Membro | Papel | Tarefa Odoo | ID Task | SOL S00123 | Preco |
|---|---|---|---|---|---|
| Vagner | Partner | Assessoria em Gestao de Processos (Partner) | 726 | Linha 345 | USD 69/h |
| Carlos Gottardi | Consultant | Assessoria em Gestao de Processos (Consultant) | 728 | Linha 347 | USD 53,8/h |
| Vinay Jain | Consultant | Assessoria em Gestao de Processos (Consultant) | 728 | Linha 347 | USD 53,8/h |
| Thiago Monteiro | PMO Consultant | Assessoria em Gestao de Projetos PMO (Consultant) | 727 | Linha 346 | USD 53,8/h |
| Stefano Tavanielli | Consultant | Assessoria em Gestao de Processos (Consultant) | 728 | Linha 347 | USD 53,8/h |

### Tarefas Clockify x Tarefas Odoo

As sub-tasks do Clockify nao tem correspondencia direta no Odoo. Todas as horas de um membro vao para a tarefa do seu papel, independente da sub-task:

| Sub-task Clockify | Clockify Task ID | Odoo: usar tarefa do papel do membro |
|---|---|---|
| 0.2 Meetings and Status updates | `69a68678e3014a23e8a94aae` | task do papel (726 / 727 / 728) |
| 2.3 Model Training & Baseline Implementation | `69a1096423746f837ee88b48` | task do papel (726 / 727 / 728) |

> **Regra:** o papel e fixo por membro. Nao criar tarefas separadas por sub-task do Clockify.

---

## Como replicar entradas do Clockify no Odoo

Quando o `comparar-rti` apontar `DIVERGE`, siga este processo:

### 1. Identificar entradas faltantes

```bash
python clockify.py comparar-rti 2026-04-01 2026-04-30
```

### 2. Buscar as entradas detalhadas do usuario divergente

```python
from clockify import ClockifyClient
import json

c = ClockifyClient()
# Substituir user ID pelo do membro divergente
entradas = c.get_time_entries("2026-04-01", "2026-04-30",
    user_id="69b873636ceaf91e50e0ae8d",   # Vinay
    project_id="68cc2795436bab22d09d1cd9"  # RTI SOW#7
)
for e in entradas:
    print(e['timeInterval']['start'][:10], e['description'], e['timeInterval']['duration'])
```

### 3. Criar as entradas no Odoo

```python
from odoo import OdooClient

odoo = OdooClient()

# Uma entrada por linha do Clockify, preservando data e descricao
odoo.create('account.analytic.line', {
    'date':        '2026-04-01',
    'employee_id': 6,           # ID Odoo do funcionario
    'project_id':  20,          # RTI Staffing Model
    'task_id':     728,         # tarefa do papel do membro
    'unit_amount': 1.0,         # horas
    'name':        'Descricao exata do Clockify',
})
```

### 4. Confirmar

```bash
python clockify.py comparar-rti 2026-04-01 2026-04-30
# Todos devem mostrar OK
```

---

## Fluxo recomendado no fechamento mensal

1. **Verificar divergencias** — `comparar-rti` no periodo do mes
2. **Replicar entradas faltantes** — seguir o processo acima, mantendo descricao e data exatas do Clockify
3. **Validar novamente** — todos os membros com `OK` e totais batem
4. **Faturar** — emitir fatura no Odoo com base no `amount_residual` do pedido S00123

```bash
# Rotina de fechamento
python clockify.py comparar-rti 2026-04-01 2026-04-30
# corrigir divergencias se houver
python clockify.py comparar-rti 2026-04-01 2026-04-30  # validar novamente
```

---

## Limitacoes

- **Reports API**: o plano atual nao inclui acesso a `reports.api.clockify.me`. O resumo por projeto e calculado localmente a partir das entradas do usuario autenticado.
- **Acesso a outros usuarios**: a API permite buscar entradas de outros membros do workspace quando o ID do usuario e conhecido. Os IDs dos membros Deepstrat estao mapeados acima.
- **Moeda**: o Clockify nao tem informacao de moeda — os projetos Ryse sao faturados em USD. A conversao para BRL e feita no Odoo no momento do lancamento da fatura.
