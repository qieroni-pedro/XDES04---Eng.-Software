# AgroGestor - Sistema de Gestão Agrícola

O **AgroGestor** é uma solução web para gerenciamento de safras, talhões, atividades agrícolas e controle de equipe, dividida entre níveis de acesso para **Gestores** e **Técnicos Agrícolas**.

---

## Arquitetura e Infraestrutura do Projeto (Release 1)

A estrutura base do ecossistema foi desenvolvida focando em padrões de mercado, segurança e testabilidade.

### 1. Backend & Banco de Dados
* **Framework:** FastAPI (Python 3.10+) com rotas modulares (`APIRouter`).
* **Banco de Dados:** SQLite (`agrogestor.db`).
  * Ativação de restrições de integridade referencial via `PRAGMA foreign_keys = ON`.
  * Tratamento de exceções operacionais robusto (`sqlite3.OperationalError`).

### 2. Trilha de Auditoria (Sistema de Logs de Segurança)
O sistema conta com um mecanismo automático de compliance e segurança. Toda operação crítica (inserção, edição, exclusão lógica) é registrada na tabela `logs_auditoria`, armazenando o autor da ação, o evento e o timestamp em formato UTC (ISO 8601).
* **Utilitário de Consulta:** Desenvolvido o script `consulta_log.py` na raiz para renderização e monitoramento dos logs formatados direto no terminal.

### 3. Módulo de Safras — CRUD 3 (Sprint 2)
Localizado em `backend/app/routers/safras.py` e `frontend/js/safras.js`, este módulo implementa o ciclo de vida completo de uma safra agrícola (RFS05–RFS08), com todas as regras de negócio do DRE aplicadas na camada de backend:

* **RFS05 – Inserir Safra:** Cadastro vinculado a um talhão com validação de campos obrigatórios, status inicial e verificação de conflito de períodos.
* **RFS06 – Editar Safra:** Edição com bloqueio dinâmico de campos após início do cultivo (talhão, variedade e data de início tornam-se somente leitura conforme RN06).
* **RFS07 – Consultar Safras:** Listagem com filtros opcionais por talhão, variedade e status, scoped por fazenda do usuário autenticado via `JOIN` com `equipe_fazendas`.
* **RFS08 – Excluir Safra:** Exclusão lógica (`soft delete`, `ativo = 0`) bloqueada caso a safra possua atividades vinculadas.
* **Encerramento de Safra (`PATCH /encerrar`):** Endpoint dedicado que registra a data real de colheita e a produtividade final (sc/ha), liberando o campo somente neste momento (RN07).
* **Regras de negócio aplicadas no backend:** RN01 (conflito de safras simultâneas no mesmo talhão), RN03 (data de colheita posterior ao plantio), RN05 (produtividade bloqueada até encerramento), RN07 (gatilho de liberação do campo de produtividade) e RNF05 (toda operação gera registro em `logs_auditoria`).

### 4. Inteligência do Dashboard (Módulo Safras)
Localizado em `backend/app/routers/safras.py`, este endpoint realiza a agregação de dados em tempo real para alimentar a camada visual do front-end:
* **Card 1 (Progresso):** Cálculo matemático dinâmico do percentual de atividades concluídas (`Realizado`) sobre o total da safra.
* **Card 2 (Linha do Tempo):** Cruzamento de dados (`JOIN`) com a tabela de usuários para listar cronologicamente as próximas 5 tarefas agendadas e seus respectivos responsáveis.
* **Card 3 (Alertas Críticos):** Filtro automatizado de eventos climáticos extremos vinculados à safra.

### 5. Automação de Testes — v2 (QA/DevOps)
* **Tecnologia:** Selenium WebDriver.
* **Escopo:** Script automatizado (`testes_selenium/teste_fluxo_completo.py`) que simula o fluxo completo do usuário no navegador (Login de Gestor, Login de Técnico, CRUD de Funcionários e Talhões, CRUD de Safras, Validação de Permissões de Telas).

---

## 📂 Estrutura de Pastas

```text
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── auth.py            # Endpoints de autenticação de usuários
│   │   │   ├── safras.py          # CRUD de Safras + agregação do Dashboard (BI)
│   │   │   ├── talhoes.py         # Regras de negócio e rotas de Talhões
│   │   │   └── usuarios.py        # Gestão e rotas de Usuários/Funcionários
│   │   ├── utils/
│   │   │   └── security.py        # Funções de hashing e segurança de senhas
│   │   ├── database.py            # Configuração e conexão do SQLite
│   │   └── main.py                # Arquivo inicial e inicialização do FastAPI
│   ├── uploads/                   # Armazenamento de arquivos de mídia/sistema
│   ├── venv/                      # Ambiente virtual do ecossistema backend
│   ├── agrogestor.db              # Banco de dados atualizado com massa de testes
│   ├── banco.py                   # Script de estruturação/população inicial do BD
│   └── conculta_log.py            # Utilitário de leitura da trilha de auditoria
│
├── frontend/
│   ├── js/
│   │   ├── auth.js                # Interceptadores e lógica de autenticação web
│   │   ├── components.js          # Componentes visuais reaproveitáveis
│   │   ├── dashboard.js           # Consumo de dados e renderização do safras.py
│   │   ├── funcionario.js         # Manipulação do DOM do CRUD de Funcionários
│   │   ├── login.js               # Envio e tratamento do formulário de login
│   │   ├── safras.js              # Manipulação do DOM do CRUD de Safras
│   │   └── talhoes.js             # Manipulação do DOM do CRUD de Talhões
│   ├── dashboard.html             # Painel visual com os 3 cards principais
│   ├── gerenciar_funcionarios.html# Interface de administração da equipe
│   ├── gerenciar_safras.html      # Interface de administração de safras
│   ├── gerenciar_talhoes.html     # Interface de administração de talhões
│   └── index.html                 # Tela de Login/Entrada do sistema
│
├── testes_selenium/
│   ├── venv/                      # Ambiente virtual isolado para a camada de QA
│   └── teste_fluxo_completo.py    # Robô de automação de testes E2E
│
├── .gitignore                     # Filtro de arquivos descartáveis para o Git
└── requirements.txt               # Dependências globais do projeto (FastAPI, Selenium, etc)
```
