-- =========================================================
-- BJJ DIGITAL 1.0
-- Estrutura do Banco de Dados - Projeto Resgate GFTeam IAPC de Irajá
-- =========================================================

PRAGMA foreign_keys = ON;

-- =========================
-- 1. TABELA DE EQUIPES
-- =========================
CREATE TABLE IF NOT EXISTS equipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    cidade TEXT,
    estado TEXT,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- 2. TABELA DE USUÁRIOS
-- =========================
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE,
    senha TEXT,
    tipo TEXT CHECK(tipo IN ('aluno', 'professor', 'admin')) DEFAULT 'aluno',
    faixa_atual TEXT,
    equipe_id INTEGER,
    assinatura_digital TEXT,
    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipe_id) REFERENCES equipes (id)
);

-- =========================
-- 3. TABELA DE QUESTÕES
-- =========================
CREATE TABLE IF NOT EXISTS questoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tema TEXT CHECK(tema IN ('regras', 'graduacoes', 'historia')) NOT NULL,
    subtema TEXT,
    faixa_destinada TEXT,
    nivel INTEGER CHECK(nivel BETWEEN 1 AND 3),
    pergunta TEXT NOT NULL,
    opcoes TEXT NOT NULL,
    resposta TEXT NOT NULL,
    imagem TEXT,
    video TEXT,
    autor_id INTEGER,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (autor_id) REFERENCES usuarios (id)
);

-- =========================
-- 4. TABELA DE EXAMES
-- =========================
CREATE TABLE IF NOT EXISTS exames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    faixa_alvo TEXT NOT NULL,
    professor_id INTEGER NOT NULL,
    equipe_id INTEGER,
    ativo INTEGER DEFAULT 0, -- 0 = inativo, 1 = ativo
    data_inicio DATETIME,
    data_fim DATETIME,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professor_id) REFERENCES usuarios (id),
    FOREIGN KEY (equipe_id) REFERENCES equipes (id)
);

-- =========================
-- 5. TABELA DE QUESTÕES DOS EXAMES
-- =========================
CREATE TABLE IF NOT EXISTS exame_questoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exame_id INTEGER NOT NULL,
    questao_id INTEGER NOT NULL,
    FOREIGN KEY (exame_id) REFERENCES exames (id),
    FOREIGN KEY (questao_id) REFERENCES questoes (id)
);

-- =========================
-- 6. TABELA DE RESULTADOS
-- =========================
CREATE TABLE IF NOT EXISTS resultados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    exame_id INTEGER,
    modo TEXT CHECK(modo IN ('Exame', 'Rola', 'Estudo')) NOT NULL,
    tema TEXT,
    pontuacao INTEGER,
    tempo_execucao TEXT,
    aprovado INTEGER DEFAULT 0,
    faixa_conquistada TEXT,
    data DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    FOREIGN KEY (exame_id) REFERENCES exames (id)
);

-- =========================
-- 7. DADOS INICIAIS
-- =========================
INSERT OR IGNORE INTO equipes (nome, cidade, estado)
VALUES ('GFTeam IAPC de Irajá', 'Rio de Janeiro', 'RJ');

INSERT OR IGNORE INTO usuarios (nome, email, tipo, faixa_atual, equipe_id)
VALUES ('Administrador do Sistema', 'admin@bjjdigital.com', 'admin', 'Preta', 1);

-- =========================================================
-- FIM DO SCRIPT
-- =========================================================
