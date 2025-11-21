import streamlit as st
from core.db import consultar_um


def api_router():

    st.set_page_config(page_title="API BJJ Digital")

    # Pega a URL completa
    full_url = st.experimental_get_query_params()
    url_parts = st.experimental_get_url().split("/")

    # Se não tiver "/api/", não é rota válida
    if "api" not in url_parts:
        st.json({"error": "Use /api/... para acessar a API"})
        return

    # -------------------------------------------------------
    # /api/certificado/<id>
    # -------------------------------------------------------
    if "certificado" in url_parts:
        try:
            cert_id = int(url_parts[-1])
        except:
            st.json({"error": "cert_id inválido"})
            return

        cert = consultar_um("""
            SELECT c.id, c.codigo, c.data_emissao,
                   u.nome AS aluno,
                   ec.faixa AS faixa
            FROM certificados c
            JOIN usuarios u ON u.id = c.usuario_id
            JOIN exames_config ec ON ec.id = c.exame_config_id
            WHERE c.id=?
        """, (cert_id,))

        if not cert:
            st.json({"error": "Certificado não encontrado"})
            return

        st.json({
            "id": cert["id"],
            "codigo": cert["codigo"],
            "nome": cert["aluno"],
            "faixa": cert["faixa"],
            "data_emissao": cert["data_emissao"]
        })
        return

    # Se nenhuma rota for válida:
    st.json({"error": "Rota inválida"})
