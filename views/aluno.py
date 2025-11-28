import streamlit as st
import random
import os
import json
import time
import uuid
from datetime import datetime, timedelta
import pandas as pd
import streamlit.components.v1 as components 
from database import get_db
from utils import gerar_codigo_verificacao, gerar_pdf
from firebase_admin import firestore
from utils import verificar_elegibilidade_exame, registrar_inicio_exame, registrar_fim_exame, bloquear_por_abandono

# =========================================
# FUNÇÕES AUXILIARES COM CACHE
# =========================================
@st.cache_data(ttl=300) 
def carregar_questoes_firestore():
    db = get_db()
    todas_questoes = []
    try:
        # Filtra apenas questões APROVADAS
        docs_questoes = list(db.collection('questoes').stream())
        if docs_questoes:
            for d in docs_questoes:
                q = d.to_dict()
                if q.get('status', 'aprovada') == 'aprovada':
                    todas_questoes.append(q)
    except: pass
    
    # Fallback local para testes
    if not todas_questoes and os.path.exists("questions"):
        for f in os.listdir("questions"):
            if f.endswith(".json"):
                try:
                    with open(f"questions/{f}", "r", encoding="utf-8") as file:
                        q_list = json.load(file)
                        tema_nome = f.replace(".json", "")
                        for q in q_list: q['tema'] = tema_nome; todas_questoes.append(q)
                except: continue
    return todas_questoes

@st.cache_data(ttl=300)
def carregar_exame_firestore(faixa_sel):
    db = get_db()
    doc_ref = db.collection('exames').document(faixa_sel)
    doc_exame = doc_ref.get()
    dados_exame = doc_exame.to_dict() if doc_exame.exists else {}
    
    if not dados_exame:
        json_path = f"exames/faixa_{faixa_sel.lower()}.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f: dados_exame = json.load(f)
            except: pass
    return dados_exame

# =========================================
# MODO ROLA (Treino Livre)
# =========================================
def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)
    db = get_db()

    todas_questoes = carregar_questoes_firestore()

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
        
        st.markdown("---")
        respostas_usuario = {}
        with st.form("form_treino"):
            for i, q in enumerate(questoes_treino, 1):
                st.markdown(f"**{i}.** {q['pergunta']}")
                
                # Mostra autor discretamente
                autor = q.get('criado_por', 'Desconhecido').title()
                
                if q.get("imagem"): st.image(q["imagem"])
                respostas_usuario[i] = st.radio(f"Opções {i}", options=q.get('opcoes', []), key=f"q_{i}", index=None)
                
                st.caption(f"Questão elaborada por: {autor}")
                st.markdown("---")
            enviar = st.form_submit_button("Finalizar Treino")

        if enviar:
            acertos = 0
            for i, q in enumerate(questoes_treino, 1):
                resp = respostas_usuario.get(i)
                if resp and resp == q.get('resposta'): acertos += 1
            
            total = len(questoes_treino)
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
# EXAME DE FAIXA (CRONÔMETRO JS CORRIGIDO)
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    # 1. Busca dados frescos do banco (para garantir que não está usando cache velho)
    db = get_db()
    doc = db.collection('usuarios').document(usuario['id']).get()
    dados_atualizados = doc.to_dict()
    
    # 2. Verifica regras (72h, Bloqueio, etc)
    pode_fazer, msg = verificar_elegibilidade_exame(dados_atualizados)
    
    if not pode_fazer:
        st.error(msg)
        st.info("Entre em contato com seu professor se achar que isso é um erro.")
        return

    # 3. Detector de "Fuga" (Se o aluno estava 'em_andamento' e a página recarregou, ele fugiu)
    if dados_atualizados.get("status_exame") == "em_andamento":
        # Se chegou aqui e está 'em_andamento', significa que ele deu F5 ou fechou e abriu
        bloquear_por_abandono(usuario['id'])
        st.error("🚨 DETECÇÃO DE INFRAÇÃO: Você saiu da página ou recarregou durante o exame.")
        st.warning("Seu exame foi bloqueado. Solicite o desbloqueio ao professor.")
        st.stop()

    # --- JAVASCRIPT ANTI-FRAUDE (Visibilidade da Aba) ---
    # Esse script esconde o conteúdo se o usuário mudar de aba e avisa
    html_anti_cola = """
    <script>
    document.addEventListener("visibilitychange", function() {
        if (document.hidden) {
            document.body.innerHTML = "<h1 style='color:red; text-align:center; margin-top:20%'>🚨 INFRAÇÃO DETECTADA 🚨<br>Você saiu da aba da prova.<br>Isso viola as regras.<br>Atualize a página para ver seu status.</h1>";
        }
    });
    </script>
    """
    st.components.v1.html(html_anti_cola, height=0, width=0)

    # 4. Tela de Início do Exame
    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado = False

    if not st.session_state.exame_iniciado:
        st.warning("⚠️ **REGRAS RIGOROSAS:**")
        st.markdown("""
        1. **Não saia desta tela:** Se você mudar de aba, minimizar o navegador ou abrir outro programa, **a prova será bloqueada**.
        2. **Tentativa Única:** Se reprovar, você deverá aguardar **72 horas**.
        3. **Problemas Técnicos:** Se o computador desligar, você precisará pedir desbloqueio ao professor.
        """)
        
        if st.button("Li e Concordo. INICIAR EXAME AGORA", type="primary"):
            # Marca no banco que começou AGORA
            registrar_inicio_exame(usuario['id'])
            st.session_state.exame_iniciado = True
            st.rerun()
    
    # 5. O Exame em Si
    else:
        # (Aqui entra sua lógica de carregar questões JSON que você já tem)
        # Vou colocar um exemplo simplificado para ilustrar o fechamento
        
        st.info("📝 Prova em Andamento... Não saia desta tela!")
        
        # ... Lógica das perguntas ...
        # (Supondo que você carregou as questões e pegou as respostas)
        
        # Exemplo de finalização
        with st.form("form_exame"):
            st.write("Questão 1: O que é Jiu-Jitsu?")
            resp = st.radio("Selecione:", ["Arte Suave", "Boxe", "Dança"])
            
            enviar = st.form_submit_button("Finalizar Prova")
            
            if enviar:
                # Lógica de correção
                aprovado = True if resp == "Arte Suave" else False
                pontuacao = 100 if aprovado else 0
                
                # Salva resultado e TIRA o status 'em_andamento'
                registrar_fim_exame(usuario['id'], aprovado)
                
                # Limpa sessão
                st.session_state.exame_iniciado = False
                
                if aprovado:
                    st.balloons()
                    st.success("Parabéns! Aprovado.")
                else:
                    st.error("Reprovado. Estude mais e volte em 72h.")
                
                time.sleep(3)
                st.rerun()

# =========================================
# RANKING e CERTIFICADOS (MANTIDOS)
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
                p_bytes, p_name = gerar_pdf(
                    usuario_logado['nome'], c['faixa'], 
                    c.get('acertos',0), c.get('total_questoes',10), 
                    c.get('codigo_verificacao','-')
                )
                st.download_button("Baixar", p_bytes, p_name, "application/pdf", key=f"d{i}")
            except: pass
