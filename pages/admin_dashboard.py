import streamlit as st
import pandas as pd
from core.db import consultar_todos


def admin_dashboard():
    st.title("🛡️ Painel Administrativo — BJJ Digital")

    st.markdown("Visão geral do sistema, dados e atalhos rápidos.")

    # ==========================================
    # CARREGAR DADOS
    # ==========================================

    usuarios = consultar_todos("SELECT * FROM usuarios")
    exames = consultar_todos("SELECT * FROM exames")
    certificados = consultar_todos("SELECT * FROM certificados")

    # ==========================================
    # CARTÕES RESUMO
    # ==========================================

    col1, col2, col3 = st.columns(3)
    col1.metric("Usuários cadastrados", len(usuarios))
    col2.metric("Exames aplicados", len(exames))
    col3.metric("Certificados emitidos", len(certificados))

    st.markdown("---")

    # ==========================================
    # USUÁRIOS POR TIPO
    # ==========================================

    tipos = {"aluno": 0, "professor": 0, "admin": 0}
    for u in usuarios:
        if u["tipo"] in tipos:
            tipos[u["tipo"]] += 1

    st.subheader("Usuários por tipo")

    df_tipo = pd.DataFrame.from_dict(tipos, orient="index", columns=["Quantidade"])
    st.bar_chart(df_tipo)

    st.markdown("---")

    # ==========================================
    # ÚLTIMOS CADASTRADOS
    # ==========================================

    st.subheader("Últimos usuários cadastrados")

    ultimos = consultar_todos("""
        SELECT nome, email, tipo, criado_em
        FROM usuarios
        ORDER BY criado_em DESC
        LIMIT 10
    """)

    if ultimos:
        df_ult = pd.DataFrame(ultimos)
        df_ult.columns = ["Nome", "Email", "Tipo", "Data"]
        st.table(df_ult)
    else:
        st.info("Nenhum usuário cadastrado.")

    st.markdown("---")

    # ==========================================
    # ATALHOS
    # ==========================================

    st.subheader("Acessos rápidos")

    st.markdown("""
    - 👉 **Gestão de Usuários**
    - 👉 **Gestão de Equipes**
    - 👉 **Gestão de Questões**
    - 👉 **Painel do Professor**
    - 👉 **Histórico de Exames**
    """)

    st.info("Use o menu lateral para navegar entre as páginas.")
