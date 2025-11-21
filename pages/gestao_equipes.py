import streamlit as st
from core.db import consultar_todos, executar


def gestao_equipes():
    st.title("🏢 Gestão de Equipes")

    # ==============================
    # LISTAR EQUIPES
    # ==============================
    st.subheader("Equipes cadastradas")

    equipes = consultar_todos("""
        SELECT e.id, e.nome, u.nome AS professor
        FROM equipes e
        LEFT JOIN usuarios u ON e.professor_id = u.id
        ORDER BY e.nome
    """)

    if equipes:
        for equipe in equipes:
            st.markdown(f"""
                **Equipe:** {equipe['nome']}  
                **Professor:** {equipe['professor'] or '—'}
                """)

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Editar {equipe['id']}", key=f"editar_{equipe['id']}"):
                    st.session_state.equipe_editando = equipe["id"]
            with col2:
                if st.button(f"Excluir {equipe['id']}", key=f"excluir_{equipe['id']}"):
                    executar("DELETE FROM equipes WHERE id = ?", (equipe["id"],))
                    st.success("Equipe removida!")
                    st.rerun()

    else:
        st.info("Nenhuma equipe cadastrada ainda.")

    st.markdown("---")

    # ==============================
    # ADICIONAR NOVA EQUIPE
    # ==============================
    st.subheader("Adicionar nova equipe")

    nome_equipe = st.text_input("Nome da equipe")

    professores = consultar_todos("""
        SELECT id, nome FROM usuarios WHERE tipo IN ('professor', 'admin')
    """)
    lista_prof = [f"{p['id']} - {p['nome']}" for p in professores]

    professor_sel = st.selectbox("Professor responsável", ["Nenhum"] + lista_prof)

    if st.button("Salvar equipe", use_container_width=True):
        if not nome_equipe:
            st.warning("Digite o nome da equipe.")
        else:
            prof_id = None
            if professor_sel != "Nenhum":
                prof_id = int(professor_sel.split(" - ")[0])

            executar("""
                INSERT INTO equipes (nome, professor_id)
                VALUES (?, ?)
            """, (nome_equipe, prof_id))

            st.success("Equipe adicionada com sucesso!")
            st.rerun()

    # ==============================
    # EDITAR EQUIPE
    # ==============================
    if "equipe_editando" in st.session_state:

        st.markdown("---")
        st.subheader("Editar equipe")

        eq_id = st.session_state.equipe_editando

        dados = consultar_todos("""
            SELECT * FROM equipes WHERE id = ?
        """, (eq_id,))

        if dados:
            equipe = dados[0]

            novo_nome = st.text_input("Nome da equipe", value=equipe["nome"])

            professor_sel = st.selectbox(
                "Professor responsável",
                ["Nenhum"] + lista_prof,
                index=0 if equipe["professor_id"] is None
                else [i+1 for i, p in enumerate(lista_prof)
                      if int(p.split(" - ")[0]) == equipe["professor_id"]][0]
            )

            if st.button("Atualizar", use_container_width=True):

                prof_id = None
                if professor_sel != "Nenhum":
                    prof_id = int(professor_sel.split(" - ")[0])

                executar("""
                    UPDATE equipes
                    SET nome=?, professor_id=?
                    WHERE id=?
                """, (novo_nome, prof_id, eq_id))

                st.success("Equipe atualizada!")
                del st.session_state.equipe_editando
                st.rerun()

            if st.button("Cancelar edição"):
                del st.session_state.equipe_editando
                st.rerun()

