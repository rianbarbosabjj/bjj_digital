import streamlit as st
import os
from core.db import consultar_todos, consultar_um
from core.certificado import gerar_certificado_pdf


# ============================================================
# PÁGINA — MEUS CERTIFICADOS
# ============================================================

def pagina_certificados(usuario):

    st.title("🎖️ Meus Certificados")

    # Buscar todos os certificados do aluno
    certificados = consultar_todos("""
        SELECT c.id, c.data_emissao, e.nome AS exame_nome, e.faixa
        FROM certificados c
        JOIN exames_config e ON e.id = c.exame_config_id
        WHERE c.usuario_id=?
        ORDER BY c.id DESC
    """, (usuario["id"],))

    if not certificados:
        st.info("Você ainda não possui certificados emitidos.")
        return

    st.markdown("Aqui estão todos os certificados que você já conquistou.")

    st.markdown("---")

    # Mostrar cada certificado em um card
    for cert in certificados:

        st.markdown(f"### 🥋 Faixa: **{cert['faixa']}**")
        st.markdown(f"📘 Exame: **{cert['exame_nome']}**")
        st.markdown(f"📅 Data: **{cert['data_emissao']}**")

        col1, col2 = st.columns([1, 1])

        # Botão de download do PDF
        with col1:
            if st.button(f"📄 Baixar PDF do Certificado #{cert['id']}", key=f"pdf_{cert['id']}"):
                
                # Pegar nome do aluno novamente (para gerar PDF)
                nome = usuario["nome"]

                pdf_path = gerar_certificado_pdf(
                    cert_id=cert["id"],
                    nome_aluno=nome,
                    faixa=cert["faixa"],
                    professor="Professor Responsável",
                    data_emissao=cert["data_emissao"]
                )

                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 Clique aqui para baixar",
                        data=f,
                        file_name=f"certificado_{cert['id']}.pdf",
                        mime="application/pdf"
                    )

                # Remover PDF temporário após gerar
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

        # Botão de validar (QR Code futuro)
        with col2:
            st.markdown(f"[🔍 Validar Certificado](https://seudominio.com/validar/{cert['id']})")

        st.markdown("---")
