import streamlit as st
import sqlite3
import pandas as pd
import bcrypt
import os
import json
from datetime import datetime
from config import DB_PATH
from utils import carregar_questoes, salvar_questoes, formatar_e_validar_cpf, carregar_todas_questoes

def gestao_usuarios(usuario_logado):
    """Página de gerenciamento de usuários, restrita ao Admin."""
    
    # 🔒 Restrição de Acesso
    if usuario_logado["tipo"] != "admin":
        st.error("Acesso negado. Esta página é restrita aos administradores.")
        return

    st.markdown("<h1 style='color:#FFD700;'>🔑 Gestão de Usuários</h1>", unsafe_allow_html=True)
    st.markdown("Edite informações, redefina senhas ou altere o tipo de perfil de um usuário.")

    conn = sqlite3.connect(DB_PATH)
    # Seleciona o CPF e o ID para uso na edição
    df = pd.read_sql_query(
        "SELECT id, nome, email, cpf, tipo_usuario, auth_provider, perfil_completo FROM usuarios ORDER BY nome", 
        conn
    )

    st.subheader("Visão Geral dos Usuários")
    st.dataframe(df, use_container_width=True)
    st.markdown("---")

    st.subheader("Editar Usuário")
    lista_nomes = df["nome"].tolist()
    nome_selecionado = st.selectbox(
        "Selecione um usuário para gerenciar:",
        options=lista_nomes,
        index=None,
        placeholder="Selecione..."
    )

    if nome_selecionado:
        try:
            # 1. Recupera o ID
            user_id_selecionado = int(df[df["nome"] == nome_selecionado]["id"].values[0])
        except IndexError:
            st.error("Usuário não encontrado no DataFrame. Tente recarregar a página.")
            conn.close()
            return
            
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 2. Busca dados completos
        cursor.execute("SELECT * FROM usuarios WHERE id=?", (user_id_selecionado,))
        user_data = cursor.fetchone()
        
        if not user_data:
            st.error("Usuário não encontrado no banco de dados. (ID não correspondeu)")
            conn.close()
            return

        with st.expander(f"Gerenciando: {user_data['nome']}", expanded=True):
            
            with st.form(key="form_edit_user"):
                st.markdown("#### 1. Informações do Perfil")
                
                col1, col2 = st.columns(2)
                novo_nome = col1.text_input("Nome:", value=user_data['nome'])
                novo_email = col2.text_input("Email:", value=user_data['email'])
                
                # NOVO CAMPO CPF
                novo_cpf_input = st.text_input("CPF:", value=user_data['cpf'] or "")
                
                # Máscara visual do CPF
                cpf_display_limpo = formatar_e_validar_cpf(novo_cpf_input)
                if cpf_display_limpo:
                    st.info(f"CPF Formatado: {cpf_display_limpo[:3]}.{cpf_display_limpo[3:6]}.{cpf_display_limpo[6:9]}-{cpf_display_limpo[9:]}")
                
                opcoes_tipo = ["aluno", "professor", "admin"]
                tipo_atual_db = user_data['tipo_usuario']
                
                index_atual = 0 
                if tipo_atual_db:
                    try:
                        index_atual = [t.lower() for t in opcoes_tipo].index(tipo_atual_db.lower())
                    except ValueError:
                        index_atual = 0 
                
                novo_tipo = st.selectbox(
                    "Tipo de Usuário:",
                    options=opcoes_tipo,
                    index=index_atual 
                )
                
                st.text_input("Provedor de Auth:", value=user_data['auth_provider'], disabled=True)
                
                submitted_info = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                
                if submitted_info:
                    # ⚠️ VALIDAÇÃO DO CPF (se não estiver vazio)
                    cpf_editado = formatar_e_validar_cpf(novo_cpf_input) if novo_cpf_input else None

                    if novo_cpf_input and not cpf_editado:
                        st.error("CPF inválido na edição. Por favor, corrija o formato (11 dígitos).")
                        conn.close()
                        return
                        
                    try:
                        # 3. Executa o UPDATE (incluindo o CPF)
                        cursor.execute(
                            "UPDATE usuarios SET nome=?, email=?, cpf=?, tipo_usuario=? WHERE id=?",
                            (novo_nome.upper(), novo_email.upper(), cpf_editado, novo_tipo, user_id_selecionado)
                        )
                        conn.commit()
                        st.success("Dados do usuário atualizados com sucesso!")
                        st.rerun() # Recarrega para refletir a mudança no DataFrame
                    except sqlite3.IntegrityError:
                        st.error(f"Erro: O email '{novo_email}' ou o CPF já está em uso por outro usuário.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")

            st.markdown("---")

            st.markdown("#### 2. Redefinição de Senha")
            if user_data['auth_provider'] == 'local':
                with st.form(key="form_reset_pass"):
                    nova_senha = st.text_input("Nova Senha:", type="password")
                    confirmar_senha = st.text_input("Confirmar Nova Senha:", type="password")
                    
                    submitted_pass = st.form_submit_button("🔑 Redefinir Senha", use_container_width=True)
                    
                    if submitted_pass:
                        if not nova_senha or not confirmar_senha:
                            st.warning("Por favor, preencha os dois campos de senha.")
                        elif nova_senha != confirmar_senha:
                            st.error("As senhas não coincidem.")
                        else:
                            novo_hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
                            cursor.execute(
                                "UPDATE usuarios SET senha=? WHERE id=?",
                                (novo_hash, user_id_selecionado)
                            )
                            conn.commit()
                            st.success("Senha do usuário redefinida com sucesso!")
            else:
                st.info(f"Não é possível redefinir a senha de usuários via '{user_data['auth_provider']}'.")
    
    conn.close()
# =========================================
# 🧩 GESTÃO DE QUESTÕES (DO SEU PROJETO ORIGINAL)
# =========================================
def gestao_questoes():
    usuario_logado = st.session_state.usuario
    # ... (restrição para Admin) ...

    # 📝 Checagem adicional para Professores (se necessário)
    if usuario_logado["tipo"] == "professor":
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM professores WHERE usuario_id=? AND status_vinculo='ativo'", (usuario_logado["id"],))
        if cursor.fetchone()[0] == 0:
            st.error("Acesso negado. Seu vínculo como professor ainda não foi aprovado ou você não tem um vínculo ativo.")
            conn.close()
            return
        conn.close()
    
    st.markdown("<h1 style='color:#FFD700;'>🧠 Gestão de Questões</h1>", unsafe_allow_html=True)

    temas_existentes = [f.replace(".json", "") for f in os.listdir("questions") if f.endswith(".json")]
    tema_selecionado = st.selectbox("Tema:", ["Novo Tema"] + temas_existentes)

    if tema_selecionado == "Novo Tema":
        tema = st.text_input("Digite o nome do novo tema:")
    else:
        tema = tema_selecionado

    questoes = carregar_questoes(tema) if tema else []

    st.markdown("### ✍️ Adicionar nova questão")
    with st.expander("Expandir para adicionar questão", expanded=False):
        pergunta = st.text_area("Pergunta:")
        opcoes = [st.text_input(f"Alternativa {letra}:", key=f"opt_{letra}") for letra in ["A", "B", "C", "D", "E"]]
        resposta = st.selectbox("Resposta correta:", ["A", "B", "C", "D", "E"])
        imagem = st.text_input("Caminho da imagem (opcional):")
        video = st.text_input("URL do vídeo (opcional):")

        if st.button("💾 Salvar Questão"):
            if pergunta.strip() and tema.strip():
                nova = {
                    "pergunta": pergunta.strip(),
                    "opcoes": [f"{letra}) {txt}" for letra, txt in zip(["A", "B", "C", "D", "E"], opcoes) if txt.strip()],
                    "resposta": resposta,
                    "imagem": imagem.strip(),
                    "video": video.strip(),
                }
                questoes.append(nova)
                salvar_questoes(tema, questoes)
                st.success("Questão adicionada com sucesso! ✅")
                st.rerun()
            else:
                st.error("A pergunta e o nome do tema não podem estar vazios.")

    st.markdown("### 📚 Questões cadastradas")
    if not questoes:
        st.info("Nenhuma questão cadastrada para este tema ainda.")
    else:
        for i, q in enumerate(questoes, 1):
            st.markdown(f"**{i}. {q['pergunta']}**")
            for alt in q["opcoes"]:
                st.markdown(f"- {alt}")
            st.markdown(f"**Resposta:** {q['resposta']}")
            if st.button(f"🗑️ Excluir questão {i}", key=f"del_{i}"):
                questoes.pop(i - 1)
                salvar_questoes(tema, questoes)
                st.warning("Questão removida.")
                st.rerun()

def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>🥋 Gestão de Exame de Faixa</h1>", unsafe_allow_html=True)

    os.makedirs("exames", exist_ok=True)
    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa = st.selectbox("Selecione a faixa:", faixas)

    exame_path = f"exames/faixa_{faixa.lower()}.json"
    if os.path.exists(exame_path):
        try:
            with open(exame_path, "r", encoding="utf-8") as f:
                exame = json.load(f)
        except json.JSONDecodeError:
            st.error("Arquivo de exame corrompido. Criando um novo.")
            exame = {} # Reseta
    else:
        exame = {}

    # Garante que a estrutura base exista
    if "questoes" not in exame:
        exame = {
            "faixa": faixa,
            "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d"),
            "criado_por": st.session_state.usuario["nome"],
            "temas_incluidos": [],
            "questoes": []
        }

    # 🔹 Carrega todas as questões disponíveis
    todas_questoes = carregar_todas_questoes()
    if not todas_questoes:
        st.warning("Nenhuma questão cadastrada nos temas (pasta 'questions') até o momento.")
        return

    # 🔹 Filtro por tema
    temas_disponiveis = sorted(list(set(q["tema"] for q in todas_questoes)))
    tema_filtro = st.selectbox("Filtrar questões por tema:", ["Todos"] + temas_disponiveis)

    # 🔹 Exibição com filtro
    if tema_filtro != "Todos":
        questoes_filtradas = [q for q in todas_questoes if q["tema"] == tema_filtro]
    else:
        questoes_filtradas = todas_questoes

    st.markdown("### ✅ Selecione as questões que farão parte do exame")
    selecao = []
    
    # Filtra questões que JÁ ESTÃO no exame para evitar duplicatas
    perguntas_no_exame = set(q["pergunta"] for q in exame["questoes"])
    questoes_para_selecao = [q for q in questoes_filtradas if q["pergunta"] not in perguntas_no_exame]

    if not questoes_para_selecao:
        st.info(f"Todas as questões {('do tema ' + tema_filtro) if tema_filtro != 'Todos' else ''} já foram adicionadas ou não há questões disponíveis.")

    for i, q in enumerate(questoes_para_selecao, 1):
        st.markdown(f"**{i}. ({q['tema']}) {q['pergunta']}**")
        if st.checkbox(f"Adicionar esta questão ({q['tema']})", key=f"{faixa}_{q['tema']}_{i}"):
            selecao.append(q)

    # 🔘 Botão para inserir as selecionadas
    if selecao and st.button("➕ Inserir Questões Selecionadas"):
        exame["questoes"].extend(selecao)
        exame["temas_incluidos"] = sorted(list(set(q["tema"] for q in exame["questoes"])))
        exame["ultima_atualizacao"] = datetime.now().strftime("%Y-%m-%d")
        
        with open(exame_path, "w", encoding="utf-8") as f:
            json.dump(exame, f, indent=4, ensure_ascii=False)
        
        st.success(f"{len(selecao)} questão(ões) adicionada(s) ao exame da faixa {faixa}.")
        st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Questões já incluídas no exame atual:")
    if not exame["questoes"]:
        st.info("Nenhuma questão adicionada ainda.")
    else:
        for i, q in enumerate(exame["questoes"], 1):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{i}. ({q['tema']}) {q['pergunta']}**")
                st.markdown(f"<small>Resposta correta: {q['resposta']}</small>", unsafe_allow_html=True)
            with col2:
                if st.button(f"Remover {i}", key=f"rem_{i}"):
                    exame["questoes"].pop(i - 1)
                    with open(exame_path, "w", encoding="utf-8") as f:
                        json.dump(exame, f, indent=4, ensure_ascii=False)
                    st.rerun()

    st.markdown("---")
    if st.button("🗑️ Excluir exame completo desta faixa", type="primary"):
        if os.path.exists(exame_path):
            os.remove(exame_path)
            st.warning(f"O exame da faixa {faixa} foi excluído.")
            st.rerun()
        else:
            st.error("O arquivo de exame não existe.")
