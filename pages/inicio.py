import streamlit as st

def tela_inicio(usuario):
    st.title("🏆 BJJ Digital — Início")

    st.markdown(f"""
    ### Bem-vinda(o), **{usuario['nome'].title()}**!

    Aqui você encontra tudo o que precisa para acompanhar sua evolução no Jiu-Jitsu, 
    acessar exames, ver rankings e participar do modo rola.
    """)

