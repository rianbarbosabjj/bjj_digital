import streamlit as st
import pandas as pd
from core.db import consultar_todos

def tela_ranking():
    st.title("🏅 Ranking de Alunos")

    dados = consultar_todos("""
        SELECT u.nome, u.faixa,
               (SELECT COUNT(*) FROM exames e WHERE e.usuario_id = u.id AND e.aprovado = 1) AS aprovacoes
        FROM usuarios u
        ORDER BY aprovacoes DESC
    """)

    if not dados:
        st.info("Ainda não há dados de ranking disponíveis.")
        return

    tabela = pd.DataFrame(dados)
    tabela.columns = ["Nome", "Faixa", "Aprovações"]

    st.dataframe(tabela)
