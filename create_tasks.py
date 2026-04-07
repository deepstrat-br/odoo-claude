# -*- coding: utf-8 -*-
from odoo import OdooClient
import json

odoo = OdooClient()

# Tag IDs
TAG = {
    'Planejamento': 31, 'Cadastros Base': 30, 'Vendas': 32, 'CRM': 43,
    'Financas': 39, 'CPCR': 35, 'Frotas': 38, 'Inventario': 29,
    'Marketing': 26, 'Site': 36, 'Treinamento': 37, 'Compras': 44,
    'RH': 45, 'Servicos': 46, 'Gestao': 47,
}

# Milestone IDs
MS = {1: 67, 2: 68, 3: 69, 4: 70, 5: 71, 6: 72}

BACKLOG = 43
A_FAZER = 71
PROJECT = 22


def html(items):
    lines = ''.join(f'<li>{i}</li>' for i in items)
    return f'<ul>{lines}</ul>'


def tags(*names):
    return [(6, 0, [TAG[n] for n in names])]


tasks = [
    # === MARCO 1 - Planejamento e Configuracao Base ===
    {
        'name': 'Kickoff e Planejamento do Projeto',
        'project_id': PROJECT, 'milestone_id': MS[1], 'stage_id': A_FAZER,
        'allocated_hours': 5.0, 'date_deadline': '2026-04-18',
        'tag_ids': tags('Planejamento', 'Gestao'),
        'user_ids': [2],
        'description': html([
            'Reuniao de kickoff com stakeholders',
            'Levantamento detalhado de requisitos por modulo',
            'Definicao de cronograma e responsaveis',
            'Alinhamento de expectativas e criterios de aceite',
        ])
    },
    {
        'name': 'Configuracao do Ambiente e Parametros Gerais',
        'project_id': PROJECT, 'milestone_id': MS[1], 'stage_id': BACKLOG,
        'allocated_hours': 4.0, 'date_deadline': '2026-04-22',
        'tag_ids': tags('Planejamento'),
        'description': html([
            'Parametros da empresa (moeda, idioma, fuso horario)',
            'Definicao de numeracao de documentos',
            'Configuracao de e-mail e notificacoes',
            'Ativacao dos modulos base',
        ])
    },
    {
        'name': 'Cadastros Mestres (Clientes, Fornecedores, Produtos)',
        'project_id': PROJECT, 'milestone_id': MS[1], 'stage_id': BACKLOG,
        'allocated_hours': 5.0, 'date_deadline': '2026-04-28',
        'tag_ids': tags('Cadastros Base'),
        'description': html([
            'Importacao/cadastro de clientes e fornecedores',
            'Cadastro de produtos, servicos e categorias',
            'Campos fiscais (CNPJ, IE, enderecos)',
            'Cadastro de contas bancarias da empresa',
        ])
    },
    {
        'name': 'Seguranca e Perfis de Acesso',
        'project_id': PROJECT, 'milestone_id': MS[1], 'stage_id': BACKLOG,
        'allocated_hours': 3.0, 'date_deadline': '2026-04-30',
        'tag_ids': tags('Planejamento'),
        'description': html([
            'Definicao de perfis de acesso por area',
            'Criacao de usuarios',
            'Associacao de permissoes',
            'Teste de restricoes por perfil',
        ])
    },
    {
        'name': 'Gestao de Projeto - Marco 1',
        'project_id': PROJECT, 'milestone_id': MS[1], 'stage_id': BACKLOG,
        'allocated_hours': 3.0, 'date_deadline': '2026-05-02',
        'tag_ids': tags('Gestao'),
        'description': html([
            'Planejamento de sprints e priorizacao',
            'Reunioes de acompanhamento semanal',
            'Documentacao de decisoes e riscos',
        ])
    },

    # === MARCO 2 - Vendas e CRM ===
    {
        'name': 'Configuracao do CRM',
        'project_id': PROJECT, 'milestone_id': MS[2], 'stage_id': BACKLOG,
        'allocated_hours': 5.0, 'date_deadline': '2026-05-11',
        'tag_ids': tags('CRM'),
        'description': html([
            'Pipeline e etapas do funil de vendas',
            'Tags e fontes de oportunidades',
            'Regras de atribuicao automatica de leads',
            'Modelos de e-mail para follow-up',
        ])
    },
    {
        'name': 'Configuracao de Vendas (Cotacoes, Pedidos, Precos)',
        'project_id': PROJECT, 'milestone_id': MS[2], 'stage_id': BACKLOG,
        'allocated_hours': 4.0, 'date_deadline': '2026-05-16',
        'tag_ids': tags('Vendas'),
        'description': html([
            'Listas de precos e condicoes comerciais',
            'Modelos de cotacao personalizados',
            'Configuracao de impostos nas linhas de venda',
            'Fluxo cotacao -> pedido -> fatura',
        ])
    },
    {
        'name': 'Equipes de Vendas e Estrutura Comercial',
        'project_id': PROJECT, 'milestone_id': MS[2], 'stage_id': BACKLOG,
        'allocated_hours': 3.0, 'date_deadline': '2026-05-20',
        'tag_ids': tags('Vendas', 'CRM'),
        'description': html([
            'Criacao de equipes de vendas',
            'Associacao de vendedores e territorios',
            'Metas comerciais (se aplicavel)',
        ])
    },
    {
        'name': 'Testes Funcionais - Vendas e CRM',
        'project_id': PROJECT, 'milestone_id': MS[2], 'stage_id': BACKLOG,
        'allocated_hours': 3.0, 'date_deadline': '2026-05-25',
        'tag_ids': tags('Vendas', 'CRM'),
        'description': html([
            'Teste ponta a ponta: Lead -> Qualificacao -> Cotacao -> Pedido',
            'Validacao do modelo de impressao de cotacao',
            'Teste de listas de precos e descontos',
        ])
    },
    {
        'name': 'Treinamento e Homologacao - Vendas e CRM',
        'project_id': PROJECT, 'milestone_id': MS[2], 'stage_id': BACKLOG,
        'allocated_hours': 3.0, 'date_deadline': '2026-05-28',
        'tag_ids': tags('Vendas', 'Treinamento'),
        'description': html([
            'Treinamento pratico com equipe de vendas',
            'Homologacao final do modulo com o cliente',
            'Coleta de feedback e ajustes pos-treinamento',
        ])
    },
    {
        'name': 'Gestao de Projeto - Marco 2',
        'project_id': PROJECT, 'milestone_id': MS[2], 'stage_id': BACKLOG,
        'allocated_hours': 2.0, 'date_deadline': '2026-05-30',
        'tag_ids': tags('Gestao'),
        'description': html([
            'Status report do marco',
            'Reuniao de revisao e licoes aprendidas',
        ])
    },

    # === MARCO 3 - Financas ===
    {
        'name': 'Estrutura Contabil (Plano de Contas, Diarios, Periodos)',
        'project_id': PROJECT, 'milestone_id': MS[3], 'stage_id': BACKLOG,
        'allocated_hours': 5.0, 'date_deadline': '2026-06-10',
        'tag_ids': tags('Financas'),
        'description': html([
            'Ativar plano de contas contabil padrao Brasil',
            'Criar diarios contabeis (banco, vendas, compras, diversos)',
            'Configurar periodos fiscais (mes a mes)',
            'Cadastrar saldos iniciais (bancos, CP/CR)',
        ])
    },
    {
        'name': 'Contas a Pagar e Receber',
        'project_id': PROJECT, 'milestone_id': MS[3], 'stage_id': BACKLOG,
        'allocated_hours': 5.0, 'date_deadline': '2026-06-17',
        'tag_ids': tags('Financas', 'CPCR'),
        'description': html([
            'Cadastrar formas e metodos de pagamento',
            'Configurar modelos de fatura (cliente e fornecedor)',
            'Faturamento manual e automatico a partir de pedidos',
            'Definir status contabil padrao e lancamentos',
        ])
    },
    {
        'name': 'Conciliacao Bancaria e Automacao',
        'project_id': PROJECT, 'milestone_id': MS[3], 'stage_id': BACKLOG,
        'allocated_hours': 4.0, 'date_deadline': '2026-06-22',
        'tag_ids': tags('Financas'),
        'description': html([
            'Importar extrato bancario de teste',
            'Configurar regras de conciliacao automatica por descricao/valor',
            'Executar conciliacao de teste (manual e automatica)',
        ])
    },
    {
        'name': 'Centros de Custo e Gestao de Orcamentos',
        'project_id': PROJECT, 'milestone_id': MS[3], 'stage_id': BACKLOG,
        'allocated_hours': 4.0, 'date_deadline': '2026-06-27',
        'tag_ids': tags('Financas'),
        'description': html([
            'Criar categorias e contas analiticas',
            'Estruturar orcamento por centro de custo',
            'Definir valores previstos mensais',
            'Testar relatorio real x orcado',
        ])
    },
    {
        'name': 'Assinatura Digital e Relatorios Financeiros',
        'project_id': PROJECT, 'milestone_id': MS[3], 'stage_id': BACKLOG,
        'allocated_hours': 4.0, 'date_deadline': '2026-06-30',
        'tag_ids': tags('Financas'),
        'description': html([
            'Criar modelo de documento para assinatura digital',
            'Fluxo de assinatura: interno, cliente e fornecedor',
            'Desenvolver relatorios financeiros essenciais',
            'Validar relatorio de orcamento basico',
        ])
    },
    {
        'name': 'Testes, Treinamento e Gestao - Financas',
        'project_id': PROJECT, 'milestone_id': MS[3], 'stage_id': BACKLOG,
        'allocated_hours': 3.0, 'date_deadline': '2026-07-03',
        'tag_ids': tags('Financas', 'Treinamento', 'Gestao'),
        'description': html([
            'Testes funcionais guiados (faturas, pagamentos, conciliacao)',
            'Treinamento do modulo financeiro com o cliente',
            'Status report e revisao do marco',
        ])
    },

    # === MARCO 4 - Cadeia de Suprimentos ===
    {
        'name': 'Estoque e Armazens',
        'project_id': PROJECT, 'milestone_id': MS[4], 'stage_id': BACKLOG,
        'allocated_hours': 5.0, 'date_deadline': '2026-07-13',
        'tag_ids': tags('Inventario'),
        'description': html([
            'Cadastrar armazem(ns) e localizacoes internas',
            'Configurar regras de movimentacao (recebimento, expedicao, interna)',
            'Cadastrar produtos com categorias de estoque',
            'Definir politicas de reabastecimento',
        ])
    },
    {
        'name': 'Pedidos de Compras e Fornecedores',
        'project_id': PROJECT, 'milestone_id': MS[4], 'stage_id': BACKLOG,
        'allocated_hours': 5.0, 'date_deadline': '2026-07-20',
        'tag_ids': tags('Compras'),
        'description': html([
            'Ativar fornecedores multiplos por produto',
            'Cadastrar condicoes comerciais e prazos',
            'Fluxo completo: pedido de compra -> recebimento -> fatura',
            'Teste com pedido real',
        ])
    },
    {
        'name': 'Gestao de Frotas',
        'project_id': PROJECT, 'milestone_id': MS[4], 'stage_id': BACKLOG,
        'allocated_hours': 3.0, 'date_deadline': '2026-07-24',
        'tag_ids': tags('Frotas'),
        'description': html([
            'Cadastro de veiculos da empresa',
            'Controle de manutencoes e custos',
            'Associacao de motoristas',
        ])
    },
    {
        'name': 'Inventario e Reabastecimento',
        'project_id': PROJECT, 'milestone_id': MS[4], 'stage_id': BACKLOG,
        'allocated_hours': 3.0, 'date_deadline': '2026-07-28',
        'tag_ids': tags('Inventario'),
        'description': html([
            'Preparacao para inventario inicial',
            'Teste de ajuste de inventario',
            'Validacao de regras de reabastecimento automatico',
        ])
    },
    {
        'name': 'Testes e Treinamento - Suprimentos',
        'project_id': PROJECT, 'milestone_id': MS[4], 'stage_id': BACKLOG,
        'allocated_hours': 2.0, 'date_deadline': '2026-07-30',
        'tag_ids': tags('Inventario', 'Compras', 'Treinamento'),
        'description': html([
            'Testes integrados (inventario, compras, frotas)',
            'Treinamento da equipe de almoxarifado',
            'Elaboracao de material de apoio',
        ])
    },
    {
        'name': 'Gestao de Projeto - Marco 4',
        'project_id': PROJECT, 'milestone_id': MS[4], 'stage_id': BACKLOG,
        'allocated_hours': 2.0, 'date_deadline': '2026-07-31',
        'tag_ids': tags('Gestao'),
        'description': html([
            'Status report do marco',
            'Reuniao de revisao e ajustes de cronograma',
        ])
    },

    # === MARCO 5 - RH, Servicos e Canais Digitais ===
    {
        'name': 'RH - Funcionarios, Folgas, Ferias e Ponto',
        'project_id': PROJECT, 'milestone_id': MS[5], 'stage_id': BACKLOG,
        'allocated_hours': 6.0, 'date_deadline': '2026-08-10',
        'tag_ids': tags('RH'),
        'description': html([
            'Cadastro de funcionarios e departamentos',
            'Configuracao de folgas e ferias',
            'Controle de ponto',
            'Politicas de aprovacao de ausencias',
        ])
    },
    {
        'name': 'RH - Recrutamento e Avaliacao de Pessoal',
        'project_id': PROJECT, 'milestone_id': MS[5], 'stage_id': BACKLOG,
        'allocated_hours': 4.0, 'date_deadline': '2026-08-15',
        'tag_ids': tags('RH'),
        'description': html([
            'Configuracao de vagas e etapas de recrutamento',
            'Avaliacao de pessoal e ciclos de feedback',
            'Relatorios de RH',
        ])
    },
    {
        'name': 'Servicos (Projetos, Campo e Helpdesk)',
        'project_id': PROJECT, 'milestone_id': MS[5], 'stage_id': BACKLOG,
        'allocated_hours': 5.0, 'date_deadline': '2026-08-20',
        'tag_ids': tags('Servicos'),
        'description': html([
            'Gestao de projetos e tarefas internas',
            'Servicos de campo (agendamento, ordens de servico)',
            'Central de atendimento (Helpdesk): categorias, SLAs, equipes',
        ])
    },
    {
        'name': 'Website Institucional e Chatbot',
        'project_id': PROJECT, 'milestone_id': MS[5], 'stage_id': BACKLOG,
        'allocated_hours': 4.0, 'date_deadline': '2026-08-24',
        'tag_ids': tags('Site'),
        'description': html([
            'Criacao do site institucional',
            'Integracao de Chatbot',
            'Geracao automatica de leads no CRM',
        ])
    },
    {
        'name': 'Marketing - WhatsApp e Campanhas',
        'project_id': PROJECT, 'milestone_id': MS[5], 'stage_id': BACKLOG,
        'allocated_hours': 4.0, 'date_deadline': '2026-08-27',
        'tag_ids': tags('Marketing'),
        'description': html([
            'Configuracao do WhatsApp Business',
            'Campanhas automatizadas de mensagens',
            'Templates e segmentacao de contatos',
        ])
    },
    {
        'name': 'Gestao de Projeto - Marco 5',
        'project_id': PROJECT, 'milestone_id': MS[5], 'stage_id': BACKLOG,
        'allocated_hours': 2.0, 'date_deadline': '2026-08-29',
        'tag_ids': tags('Gestao'),
        'description': html([
            'Status report do marco',
            'Reuniao de revisao e licoes aprendidas',
        ])
    },

    # === MARCO 6 - Go-Live e Estabilizacao ===
    {
        'name': 'Validacao Final e Auditoria',
        'project_id': PROJECT, 'milestone_id': MS[6], 'stage_id': BACKLOG,
        'allocated_hours': 4.0, 'date_deadline': '2026-09-04',
        'tag_ids': tags('Gestao', 'Planejamento'),
        'description': html([
            'Auditoria de permissoes e seguranca',
            'Teste ponta a ponta de todos os fluxos integrados',
            'Verificacao de integracoes entre modulos',
        ])
    },
    {
        'name': 'Migracao de Dados Finais',
        'project_id': PROJECT, 'milestone_id': MS[6], 'stage_id': BACKLOG,
        'allocated_hours': 3.0, 'date_deadline': '2026-09-06',
        'tag_ids': tags('Cadastros Base'),
        'description': html([
            'Saldos iniciais definitivos',
            'Inventario final (input do cliente)',
            'Validacao de dados migrados',
        ])
    },
    {
        'name': 'Capacitacao Consolidada e Manuais',
        'project_id': PROJECT, 'milestone_id': MS[6], 'stage_id': BACKLOG,
        'allocated_hours': 3.0, 'date_deadline': '2026-09-09',
        'tag_ids': tags('Treinamento'),
        'description': html([
            'Treinamento consolidado por area',
            'Elaboracao de manuais de uso',
            'FAQ e documentacao de processos-chave',
        ])
    },
    {
        'name': 'Go-Live e Monitoramento',
        'project_id': PROJECT, 'milestone_id': MS[6], 'stage_id': BACKLOG,
        'allocated_hours': 2.0, 'date_deadline': '2026-09-10',
        'tag_ids': tags('Gestao'),
        'description': html([
            'Ativacao do ambiente de producao',
            'Monitoramento inicial pos-ativacao',
            'Suporte imediato a equipe',
        ])
    },
    {
        'name': 'Estabilizacao e Encerramento do Projeto',
        'project_id': PROJECT, 'milestone_id': MS[6], 'stage_id': BACKLOG,
        'allocated_hours': 3.0, 'date_deadline': '2026-09-12',
        'tag_ids': tags('Gestao'),
        'description': html([
            'Coleta de feedback pos go-live',
            'Ajustes e correcoes finais',
            'Encerramento formal do projeto e entrega de documentacao',
        ])
    },
]

print(f'Creating {len(tasks)} tasks...')
total_hours = 0
for i, t in enumerate(tasks, 1):
    tid = odoo.create('project.task', t)
    total_hours += t['allocated_hours']
    print(f'  [{i:02d}] ID {tid} | {t["allocated_hours"]:4.0f}h | {t["name"]}')

print(f'\nTotal: {len(tasks)} tasks | {total_hours:.0f}h')
