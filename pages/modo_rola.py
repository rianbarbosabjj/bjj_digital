import streamlit as st
import pandas as pd

def tela_modo_rola(usuario):
    st.title("🥋 Modo Rola")

    st.markdown("Registro rápido de rolas entre alunos.")

    if "rolas" not in st.session_state:
        st.session_state.rolas = []

    col1, col2 = st.columns(2)
    with col1:
        adversario = st.text_input("Nome do adversário")
    with col2:
        resultado = st.selectbox("Resultado", ["Vitória", "Empate", "Derrota"])

    if st.button("Registrar rola", use_container_width=True):
        if adversario:
            st.session_state.rolas.append({
                "aluno": usuario["nome"],
                "adversario": adversario,
                "resultado": resultado
            })
            st.success("Rola registrada!")

    if st.session_state.rolas:
        st.subheader("Histórico")
        st.dataframe(pd.DataFrame(st.session_state.rolas))

