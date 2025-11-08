def modo_exame():
    mostrar_cabecalho("🏁 Exame de Faixa")

    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa = st.selectbox("Selecione a faixa para o exame:", faixas)
    usuario = st.text_input("Nome do aluno:")
    professor = st.text_input("Nome do professor responsável:")
    tema = "regras"

    # Inicializa estados da sessão
    if "quiz_iniciado" not in st.session_state:
        st.session_state.quiz_iniciado = False
        st.session_state.respostas = {}
        st.session_state.pontuacao = 0

    if st.button("Iniciar Exame") or st.session_state.quiz_iniciado:
        st.session_state.quiz_iniciado = True
        questoes = carregar_questoes(tema)
        random.shuffle(questoes)
        questoes = questoes[:5]
        total = len(questoes)

        for i, q in enumerate(questoes, 1):
            if "video" in q and q["video"]:
                st.video(q["video"])
            if "imagem" in q and q["imagem"]:
                st.image(q["imagem"], use_container_width=True)
            st.subheader(f"{i}. {q['pergunta']}")

            key_resposta = f"resposta_{i}"
            resposta = st.radio("Escolha uma opção:", q["opcoes"], key=key_resposta, index=None)

            if resposta and key_resposta not in st.session_state.respostas:
                st.session_state.respostas[key_resposta] = resposta
                if resposta.startswith(q["resposta"]):
                    st.session_state.pontuacao += 1

        # Botão final
        if len(st.session_state.respostas) == total:
            if st.button("Finalizar Exame"):
                codigo = gerar_codigo_unico()
                salvar_resultado(usuario, "Exame", tema, faixa, st.session_state.pontuacao, "00:05:00", codigo)
                caminho_pdf = gerar_pdf(usuario, faixa, st.session_state.pontuacao, total, codigo, professor)

                with open(caminho_pdf, "rb") as file:
                    st.download_button(
                        label="📄 Baixar Relatório PDF",
                        data=file,
                        file_name=os.path.basename(caminho_pdf),
                        mime="application/pdf"
                    )

                st.success(f"✅ {usuario}, você fez {st.session_state.pontuacao}/{total} pontos.")
                st.info(f"Resultado salvo para a faixa {faixa}. Código: {codigo}")

                # Reset do quiz
                st.session_state.quiz_iniciado = False
                st.session_state.respostas = {}
                st.session_state.pontuacao = 0
