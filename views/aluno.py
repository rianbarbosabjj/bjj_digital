import streamlit as st
import time
import random
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components 
from database import get_db
from firebase_admin import firestore # Mantemos a importação

# --- IMPORTAÇÃO DIRETA (PARA DIAGNÓSTICO DE ERROS) ---
from utils import (
    registrar_inicio_exame, 
    registrar_fim_exame, 
    bloquear_por_abandono,
    verificar_elegibilidade_exame,
    carregar_todas_questoes,
    gerar_codigo_verificacao,
    gerar_pdf,
    normalizar_link_video 
)

# ==============================================================================
# 1. ÁREA DE CURSOS (NOVA FUNCIONALIDADE INSERIDA)
# ==============================================================================
def area_cursos_aluno():
    st.markdown("<h1 style='color:#32CD32;'>🎓 Meus Cursos e Treinamentos</h1>", unsafe_allow_html=True)
    
    db = get_db()
    user = st.session_state.usuario
    user_id = user['id']
    user_equipe = user.get('equipe_id') # ID da equipe do aluno

    tab_meus, tab_catalogo = st.tabs(["📚 Meus Cursos (Inscrito)", "🔍 Catálogo de Cursos"])

    # --- ABA 1: MEUS CURSOS ---
    with tab_meus:
        # Busca matrículas do aluno
        matriculas_ref = db.collection('usuarios').document(user_id).collection('matriculas').stream()
        matriculas = [m.to_dict() | {'id': m.id} for m in matriculas_ref]

        if not matriculas:
            st.info("Você ainda não está matriculado em nenhum curso. Vá na aba 'Catálogo' para se inscrever.")
        else:
            for mat in matriculas:
                # Busca dados atualizados do curso
                curso_doc = db.collection('cursos').document(mat['curso_id']).get()
                if not curso_doc.exists:
                    st.warning(f"O curso ID {mat['curso_id']} não existe mais.")
                    continue
                
                curso = curso_doc.to_dict()
                
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    if curso.get('url_capa'):
                        c1.image(curso.get('url_capa'), use_container_width=True)
                    else:
                        c1.markdown("🖼️")
                    
                    with c2:
                        st.subheader(curso.get('titulo'))
                        st.caption(f"Categoria: {curso.get('categoria')} | Progresso: {mat.get('progresso', 0)}%")
                        st.progress(mat.get('progresso', 0) / 100)
                        
                        if st.button(f"▶️ Acessar Aula", key=f"go_c_{mat['id']}"):
                            # Aqui futuramente entra o player de aula
                            st.session_state.curso_ativo_id = mat['curso_id']
                            st.toast("Acessando ambiente de aula...")
                            # st.rerun() 

    # --- ABA 2: CATÁLOGO ---
    with tab_catalogo:
        st.subheader("Cursos Disponíveis")
        
        # Busca cursos ativos
        cursos_ref = db.collection('cursos').where('ativo', '==', True).stream()
        
        # Lista de IDs já matriculados
        ids_matriculados = [m['curso_id'] for m in matriculas]
        
        cursos_visiveis = []

        for doc in cursos_ref:
            c = doc.to_dict()
            c['id'] = doc.id
            
            # --- FILTRO DE VISIBILIDADE ---
            visibilidade = c.get('visibilidade', 'todos')
            equipe_curso = c.get('equipe_id')
            
            mostrar = False
            
            # Regra 1: Público
            if visibilidade == 'todos':
                mostrar = True
            
            # Regra 2: Equipe (Aluno deve ser da mesma equipe do criador)
            elif visibilidade == 'equipe':
                # Compara como string para garantir
                if user_equipe and equipe_curso and (str(user_equipe) == str(equipe_curso)):
                    mostrar = True
            
            if mostrar:
                cursos_visiveis.append(c)

        if not cursos_visiveis:
            st.info("Nenhum curso disponível para o seu perfil no momento.")
        else:
            cols = st.columns(3)
            for i, curso in enumerate(cursos_visiveis):
                with cols[i % 3]:
                    with st.container(border=True):
                        if curso.get('url_capa'):
                            st.image(curso.get('url_capa'), use_container_width=True)
                        
                        st.markdown(f"**{curso.get('titulo')}**")
                        st.caption(f"{curso.get('categoria')}")
                        
                        # Verifica matrícula
                        if curso['id'] in ids_matriculados:
                            st.success("✅ Já Matriculado")
                        else:
                            with st.expander("Ver Detalhes"):
                                st.write(curso.get('descricao'))
                                st.caption(f"Duração: {curso.get('duracao_estimada')}")
                                
                                if st.button("Inscrever-se Grátis", key=f"sub_{curso['id']}", type="primary"):
                                    try:
                                        dados_matricula = {
                                            "curso_id": curso['id'],
                                            "titulo_curso": curso['titulo'],
                                            "data_inscricao": firestore.SERVER_TIMESTAMP,
                                            "progresso": 0,
                                            "status": "ativo",
                                            "ultimo_acesso": firestore.SERVER_TIMESTAMP
                                        }
                                        db.collection('usuarios').document(user_id).collection('matriculas').add(dados_matricula)
                                        st.toast(f"Inscrito em {curso.get('titulo')}")
                                        time.sleep(1.5); st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro: {e}")

# =========================================
# CARREGADOR DE EXAME (Inalterado)
# =========================================
def carregar_exame_especifico(faixa_alvo):
    db = get_db()
    questoes_finais = []
    tempo = 45; nota = 70; qtd_alvo = 10
    
    try:
        configs = db.collection('config_exames').where('faixa', '==', faixa_alvo).limit(1).stream()
        config_doc = None
        for doc in configs: 
            config_doc = doc.to_dict()
            break
        
        if config_doc:
            tempo = int(config_doc.get('tempo_limite', 45))
            nota = int(config_doc.get('aprovacao_minima', 70))
            
            # MODO MANUAL
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

    # FALLBACK
    if not questoes_finais:
        try:
            q_ref = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
            pool = []
            for doc in q_ref:
                d = doc.to_dict()
                if 'alternativas' not in d and 'opcoes' in d:
                    ops = d['opcoes']
                    d['alternativas'] = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                pool.append(d)
            if pool:
                if len(pool) > qtd_alvo:
                    questoes_finais = random.sample(pool, qtd_alvo)
                else:
                    questoes_finais = pool
        except: pass

    return questoes_finais, tempo, nota

# =========================================
# TELAS SECUNDÁRIAS (Inalteradas)
# =========================================
def modo_rola(usuario):
    st.markdown("## 🥋 Modo Rola"); st.info("Em breve.")

def meus_certificados(usuario):
    if st.button("🏠 Voltar ao Início", key="btn_back_cert"):
        st.session_state.menu_selection = "Início"
        st.rerun()
        
    st.markdown("## 🏅 Meus Certificados")
    
    try:
        db = get_db()
        docs = db.collection('resultados').where('usuario', '==', usuario['nome']).where('aprovado', '==', True).stream()
        
        lista_certificados = []
        
        # --- INÍCIO DA CORREÇÃO DE DATAS E ALINHAMENTO (MANTIDO) ---
        for doc in docs:
            cert = doc.to_dict()
            
            data_raw = cert.get('data')
            data_obj = datetime.min 

            # 1. Se for Timestamp do Google
            if hasattr(data_raw, 'to_datetime'):
                data_obj = data_raw.to_datetime()
            
            # 2. Se JÁ for um datetime do Python
            elif isinstance(data_raw, datetime):
                data_obj = data_raw
            
            # 3. Se for texto (string)
            elif isinstance(data_raw, str):
                try: data_obj = datetime.fromisoformat(data_raw.replace('Z', ''))
                except: pass
            
            # Remove fuso horário
            if data_obj.tzinfo is not None:
                data_obj = data_obj.replace(tzinfo=None)
            
            cert['data_ordenacao'] = data_obj
            lista_certificados.append(cert)
        # --- FIM DA CORREÇÃO ---
            
        lista_certificados.sort(key=lambda x: x.get('data_ordenacao', datetime.min), reverse=True)
        
        if not lista_certificados:
            st.info("Nenhum certificado disponível.")
            return

        for i, cert in enumerate(lista_certificados):
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**Faixa {cert.get('faixa')}**")
                
                d_str = "-"
                data_obj_exibicao = cert.get('data_ordenacao', datetime.min)
                if data_obj_exibicao != datetime.min:
                    try: d_str = data_obj_exibicao.strftime('%d/%m/%Y')
                    except: d_str = str(data_obj_exibicao)[:10]

                c1.caption(f"Data: {d_str} | Nota: {cert.get('pontuacao', 0):.0f}% | Ref: {cert.get('codigo_verificacao')}")
                
                def generate_certificate(cert, user_name):
                    pdf_bytes, pdf_name = gerar_pdf(
                        user_name, cert.get('faixa'), 
                        cert.get('pontuacao', 0), cert.get('total', 10), 
                        cert.get('codigo_verificacao')
                    )
                    if pdf_bytes:
                        return pdf_bytes, pdf_name
                    return b"", f"Erro_ao_baixar_{cert.get('codigo_verificacao')}.pdf"

                c2.download_button(
                    label="📄 Baixar PDF",
                    data=lambda: generate_certificate(cert, usuario['nome'])[0],
                    file_name=lambda: generate_certificate(cert, usuario['nome'])[1],
                    mime="application/pdf", 
                    key=f"d_{i}",
                    on_click=lambda: st.toast("Gerando certificado...")
                )

    except Exception as e: 
        st.error(f"Erro ao carregar lista de certificados: {e}")

def ranking(): st.markdown("## 🏆 Ranking"); st.info("Em breve.")

# =========================================
# EXAME PRINCIPAL (Inalterado)
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    if "exame_iniciado" not in st.session_state: st.session_state.exame_iniciado = False
    if "resultado_prova" not in st.session_state: st.session_state.resultado_prova = None

    db = get_db()
    doc_ref = db.collection('usuarios').document(usuario['id'])
    doc = doc_ref.get()
    if not doc.exists: st.error("Erro perfil."); return
    dados = doc.to_dict()
    
    # === TELA DE RESULTADO ===
    if st.session_state.resultado_prova:
        res = st.session_state.resultado_prova
        st.balloons()
        
        with st.container(border=True):
            st.success(f"Parabéns você foi aprovado(a)! Sua nota foi {res['nota']:.0f}%.")
            
            try:
                with st.spinner("Preparando seu certificado oficial..."):
                    p_b, p_n = gerar_pdf(usuario['nome'], res['faixa'], res['nota'], res['total'], res['codigo'])
                
                if p_b: 
                    st.download_button(
                        label="📥 Baixar Certificado", 
                        data=p_b, 
                        file_name=p_n, 
                        mime="application/pdf", 
                        key="dl_res", 
                        type="primary", 
                        use_container_width=True
                    )
                else:
                    st.error(f"⚠️ {p_n}")
                    st.caption("Tente novamente na aba 'Meus Certificados'.")
            except Exception as e: 
                st.error(f"Erro inesperado: {e}")
            
        if st.button("Voltar ao Início"):
            st.session_state.resultado_prova = None
            st.rerun()
        return

    # CHECAGEM DE ABANDONO
    if dados.get("status_exame") == "em_andamento" and not st.session_state.exame_iniciado:
        is_timeout = False
        try:
            start_str = dados.get("inicio_exame_temp")
            if start_str:
                if isinstance(start_str, str):
                    start_dt = datetime.fromisoformat(start_str.replace('Z', ''))
                else:
                    start_dt = start_str
                
                _, t_lim, _ = carregar_exame_especifico(dados.get('faixa_exame'))
                limit_dt = start_dt + timedelta(minutes=t_lim)
                if datetime.utcnow() > limit_dt.replace(tzinfo=None): is_timeout = True
        except: pass

        if is_timeout:
            registrar_fim_exame(usuario['id'], False)
            st.error("⌛ Tempo ESGOTADO!")
            return
        else:
            bloquear_por_abandono(usuario['id'])
            st.error("🚨 BLOQUEADO! Página recarregada ou saída detectada.")
            st.caption("Por segurança, o exame foi bloqueado. Contate seu professor.")
            return

    if not dados.get('exame_habilitado'):
        status_atual = dados.get('status_exame', 'pendente')
        if status_atual == 'aprovado':
             st.success("✅ Você já foi aprovado neste exame!")
             st.info("Baixe seu certificado na aba 'Meus Certificados'.")
        elif status_atual == 'bloqueado':
             st.error("🔒 Exame Bloqueado.")
        else:
             st.warning("🔒 Exame não autorizado.")
        return

    elegivel, motivo = verificar_elegibilidade_exame(dados)
    if not elegivel: st.error(f"🚫 {motivo}"); return

    qs, tempo_limite, min_aprovacao = carregar_exame_especifico(dados.get('faixa_exame'))
    qtd = len(qs)

    # === TELA DE INÍCIO ===
    if not st.session_state.exame_iniciado:
        st.markdown(f"### 📋 Exame de Faixa **{dados.get('faixa_exame')}**")
        
        with st.container(border=True):
            st.markdown("#### 📜 Instruções para a realização do Exame")
            st.markdown("""
* Após clicar em **✅ Iniciar exame**, não será possível pausar ou interromper o cronômetro.
* Se o tempo acabar antes de você finalizar, você será considerado **reprovado**.
* **Não é permitido** consultar materiais externos de qualquer tipo.
* Em caso de **reprovação**, você poderá realizar o exame novamente somente após **3 dias**.
* Realize o exame em um local confortável e silencioso para garantir sua concentração.
* **Não atualize a página (F5)**, não feche o navegador e não troque de dispositivo durante a prova. Isso **bloqueia** o exame automaticamente.
* Utilize um dispositivo com bateria suficiente ou mantido na energia.
* O exame é **individual**. Qualquer tentativa de fraude resultará em reprovação imediata.
* Leia cada questão com atenção antes de responder.
* Se aprovado, você poderá baixar seu certificado na aba *Meus Certificados*.

**Boa prova!** 🥋
            """)
            
            st.markdown("---")
            
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; background-color: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px;">
                <div style="text-align: left;">
                    <span style="font-size: 0.9em; color: #aaa;">Questões</span><br>
                    <span style="font-size: 1.5em; font-weight: bold; color: white;">{qtd}</span>
                </div>
                <div style="text-align: center;">
                    <span style="font-size: 0.9em; color: #aaa;">Tempo</span><br>
                    <span style="font-size: 1.5em; font-weight: bold; color: white;">{tempo_limite} min</span>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 0.9em; color: #aaa;">Mínimo</span><br>
                    <span style="font-size: 1.5em; font-weight: bold; color: white;">{min_aprovacao}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.write("") 
        
        if qtd > 0:
            if st.button("✅ (estou ciente) INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
                st.session_state.questoes_prova = qs
                st.session_state.params_prova = {"tempo": tempo_limite, "min": min_aprovacao}
                st.rerun()
        else: st.warning("Sem questões disponíveis.")

    # === TELA DA PROVA ===
    else:
        qs = st.session_state.get('questoes_prova', [])
        restante = int(st.session_state.fim_prova_ts - time.time())
        
        if restante <= 0:
            st.error("⌛ Tempo ESGOTADO!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            time.sleep(2)
            st.rerun()

        cor = "#FFD770" if restante > 300 else "#FF4B4B"
        components.html(f"""
        <div style="border:2px solid {cor};border-radius:10px;padding:10px;text-align:center;background:rgba(0,0,0,0.3);font-family:sans-serif;color:white;">
            TEMPO RESTANTE<br>
            <span id="t" style="color:{cor};font-size:30px;font-weight:bold;">--:--</span>
        </div>
        <script>
            var t={restante};
            setInterval(function(){{
                var m=Math.floor(t/60),s=t%60;
                document.getElementById('t').innerHTML=m+":"+(s<10?"0"+s:s);
                if(t--<=0)window.parent.location.reload();
            }},1000);
        </script>
        """, height=100)

        with st.form("prova"):
            resps = {}
            for i, q in enumerate(qs):
                st.markdown(f"**{i+1}. {q.get('pergunta')}**")
                
                if q.get('url_imagem'):
                    st.image(q.get('url_imagem'), use_container_width=True)
                
                if q.get('url_video'):
                    vid = normalizar_link_video(q.get('url_video'))
                    try: st.video(vid)
                    except: st.markdown(f"[Ver Vídeo]({vid})")

                opts = []
                if 'alternativas' in q:
                    opts = [q['alternativas'].get(k) for k in ["A","B","C","D"]]
                elif 'opcoes' in q:
                    opts = q['opcoes']
                
                resps[i] = st.radio("R:", opts, key=f"q{i}", index=None, label_visibility="collapsed")
                st.markdown("---")
                
            if st.form_submit_button("Finalizar Exame", type="primary"):
                acertos = 0
                for i, q in enumerate(qs):
                    resp = str(resps.get(i) or "").strip().lower()
                    certa = q.get('resposta_correta', 'A')
                    txt_certo = q.get('alternativas', {}).get(certa, "").strip().lower()
                    
                    if resp == txt_certo:
                        acertos += 1

                nota = (acertos/len(qs))*100
                aprovado = nota >= st.session_state.params_prova['min']
                
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                
                cod = None
                if aprovado:
                    cod = gerar_codigo_verificacao()
                    st.session_state.resultado_prova = {
                        "nota": nota, "aprovado": True, 
                        "faixa": dados.get('faixa_exame'), "acertos": acertos, 
                        "total": len(qs), "codigo": cod
                    }
                    
                    try:
                        db.collection('resultados').add({
                            "usuario": usuario['nome'],
                            "faixa": dados.get('faixa_exame'),
                            "pontuacao": nota,
                            "acertos": acertos,
                            "total": len(qs),
                            "aprovado": aprovado,
                            "codigo_verificacao": cod,
                            "data": firestore.SERVER_TIMESTAMP
                        })
                    except: pass
                
                else:
                    st.error(f"Reprovado. Nota: {nota:.0f}%")
                    time.sleep(3)
                
                st.rerun()

# ==============================================================================
# 5. APP PRINCIPAL DO ALUNO (MENU DE NAVEGAÇÃO)
# ==============================================================================
def app_aluno():
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
        st.title("Área do Aluno")
        
        # Menu Principal
        menu = st.radio(
            "Navegação", 
            [
                "Dashboard", 
                "Cursos",  # <--- NOVA OPÇÃO
                "Modo Rola", 
                "Exame de Faixa", 
                "Meus Certificados", 
                "Ranking",
                "Sair"
            ]
        )
        st.markdown("---")
        
        # Info do Usuário
        user = st.session_state.usuario
        st.caption(f"Aluno: {user.get('nome','').split()[0]}")
        st.caption(f"Faixa: {user.get('faixa_atual', 'Branca')}")

    # Roteamento
    if menu == "Dashboard":
        st.title("📊 Dashboard")
        st.info("Bem-vindo à sua área de aluno!")
        # Aqui você pode adicionar cards de progresso, última aula vista, etc.
        
    elif menu == "Cursos":
        area_cursos_aluno() # <--- CHAMA A NOVA TELA DE CURSOS
        
    elif menu == "Modo Rola":
        modo_rola(user)
        
    elif menu == "Exame de Faixa":
        exame_de_faixa(user)
        
    elif menu == "Meus Certificados":
        meus_certificados(user)
        
    elif menu == "Ranking":
        ranking()
        
    elif menu == "Sair":
        st.session_state.logado = False
        st.rerun()

if __name__ == "__main__":
    app_aluno()
    
