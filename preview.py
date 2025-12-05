import streamlit as st
import base64
from utils import gerar_pdf

st.set_page_config(layout="wide", page_title="Laboratório de Certificado")

st.title("🧪 Laboratório de Certificado")

# 1. Controles para você testar layouts diferentes
c1, c2, c3 = st.columns(3)
nome_teste = c1.text_input("Nome do Aluno", "FULANO DE TAL DA SILVA")
faixa_teste = c2.selectbox("Faixa", ["Branca", "Azul", "Roxa", "Marrom", "Preta"])
nota_teste = c3.slider("Nota", 0, 100, 95)

# 2. Gera o PDF com os dados falsos
if st.button("🔄 Atualizar Preview"):
    # Gera o PDF usando sua função real
    pdf_bytes, nome_arq = gerar_pdf(
        usuario_nome=nome_teste,
        faixa=faixa_teste,
        pontuacao=nota_teste,
        total=10,
        codigo="BJJDIGITAL-TESTE-0001"
    )

    if pdf_bytes:
        # 3. Exibe o PDF na tela (Embed)
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.error("Erro ao gerar PDF")
