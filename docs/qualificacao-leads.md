# Qualificacao de Leads — Metodologia

Processo padrao para enriquecer e qualificar leads recebidos no CRM do Odoo.
Este documento e lido automaticamente pelo Claude (via MCP ou Claude Code) para executar a qualificacao.

---

## Quando executar

- Periodicamente (semanal ou quinzenal) sobre leads novos nao qualificados
- Leads nao qualificados sao aqueles com `priority = '0'` e sem pesquisa no campo `description`
- O campo description de leads nao qualificados contem apenas "Source: Webhook" sem tag `<b>Pesquisa:</b>`

---

## Etapa 1 — Coleta de dados

Para cada lead, extrair:
- `contact_name` — nome do contato
- `partner_name` — empresa informada (pode estar vazio ou no campo description como "Company: XXX")
- `email_from` — email (pista sobre empresa: dominio corporativo vs Gmail)
- `phone` — telefone (DDD indica regiao)
- `description` — comentarios e campo "Company" do formulario
- `website` — se preenchido

---

## Etapa 2 — Pesquisa da empresa

Para cada lead, pesquisar online:

1. **Buscar o nome da empresa** no Google (ex: "HerbCitrum empresa")
2. **Verificar se tem site** — empresas com site proprio sao mais qualificadas
3. **Verificar Instagram/redes sociais** — presenca digital indica atividade
   - **IMPORTANTE:** Sempre coletar e adicionar links dos perfis encontrados (LinkedIn, Instagram, Facebook, TikTok, etc.)
4. **Analisar o email** — dominio corporativo (empresa@empresa.com) > Gmail/Outlook
5. **Analisar o DDD** — identificar cidade/estado

### Sinais positivos (aumentam prioridade)
- Site proprio com produtos/servicos
- Email corporativo (nao Gmail/Outlook)
- Presenca em redes sociais com atividade recente (LinkedIn atualizado, Instagram/Facebook com posts regulares)
- **Links localizados para perfis de redes sociais** — sempre coletar (LinkedIn, Instagram, Facebook, TikTok, etc.)
- Empresa encontrada em cadastros (CNPJ, LinkedIn)
- Segmento com necessidade real de ERP (logistica, e-commerce, industria, servicos B2B)
- Regiao com forte atividade empresarial (SP, Campinas, Curitiba, etc.)

### Sinais negativos (reduzem prioridade)
- Email de universidade (@edu.br) — provavel estudante
- Nome da empresa = nome pessoal, handle Instagram ou sigla de 2 letras
- Empresa nao encontrada online
- Nome sem sentido (spam/bot)
- Telefone incompleto ou invalido
- Campo "Company" com conteudo academico (ODS, trabalho de escola)
- Email com typo no dominio (.gom, .con)

---

## Etapa 3 — Classificacao de prioridade

| Estrelas | Criterio | Exemplos |
|---|---|---|
| 3 | Empresa real confirmada, com site/presenca digital, segmento com necessidade de ERP | E-commerce com produto, rede de consultoras, industria |
| 2 | Empresa provavelmente real, mas sem confirmacao online; ou segmento com potencial | Transportadora sem site, consultoria com email profissional, nome plausivel em polo tech |
| 1 | Pouca informacao, possivel micro/MEI, ou sinais mistos | Email pessoal + empresa nao encontrada, mas nome plausivel |
| 0 | Spam, bot, projeto academico, ou dados muito incompletos | Nome sem sentido, handle Instagram, ODS/trabalho escolar |

---

## Etapa 4 — Atualizacao do lead

Para cada lead, atualizar:

1. **`contact_name`** — capitalizar corretamente (Title Case para nomes proprios)
   - "josilene costa" → "Josilene Costa"
   - "DIEGO NEVES ANDRADE" → "Diego Neves Andrade"
   - Manter preposicoes em minusculo: "de", "da", "do", "dos", "das"

2. **`partner_name`** — nome da empresa limpo e capitalizado
   - "souzatransportes" → "Souza Transportes"
   - "costaconsultoria,info" → "Costa Consultoria"

3. **`name`** (titulo do lead) — formato padrao:
   - `Lead Odoo: {Nome do Contato} — {Empresa}` (quando tem empresa)
   - `Lead Odoo: {Nome do Contato}` (quando nao tem empresa)

4. **`description`** — manter o "Source:" original e adicionar bloco de pesquisa:
   ```html
   <p>Source: Webhook #44<br/>Company: NomeDaEmpresa</p>
   <p><b>Pesquisa:</b> [Resultado da pesquisa online. O que a empresa faz,
   onde esta, se tem site, se tem presenca digital, segmento de atuacao.]</p>
   <p><b>Redes Sociais:</b> [Listar links para os perfis encontrados]<br/>
   Exemplo: <a href="https://linkedin.com/company/...">LinkedIn</a> | 
   <a href="https://instagram.com/...">Instagram</a> | 
   <a href="https://facebook.com/...">Facebook</a></p>
   <p><b>Potencial:</b> [Alto/Medio/Baixo. Justificativa e modulos Odoo sugeridos.]</p>
   ```

5. **`website`** — preencher se encontrado na pesquisa

6. **`priority`** — conforme tabela da Etapa 3

---

## Etapa 5 — Acoes automaticas por prioridade

### Prioridade 3 (alta) — WhatsApp + Call

1. **Enviar WhatsApp automaticamente** usando template 17 ("Abordagem Leads enviados pela Odoo").
   - Nao precisa de confirmacao do usuario — envio direto.
   - Se o telefone estiver incompleto/invalido, registrar o erro no resultado.

2. **Criar atividade tipo Call** (Ligacao):
   - **`activity_type_id: 2`** — Call (ID correto; NAO usar 4 que e To Do)
   - **Resumo:** "Ligar para {Nome} ({Empresa})"
   - **Prazo:** dia do processamento
   - **Responsavel:** usuario logado
   - **Nota:** incluir pontos especificos para abordar na ligacao:
     - Confirmar relacao do contato com a empresa
     - Entender volume/operacao
     - Mapear dores e necessidades
     - Sugerir modulos Odoo relevantes

### Prioridade 2 (media) — Revisao manual

1. **Criar atividade tipo To Do** (Revisao):
   - **`activity_type_id: 4`** — To Do (ID correto; NAO usar 5 que e Upload Document)
   - **Resumo:** "Revisar lead: {Nome} ({Empresa})"
   - **Prazo:** dia do processamento
   - **Responsavel:** usuario logado
   - **Nota:** incluir resumo da pesquisa e indicar que o usuario deve decidir manualmente
     se vale abordar (WhatsApp/ligacao) ou arquivar.

> **IDs de activity_type no Odoo (referencia):**
> `1` Email | `2` Call | `3` Meeting | `4` To Do | `5` Upload Document | `19` WhatsApp

### Prioridade 0-1 (baixa/spam) — Sem acao

Apenas atualizar dados do lead. Nenhuma atividade ou mensagem criada.

### Arquivar leads de prioridade 0

Para arquivar definitivamente, usar `active = False` (nao apenas mover de etapa):

```python
odoo.update('crm.lead', lead_id, {'active': False})
```

> **Atenção:** Mover para a etapa "Arquivadas" (`stage_id = 9`) NAO arquiva o lead — ele continua visivel na pipeline. Somente `active = False` remove o lead da pipeline.

---

## Telefones — Validacao basica

Formato valido Brasil: `+55 {DDD 2 digitos} {9 digitos}`
- Total apos +55: 11 digitos
- Se tem menos digitos: marcar como incompleto na pesquisa
- Se DDD esta faltando: tentar inferir pelo contexto (cidade/estado do lead)

### DDDs de referencia
- 11 SP capital | 19 Campinas | 15 Sorocaba | 12 S.J. Campos
- 21 RJ | 31 BH | 41 Curitiba | 51 POA
- 61 Brasilia | 62 Goiania | 65 Cuiaba | 68 Rio Branco
- 71 Salvador | 81 Recife | 85 Fortaleza
- 91 Belem | 92 Manaus | 95 Roraima | 98 S. Luis

---

## Notas

- **Moeda:** BRL (R$). Nunca assumir outra moeda.
- **Idioma:** Leads e descricoes em portugues.
- **model_id de crm.lead:** consultar via `ir.model` se necessario para criar atividades.
- **Nao alterar** leads que ja foram qualificados (que ja tem `<b>Pesquisa:</b>` na description).
