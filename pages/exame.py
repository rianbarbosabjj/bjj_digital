import streamlit as st
import json
import random
from datetime import datetime
from core.db import consultar_um, consultar_todos, executar, executar_retorna_id
from core.certificado import gerar_certificado_pdf


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

    questoes = []
    for qid in questoes_ids:
        q = consultar_um("SELECT * FROM questoes WHERE id=?", (qid,))
        if q:
            questoes.append(q)

    if not questoes:
        st.error("Erro ao carregar questões.")
        return

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
        correta = q["resposta"]
        opcoes = json.loads(q["opcoes"])
        correta_texto = next((x for x in opcoes if x.startswith(correta)), None)

        if respostas[q["id"]] == correta_texto:
            acertos += 1

    percentual = round((acertos / total) * 100, 2)
    aprovado = 1 if percentual >= 70 else 0

    # Registrar resultado do exame
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

    st.markdown("## 📊 Resultado do Exame")

    st.info(f"Questões respondidas: **{total}**")
    st.info(f"Acertos: **{acertos}**")
    st.info(f"Percentual: **{percentual}%**")

    # ============================================================
    # APROVAÇÃO
    # ============================================================

    if aprovado:
        st.success("🎉 Parabéns! Você foi **APROVADA** no exame!")

        # Registrar certificado
        cert_id = executar_retorna_id("""
            INSERT INTO certificados (usuario_id, exame_config_id, data_emissao)
            VALUES (?, ?, ?)
        """, (
            usuario["id"],
            exame_config["id"],
            datetime.now().strftime("%d/%m/%Y %H:%M")
        ))

        # Criar código BJJDIGITAL-YYYY-XXXX
        ano_atual = datetime.now().year
        codigo_formatado = f"BJJDIGITAL-{ano_atual}-{str(cert_id).zfill(4)}"

        # Atualizar certificado com o código final
        executar("""
            UPDATE certificados
            SET codigo=?
            WHERE id=?
        """, (codigo_formatado, cert_id))

        # Gerar PDF com o código
        pdf_path, codigo_cert = gerar_certificado_pdf(
            cert_id=cert_id,
            nome_aluno=usuario["nome"],
            faixa=exame_config["faixa"],
            professor="Professor Responsável",
            data_emissao=datetime.now().strftime("%d/%m/%Y")
        )

        st.success("Seu certificado está pronto! 🎖️")

        # Botão para baixar imediatamente
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 Baixar Certificado Agora",
                data=f,
                file_name=f"{codigo_cert}.pdf",
                mime="application/pdf"
            )

        # Remover PDF temporário
        import os
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        st.info("Você também pode acessar esse certificado em **Meus Certificados**.")

    else:
        st.error("❌ Você foi **REPROVADA**. Continue treinando e tente novamente.")

