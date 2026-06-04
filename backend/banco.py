import sqlite3

# Nome do arquivo do banco de dados SQLite
DB_NAME = "agrogestor.db"

# Código SQL contendo o esquema completo das tabelas e restrições
DATABASE_SCHEMA = """
-- =========================================================================
-- 1. MÓDULO DE USUÁRIOS E PERFIS (Autenticação e RBAC)
-- =========================================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    senha_hash TEXT NOT NULL, 
    perfil TEXT CHECK(perfil IN ('Gestor', 'Técnico Agrícola')) NOT NULL,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================================
-- 2. MÓDULO DE FAZENDAS E ASSOCIAÇÃO DE EQUIPE (AGREGAÇÃO)
-- =========================================================================
CREATE TABLE IF NOT EXISTS fazendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    localizacao TEXT NOT NULL,
    ativo INTEGER DEFAULT 1 CHECK(ativo IN (0, 1)) -- Soft Delete
);

-- TABELA DE AGREGAÇÃO: Resolve o problema de técnicos e gerentes sem sujar as tabelas principais
CREATE TABLE IF NOT EXISTS equipe_fazendas (
    id_fazenda INTEGER NOT NULL,
    id_usuario INTEGER NOT NULL,
    papel TEXT CHECK(papel IN ('Gerente', 'Técnico')) NOT NULL,
    PRIMARY KEY (id_fazenda, id_usuario), -- Evita duplicar o mesmo usuário na mesma fazenda
    FOREIGN KEY (id_fazenda) REFERENCES fazendas(id) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS talhoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_fazenda INTEGER NOT NULL,
    nome TEXT NOT NULL,
    area_ha REAL NOT NULL,
    tipo_solo TEXT CHECK(tipo_solo IN ('Argiloso', 'Arenoso', 'Misto')) NOT NULL, 
    ativo INTEGER DEFAULT 1 CHECK(ativo IN (0, 1)), 
    FOREIGN KEY (id_fazenda) REFERENCES fazendas(id) ON DELETE CASCADE
);

-- =========================================================================
-- 3. MÓDULO DE SAFRAS 
-- =========================================================================
CREATE TABLE IF NOT EXISTS safras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_talhao INTEGER NOT NULL,
    variedade_cultura TEXT NOT NULL, 
    data_inicio_prevista TEXT NOT NULL,
    data_colheita_prevista TEXT NOT NULL,
    status TEXT CHECK(status IN ('Planejada', 'Em andamento', 'Colhida/Finalizada')) NOT NULL, 
    produtividade_safra REAL DEFAULT NULL, 
    ativo INTEGER DEFAULT 1 CHECK(ativo IN (0, 1)),     
    FOREIGN KEY (id_talhao) REFERENCES talhoes(id)
);

-- =========================================================================
-- 4. MÓDULO DE ATIVIDADES AGRÍCOLAS
-- =========================================================================
CREATE TABLE IF NOT EXISTS atividades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_safra INTEGER NOT NULL,
    id_responsavel INTEGER NOT NULL, 
    tipo_atividade TEXT CHECK(tipo_atividade IN ('Adubação', 'Irrigação', 'Pulverização', 'Manejo de pragas/doenças', 'Plantio', 'Colheita')) NOT NULL,
    status TEXT CHECK(status IN ('Agendado', 'Em andamento', 'Realizado')) NOT NULL,
    data_execucao TEXT NOT NULL,
    FOREIGN KEY (id_safra) REFERENCES safras(id) ON DELETE CASCADE,
    FOREIGN KEY (id_responsavel) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS detalhes_irrigacao (
    id_atividade INTEGER PRIMARY KEY,
    lamina_mm REAL NOT NULL,
    horas_aplicacao REAL NOT NULL,
    FOREIGN KEY (id_atividade) REFERENCES atividades(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS detalhes_manejo_insumos (
    id_atividade INTEGER PRIMARY KEY,
    produto_usado TEXT NOT NULL, 
    praga_doenca_identificada TEXT,  
    caminho_foto_nota_fiscal TEXT NOT NULL, 
    caminho_foto_receita_agronomica TEXT NOT NULL, 
    FOREIGN KEY (id_atividade) REFERENCES atividades(id) ON DELETE CASCADE,
    
    CONSTRAINT check_nota_fiscal CHECK (
        caminho_foto_nota_fiscal LIKE '%.pdf' OR 
        caminho_foto_nota_fiscal LIKE '%.jpg' OR 
        caminho_foto_nota_fiscal LIKE '%.jpeg' OR 
        caminho_foto_nota_fiscal LIKE '%.png'
    ),
    
    CONSTRAINT check_receita_agronomica CHECK (
        caminho_foto_receita_agronomica LIKE '%.pdf'
    )
);

-- =========================================================================
-- 5. MÓDULO DE EVENTOS EXTREMOS E COMPLIANCE
-- =========================================================================
CREATE TABLE IF NOT EXISTS eventos_extremos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_safra INTEGER NOT NULL,
    tipo_evento TEXT CHECK(tipo_evento IN ('Granizo', 'Seca/Estiagem', 'Geada', 'Vendaval/Tempestade', 'Quebra Crítica de Maquinário', 'Outro')) NOT NULL, 
    data_ocorrência TEXT NOT NULL,
    descricao_danos TEXT NOT NULL, 
    FOREIGN KEY (id_safra) REFERENCES safras(id)
);

CREATE TABLE IF NOT EXISTS logs_auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER,
    acao TEXT NOT NULL,         
    detalhes TEXT,              
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE SET NULL
);
"""


def inicializar_banco():
    print(f"Iniciando a criação do banco de dados: {DB_NAME}...")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.executescript(DATABASE_SCHEMA)
        conn.commit()
        print("Tabelas criadas com sucesso!")
        
        cursor.execute("SELECT COUNT(*) FROM usuarios;")
        if cursor.fetchone()[0] == 0:
            print("Populando o banco com a nova estrutura de Agregação...")
            
            # 1. Cadastra todos os Usuários primeiro (Sem chaves estrangeiras travando o insert)
            usuarios_dados = [
                # Gestores (IDs de 1 a 4)
                ('Gestor Fazenda 1', 'gestor1@agrogestor.com', 'hash_senha_gestor1', 'Gestor'),
                ('Gestor Fazenda 2', 'gestor2@agrogestor.com', 'hash_senha_gestor2', 'Gestor'),
                ('Gestor Fazenda 3', 'gestor3@agrogestor.com', 'hash_senha_gestor3', 'Gestor'),
                ('Gestor Fazenda 4', 'gestor4@agrogestor.com', 'hash_senha_gestor4', 'Gestor'),
                # Técnicos (IDs de 5 a 8)
                ('Técnico Alfa', 'tecnico.alfa@agrogestor.com', 'hash_senha_alfa', 'Técnico Agrícola'),
                ('Técnico Beta', 'tecnico.beta@agrogestor.com', 'hash_senha_beta', 'Técnico Agrícola'),
                ('Técnico Gama', 'tecnico.gama@agrogestor.com', 'hash_senha_gama', 'Técnico Agrícola'),
                ('Técnico Delta', 'tecnico.delta@agrogestor.com', 'hash_senha_delta', 'Técnico Agrícola')
            ]
            cursor.executemany("INSERT INTO usuarios (nome, email, senha_hash, perfil) VALUES (?, ?, ?, ?);", usuarios_dados)
            
            # 2. Cadastra as Fazendas limpas (Sem precisar saber quem é o gerente aqui)
            fazendas_dados = [
                ('Fazenda Ouro Verde', 'Passos - MG'),    # ID 1
                ('Fazenda Bela Vista', 'Uberaba - MG'),   # ID 2
                ('Fazenda Santa Fé', 'Itajubá - MG'),     # ID 3
                ('Fazenda Vale do Sol', 'Lavras - MG')    # ID 4
            ]
            cursor.executemany("INSERT INTO fazendas (nome, localizacao) VALUES (?, ?);", fazendas_dados)
            
            # 3. Alimenta a TABELA DE AGREGAÇÃO (Vincula a equipe e define os papéis)
            # Formato: (id_fazenda, id_usuario, papel)
            equipe_dados = [
                # Vinculando os Gerentes às suas respectivas fazendas
                (1, 1, 'Gerente'),
                (2, 2, 'Gerente'),
                (3, 3, 'Gerente'),
                (4, 4, 'Gerente'),
                # Vinculando os Técnicos às fazendas (1 fazenda com seu técnico dedicado)
                (1, 5, 'Técnico'), # Alfa na Ouro Verde
                (2, 6, 'Técnico'), # Beta na Bela Vista
                (3, 7, 'Técnico'), # Gama na Santa Fé
                (4, 8, 'Técnico')  # Delta na Vale do Sol
            ]
            cursor.executemany("INSERT INTO equipe_fazendas (id_fazenda, id_usuario, papel) VALUES (?, ?, ?);", equipe_dados)
            
            # 4. Log de Auditoria Inicial (A tabela de talhões inicia perfeitamente vazia)
            cursor.execute(
                "INSERT INTO logs_auditoria (id_usuario, acao, detalhes) VALUES (NULL, 'DB_POPULADO', 'Estrutura inicial criada usando tabela de agregação (equipe_fazendas). Módulo de talhões iniciado vazio.');"
            )
            
            conn.commit()
            print("Carga inicial estruturada injetada com sucesso!")
            print("\n--- MAPEAMENTO VIA TABELA DE AGREGAÇÃO CONCLUÍDO ---")
        else:
            print("O banco de dados já possui registros cadastrados.")
            
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Erro ao inicializar ou popular o banco: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inicializar_banco()