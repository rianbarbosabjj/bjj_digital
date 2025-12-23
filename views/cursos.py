#/views/cursos.py

import streamlit as st

def pagina_cursos(usuario):
    tipo = usuario.get("tipo")

    if tipo in ["admin", "professor"]:
        from views.cursos_professor import pagina_cursos_professor
        pagina_cursos_professor(usuario)
    else:
        # --- MUDANÇA AQUI: Apontamos para o arquivo novo ---
        from views.painel_aluno import render_painel_aluno
        render_painel_aluno(usuario)
