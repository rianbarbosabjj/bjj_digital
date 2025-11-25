import streamlit as st
import random
import os
import json
import time
import uuid  # Import para gerar ID único do timer
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from database import get_db
from utils import gerar_codigo_verificacao, gerar_pdf
from firebase_admin import firestore

# =========================================
# MODO ROLA (Treino Livre)
# =========================================
def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)
    db = get_db()

    todas_questoes = []
    # Tenta carregar do Firestore
    try:
        docs_questoes = list(db.collection('questoes').stream())
        if docs_questoes:
            todas_questoes = [d.to_dict() for d in docs_questoes]
    except: pass
    
    # Fallback local
    if not todas_questoes and os.path.exists("questions"):
        for f in os.listdir("questions"):
            if f.endswith(".json"):
                try:
                    with open(f"questions/{f}", "r", encoding="utf-8") as file:
                        q_list = json.load(file)
                        tema_nome = f.replace(".json", "")
                        for q in q_list: q['tema'] = tema_nome; todas_questoes.append(q)
                except: continue

    if not todas_questoes:
        st.warning("Banco de questões vazio.")
        return

    temas = sorted(list(set(q.get('tema', 'Geral') for q in todas_questoes)))
    temas.insert(0, "Todos os Temas")

    col1, col2 = st.columns(2)
    with col1: tema = st.selectbox("Selecione o tema:", temas)
    with col2: faixa = st.selectbox("Sua faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])

    if st.button("Iniciar Treino 🤼", use_container_width=True):
        if tema == "Todos os Temas":
            questoes_selecionadas = todas_questoes
        else:
            questoes_selecionadas = [q for q in todas_questoes if q.get('tema') == tema]

        if not questoes_selecionadas:
            st.error("Nenhuma questão encontrada.")
            return

        random.shuffle(questoes_selecionadas)
        questoes_treino = questoes_selecionadas[:10] 
        
        acertos = 0
        respostas_usuario = {}
        
        st.markdown("---")
        with st.form("form_treino"):
            for i, q in enumerate(questoes_treino, 1):
                st.markdown(f"**{i}.** {q['pergunta']}")
                if q.get("imagem"): st.image(q["imagem"])
                respostas_usuario[i] = st.radio(f"Opções {i}", options=q.get('opcoes', []), key=f"q_{i}", index=None)
                st.markdown("---")
            enviar = st.form_submit_button("Finalizar Treino")

        if enviar:
            total = len(questoes_treino)
            for i, q in enumerate(questoes_treino, 1):
                resp = respostas_usuario.get(i)
                if resp and resp == q.get('resposta'): acertos += 1
            
            percentual = int((acertos / total) * 100) if total > 0 else 0
            try:
                db.collection('rola_resultados').add({
                    "usuario": usuario_logado["nome"], "faixa": faixa, "tema": tema,
                    "acertos": acertos, "total": total, "percentual": percentual,
                    "data": firestore.SERVER_TIMESTAMP
                })
            except: pass
            st.balloons()
            st.success(f"Treino concluído! {acertos}/{total} ({percentual}%).")

# =========================================
# EXAME DE FAIXA (TIMER CORRIGIDO)
# =========================================
def exame_de_faixa(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🥋 Exame de Faixa</h1>", unsafe_allow_html=True)
    db = get_db()

    # --- 1. PERMISSÃO ---
    if usuario_logado["tipo"] == "aluno":
        alunos_query = db.collection('alunos').where('usuario_id', '==', usuario_logado['id']).stream()
        aluno_doc = next(alunos_query, None)
        permitido = False
        msg = "Exame não liberado."
        
        if aluno_doc:
            dados = aluno_doc.to_dict()
            if dados.get('exame_habilitado'):
                agora = datetime.now()
                ini = dados.get('exame_inicio')
                fim = dados.get('exame_fim')
                if ini and fim:
                    try:
                        ini = ini.replace(tzinfo=None)
                        fim = fim.replace(tzinfo=None)
                        if ini <= agora <= fim: permitido = True
                        else: msg = f"Fora do prazo. ({ini.strftime('%d/%m')} - {fim.strftime('%d/%m')})"
                    except: permitido = True
                else: permitido = True 
        if not permitido:
            st.warning(f"🚫 {msg}")
            return

    # --- 2. SELEÇÃO ---
    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa_sel = st.selectbox("Selecione a faixa:", faixas)
    
    # Inicialização de Estado
    if 'prova_iniciada' not in st.session_state: st.session_state.prova_iniciada = False
    if 'prova_concluida' not in st.session_state: st.session_state.prova_concluida = False
    if 'resultado_final' not in st.session_state: st.session_state.resultado_final = {}
    
    # Reset se mudar faixa
    if 'ultima_faixa_sel' not in st.session_state: st.session_state.ultima_faixa_sel = faixa_sel
    elif st.session_state.ultima_faixa_sel != faixa_sel:
        st.session_state.prova_iniciada = False
        st.session_state.prova_concluida = False
        st.session_state.ultima_faixa_sel = faixa_sel

    # --- 3. TELA DE RESULTADOS (Se já acabou) ---
    if st.session_state.prova_concluida:
        res = st.session_state.resultado_final
        if res.get('faixa') == faixa_sel:
            st.markdown("---")
            if res['aprovado']:
                st.balloons()
                st.success(f"🎉 APROVADO! Nota: {res['percentual']}% ({res['acertos']}/{res['total']})")
                st.info("Seu certificado foi gerado e o código de verificação registrado.")
                
                # Botão de Download
                # Usamos um ID único no botão para evitar conflitos de renderização
                try:
                    pdf_path = gerar_pdf(
                        usuario_logado['nome'], 
                        res['faixa'], 
                        res['acertos'], 
                        res['total'], 
                        res['codigo']
                    )
                    if os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                label="📥 BAIXAR CERTIFICADO AGORA",
                                data=f.read(),
                                file_name=os.path.basename(pdf_path),
                                mime="application/pdf",
                                use_container_width=True,
                                key="btn_download_final"
                            )
                    else:
                        st.error("Erro: Arquivo PDF não foi criado.")
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")
            else:
                msg_tempo = "Tempo Esgotado. " if res.get('tempo_esgotado') else ""
                st.error(f"Reprovado. {msg_tempo}Nota: {res['percentual']}%. Mínimo: 70%.")
            
            if st.button("🔄 Voltar ao Início"):
                st.session_state.prova_iniciada = False
                st.session_state.prova_concluida = False
                st.rerun()
            return

    # --- 4. CARREGA PROVA ---
    doc_ref = db.collection('exames').document(faixa_sel)
    doc_exame = doc_ref.get()
    dados_exame = doc_exame.to_dict() if doc_exame.exists else {}
    
    if not dados_exame:
        json_path = f"exames/faixa_{faixa_sel.lower()}.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f: dados_exame = json.load(f)
            except: pass

    if not dados_exame:
        st.info(f"Sem prova cadastrada para {faixa_sel}.")
        return

    lista_questoes = dados_exame.get('questoes', [])
    tempo_limite = dados_exame.get('tempo_limite', 60)

    if not lista_questoes:
        st.warning("Prova vazia.")
        return

    # --- 5. TELA DE INSTRUÇÕES ---
    if not st.session_state.prova_iniciada:
        st.markdown("---")
        with st.container(border=True):
            st.markdown(f"### 📜 Instruções - Faixa {faixa_sel}")
            st.markdown(f"""
            * **Questões:** {len(lista_questoes)}
            * **Tempo Limite:** ⏱️ {tempo_limite} minutos
            * **Aprovação:** 70% de acertos
            
            Ao clicar em iniciar, o tempo começará a contar.
            """)
            
            if st.button("✅ Começar Agora", type="primary", use_container_width=True):
                st.session_state.prova_iniciada = True
                st.session_state.prova_concluida = False
                st.session_state.fim_prova = datetime.now() + timedelta(minutes=tempo_limite)
                st.rerun()
        return 

    # --- 6. PROVA EM ANDAMENTO ---
    
    # Tempo
    agora = datetime.now()
    tempo_restante = st.session_state.fim_prova - agora
    segundos_restantes = int(tempo_restante.total_seconds())
    
    tempo_esgotado = segundos_restantes <= 0

    if not tempo_esgotado:
        # CRONÔMETRO COM ID ÚNICO PARA EVITAR CONFLITOS
        timer_id = f"timer_{uuid.uuid4()}"
        st.markdown(
            f"""
            <div style="text-align: center; padding: 10px; border: 2px solid #FFD700; border-radius: 10px; margin-bottom: 20px; background-color: #0e2d26;">
                <h3 id="{timer_id}" style="color: #FFD700; margin: 0;">Carregando...</h3>
            </div>
            <script>
            (function() {{
                var timeleft = {segundos_restantes};
                var timerElement = document.getElementById("{timer_id}");
                if (timerElement) {{
                    var downloadTimer = setInterval(function(){{
                    if(timeleft <= 0){{
                        clearInterval(downloadTimer);
                        timerElement.innerHTML = "⌛ Tempo Esgotado!";
                    }} else {{
                        var m = Math.floor(timeleft / 60);
                        var s = timeleft % 60;
                        timerElement.innerHTML = "⏱️ " + m + ":" + (s < 10 ? "0" : "") + s;
                    }}
                    timeleft -= 1;
                    }}, 1000);
                }}
            }})();
            </script>
            """,
            unsafe_allow_html=True
        )
    else:
        st.error("⌛ TEMPO ESGOTADO!")

    # Prova
    respostas = {}
    finalizar = False
    
    if not tempo_esgotado:
        with st.form(key=f"form_prova_{faixa_sel}"):
            for i, q in enumerate(lista_questoes, 1):
                st.markdown(f"**{i}.** {q['pergunta']}")
                if q.get("imagem"): st.image(q["imagem"])
                respostas[i] = st.radio("Alternativa:", q.get('opcoes', []), key=f"resp_{i}", index=None)
                st.markdown("---")
            
            finalizar = st.form_submit_button("Finalizar Exame 🏁", use_container_width=True)
    else:
        finalizar = True 
        
    # --- 7. FINALIZAÇÃO ---
    if finalizar:
        acertos = 0
        total = len(lista_questoes)
        
        if not tempo_esgotado:
            for i, q in enumerate(lista_questoes, 1):
                resp_user = respostas.get(i)
                resp_certa = q.get('resposta')
                if resp_user:
                    # Verifica se a resposta contém o texto correto
                    if resp_user == resp_certa or resp_user.startswith(f"{resp_certa})"):
                        acertos += 1
        
        percentual = int((acertos / total) * 100) if total > 0 else 0
        aprovado = percentual >= 70
        
        # Gera código (agora usando utils.py corrigido com Firestore)
        codigo = gerar_codigo_verificacao() if aprovado else None

        if aprovado:
            try:
                db.collection('resultados').add({
                    "usuario": usuario_logado["nome"], "modo": "Exame de Faixa",
                    "faixa": faixa_sel, "pontuacao": percentual,
                    "acertos": acertos, "total_questoes": total,
                    "data": firestore.SERVER_TIMESTAMP, "codigo_verificacao": codigo
                })
            except Exception as e:
                st.error(f"Erro ao salvar resultado na nuvem: {e}")
        
        # Salva estado e recarrega para limpar a tela
        st.session_state.prova_concluida = True
        st.session_state.resultado_final = {
            "usuario": usuario_logado["nome"], "faixa": faixa_sel,
            "acertos": acertos, "total": total, "percentual": percentual,
            "codigo": codigo, "aprovado": aprovado, "tempo_esgotado": tempo_esgotado
        }
        st.rerun()

# =========================================
# RANKING
# =========================================
def ranking():
    st.markdown("<h1 style='color:#FFD700;'>🏆 Ranking</h1>", unsafe_allow_html=True)
    db = get_db()
    
    docs = db.collection('rola_resultados').stream()
    data = [d.to_dict() for d in docs]
    if not data: st.info("Ranking vazio."); return
    df = pd.DataFrame(data)
    if 'usuario' in df.columns:
        rdf = df.groupby("usuario", as_index=False).agg(media=("percentual", "mean"), total=("usuario", "count")).sort_values("media", ascending=False)
        st.dataframe(rdf, use_container_width=True)

# =========================================
# MEUS CERTIFICADOS
# =========================================
def meus_certificados(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>📜 Meus Certificados</h1>", unsafe_allow_html=True)
    db = get_db()
    docs = db.collection('resultados').where('usuario', '==', usuario_logado['nome']).where('modo', '==', 'Exame de Faixa').stream()
    
    lista = [d.to_dict() for d in docs]
    if not lista: st.info("Sem certificados."); return

    for i, c in enumerate(lista):
        with st.container(border=True):
            st.write(f"**{c['faixa']}** | {c['pontuacao']}% | {c.get('codigo_verificacao')}")
            try:
                p = gerar_pdf(usuario_logado['nome'], c['faixa'], c.get('acertos',0), c.get('total_questoes',10), c.get('codigo_verificacao','-'))
                with open(p, "rb") as f: st.download_button("Baixar", f.read(), os.path.basename(p), "application/pdf", key=f"d{i}")
            except: pass
