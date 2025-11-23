import streamlit as st
import json
import os
import random
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px
from config import DB_PATH
from utils import carregar_questoes, gerar_codigo_verificacao, gerar_pdf, normalizar_nome

def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)
    
    # Listar temas
    path_questions = "questions"
    os.makedirs(path_questions, exist_ok=True)
    temas = [f.replace(".json", "") for f in os.listdir(path_questions) if f.endswith(".json")]
    temas.append("Todos os Temas")

    col1, col2 = st.columns(2)
    with col1: tema = st.selectbox("Selecione o tema:", temas)
    with col2: faixa = st.selectbox("Sua faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])

    if st.button("Iniciar Treino 🤼", use_container_width=True):
        # Lógica de carregar questões (Copiado do original)
        if tema == "Todos os Temas":
            questoes = []
            for arquivo in os.listdir(path_questions):
                if arquivo.endswith(".json"):
                    try:
                        with open(f"{path_questions}/{arquivo}", "r", encoding="utf-8") as f:
                            questoes += json.load(f)
                    except: continue
        else:
            questoes = carregar_questoes(tema)
            
        random.shuffle(questoes)
        # ... (Restante da lógica do loop de questões e salvamento no banco) ...

def exame_de_faixa(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🥋 Exame de Faixa</h1>", unsafe_allow_html=True)
    # Copie aqui a função exame_de_faixa completa do app.py original
    # Incluindo a verificação de 'exame_habilitado' no banco

def ranking():
    st.markdown("<h1 style='color:#FFD700;'>🏆 Ranking</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM rola_resultados", conn)
    conn.close()
    
    if not df.empty:
        # Lógica de agrupamento e plotagem do gráfico
        ranking_df = df.groupby("usuario", as_index=False).agg(media=("percentual", "mean")).sort_values("media", ascending=False)
        st.dataframe(ranking_df, use_container_width=True)
        # st.plotly_chart(...)

def meus_certificados(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>📜 Meus Certificados</h1>", unsafe_allow_html=True)
    # Copie a função meus_certificados completa, que usa gerar_pdf
