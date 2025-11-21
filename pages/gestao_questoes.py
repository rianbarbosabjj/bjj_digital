import streamlit as st
import json
import os


QUESTIONS_DIR = "questions"


def carregar_questoes(tema):
    caminho = f"{QUESTIONS_DIR}/{tema}.json"
    if not os.path.exists(caminho):
        return []
    try:
        return json.load(open(caminho, "r", encoding="utf-8"))
    except:
        return []


def salvar_questoes(tema, questoes):
    os.makedirs(QUESTIONS_DIR, exist_ok=True)
    with open(f"{QUESTIONS_DIR}/{tema}.json", "w", encoding="utf-8") as f:
        json.dump(questoes, f, indent=4, ensure_ascii=False)


def gestao_questoes():
    st.title("🧠 Gestão de Questões")

    os.makedirs(QUESTIONS_DIR, exist_ok=True)

    temas = [f.replace(".json", "") for f in os.listdir(QUESTIONS_DIR) if f.endswith(".json")]

    tema = st.selectbox("Selecione o tema", ["Criar novo tema"] + temas)

    # ===============================================
    # CRIAR NOVO TEMA
    # ===============================================
    if tema == "Criar novo tema":
        novo = st.text_input("Nome do novo tema")

        if st.button("Criar Tema"):
            if not novo.strip():
                st.error("Digite um nome válido.")
                return

            salvar_questoes(novo, [])
            st.success("Tema criado!")
            st.rerun()
        return

    # ===============================================
    # TEMA EXISTE → CARREGAR QUESTÕES
    # ===============================================
    questoes = carregar_questoes(tema)

    st.markdown("---")
    st.subheader(f"Questões do tema **{tema}**")

    # ===============================================
    # FORM DE ADIÇÃO DE QUESTÃO
    # ===============================================
    with st.expander("➕ Adicionar Nova Questão", expanded=False):

        pergunta = st.text_area("Pergunta")
        altA = st.text_input("Alternativa A")
        altB = st.text_input("Alternativa B")
        altC = st.text_input("Alternativa C")
        altD = st.text_input("Alternativa D")
        altE = st.text_input("Alternativa E")

        resposta = st.selectbox("Resposta correta", ["A", "B", "C", "D", "E"])
        imagem = st.text_input("Caminho da imagem (opcional)")
        video = st.text_input("URL do vídeo (opcional)")

        if st.button("Salvar Questão"):

            nova_q = {
                "pergunta": pergunta,
                "opcoes": [
                    f"A) {altA}",
                    f"B) {altB}",
                    f"C) {altC}",
                    f"D) {altD}",
                    f"E) {altE}",
                ],
                "resposta": resposta,
                "imagem": imagem.strip(),
                "video": video.strip()
            }

            questoes.append(nova_q)
            salvar_questoes(tema, questoes)
            st.success("Questão adicionada com sucesso!")
            st.rerun()

    # ===============================================
    # LISTA DE QUESTÕES
    # ===============================================
    if not questoes:
        st.info("Nenhuma questão cadastrada ainda.")
        return

    for idx, q in enumerate(questoes, start=1):
        st.markdown(f"### {idx}. {q['pergunta']}")
        for alt in q["opcoes"]:
            st.markdown(f"- {alt}")
        st.markdown(f"**Resposta correta:** {q['resposta']}")

        if st.button(f"🗑️ Excluir {idx}", key=f"del_{idx}"):
            questoes.pop(idx - 1)
            salvar_questoes(tema, questoes)
            st.rerun()

        st.markdown("---")

