import streamlit as st
import sqlite3
import pandas as pd
from config import DB_PATH

def painel_professor():
    st.markdown("<h1 style='color:#FFD700;'>👩‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    usuario_logado = st.session_state.usuario
    prof_usuario_id = usuario_logado["id"]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 🔍 Identifica a(s) equipe(s) onde o professor é responsável
    cursor.execute("SELECT id, nome FROM equipes WHERE professor_responsavel_id=?", (prof_usuario_id,))
    equipes_responsaveis = cursor.fetchall()

    if not equipes_responsaveis:
        st.warning("Você não está cadastrado como Professor Responsável em nenhuma equipe. Operações de gestão limitadas.")
        conn.close()
        return

    st.success(f"Você é responsável pelas equipes: {', '.join([e[1] for e in equipes_responsaveis])}")
    
    equipe_ids = [e[0] for e in equipes_responsaveis]
    
    # --- ABA DE PENDÊNCIAS ---
    st.markdown("## 🔔 Aprovação de Vínculos Pendentes")

    # 2. 📝 Busca Pendências de Alunos
    pendencias_alunos = pd.read_sql_query(f"""
        SELECT 
            a.id AS aluno_pk_id, u.nome AS Aluno, u.email AS Email, a.faixa_atual AS Faixa, 
            e.nome AS Equipe, a.data_pedido
        FROM alunos a
        JOIN usuarios u ON a.usuario_id = u.id
        LEFT JOIN equipes e ON a.equipe_id = e.id
        WHERE a.status_vinculo='pendente' AND a.equipe_id IN ({','.join(['?'] * len(equipe_ids))})
    """, conn, params=equipe_ids)

    # 3. 👩‍🏫 Busca Pendências de Professores
    pendencias_professores = pd.read_sql_query(f"""
        SELECT 
            p.id AS prof_pk_id, u.nome AS Professor, u.email AS Email, 
            e.nome AS Equipe, u.data_criacao
        FROM professores p
        JOIN usuarios u ON p.usuario_id = u.id
        LEFT JOIN equipes e ON p.equipe_id = e.id
        WHERE p.status_vinculo='pendente' AND p.equipe_id IN ({','.join(['?'] * len(equipe_ids))})
    """, conn, params=equipe_ids)

    if pendencias_alunos.empty and pendencias_professores.empty:
        st.info("Não há novos pedidos de vínculo pendentes para suas equipes.")
    else:
        # --- APROVAR ALUNOS ---
        if not pendencias_alunos.empty:
            st.markdown("### Alunos para Aprovação:")
            st.dataframe(pendencias_alunos, use_container_width=True)
            
            aluno_para_aprovar = st.selectbox("Selecione o Aluno para Ação:", pendencias_alunos["Aluno"].tolist(), key="aprov_aluno_sel")
            aluno_pk_id = pendencias_alunos[pendencias_alunos["Aluno"] == aluno_para_aprovar]["aluno_pk_id"].iloc[0]
            
            col_a1, col_a2 = st.columns(2)
            if col_a1.button(f"✅ Aprovar Vínculo de {aluno_para_aprovar}", key="btn_aprov_aluno"):
                # Obtém o ID da PK do professor na tabela 'professores'
                cursor.execute("SELECT id FROM professores WHERE usuario_id=?", (prof_usuario_id,))
                prof_pk_id_vinculo = cursor.fetchone()[0]

                cursor.execute(
                    "UPDATE alunos SET status_vinculo='ativo', professor_id=? WHERE id=?", 
                    (prof_pk_id_vinculo, int(aluno_pk_id))
                )
                conn.commit()
                st.success(f"Vínculo do aluno {aluno_para_aprovar} ATIVADO.")
                st.rerun()
            
            if col_a2.button(f"❌ Rejeitar Vínculo de {aluno_para_aprovar}", key="btn_rejeitar_aluno"):
                cursor.execute("UPDATE alunos SET status_vinculo='rejeitado' WHERE id=?", (int(aluno_pk_id),))
                conn.commit()
                st.warning(f"Vínculo do aluno {aluno_para_aprovar} REJEITADO.")
                st.rerun()

        # --- APROVAR PROFESSORES ---
        if not pendencias_professores.empty:
            st.markdown("### Professores para Aprovação:")
            st.dataframe(pendencias_professores, use_container_width=True)

            prof_para_aprovar = st.selectbox("Selecione o Professor para Ação:", pendencias_professores["Professor"].tolist(), key="aprov_prof_sel")
            prof_pk_id = pendencias_professores[pendencias_professores["Professor"] == prof_para_aprovar]["prof_pk_id"].iloc[0]
            
            col_p1, col_p2 = st.columns(2)
            if col_p1.button(f"✅ Aprovar Vínculo de {prof_para_aprovar}", key="btn_aprov_prof"):
                cursor.execute(
                    "UPDATE professores SET status_vinculo='ativo' WHERE id=?", 
                    (int(prof_pk_id),)
                )
                conn.commit()
                st.success(f"Vínculo do professor {prof_para_aprovar} ATIVADO.")
                st.rerun()
                
            if col_p2.button(f"❌ Rejeitar Vínculo de {prof_para_aprovar}", key="btn_rejeitar_prof"):
                cursor.execute("UPDATE professores SET status_vinculo='rejeitado' WHERE id=?", (int(prof_pk_id),))
                conn.commit()
                st.warning(f"Vínculo do professor {prof_para_aprovar} REJEITADO.")
                st.rerun()

    conn.close()

# =========================================
# 🏛️ GESTÃO DE EQUIPES (DO SEU PROJETO ORIGINAL)
# =========================================
def gestao_equipes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Gestão de Equipes</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Definição das variáveis de aba
    aba1, aba2, aba3 = st.tabs(["🏫 Equipes", "👩‍🏫 Professores", "🥋 Alunos"])

    # --- ABA 1: Criação e Edição de Equipe ---
    with aba1:
        st.subheader("Cadastrar nova equipe")
        nome_equipe = st.text_input("Nome da nova equipe:")
        descricao = st.text_area("Descrição da nova equipe:")

        professores_df = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='professor'", conn)
        professor_responsavel_id = None
        if not professores_df.empty:
            prof_resp_nome = st.selectbox(
                "👩‍🏫 Professor responsável:",
                ["Nenhum"] + professores_df["nome"].tolist()
            )
            if prof_resp_nome != "Nenhum":
                professor_responsavel_id = int(professores_df.loc[professores_df["nome"] == prof_resp_nome, "id"].values[0])

        if st.button("➕ Criar Equipe"):
            if nome_equipe.strip():
                # 1. Cria a equipe
                cursor.execute(
                    "INSERT INTO equipes (nome, descricao, professor_responsavel_id) VALUES (?, ?, ?)",
                    (nome_equipe, descricao, professor_responsavel_id)
                )
                novo_equipe_id = cursor.lastrowid
                
                # 2. VERIFICA E ATIVA O VÍNCULO DO PROFESSOR RESPONSÁVEL
                if professor_responsavel_id:
                    cursor.execute("SELECT id FROM professores WHERE usuario_id=? AND status_vinculo='ativo'", 
                                   (professor_responsavel_id,))
                    
                    if not cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO professores (usuario_id, equipe_id, pode_aprovar, eh_responsavel, status_vinculo)
                            VALUES (?, ?, 1, 1, 'ativo')
                        """, (professor_responsavel_id, novo_equipe_id))
                
                conn.commit()
                st.success(f"Equipe '{nome_equipe}' criada com sucesso! Professor Responsável ativado.")
                st.rerun()
            else:
                st.error("O nome da equipe é obrigatório.")

        st.markdown("---")
        st.subheader("Equipes existentes")
        equipes_df = pd.read_sql_query("""
            SELECT e.id, e.nome, e.descricao, COALESCE(u.nome, 'Nenhum') AS professor_responsavel
            FROM equipes e
            LEFT JOIN usuarios u ON e.professor_responsavel_id = u.id
        """, conn)
        if equipes_df.empty:
            st.info("Nenhuma equipe cadastrada.")
        else:
            st.dataframe(equipes_df, use_container_width=True)
            st.markdown("### ✏️ Editar ou Excluir Equipe")

            equipe_lista = equipes_df["nome"].tolist()
            equipe_sel = st.selectbox("Selecione a equipe:", equipe_lista)
            equipe_id = int(equipes_df.loc[equipes_df["nome"] == equipe_sel, "id"].values[0])
            dados_equipe = equipes_df[equipes_df["id"] == equipe_id].iloc[0]

            with st.expander(f"Gerenciar {equipe_sel}", expanded=True):
                novo_nome = st.text_input("Novo nome da equipe:", value=dados_equipe["nome"])
                nova_desc = st.text_area("Descrição:", value=dados_equipe["descricao"] or "")

                prof_atual = dados_equipe["professor_responsavel"]
                prof_opcoes = ["Nenhum"] + professores_df["nome"].tolist()
                index_atual = prof_opcoes.index(prof_atual) if prof_atual in prof_opcoes else 0
                novo_prof = st.selectbox("👩‍🏫 Professor responsável:", prof_opcoes, index=index_atual)
                novo_prof_id = None
                if novo_prof != "Nenhum":
                    novo_prof_id = int(professores_df.loc[professores_df["nome"] == novo_prof, "id"].values[0])

                col1, col2 = st.columns(2)
                if col1.button("💾 Salvar Alterações"):
                    cursor.execute(
                        "UPDATE equipes SET nome=?, descricao=?, professor_responsavel_id=? WHERE id=?",
                        (novo_nome, nova_desc, novo_prof_id, equipe_id)
                    )
                    conn.commit()
                    st.success(f"Equipe '{novo_nome}' atualizada com sucesso! ✅")
                    st.rerun()

                if col2.button("🗑️ Excluir Equipe"):
                    cursor.execute("DELETE FROM equipes WHERE id=?", (equipe_id,))
                    conn.commit()
                    st.warning(f"Equipe '{equipe_sel}' excluída com sucesso.")
                    st.rerun()

    # === 👩‍🏫 ABA 2 - PROFESSORES (Apoio) ===
    with aba2:
        st.subheader("Vincular professor de apoio a uma equipe")

        professores_df = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='professor'", conn)
        equipes_df = pd.read_sql_query("SELECT id, nome FROM equipes", conn)

        if professores_df.empty or equipes_df.empty:
            st.warning("Cadastre professores e equipes primeiro.")
        else:
            prof = st.selectbox("Professor de apoio:", professores_df["nome"])
            equipe_prof = st.selectbox("Equipe:", equipes_df["nome"])
            prof_id = int(professores_df.loc[professores_df["nome"] == prof, "id"].values[0])
            equipe_id = int(equipes_df.loc[equipes_df["nome"] == equipe_prof, "id"].values[0])

            if st.button("📎 Vincular Professor de Apoio"):
                cursor.execute("""
                    INSERT INTO professores (usuario_id, equipe_id, pode_aprovar, status_vinculo)
                    VALUES (?, ?, ?, ?)
                """, (prof_id, equipe_id, 0, "ativo"))
                conn.commit()
                st.success(f"Professor {prof} vinculado como apoio à equipe {equipe_prof}.")
                st.rerun()

        st.markdown("---")
        st.subheader("Professores vinculados")
        profs_df = pd.read_sql_query("""
            SELECT p.id, u.nome AS professor, e.nome AS equipe, p.status_vinculo
            FROM professores p
            JOIN usuarios u ON p.usuario_id = u.id
            JOIN equipes e ON p.equipe_id = e.id
        """, conn)
        if profs_df.empty:
            st.info("Nenhum professor vinculado ainda.")
        else:
            st.dataframe(profs_df, use_container_width=True)

    # === 🥋 ABA 3 - ALUNOS (Com Edição de Vínculo Segura) ===
    with aba3:
        st.subheader("Vincular aluno a professor e equipe")

        alunos_df = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='aluno'", conn)
        
        professores_disponiveis_df = pd.read_sql_query("""
            -- Professores Responsáveis
            SELECT 
                u.id AS usuario_id, u.nome AS nome_professor, e.id AS equipe_id
            FROM usuarios u
            INNER JOIN equipes e ON u.id = e.professor_responsavel_id
            
            UNION
            
            -- Professores Auxiliares Ativos
            SELECT 
                u.id AS usuario_id, u.nome AS nome_professor, p.equipe_id
            FROM professores p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.status_vinculo='ativo'
        """, conn)
        
        professores_disponiveis_nomes = sorted(professores_disponiveis_df["nome_professor"].unique().tolist())
        equipes_df = pd.read_sql_query("SELECT id, nome FROM equipes", conn)

        if alunos_df.empty or professores_disponiveis_df.empty or equipes_df.empty:
            st.warning("Cadastre alunos, professores e equipes primeiro.")
        else:
            aluno = st.selectbox("🥋 Aluno:", alunos_df["nome"])
            aluno_id = int(alunos_df.loc[alunos_df["nome"] == aluno, "id"].values[0])

            # 🚨 CORREÇÃO CRÍTICA: Busca o vínculo existente de forma segura (LEFT JOIN)
            vinc_existente_df = pd.read_sql_query(f"""
                SELECT a.professor_id, a.equipe_id, up.nome as professor_nome, e.nome as equipe_nome
                FROM alunos a
                LEFT JOIN professores p ON a.professor_id = p.id
                LEFT JOIN usuarios up ON p.usuario_id = up.id
                LEFT JOIN equipes e ON a.equipe_id = e.id
                WHERE a.usuario_id={aluno_id}
            """, conn)
            
            vinc_existente = vinc_existente_df.iloc[0] if not vinc_existente_df.empty else None
            
            default_prof_index = 0
            default_equipe_index = 0
            
            if vinc_existente is not None and vinc_existente['professor_nome']:
                # 🎯 AGORA USAMOS OS NOMES CORRETOS JÁ BUSCADOS VIA JOIN
                prof_atual_nome = vinc_existente['professor_nome']
                equipe_atual_nome = vinc_existente['equipe_nome']
                
                if prof_atual_nome in professores_disponiveis_nomes:
                    default_prof_index = professores_disponiveis_nomes.index(prof_atual_nome)
                if equipe_atual_nome in equipes_df["nome"].tolist():
                    default_equipe_index = equipes_df["nome"].tolist().index(equipe_atual_nome)

            # --- Selectboxes re-renderizadas ---
            professor_nome = st.selectbox("👩‍🏫 Professor vinculado (nome):", professores_disponiveis_nomes, index=default_prof_index)
            equipe_aluno = st.selectbox("🏫 Equipe do aluno:", equipes_df["nome"], index=default_equipe_index)

            equipe_id = int(equipes_df.loc[equipes_df["nome"] == equipe_aluno, "id"].values[0])

            # 1. Encontra o usuario_id do professor selecionado
            prof_usuario_id = professores_disponiveis_df.loc[professores_disponiveis_df["nome_professor"] == professor_nome, "usuario_id"].iloc[0]

            # 2. Encontra a PK na tabela 'professores' (p.id) e garante o vínculo ativo
            cursor.execute("SELECT id FROM professores WHERE usuario_id=? AND status_vinculo='ativo'", (prof_usuario_id,))
            prof_pk_id_result = cursor.fetchone()
            professor_id = prof_pk_id_result[0] if prof_pk_id_result else None

            if not professor_id:
                # Lógica para criar/ativar o registro na tabela professores
                cursor.execute("SELECT id FROM professores WHERE usuario_id=?", (prof_usuario_id,))
                existing_prof_record = cursor.fetchone()
                
                if existing_prof_record:
                    cursor.execute("UPDATE professores SET status_vinculo='ativo', equipe_id=? WHERE usuario_id=?", (equipe_id, prof_usuario_id))
                    conn.commit()
                    professor_id = existing_prof_record[0]
                    st.info(f"O vínculo do professor {professor_nome} foi ATIVADO para prosseguir.")
                else:
                    cursor.execute("""
                        INSERT INTO professores (usuario_id, equipe_id, pode_aprovar, eh_responsavel, status_vinculo)
                        VALUES (?, ?, 1, 0, 'ativo')
                    """, (prof_usuario_id, equipe_id))
                    conn.commit()
                    professor_id = cursor.lastrowid
                    st.info(f"Vínculo do professor {professor_nome} CRIADO para prosseguir.")
            
            # --- Tenta Vincular/Editar o Aluno ---
            
            # Verifica se o aluno já tem um registro na tabela 'alunos'
            cursor.execute("SELECT id FROM alunos WHERE usuario_id=?", (aluno_id,))
            aluno_registro_id = cursor.fetchone()
            
            botao_texto = "✅ Vincular Aluno" if aluno_registro_id is None else "💾 Atualizar Vínculo"

            if professor_id and st.button(botao_texto):
                
                if aluno_registro_id:
                    # UPDATE: Aluno já existe, atualiza o vínculo
                    cursor.execute("""
                        UPDATE alunos SET professor_id=?, equipe_id=?, status_vinculo='ativo'
                        WHERE usuario_id=?
                    """, (professor_id, equipe_id, aluno_id))
                    st.success(f"Vínculo do aluno {aluno} ATUALIZADO (Professor: {professor_nome}, Equipe: {equipe_aluno}).")
                else:
                    # INSERT: Aluno não existe, cria o vínculo
                    cursor.execute("""
                        INSERT INTO alunos (usuario_id, faixa_atual, turma, professor_id, equipe_id, status_vinculo)
                        VALUES (?, ?, ?, ?, ?, 'ativo')
                    """, (aluno_id, "Branca", "Turma 1", professor_id, equipe_id))
                    st.success(f"Aluno {aluno} VINCULADO com sucesso (Professor: {professor_nome}, Equipe: {equipe_aluno}).")
                
                conn.commit()
                st.rerun()

        st.markdown("---")
        st.subheader("Alunos vinculados")
        alunos_vinc_df = pd.read_sql_query("""
            SELECT a.id, u.nome AS aluno, e.nome AS equipe, up.nome AS professor
            FROM alunos a
            JOIN usuarios u ON a.usuario_id = u.id
            JOIN equipes e ON a.equipe_id = e.id
            JOIN professores p ON a.professor_id = p.id
            JOIN usuarios up ON p.usuario_id = up.id
        """, conn)
        if alunos_vinc_df.empty:
            st.info("Nenhum aluno vinculado ainda.")
        else:
            st.dataframe(alunos_vinc_df, use_container_width=True)

    conn.close()
