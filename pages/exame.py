import streamlit as st
import json
import random
from core.db import consultar_um, consultar_todos, executar
from datetime import datetime

# ============================================================
# TELA DE EXAME — LADO DO ALUNO
# ============================================================

def tela_exame(usuario):

    st.title("🥋 Exame de Faixa")

    faixa = usuario["faixa"]

    st.markdown(f"### Sua faixa atual: **{faixa}**")

    # ============================================================
    # BUSCAR O EXAME ATIVO PARA ESSA FAIXA
    # ============================================================

    exame_config = consultar_um("""
        SELECT * FROM exames_config
        WHERE faixa=? AND ativo=1
    """, (faixa,))

    if not exame_config:
        st.warning("Nenhum exame ativo disponível para sua faixa no momento.")
        return

    st.success(f"Exame ativo encontrado: **{exame_config['nome']}**")

    questoes_ids = json.loads(exame_config["questoes_ids"])
    embaralhar = bool(exame_config["embaralhar"])

    # ============================================================
    # CARREGAR QUESTÕES DO BANCO
    # ============================================================

    if not questoes_ids:
        st.error("Exame ativo não possui questões configuradas.")
        return

    # Carrega TODAS as questões selecionadas
    questoes = []
    for qid in questoes_ids:
        q = consultar_um("SELECT * FROM questoes WHERE id=?", (qid,))
        if q:
            questoes.append(q)

    if not questoes:
        st.error("Erro ao carregar questões.")
        return

    # Embaralhar ordem (se professor marcou)
    if embaralhar:
        random.shuffle(questoes)

    st.markdown("---")
    st.markdown("## 📘 Questões:")

    respostas = {}

    # ============================================================
    # FORMULÁRIO DO EXAME
    # ============================================================

    with st.form("form_exame"):

        for i, q in enumerate(questoes, start=1):

            st.markdown(f"### {i}. {q['pergunta']}")

            # Mostrar imagem se existir
            if q["imagem"]:
                st.image(q["imagem"], use_column_width=True)

            # Mostrar vídeo se existir
            if q["video"]:
                st.video(q["video"])

            opcoes = json.loads(q["opcoes"])

            resposta = st.radio(
                "Selecione a resposta:",
                options=opcoes,
                index=None,
                key=f"q_{q['id']}"
            )

            respostas[q["id"]] = resposta

            st.markdown("---")

        submit = st.form_submit_button("Finalizar Exame", type="primary")

    if not submit:
        return

    # ============================================================
    # CORREÇÃO DO EXAME
    # ============================================================

    acertos = 0
    total = len(questoes)

    for q in questoes:
        correta = q["resposta"]  # Letra correta
        opcoes = json.loads(q["opcoes"])

        # localizar label correta
        correta_texto = next((x for x in opcoes if x.startswith(correta)), None)

        if respostas[q["id"]] == correta_texto:
            acertos += 1

    percentual = round((acertos / total) * 100, 2)
    aprovado = 1 if percentual >= 70 else 0

    # ============================================================
    # SALVAR RESULTADO
    # ============================================================

    executar("""
        INSERT INTO exames (usuario_id, exame_config_id, acertos, total, percentual, aprovado, data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        usuario["id"],
        exame_config["id"],
        acertos,
        total,
        percentual,
        aprovado,
        datetime.now().strftime("%d/%m/%Y %H:%M")
    ))

    # ============================================================
    # EXIBIR RESULTADO
    # ============================================================

    st.markdown("## 📊 Resultado do Exame")

    st.info(f"Questões respondidas: **{total}**")
    st.info(f"Acertos: **{acertos}**")
    st.info(f"Percentual: **{percentual}%**")

    if aprovado:
        st.success("🎉 Parabéns! Você foi **APROVADA** no exame!")
        st.markdown("Seu certificado ficará disponível em breve.")
    else:
        st.error("❌ Você foi **REPROVADA**. Continue treinando e tente novamente.")

    st.markdown("---")
    st.markdown("Se quiser refazer, peça ao professor para atualizar seu exame ativo.")
