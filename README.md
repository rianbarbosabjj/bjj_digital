# 🥋 BJJ Digital - Plataforma de Gestão de Jiu-Jitsu

O **BJJ Digital** é um LMS (Learning Management System) focado no ensino, graduação e gestão de academias de Jiu-Jitsu. A plataforma permite que professores gerenciem equipes, criem cursos multimídia e apliquem exames de faixa teóricos, enquanto alunos acompanham seu progresso e acessam conteúdos exclusivos.

## 🚀 Funcionalidades Principais

### 👤 Alunos
* **Dashboard Interativo:** Acompanhamento de cursos matriculados e novos conteúdos.
* **Cursos Online:** Player de vídeo, textos e materiais de apoio com marcação de progresso.
* **Exames de Faixa:** Provas teóricas com cronômetro, gerador de questões aleatórias e correção automática.
* **Certificação:** Geração automática de certificados em PDF com QR Code de validação.
* **Checkout:** Integração com Mercado Pago (Pix e Cartão) para compra de cursos.

### 👨‍🏫 Professores
* **Gestão de Equipes:** Aprovação de alunos e gestão de professores auxiliares/delegados.
* **Editor de Cursos (Lego):** Criador de aulas flexível (blocos de texto, vídeo, imagem).
* **Painel Financeiro:** Acompanhamento de vendas (Split de pagamento: 90% Professor / 10% Plataforma) e solicitação de saques.
* **Dashboard:** Estatísticas de desempenho dos alunos e membros da equipe.

### 🛡️ Admin
* **Banco de Questões:** Cadastro, edição e aprovação de questões para exames.
* **Gestão de Usuários:** Controle total sobre perfis e acessos.
* **Analytics:** Visão global da plataforma (KPIs, gráficos de crescimento).

## 🛠️ Tecnologias Utilizadas

* **Frontend & Backend:** [Streamlit](https://streamlit.io/) (Python).
* **Banco de Dados:** Google Firebase Firestore (NoSQL).
* **Armazenamento:** Firebase Storage.
* **Autenticação:** Firebase Auth + Gestão de Sessão Local + Google OAuth.
* **Pagamentos:** SDK Mercado Pago.
* **Relatórios:** FPDF (Geração de PDFs) e Plotly (Dashboards).

## 📂 Estrutura do Projeto

```text
/
├── .streamlit/          # Segredos e configurações (secrets.toml)
├── assets/              # Imagens, logos e templates de certificado
├── main/
│   ├── app.py           # Ponto de entrada da aplicação
│   ├── auth.py          # Lógica de autenticação
│   ├── database.py      # Conexão com Firebase
│   └── utils.py         # Funções auxiliares (Upload, PDF, Financeiro)
├── views/               # Telas do sistema
│   ├── admin.py         # Painel Administrativo
│   ├── aluno.py         # Lógica de Exames e Certificados
│   ├── aulas_aluno.py   # Player de aulas (Visão do aluno)
│   ├── aulas_professor.py # Editor de aulas (Visão do professor)
│   ├── cursos_professor.py # Gestão de cursos
│   ├── painel_aluno.py  # Dashboard de cursos do aluno
│   ├── login.py         # Telas de Login e Registro
│   └── dashboard.py     # Dashboards analíticos
└── requirements.txt     # Dependências do projeto
