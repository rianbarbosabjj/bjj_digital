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

# =========================================
# MODO ROLA
# =========================================
def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)

    path_questions = "questions"
    os.makedirs(path_questions, exist_ok=True)
    temas = [f.replace(".json", "") for f in os.listdir(path_questions) if f.endswith(".json")]
    temas.append("Todos os Temas")

    col1, col2 = st.columns(2)
    with col1:
        tema = st.selectbox("Selecione o tema:", temas)
    with col2:
        faixa = st.selectbox("Sua faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])

    if st.button("Iniciar Treino 🤼", use_container_width=True):
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

        if not questoes:
            st.error("Nenhuma questão disponível.")
            return

        random.shuffle(questoes)
        acertos = 0
        total = len(questoes)

        st.markdown(f"### 🧩 Total de questões: {total}")

        for i, q in enumerate(questoes, 1):
            st.markdown(f"### {i}. {q['pergunta']}")
            
            if q.get("imagem") and os.path.exists(q["imagem"]):
                st.image(q["imagem"])
            
            resposta = st.radio("Escolha:", q["opcoes"], key=f"rola_{i}")
            
            if st.button(f"Confirmar {i}", key=f"conf_{i}"):
                if resposta.startswith(q["resposta"]):
                    st.success("Correto!")
                else:
                    st.error(f"Errado. Era: {q['resposta']}")
            st.markdown("---")

# =========================================
# EXAME DE FAIXA (CORRIGIDO)
# =========================================
def exame_de_faixa(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🥋 Exame de Faixa</h1>", unsafe_allow_html=True)

    # Verifica liberação
    if usuario_logado["tipo"] == "aluno":
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT exame_habilitado FROM alunos WHERE usuario_id=?", (usuario_logado["id"],))
        dado = cursor.fetchone()
        conn.close()
        
        if not dado or dado[0] == 0:
            st.warning("🚫 Seu exame ainda não foi liberado pelo professor.")
            return

    faixa = st.selectbox("Selecione sua faixa:", ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
    
    exame_path = f"exames/faixa_{faixa.lower()}.json"
    if not os.path.exists(exame_path):
        st.error("Nenhum exame cadastrado para esta faixa.")
        return

    try:
        with open(exame_path, "r", encoding="utf-8") as f:
            exame = json.load(f)
    except:
        st.error("Erro ao carregar arquivo do exame.")
        return

    questoes = exame.get("questoes", [])
    if not questoes:
        st.info("Sem questões neste exame.")
        return

    # Renderiza as questões
    respostas = {}
    for i, q in enumerate(questoes, 1):
        st.markdown(f"**{i}. {q['pergunta']}**")
        if q.get("imagem") and os.path.exists(q["imagem"]):
            st.image(q["imagem"])
            
        respostas[i] = st.radio("Alternativa:", q["opcoes"], key=f"exame_resp_{i}", index=None)
        st.markdown("---")

    # Botão de Finalizar
    finalizar = st.button("Finalizar Exame 🏁", use_container_width=True)

    # --- LÓGICA DE PROCESSAMENTO ---
    if finalizar:
        acertos = sum(1 for i, q in enumerate(questoes, 1) if respostas.get(i, "") and respostas[i].startswith(q["resposta"]))
        total = len(questoes)
        percentual = int((acertos / total) * 100) if total > 0 else 0
        
        st.markdown(f"## Resultado: {percentual}% de acertos ({acertos}/{total})")

        if percentual >= 70:
            st.success("🎉 APROVADO! Seu certificado foi gerado.")
            
            codigo = gerar_codigo_verificacao()
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO resultados (usuario, modo, faixa, pontuacao, acertos, total_questoes, data, codigo_verificacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (usuario_logado["nome"], "Exame de Faixa", faixa, percentual, acertos, total, datetime.now(), codigo))
            conn.commit()
            conn.close()

            st.session_state["certificado_pronto"] = True
            st.session_state["dados_certificado"] = {
                "usuario": usuario_logado["nome"],
                "faixa": faixa,
                "acertos": acertos,
                "total": total,
                "codigo": codigo
            }
        else:
            st.error("Reprovado. Tente novamente.")
            st.session_state["certificado_pronto"] = False

    # --- BOTÃO DE DOWNLOAD (COM TRATAMENTO DE ERRO) ---
    if st.session_state.get("certificado_pronto"):
        st.info("📥 Seu certificado está pronto para download abaixo:")
        
        dados = st.session_state["dados_certificado"]
        
        try:
            caminho_pdf = gerar_pdf(
                dados["usuario"],
                dados["faixa"],
                dados["acertos"],
                dados["total"],
                dados["codigo"]
            )
            
            if os.path.exists(caminho_pdf):
                with open(caminho_pdf, "rb") as f:
                    st.download_button(
                        label="📄 Baixar Certificado PDF",
                        data=f.read(),
                        file_name=os.path.basename(caminho_pdf),
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                st.error(f"Erro: O arquivo PDF não foi encontrado em {caminho_pdf}.")
                
        except Exception as e:
            st.error(f"Ocorreu um erro ao gerar o PDF: {e}")
            # Dica: Se o erro for 'name gerar_qrcode is not defined', verifique o arquivo utils.py

# =========================================
# RANKING
# =========================================
def ranking():
    st.markdown("<h1 style='color:#FFD700;'>🏆 Ranking</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM rola_resultados", conn)
    conn.close()

    if df.empty:
        st.info("Ranking vazio.")
        return

    ranking_df = df.groupby("usuario", as_index=False).agg(
        media_percentual=("percentual", "mean"),
        total_treinos=("id", "count")
    ).sort_values(by="media_percentual", ascending=False)

    ranking_df["media_percentual"] = ranking_df["media_percentual"].round(2)
    st.dataframe(ranking_df, use_container_width=True)

    fig = px.bar(ranking_df.head(10), x="usuario", y="media_percentual", title="Top 10 Média de Acertos")
    st.plotly_chart(fig, use_container_width=True)

# =========================================
# MEUS CERTIFICADOS
# =========================================
def meus_certificados(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>📜 Meus Certificados</h1>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT faixa, pontuacao, data, codigo_verificacao, acertos, total_questoes
        FROM resultados
        WHERE usuario = ? AND modo = 'Exame de Faixa'
        ORDER BY data DESC
    """, (usuario_logado["nome"],))
    certificados = cursor.fetchall()
    conn.close()

    if not certificados:
        st.info("Nenhum certificado encontrado.")
        return

    for i, (faixa, pontuacao, data, codigo, acertos, total) in enumerate(certificados, 1):
        st.markdown(f"### 🥋 Faixa {faixa}")
        st.write(f"Data: {data} | Nota: {pontuacao}% | Código: {codigo}")
        
        acertos_safe = acertos if acertos is not None else int((pontuacao/100)*10)
        total_safe = total if total is not None else 10

        try:
            caminho_pdf = gerar_pdf(usuario_logado["nome"], faixa, acertos_safe, total_safe, codigo)
            with open(caminho_pdf, "rb") as f:
                st.download_button(
                    label=f"Baixar Certificado {faixa}",
                    data=f.read(),
                    file_name=os.path.basename(caminho_pdf),
                    mime="application/pdf",
                    key=f"cert_{i}",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"Erro ao gerar este certificado: {e}")
        st.markdown("---")
