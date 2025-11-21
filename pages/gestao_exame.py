import streamlit as st
import pandas as pd
from core.db import consultar_todos, executar


def gestao_exames():
    st.title("📝 Gestão de Exames")

    # ==========================================
    # CARREGAR EXAMES
    # ==========================================

    exames = consultar_todos("""
        SELECT e.id, u.nome AS aluno, e.faixa, e.nota, e.aprovado, e.data
        FROM exames e
        JOIN usuarios u ON u.id = e.usuario_id
        ORDER BY e.data DESC
    """)

    if not exames:
        st.info("Nenhum exame registrado ainda.")
        return

    df = pd.DataFrame(exames)
    df.columns = ["ID", "Aluno", "Faixa", "Nota", "Aprovado", "Data"]

    st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # ==========================================
    # FILTROS
    # ==========================================

    st.subheader("Filtrar exames")

    alunos = sorted(list(set(df["Aluno"].tolist())))
    faixas = sorted(list(set(df["Faixa"].tolist())))

    col1, col2 = st.columns(2)
    with col1:
        filtro_aluno = st.selectbox("Filtrar por aluno", ["Todos"] + alunos)
    with col2:
        filtro_faixa = st.selectbox("Filtrar por faixa", ["Todos"] + faixas)

    df_filtrado = df.copy()

    if filtro_aluno != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Aluno"] == filtro_aluno]

    if filtro_faixa != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Faixa"] == filtro_faixa]

    st.dataframe(df_filtrado, use_container_width=True)

    st.markdown("---")

    # ==========================================
    # REMOVER EXAME
    # ==========================================

    st.subheader("Excluir exame")

    lista_ids = df["ID"].tolist()
    id_sel = st.selectbox("Escolha o exame para excluir", lista_ids)

    if st.button("Excluir", use_container_width=True):
        executar("DELETE FROM exames WHERE id=?", (id_sel,))
        st.success("Exame removido com sucesso!")
        st.rerun()

