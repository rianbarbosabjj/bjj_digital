import streamlit as st

def pagina_cursos(usuario):
    tipo = usuario.get("tipo")

    if tipo in ["admin", "professor"]:
        from views.cursos_professor import pagina_cursos_professor
        pagina_cursos_professor(usuario)
    else:
        from views.cursos_aluno import pagina_cursos_aluno
        pagina_cursos_aluno(usuario)
