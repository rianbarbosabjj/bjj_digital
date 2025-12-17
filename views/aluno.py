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
import utils as ce # Utils para funções de banco
import views.aulas as aulas_view # Importação para usar estilos ou lógica compartilhada

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
# TELAS SECUNDÁRIAS
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
        
        # --- INÍCIO DA CORREÇÃO DE DATAS E ALINHAMENTO ---
        for doc in docs:
            cert = doc.to_dict()
            
            data_raw = cert.get('data')
            data_obj = datetime.min 

            # 1. Se for Timestamp do Google (tem método .to_datetime)
            if hasattr(data_raw, 'to_datetime'):
                data_obj = data_raw.to_datetime()
            
            # 2. Se JÁ for um datetime do Python
            elif isinstance(data_raw, datetime):
                data_obj = data_raw
            
            # 3. Se for texto (string)
            elif isinstance(data_raw, str):
                try: data_obj = datetime.fromisoformat(data_raw.replace('Z', ''))
                except: pass
            
            # IMPORTANTE: Remove fuso horário para garantir que a ordenação funcione
            if data_obj.tzinfo is not None:
                data_obj = data_obj.replace(tzinfo=None)
            
            cert['data_ordenacao'] = data_obj
            lista_certificados.append(cert)
        # --- FIM DA CORREÇÃO ---
            
        # 2. Ordena a lista do mais recente para o mais antigo
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
                
                # --- FUNÇÃO DE GERAÇÃO ENCAPSULADA PARA O BOTÃO ---
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

#=============================================

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

    # CARREGAMENTO
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
            
            # PAINEL DE MÉTRICAS (VISUAL LIMPO)
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

        # Timer Visual
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
# NOVAS FUNCIONALIDADES (ABAS DE CURSOS)
# ==============================================================================

def assistir_curso_player(curso, usuario):
    """
    Player seguro para o aluno assistir às aulas sem permissão de edição.
    """
    st.subheader(f"📺 {curso.get('titulo', 'Curso')}")
    if st.button("⬅ Voltar ao Painel"):
        st.session_state['aluno_view'] = 'dashboard'
        st.rerun()
        
    st.markdown("---")
    
    try:
        modulos = ce.listar_modulos_e_aulas(curso['id']) or []
    except:
        modulos = []
        
    if not modulos:
        st.info("Este curso ainda não possui conteúdo liberado.")
        return

    # Barra de Progresso do Curso (Simulada ou Real)
    # Aqui você poderia calcular quantas aulas o aluno já viu
    # progresso_total = calcular_progresso(usuario['id'], curso['id']) 
    # st.progress(progresso_total, text=f"Seu Progresso: {int(progresso_total*100)}%")

    for i, mod in enumerate(modulos):
        mod_titulo = mod.get('titulo', f'Módulo {i+1}')
        aulas = mod.get('aulas', [])
        
        # Expander padrão (aberto se for o primeiro, fechado os outros)
        with st.expander(f"📂 {mod_titulo}", expanded=(i==0)):
            if mod.get('descricao'):
                st.caption(mod['descricao'])
                
            if not aulas:
                st.caption("Sem aulas disponíveis neste módulo.")
            else:
                for aula in aulas:
                    # Visualização da Aula (Card Simples)
                    tp = aula.get('tipo', 'texto')
                    icone = "🎥" if tp == 'video' else "🖼️" if tp == 'imagem' else "📝"
                    
                    with st.container(border=True):
                        st.markdown(f"**{icone} {aula.get('titulo')}**")
                        
                        # Conteúdo da Aula
                        conteudo = aula.get('conteudo', {})
                        
                        if tp == 'video':
                            url = conteudo.get('url') or conteudo.get('arquivo_video')
                            if url:
                                st.video(url)
                            else:
                                st.warning("Vídeo indisponível.")
                                
                        elif tp == 'imagem':
                            url = conteudo.get('url') or conteudo.get('arquivo_imagem')
                            if url:
                                st.image(url, use_container_width=True)
                                
                        elif tp == 'texto':
                            st.markdown(conteudo.get('texto', ''))
                            
                        # Material de Apoio
                        pdf_link = conteudo.get('material_apoio')
                        if pdf_link:
                            st.markdown(f"[📎 Baixar Material de Apoio]({pdf_link})")
                            
                        # Botão de Concluir Aula (Futuro)
                        # if st.button("Marcar como Concluída", key=f"conc_{aula['id']}"): ...

def meus_cursos_inscritos(usuario):
    """Lista os cursos que o aluno já está matriculado."""
    cursos = ce.listar_cursos_inscritos(usuario['id'])
    
    if not cursos:
        st.info("Você ainda não está inscrito em nenhum curso.")
        st.markdown("👉 Vá até a aba **Mural de Cursos** para encontrar novidades!")
        return

    for c in cursos:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {c.get('titulo')}")
                # Barra de progresso (buscando da inscrição)
                prog = c.get('progresso', 0)
                st.progress(prog / 100, text=f"Progresso: {prog}%")
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("▶ Acessar", key=f"play_{c['id']}", type="primary", use_container_width=True):
                    st.session_state['curso_ativo'] = c
                    st.session_state['aluno_view'] = 'assistir'
                    st.rerun()

def mural_cursos(usuario):
    """Loja de Cursos disponíveis para inscrição."""
    cursos_disp = ce.listar_cursos_disponiveis_para_aluno(usuario)
    
    if not cursos_disp:
        st.success("Tudo em dia! Você já possui todos os cursos disponíveis para sua equipe.")
        return

    for c in cursos_disp:
        with st.container(border=True):
            col_txt, col_meta, col_btn = st.columns([3, 1, 1])
            
            with col_txt:
                mod_badge = f"<span style='background:#333; color:#fff; padding:2px 6px; border-radius:4px; font-size:0.7em'>{c.get('modalidade','EAD')}</span>"
                st.markdown(f"#### {c.get('titulo')} {mod_badge}", unsafe_allow_html=True)
                st.caption(c.get('descricao', '')[:120] + "...")
                st.caption(f"👨‍🏫 Prof. {c.get('professor_nome', '-')}")
            
            with col_meta:
                preco = float(c.get('preco', 0))
                if preco > 0:
                    st.markdown(f"<h3 style='color:#FFD770'>R$ {preco:.2f}</h3>", unsafe_allow_html=True)
                else:
                    st.markdown("<h3 style='color:#4CAF50'>GRÁTIS</h3>", unsafe_allow_html=True)

            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                label_btn = "Comprar" if preco > 0 else "Matricular"
                tipo_btn = "secondary" if preco > 0 else "primary"
                
                if st.button(label_btn, key=f"ins_{c['id']}", type=tipo_btn, use_container_width=True):
                    if preco > 0:
                        st.toast("Módulo de pagamento em breve!", icon="💳")
                    else:
                        ce.inscrever_usuario_em_curso(usuario['id'], c['id'])
                        st.balloons()
                        st.success(f"Matrícula realizada em {c.get('titulo')}!")
                        time.sleep(2)
                        st.rerun()

# =========================================
# APP PRINCIPAL DO ALUNO (ORQUESTRADOR)
# =========================================
def app_aluno(usuario):
    if 'aluno_view' not in st.session_state:
        st.session_state['aluno_view'] = 'dashboard'
    if 'curso_ativo' not in st.session_state:
        st.session_state['curso_ativo'] = None

    # Roteamento: Player vs Dashboard
    if st.session_state['aluno_view'] == 'assistir':
        if st.session_state['curso_ativo']:
            assistir_curso_player(st.session_state['curso_ativo'], usuario)
        else:
            st.session_state['aluno_view'] = 'dashboard'
            st.rerun()
    else:
        # Dashboard Principal com Abas
        st.subheader(f"Painel do Aluno: {usuario['nome']}")
        
        tab_painel, tab_mural = st.tabs(["🥋 Painel & Meus Cursos", "🔍 Mural de Cursos"])
        
        with tab_painel:
            st.markdown("<br>", unsafe_allow_html=True)
            # Menu interno do painel
            menu_opcoes = ["Meus Cursos (Aulas)", "Exame de Faixa", "Meus Certificados", "Ranking"]
            escolha = st.radio("Navegação Rápida", menu_opcoes, horizontal=True, label_visibility="collapsed")
            st.markdown("---")
            
            if escolha == "Meus Cursos (Aulas)":
                meus_cursos_inscritos(usuario)
            elif escolha == "Exame de Faixa":
                exame_de_faixa(usuario)
            elif escolha == "Meus Certificados":
                meus_certificados(usuario)
            elif escolha == "Ranking":
                ranking()
                
        with tab_mural:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### 🚀 Novos Cursos Disponíveis")
            mural_cursos(usuario)
