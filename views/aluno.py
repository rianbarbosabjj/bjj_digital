import streamlit as st
import time
import random
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components 
from database import get_db
from firebase_admin import firestore 

from utils import (
    registrar_inicio_exame, registrar_fim_exame, bloquear_por_abandono,
    verificar_elegibilidade_exame, carregar_todas_questoes,
    gerar_codigo_verificacao, gerar_pdf, normalizar_link_video 
)

# ==============================================================================
# 1. ÁREA DE CURSOS DO ALUNO
# ==============================================================================
def area_cursos_aluno():
    st.markdown("<h1 style='color:#32CD32;'>🎓 Meus Cursos e Treinamentos</h1>", unsafe_allow_html=True)
    db = get_db()
    user = st.session_state.usuario
    user_id = user['id']
    user_equipe = user.get('equipe_id') 

    tab_meus, tab_catalogo = st.tabs(["📚 Meus Cursos (Inscrito)", "🔍 Catálogo de Cursos"])

    # --- ABA 1: MEUS CURSOS ---
    with tab_meus:
        matriculas_ref = db.collection('usuarios').document(user_id).collection('matriculas').stream()
        matriculas = [m.to_dict() | {'id': m.id} for m in matriculas_ref]

        if not matriculas:
            st.info("Você ainda não está matriculado em nenhum curso. Vá na aba 'Catálogo' para se inscrever.")
        else:
            for mat in matriculas:
                curso_doc = db.collection('cursos').document(mat['curso_id']).get()
                if not curso_doc.exists: continue
                curso = curso_doc.to_dict()
                
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    if curso.get('url_capa'): c1.image(curso.get('url_capa'), use_container_width=True)
                    else: c1.markdown("🖼️")
                    
                    with c2:
                        st.subheader(curso.get('titulo'))
                        st.caption(f"Categoria: {curso.get('categoria')} | Progresso: {mat.get('progresso', 0)}%")
                        st.progress(mat.get('progresso', 0) / 100)
                        if st.button(f"▶️ Acessar Aula", key=f"go_c_{mat['id']}"):
                            st.session_state.curso_ativo_id = mat['curso_id']
                            st.toast("Carregando player...")

    # --- ABA 2: CATÁLOGO ---
    with tab_catalogo:
        st.subheader("Cursos Disponíveis")
        cursos_ref = db.collection('cursos').where('ativo', '==', True).stream()
        ids_matriculados = [m['curso_id'] for m in matriculas]
        
        cursos_visiveis = []
        for doc in cursos_ref:
            c = doc.to_dict(); c['id'] = doc.id
            visibilidade = c.get('visibilidade', 'todos')
            equipe_curso = c.get('equipe_id')
            
            mostrar = False
            if visibilidade == 'todos': mostrar = True
            elif visibilidade == 'equipe':
                if user_equipe and equipe_curso and (str(user_equipe) == str(equipe_curso)): mostrar = True
            
            if mostrar: cursos_visiveis.append(c)

        if not cursos_visiveis: st.info("Nenhum curso disponível.")
        else:
            cols = st.columns(3)
            for i, curso in enumerate(cursos_visiveis):
                with cols[i % 3]:
                    with st.container(border=True):
                        if curso.get('url_capa'): st.image(curso.get('url_capa'), use_container_width=True)
                        st.markdown(f"**{curso.get('titulo')}**")
                        
                        if curso['id'] in ids_matriculados:
                            st.success("✅ Já Matriculado")
                        else:
                            with st.expander("Detalhes"):
                                st.write(curso.get('descricao'))
                                if st.button("Inscrever-se", key=f"sub_{curso['id']}", type="primary"):
                                    try:
                                        # 1. Salva no Perfil do Aluno
                                        db.collection('usuarios').document(user_id).collection('matriculas').add({
                                            "curso_id": curso['id'], "titulo_curso": curso['titulo'],
                                            "data_inscricao": firestore.SERVER_TIMESTAMP, "progresso": 0
                                        })
                                        # 2. Salva na Lista do Curso (PARA O PROFESSOR VER)
                                        db.collection('cursos').document(curso['id']).collection('inscritos').document(user_id).set({
                                            "nome": user['nome'], "email": user['email'],
                                            "data": firestore.SERVER_TIMESTAMP
                                        })
                                        st.toast("Inscrição realizada!"); time.sleep(1); st.rerun()
                                    except Exception as e: st.error(f"Erro: {e}")

# =========================================
# FUNÇÕES DE EXAME E OUTRAS (MANTIDAS)
# =========================================
def carregar_exame_especifico(faixa_alvo):
    db = get_db()
    questoes_finais = []; tempo = 45; nota = 70; qtd_alvo = 10
    try:
        configs = db.collection('config_exames').where('faixa', '==', faixa_alvo).limit(1).stream()
        config_doc = None
        for doc in configs: config_doc = doc.to_dict(); break
        
        if config_doc:
            tempo = int(config_doc.get('tempo_limite', 45))
            nota = int(config_doc.get('aprovacao_minima', 70))
            if config_doc.get('questoes_ids'):
                ids = config_doc['questoes_ids']
                for q_id in ids:
                    q_snap = db.collection('questoes').document(q_id).get()
                    if q_snap.exists:
                        d = q_snap.to_dict()
                        if 'alternativas' not in d and 'opcoes' in d:
                            ops = d['opcoes']
                            d['alternativas'] = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                        questoes_finais.append(d)
                random.shuffle(questoes_finais)
                return questoes_finais, tempo, nota
            qtd_alvo = int(config_doc.get('qtd_questoes', 10))
    except: pass

    if not questoes_finais:
        try:
            q_ref = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
            pool = []
            for doc in q_ref:
                d = doc.to_dict()
                if 'alternativas' not in d and 'opcoes' in d:
                    ops = d['opcoes']; d['alternativas'] = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                pool.append(d)
            if pool:
                questoes_finais = random.sample(pool, qtd_alvo) if len(pool) > qtd_alvo else pool
        except: pass
    return questoes_finais, tempo, nota

def modo_rola(usuario): st.markdown("## 🥋 Modo Rola"); st.info("Em breve.")

def meus_certificados(usuario):
    if st.button("🏠 Voltar"): st.session_state.menu_selection = "Início"; st.rerun()
    st.markdown("## 🏅 Meus Certificados")
    try:
        db = get_db()
        docs = db.collection('resultados').where('usuario', '==', usuario['nome']).where('aprovado', '==', True).stream()
        lista = []
        for doc in docs:
            cert = doc.to_dict()
            dr = cert.get('data')
            do = datetime.min
            if hasattr(dr, 'to_datetime'): do = dr.to_datetime()
            elif isinstance(dr, datetime): do = dr
            elif isinstance(dr, str):
                try: do = datetime.fromisoformat(dr.replace('Z', ''))
                except: pass
            if do.tzinfo: do = do.replace(tzinfo=None)
            cert['data_ordenacao'] = do; lista.append(cert)
        lista.sort(key=lambda x: x.get('data_ordenacao'), reverse=True)
        
        if not lista: st.info("Nenhum certificado.")
        for i, c in enumerate(lista):
            with st.container(border=True):
                c1, c2 = st.columns([3,1])
                dt = c['data_ordenacao'].strftime('%d/%m/%Y') if c['data_ordenacao'] != datetime.min else "-"
                c1.markdown(f"**{c.get('faixa')}** | {dt} | Nota: {c.get('pontuacao',0):.0f}%")
                def gen(ct, un):
                    b, n = gerar_pdf(un, ct.get('faixa'), ct.get('pontuacao',0), ct.get('total',10), ct.get('codigo_verificacao'))
                    return (b, n) if b else (b"", "erro.pdf")
                c2.download_button("📄 PDF", data=lambda: gen(c, usuario['nome'])[0], file_name=lambda: gen(c, usuario['nome'])[1], mime="application/pdf", key=f"d_{i}")
    except Exception as e: st.error(f"Erro: {e}")

def ranking(): st.markdown("## 🏆 Ranking"); st.info("Em breve.")

def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0]}")
    if "exame_iniciado" not in st.session_state: st.session_state.exame_iniciado = False
    if "resultado_prova" not in st.session_state: st.session_state.resultado_prova = None
    db = get_db(); doc = db.collection('usuarios').document(usuario['id']).get()
    if not doc.exists: st.error("Erro perfil."); return
    dados = doc.to_dict()

    if st.session_state.resultado_prova:
        res = st.session_state.resultado_prova
        st.balloons()
        st.success(f"Aprovado! Nota: {res['nota']:.0f}%")
        pb, pn = gerar_pdf(usuario['nome'], res['faixa'], res['nota'], res['total'], res['codigo'])
        if pb: st.download_button("📥 Baixar Certificado", data=pb, file_name=pn, mime="application/pdf", type="primary")
        if st.button("Voltar"): st.session_state.resultado_prova = None; st.rerun()
        return

    if dados.get("status_exame") == "em_andamento" and not st.session_state.exame_iniciado:
        st.error("🚨 Exame bloqueado por reinício de página."); return

    if not dados.get('exame_habilitado'):
        st.warning("🔒 Exame não autorizado."); return

    qs, tempo_limite, min_aprovacao = carregar_exame_especifico(dados.get('faixa_exame'))
    
    if not st.session_state.exame_iniciado:
        st.markdown(f"**Prova: {dados.get('faixa_exame')}** | {len(qs)} questões | {tempo_limite} min | Min: {min_aprovacao}%")
        if st.button("✅ INICIAR EXAME", type="primary"):
            registrar_inicio_exame(usuario['id'])
            st.session_state.exame_iniciado = True
            st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
            st.session_state.questoes_prova = qs
            st.session_state.params_prova = {"min": min_aprovacao}
            st.rerun()
    else:
        qs = st.session_state.get('questoes_prova', [])
        restante = int(st.session_state.fim_prova_ts - time.time())
        if restante <= 0:
            st.error("Tempo Esgotado!"); registrar_fim_exame(usuario['id'], False); st.session_state.exame_iniciado = False; time.sleep(2); st.rerun()
        
        components.html(f"<div style='color:red;font-size:24px;font-weight:bold;text-align:center'>Tempo: {restante//60}:{restante%60:02d}</div>", height=50)
        
        with st.form("prova"):
            resps = {}
            for i, q in enumerate(qs):
                st.markdown(f"**{i+1}. {q.get('pergunta')}**")
                if q.get('url_imagem'): st.image(q.get('url_imagem'), width=200)
                opts = q.get('opcoes', [])
                if 'alternativas' in q: opts = [q['alternativas'][k] for k in sorted(q['alternativas'].keys())]
                resps[i] = st.radio("R:", opts, key=f"q{i}")
                st.divider()
            
            if st.form_submit_button("Finalizar"):
                acertos = 0
                for i, q in enumerate(qs):
                    certa = q.get('resposta_correta', 'A')
                    txt_certo = q.get('alternativas', {}).get(certa, "").lower().strip()
                    if str(resps.get(i,"")).lower().strip() == txt_certo: acertos += 1
                
                nota = (acertos/len(qs))*100
                aprovado = nota >= st.session_state.params_prova['min']
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                
                if aprovado:
                    cod = gerar_codigo_verificacao()
                    st.session_state.resultado_prova = {"nota": nota, "aprovado": True, "faixa": dados.get('faixa_exame'), "total": len(qs), "codigo": cod}
                    db.collection('resultados').add({"usuario": usuario['nome'], "faixa": dados.get('faixa_exame'), "pontuacao": nota, "aprovado": True, "codigo_verificacao": cod, "data": firestore.SERVER_TIMESTAMP})
                else:
                    st.error(f"Reprovado. Nota: {nota:.0f}%"); time.sleep(2)
                st.rerun()

# ==============================================================================
# 5. APP PRINCIPAL DO ALUNO
# ==============================================================================
def app_aluno():
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
        st.title("Área do Aluno")
        menu = st.radio("Navegação", ["Dashboard", "Cursos", "Modo Rola", "Exame de Faixa", "Meus Certificados", "Ranking", "Sair"])
        st.markdown("---")
        user = st.session_state.usuario
        st.caption(f"Aluno: {user.get('nome','').split()[0]}")

    if menu == "Dashboard": st.title("📊 Dashboard"); st.info("Bem-vindo!")
    elif menu == "Cursos": area_cursos_aluno()
    elif menu == "Modo Rola": modo_rola(user)
    elif menu == "Exame de Faixa": exame_de_faixa(user)
    elif menu == "Meus Certificados": meus_certificados(user)
    elif menu == "Ranking": ranking()
    elif menu == "Sair": st.session_state.logado = False; st.rerun()

if __name__ == "__main__":
    app_aluno()
