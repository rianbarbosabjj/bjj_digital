import streamlit as st
from core.db import consultar_um

def api_router(params):

    st.set_page_config(page_title="API BJJ Digital")

    if params.get("api") == ["certificado"]:

        # id do certificado
        if "id" not in params:
            st.json({"error": "Parâmetro id não informado"})
            return

        try:
            cert_id = int(params["id"][0])
        except:
            st.json({"error": "ID inválido"})
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

    st.json({"error": "API desconhecida"})
