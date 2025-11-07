-- =========================================================
-- BJJ DIGITAL 1.0 — Banco de Teste
-- Projeto Resgate GFTeam IAPC de Irajá
-- =========================================================
PRAGMA foreign_keys = ON;

-- =========================
-- 1. EQUIPES
-- =========================
CREATE TABLE IF NOT EXISTS equipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    cidade TEXT,
    estado TEXT,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO equipes (nome, cidade, estado) VALUES
('GFTeam IAPC de Irajá', 'Rio de Janeiro', 'RJ'),
('GFTeam Bangu', 'Rio de Janeiro', 'RJ'),
('GFTeam Itaboraí', 'Itaboraí', 'RJ');

-- =========================
-- 2. USUÁRIOS
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

INSERT OR IGNORE INTO usuarios (nome, email, tipo, faixa_atual, equipe_id) VALUES
('Administrador do Sistema', 'admin@bjjdigital.com', 'admin', 'Preta', 1),
('Professor Rian Barbosa', 'rian.gfteam@bjjdigital.com', 'professor', 'Preta', 1),
('Professor Deley Silva', 'deley.gfteam@bjjdigital.com', 'professor', 'Preta', 2),
('Aluno João Pedro', 'joao.aluno@bjjdigital.com', 'aluno', 'Azul', 1),
('Aluna Ana Clara', 'ana.aluna@bjjdigital.com', 'aluno', 'Branca', 1),
('Aluno Pedro Henrique', 'pedro.aluno@bjjdigital.com', 'aluno', 'Amarela', 2),
('Aluno Lucas Lima', 'lucas.aluno@bjjdigital.com', 'aluno', 'Cinza', 3);

-- =========================
-- 3. QUESTÕES
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

-- Regras e Arbitragem
INSERT INTO questoes (tema, subtema, faixa_destinada, nivel, pergunta, opcoes, resposta, imagem)
VALUES
('regras', 'Gestos', 'Branca', 1, 'Quando o árbitro estende o braço à frente e faz movimento vertical em direção ao solo, o que ele indica?', 'A) Parar a luta|B) Início da luta|C) Punição|D) Declaração do vencedor', 'B', 'assets/jiujitsu/inicio_luta.png'),
('regras', 'Gestos', 'Branca', 1, 'O que significa o gesto do árbitro com os braços abertos na altura dos ombros?', 'A) Interrupção da luta|B) Início da luta|C) Finalização|D) Declaração do vencedor', 'A', 'assets/jiujitsu/interrupcao.png'),
('regras', 'Pontuação', 'Azul', 2, 'Quantos pontos valem uma raspagem bem-sucedida?', 'A) 2 pontos|B) 3 pontos|C) 4 pontos|D) 1 ponto', 'A', NULL),
('regras', 'Punições', 'Roxa', 3, 'Qual a sequência correta das punições no jiu-jitsu?', 'A) Aviso > Vantagem > 2 pontos > Desclassificação|B) Aviso > Punição > Reinício em pé|C) Vantagem > Desclassificação|D) Punição direta', 'A', NULL),
('regras', 'Finalizações', 'Marrom', 3, 'O que o árbitro faz para indicar o fim da luta por finalização?', 'A) Estende os braços|B) Bate no ombro do atleta|C) Interrompe verbalmente e toca o atleta finalizado|D) Levanta a mão do finalizador', 'C', NULL);

-- Graduações e Faixas
INSERT INTO questoes (tema, subtema, faixa_destinada, nivel, pergunta, opcoes, resposta, imagem)
VALUES
('graduacoes', 'Faixas', 'Branca', 1, 'Qual é a ordem correta das faixas no jiu-jitsu adulto?', 'A) Branca, Azul, Roxa, Marrom, Preta|B) Azul, Branca, Roxa, Marrom, Preta|C) Branca, Roxa, Azul, Marrom, Preta|D) Branca, Azul, Preta, Marrom', 'A', 'assets/jiujitsu/faixas.png'),
('graduacoes', 'Faixas', 'Amarela', 1, 'Após quantos graus na faixa preta o atleta se torna faixa coral?', 'A) 4º grau|B) 5º grau|C) 6º grau|D) 7º grau', 'D', 'assets/jiujitsu/faixa_preta.png'),
('graduacoes', 'Significado', 'Verde', 2, 'A faixa simboliza o quê dentro do jiu-jitsu?', 'A) Hierarquia e evolução técnica|B) Idade do praticante|C) Peso corporal|D) Tempo de filiação', 'A', NULL),
('graduacoes', 'Tempo', 'Azul', 2, 'Em média, quanto tempo um aluno leva para conquistar a faixa azul?', 'A) 1 ano|B) 2 anos|C) 5 anos|D) 8 meses', 'B', NULL),
('graduacoes', 'Infantil', 'Cinza', 1, 'As faixas infantis são destinadas a alunos de qual faixa etária?', 'A) Até 12 anos|B) 13 a 15 anos|C) 16 a 18 anos|D) Acima de 18 anos', 'A', NULL);

-- História e Projeto Resgate
INSERT INTO questoes (tema, subtema, faixa_destinada, nivel, pergunta, opcoes, resposta, imagem)
VALUES
('historia', 'Jiu-Jitsu', 'Branca', 1, 'O jiu-jitsu tem origem em qual país?', 'A) Índia|B) Japão|C) Brasil|D) China', 'A', 'assets/jiujitsu/historia_jj.png'),
('historia', 'Jiu-Jitsu', 'Branca', 1, 'Quem trouxe o jiu-jitsu ao Brasil?', 'A) Jigoro Kano|B) Mitsuyo Maeda|C) Hélio Gracie|D) Carlos Gracie', 'B', 'assets/jiujitsu/mitsuyo_maeda.png'),
('historia', 'GFTeam', 'Azul', 2, 'Quem é o fundador da GFTeam?', 'A) Julio Cesar Pereira|B) Hélio Gracie|C) Rigan Machado|D) Rickson Gracie', 'A', 'assets/jiujitsu/gfteam_fundador.png'),
('historia', 'Projeto Resgate', 'Branca', 1, 'O Projeto Resgate surgiu com o objetivo de:', 'A) Ensinar defesa pessoal a policiais|B) Promover inclusão social através do jiu-jitsu|C) Criar campeonatos profissionais|D) Treinar árbitros de competição', 'B', 'assets/jiujitsu/projeto_resgate.png'),
('historia', 'GFTeam', 'Preta', 3, 'A GFTeam é conhecida por enfatizar principalmente:', 'A) Competição e força física|B) Técnica, humildade e coletividade|C) Filosofia oriental|D) Defesa pessoal militar', 'B', 'assets/jiujitsu/gfteam_logo.png');

-- =========================
-- 4. EXAMES
-- =========================
CREATE TABLE IF NOT EXISTS exames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    faixa_alvo TEXT NOT NULL,
    professor_id INTEGER NOT NULL,
    equipe_id INTEGER,
    ativo INTEGER DEFAULT 1,
    data_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professor_id) REFERENCES usuarios (id),
    FOREIGN KEY (equipe_id) REFERENCES equipes (id)
);

INSERT INTO exames (nome, faixa_alvo, professor_id, equipe_id)
VALUES ('Exame Faixa Azul - GFTeam IAPC', 'Azul', 2, 1);

-- =========================
-- 5. EXAME_QUESTOES
-- =========================
CREATE TABLE IF NOT EXISTS exame_questoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exame_id INTEGER NOT NULL,
    questao_id INTEGER NOT NULL,
    FOREIGN KEY (exame_id) REFERENCES exames (id),
    FOREIGN KEY (questao_id) REFERENCES questoes (id)
);

INSERT INTO exame_questoes (exame_id, questao_id)
VALUES (1, 3), (1, 4), (1, 9), (1, 13), (1, 14);

-- =========================
-- 6. RESULTADOS
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

-- =========================================================
-- FIM DO SCRIPT
-- =========================================================
