import streamlit as st
from core.questions import montar_prova_embaralhada
from core.db import executar


def tela_exame(usuario):
    st.title("🧪 Exame de Faixa")

    faixa = usuario.get("faixa", "branca")

    st.info(f"Exame disponível para a faixa **{faixa}**.")

    # Carrega prova
    prova = montar_prova_embaralhada(faixa)

    if not prova:
        st.warning("Ainda não há questões cadastradas para essa faixa.")
        return

    respostas = {}

    for i, q in enumerate(prova):
        st.markdown(f"#### {i+1}. {q['pergunta']}")
        respostas[q["id"]] = st.radio(
            "Selecione",
            ["a", "b", "c", "d"],
            key=f"resposta_{i}"
        )
        st.markdown("---")

    if st.button("Enviar exame", use_container_width=True):
        acertos = 0
        total = len(prova)

        for q in prova:
            if respostas[q["id"]] == q["correta"]:
                acertos += 1

        nota = round((acertos / total) * 10, 2)
        aprovado = 1 if nota >= 6 else 0

        executar("""
            INSERT INTO exames (usuario_id, faixa, nota, aprovado)
            VALUES (?, ?, ?, ?)
        """, (usuario["id"], faixa, nota, aprovado))

        if aprovado:
            st.success(f"Parabéns! Você foi aprovada(o) com nota **{nota}**! 🎉")
        else:
            st.error(f"Você obteve nota **{nota}**. Continue treinando!")

