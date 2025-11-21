import streamlit as st
import pandas as pd
from core.db import consultar_todos, buscar_usuario_por_id, salvar_certificado
from core.pdf import gerar_certificado
from core.utils import gerar_codigo_unico


def painel_professor():
    st.title("👩‍🏫 Painel do Professor")

    # ==============================
    # LISTA DE ALUNOS
    # ==============================
    st.subheader("Lista de alunos")

    alunos = consultar_todos("""
        SELECT id, nome, faixa
        FROM usuarios
        WHERE tipo = 'aluno'
        ORDER BY nome
    """)

    if not alunos:
        st.info("Nenhum aluno cadastrado ainda.")
        return

    df = pd.DataFrame(alunos)
    df.columns = ["ID", "Nome", "Faixa"]

    st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # ==============================
    # GERAR CERTIFICADO MANUAL
    # ==============================
    st.subheader("Gerar certificado manualmente")

    lista_nomes = [f"{a['id']} - {a['nome']}" for a in alunos]
    sel = st.selectbox("Selecione o aluno", lista_nomes)

    faixa = st.selectbox(
        "Selecione a faixa para o certificado",
        ["branca", "cinza", "amarela", "laranja", "verde", "azul", "roxa", "marrom", "preta"]
    )

    if st.button("Gerar Certificado", use_container_width=True):

        id_user = int(sel.split(" - ")[0])
        usuario = buscar_usuario_por_id(id_user)

        codigo = gerar_codigo_unico()
        caminho_pdf = gerar_certificado(
            nome=usuario["nome"],
            faixa=faixa,
            codigo_unico=codigo,
            selo_path="assets/selo_dourado.png"
        )

        salvar_certificado(
            usuario_id=id_user,
            faixa=faixa,
            codigo_qr=codigo,
            caminho_pdf=caminho_pdf
        )

        st.success("Certificado gerado com sucesso!")
        st.markdown(f"📄 **Download:** `{caminho_pdf}`")
        st.download_button(
            label="Baixar PDF",
            data=open(caminho_pdf, "rb").read(),
            file_name=f"certificado_{codigo}.pdf"
        )

    st.markdown("---")

    # ==============================
    # ÚLTIMOS EXAMES
    # ==============================
    st.subheader("Últimos exames aplicados")

    exames = consultar_todos("""
        SELECT u.nome, e.faixa, e.nota, e.aprovado, e.data
        FROM exames e
        JOIN usuarios u ON u.id = e.usuario_id
        ORDER BY e.data DESC
        LIMIT 20
    """)

    if exames:
        df2 = pd.DataFrame(exames)
        df2.columns = ["Aluno", "Faixa", "Nota", "Aprovado", "Data"]
        st.dataframe(df2, use_container_width=True)
    else:
        st.info("Nenhum exame registrado ainda.")

