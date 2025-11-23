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
# 🤼 MODO ROLA (DO SEU PROJETO ORIGINAL)
# =========================================
def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)

    temas = [f.replace(".json", "") for f in os.listdir("questions") if f.endswith(".json")]
    temas.append("Todos os Temas")

    col1, col2 = st.columns(2)
    with col1:
        tema = st.selectbox("Selecione o tema:", temas)
    with col2:
        faixa = st.selectbox("Sua faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])

    if st.button("Iniciar Treino 🤼", use_container_width=True):
        # 🔹 Carrega questões conforme seleção
        if tema == "Todos os Temas":
            questoes = []
            for arquivo in os.listdir("questions"):
                if arquivo.endswith(".json"):
                    caminho = f"questions/{arquivo}"
                    try:
                        with open(caminho, "r", encoding="utf-8") as f:
                            questoes += json.load(f)
                    except json.JSONDecodeError:
                        st.warning(f"⚠️ Arquivo '{arquivo}' ignorado (erro de formatação).")
                        continue
        else:
            questoes = carregar_questoes(tema)

        if not questoes:
            st.error("Nenhuma questão disponível para este tema.")
            return

        random.shuffle(questoes)
        acertos = 0
        total = len(questoes)

        st.markdown(f"### 🧩 Total de questões: {total}")

        for i, q in enumerate(questoes, 1):
            st.markdown(f"### {i}. {q['pergunta']}")

            # 🔹 Exibe imagem (somente se existir e for válida)
            if q.get("imagem"):
                imagem_path = q["imagem"].strip()
                if imagem_path and os.path.exists(imagem_path):
                    st.image(imagem_path, use_container_width=True)
                elif imagem_path:
                    st.warning(f"⚠️ Imagem não encontrada: {imagem_path}")
            # (Sem else — espaço oculto se não houver imagem)

            # 🔹 Exibe vídeo (somente se existir)
            if q.get("video"):
                try:
                    st.video(q["video"])
                except Exception:
                    st.warning("⚠️ Não foi possível carregar o vídeo associado a esta questão.")
            # (Sem else — espaço oculto se não houver vídeo)

            resposta = st.radio("Escolha a alternativa:", q["opcoes"], key=f"rola_{i}")

            if st.button(f"Confirmar resposta {i}", key=f"confirma_{i}"):
                if resposta.startswith(q["resposta"]):
                    acertos += 1
                    st.success("✅ Correto!")
                else:
                    st.error(f"❌ Incorreto. Resposta correta: {q['resposta']}")
            
            st.markdown("---") # separador visual entre as questões

        percentual = int((acertos / total) * 100)
        st.markdown(f"## Resultado Final: {percentual}% de acertos ({acertos}/{total})")

        # 🔹 Salva resultado no banco
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rola_resultados (usuario, faixa, tema, acertos, total, percentual)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (usuario_logado["nome"], faixa, tema, acertos, total, percentual))
        conn.commit()
        conn.close()

        st.success("Resultado salvo com sucesso! 🏆")

# =========================================
# 🥋 EXAME DE FAIXA (DO SEU PROJETO ORIGINAL)
# =========================================
def exame_de_faixa(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🥋 Exame de Faixa</h1>", unsafe_allow_html=True)

    # Verifica se o aluno foi liberado para o exame
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT exame_habilitado FROM alunos WHERE usuario_id=?", (usuario_logado["id"],))
    dado = cursor.fetchone()
    conn.close()

    # 🔒 Apenas alunos precisam de liberação
    if usuario_logado["tipo"] not in ["admin", "professor"]:
        if not dado or dado[0] == 0:
            st.warning("🚫 Seu exame de faixa ainda não foi liberado. Aguarde a autorização do professor.")
            return

    faixa = st.selectbox(
        "Selecione sua faixa:",
        ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    )

    exame_path = f"exames/faixa_{faixa.lower()}.json"
    if not os.path.exists(exame_path):
        st.error("Nenhum exame cadastrado para esta faixa ainda.")
        return

    # 🔍 Tenta carregar o exame
    try:
        with open(exame_path, "r", encoding="utf-8") as f:
            exame = json.load(f)
    except json.JSONDecodeError:
        st.error(f"⚠️ O arquivo '{exame_path}' está corrompido. Verifique o formato JSON.")
        return

    questoes = exame.get("questoes", [])
    if not questoes:
        st.info("Ainda não há questões cadastradas para esta faixa.")
        return

    st.markdown(f"### 🧩 Total de questões: {len(questoes)}")

    respostas = {}
    for i, q in enumerate(questoes, 1):
        st.markdown(f"### {i}. {q['pergunta']}")

        # 🔹 Exibe imagem somente se existir e for válida
        if q.get("imagem"):
            imagem_path = q["imagem"].strip()
            if imagem_path and os.path.exists(imagem_path):
                st.image(imagem_path, use_container_width=True)
            elif imagem_path:
                st.warning(f"⚠️ Imagem não encontrada: {imagem_path}")

        # 🔹 Exibe vídeo somente se existir
        if q.get("video"):
            try:
                st.video(q["video"])
            except Exception:
                st.warning("⚠️ Não foi possível carregar o vídeo associado a esta questão.")

        # 🔹 Corrigido: nenhuma alternativa vem pré-selecionada
        respostas[i] = st.radio(
            "Escolha a alternativa:",
            q["opcoes"],
            key=f"exame_{i}",
            index=None
        )

        st.markdown("---")

    # 🔘 Botão para finalizar o exame
    finalizar = st.button("Finalizar Exame 🏁", use_container_width=True)

    if finalizar:
        acertos = sum(
            1 for i, q in enumerate(questoes, 1)
            if respostas.get(i, "") and respostas[i].startswith(q["resposta"])
        )

        total = len(questoes)
        percentual = int((acertos / total) * 100)
        st.markdown(f"## Resultado Final: {percentual}% de acertos ({acertos}/{total})")

        # 🔹 Reseta variáveis antes de definir novo estado
        st.session_state["certificado_pronto"] = False

        if percentual >= 70:
            st.success("🎉 Parabéns! Você foi aprovado(a) no Exame de Faixa! 👏")

            codigo = gerar_codigo_verificacao()
            st.session_state["certificado_pronto"] = True
            st.session_state["dados_certificado"] = {
                "usuario": usuario_logado["nome"],
                "faixa": faixa,
                "acertos": acertos,
                "total": total,
                "codigo": codigo
            }

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            # [BUGFIX] Salva acertos e total para recriação do PDF
            cursor.execute("""
                INSERT INTO resultados (usuario, modo, faixa, pontuacao, acertos, total_questoes, data, codigo_verificacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (usuario_logado["nome"], "Exame de Faixa", faixa, percentual, acertos, total, datetime.now(), codigo))
            conn.commit()
            conn.close()

        else:
            st.error("😞 Você não atingiu a pontuação mínima (70%). Continue treinando e tente novamente! 💪")

    # 🔘 Exibição do botão de download — somente após clique e aprovação
    if st.session_state.get("certificado_pronto") and finalizar:
        dados = st.session_state["dados_certificado"]
        caminho_pdf = gerar_pdf(
            dados["usuario"],
            dados["faixa"],
            dados["acertos"],
            dados["total"],
            dados["codigo"]
        )

        st.info("Clique abaixo para gerar e baixar seu certificado.")
        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label="📥 Baixar Certificado de Exame",
                data=f.read(),
                file_name=os.path.basename(caminho_pdf),
                mime="application/pdf",
                use_container_width=True
            )

        st.success("Certificado gerado com sucesso! 🥋")

# =========================================
# 🏆 RANKING (DO SEU PROJETO ORIGINAL)
# =========================================
def ranking():
    st.markdown("<h1 style='color:#FFD700;'>🏆 Ranking do Modo Rola</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM rola_resultados", conn)
    conn.close()

    if df.empty:
        st.info("Nenhum resultado disponível no ranking ainda.")
        return

    filtro_faixa = st.selectbox("Filtrar por faixa:", ["Todas"] + sorted(df["faixa"].unique().tolist()))
    if filtro_faixa != "Todas":
        df = df[df["faixa"] == filtro_faixa]

    if df.empty:
        st.info("Nenhum resultado para esta faixa.")
        return

    ranking_df = df.groupby("usuario", as_index=False).agg(
        media_percentual=("percentual", "mean"),
        total_treinos=("id", "count")
    ).sort_values(by="media_percentual", ascending=False).reset_index(drop=True)

    ranking_df["Posição"] = range(1, len(ranking_df) + 1)
    ranking_df["media_percentual"] = ranking_df["media_percentual"].round(2)
    
    st.dataframe(
        ranking_df[["Posição", "usuario", "media_percentual", "total_treinos"]], 
        use_container_width=True,
        column_config={"media_percentual": st.column_config.NumberColumn(format="%.2f%%")}
    )

    fig = px.bar(
        ranking_df.head(10),
        x="usuario",
        y="media_percentual",
        text_auto=True,
        title="Top 10 - Modo Rola (% Média de Acertos)",
        color="media_percentual",
        color_continuous_scale="YlOrBr",
    )
    fig.update_layout(xaxis_title="Usuário", yaxis_title="% Média de Acertos")
    st.plotly_chart(fig, use_container_width=True)

# =========================================
# 📜 MEUS CERTIFICADOS (DO SEU PROJETO ORIGINAL)
# =========================================
def meus_certificados(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>📜 Meus Certificados</h1>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # [BUGFIX] Seleciona acertos e total_questoes
    cursor.execute("""
        SELECT faixa, pontuacao, data, codigo_verificacao, acertos, total_questoes
        FROM resultados
        WHERE usuario = ? AND modo = 'Exame de Faixa'
        ORDER BY data DESC
    """, (usuario_logado["nome"],))
    certificados = cursor.fetchall()
    conn.close()

    if not certificados:
        st.info("Você ainda não possui certificados emitidos. Complete um exame de faixa para conquistá-los! 🥋")
        return

    for i, (faixa, pontuacao, data, codigo, acertos, total) in enumerate(certificados, 1):
        st.markdown(f"### 🥋 {i}. Faixa {faixa}")
        st.markdown(f"- **Aproveitamento:** {pontuacao}%")
        st.markdown(f"- **Data:** {datetime.fromisoformat(data).strftime('%d/%m/%Y às %H:%M')}")
        st.markdown(f"- **Código de Verificação:** `{codigo}`")

        # Define um nome de arquivo padronizado
        nome_arquivo = f"Certificado_{normalizar_nome(usuario_logado['nome'])}_{normalizar_nome(faixa)}.pdf"
        caminho_pdf_esperado = f"relatorios/{nome_arquivo}"

        # 🔹 Se o certificado não estiver salvo, ele será recriado
        if not os.path.exists(caminho_pdf_esperado):
            
            # [BUGFIX] Usa os valores corretos do banco.
            # Se acertos ou total for NULO (de dados antigos), usa um fallback.
            acertos_pdf = acertos if acertos is not None else int((pontuacao / 100) * 10) # Fallback
            total_pdf = total if total is not None else 10 # Fallback

            caminho_pdf = gerar_pdf(
                usuario_logado["nome"],
                faixa,
                acertos_pdf,
                total_pdf,
                codigo
            )
        else:
            caminho_pdf = caminho_pdf_esperado
        
        try:
            with open(caminho_pdf, "rb") as f:
                st.download_button(
                    label=f"📥 Baixar Certificado - Faixa {faixa}",
                    data=f.read(),
                    file_name=os.path.basename(caminho_pdf),
                    mime="application/pdf",
                    key=f"baixar_{i}",
                    use_container_width=True
                )
        except FileNotFoundError:
            st.error(f"Erro ao tentar recarregar o certificado '{nome_arquivo}'. Tente novamente.")
            
        st.markdown("---")
