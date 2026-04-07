# Projetos & Timesheets — Principios e Convencoes

Como a Deepstrat usa projetos e timesheets no Odoo. Este arquivo descreve o **por que** e o **como** — nao IDs ou dados especificos de projetos.

---

## Projetos

### Responsabilidade e ciclo de vida

Todo projeto deve ter um gerente (`user_id`) definido. Projetos sem gerente ficam orfaos e nao aparecem em relatorios pessoais. O ciclo esperado e:

1. Criacao com cliente, gerente e datas de inicio/fim
2. Tarefas planejadas no backlog antes de iniciar
3. Execucao com horas lancadas em tarefas especificas
4. Encerramento formal: projetos concluidos devem ser arquivados (`active = False`), nao deixados ativos indefinidamente

### Datas sao obrigatorias

`date_start` e `date` (prazo final) devem ser preenchidos em todo projeto. Sem datas nao ha visibilidade de timeline nem alertas de atraso.

---

## Tarefas

### Fluxo esperado

```
Backlog → A fazer → Em andamento → QA/QC → Concluido
                  ↘ Aguardando ↗
                  ↘ Bloqueado  ↗
```

- **Backlog**: identificada mas nao priorizada. Pode ficar aqui indefinidamente.
- **A fazer**: priorizada e pronta para iniciar — alguem vai pegar em breve.
- **Em andamento**: trabalho ativo. Deve ter responsavel e horas sendo lancadas.
- **Aguardando**: dependencia externa (cliente, aprovacao, fornecedor). Nao e impedimento interno.
- **Bloqueado**: impedimento interno — tecnico ou de recurso. Requer resolucao ativa.
- **QA/QC**: desenvolvimento concluido, aguardando revisao ou validacao.
- **Concluido**: aceita e encerrada.

Nunca pular de Backlog para Concluido sem registrar horas ou sem passar por Em andamento.

### Responsavel e estimativas

- Toda tarefa em andamento deve ter responsavel (`user_ids`)
- Horas planejadas (`allocated_hours`) devem ser preenchidas antes de iniciar — sem estimativa nao ha como medir estouro
- Tarefas sem prazo (`date_deadline`) nao aparecem em alertas de vencimento

### Prioridade

`priority = 1` (urgente) deve ser usado com moderacao. Se tudo e urgente, nada e.

---

## Timesheets

### Principios de lancamento

- Lancar horas no mesmo dia ou no dia seguinte. Lancamentos retroativos de semanas perdem confiabilidade.
- Cada lancamento deve ter uma descricao (`name`) do que foi feito — nao apenas "desenvolvimento".
- Sempre vincular a uma tarefa (`task_id`) quando possivel. Horas soltas no projeto dificultam analise por tarefa.
- A data do lancamento (`date`) deve refletir o dia em que o trabalho ocorreu, nao o dia do lancamento.

### Validacao

Horas nao validadas podem ser editadas pelo funcionario. Apos validacao pelo gestor, so o gestor pode corrigir. A validacao deve ocorrer semanalmente, nao ao final do mes.

### O que as horas revelam

O timesheet e a unica fonte de verdade sobre onde o tempo da equipe foi gasto. Inconsistencias comuns:

- Tarefa "Em andamento" sem horas lancadas → trabalho acontecendo fora do sistema
- Horas em tarefas de backlog → trabalho sendo feito sem priorizacao formal
- Projeto com horas acima de 120% do planejado → escopo cresceu sem revisao de estimativa
- Funcionario sem horas na semana → ou nao lancou, ou esta alocado em projeto nao mapeado

### Metricas de saude

| Metrica | Sinal saudavel |
|---|---|
| `effective_hours / allocated_hours` por tarefa | Entre 70% e 130% |
| Horas nao validadas | Zero ao fim de cada semana |
| Tarefas "Em andamento" sem horas recentes | Zero — ou mover para Aguardando/Bloqueado |
| Tarefas com prazo vencido e nao concluidas | Necessita decisao: estender prazo ou cancelar |

---

## Relacao entre tarefas e horas

O campo `effective_hours` na tarefa e calculado automaticamente a partir dos timesheets vinculados. Nao editar diretamente. O ciclo correto e:

1. Planejar horas na tarefa (`allocated_hours`)
2. Lacar horas nos timesheets conforme trabalho avanca
3. `effective_hours` e `remaining_hours` se atualizam automaticamente
4. Usar esses campos para decidir se a tarefa precisa de mais tempo ou esta dentro do plano

---

## Sinais de que o processo esta quebrado

- Muitas tarefas em "Em andamento" simultaneamente por uma mesma pessoa → falta de foco
- Backlog crescendo sem priorizacao → acumulo de debito de planejamento
- Horas lancadas somente no ultimo dia do mes → lancamento em lote, nao rastreavel
- Projeto encerrado com tarefas abertas → encerramento nao foi formalizado
- Estouro de horas sem registro de causa → escopo cresceu silenciosamente
