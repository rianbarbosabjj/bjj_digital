import streamlit as st
import pandas as pd
import bcrypt
import time 
import io 
from datetime import datetime, date, time as dtime 
from database import get_db, OPCOES_SEXO
from firebase_admin import firestore

# Tenta importar dashboard
try:
    from views.dashboard_admin import render_dashboard_geral
except ImportError:
    def render_dashboard_geral(): st.warning("Dashboard não encontrado.")

# Importa utils
import utils as ce 

# --- CORES ---
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"

# --- CONSTANTES ---
FAIXAS_COMPLETAS = [" ", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
NIVEIS = [1, 2, 3, 4]
MAPA_NIVEL = {1: "🟢 Fácil", 2: "🔵 Médio", 3: "🟠 Difícil", 4: "🔴 Muito Difícil"}

# --- ESTILOS ---
def aplicar_estilos_admin():
    st.markdown(f"""
    <style>
    .admin-card {{
        background: linear-gradient(145deg, rgba(14, 45, 38, 0.95), rgba(9, 31, 26, 0.98));
        border: 1px solid rgba(255, 215, 112, 0.15); border-radius: 15px; padding: 1rem;
        margin-bottom: 1rem; position: relative;
    }}
    .admin-header {{
        background: linear-gradient(135deg, {COR_BOTAO}, #0e2d26);
        padding: 1.5rem; border-radius: 0 0 20px 20px; margin-bottom: 2rem;
        text-align: center; color: white;
    }}
    .stButton>button {{ width: 100%; border-radius: 8px; }}
    </style>
    """, unsafe_allow_html=True)

# =========================================
# GESTÃO DE USUÁRIOS
# =========================================
def gestao_usuarios_tab():
    db = get_db()
    users = [d.to_dict() | {"id": d.id} for d in db.collection('usuarios').stream()]
    if not users: st.warning("Sem usuários."); return
    
    df = pd.DataFrame(users)
    busca = st.text_input("🔍 Buscar Nome/CPF:")
    if busca:
        t = busca.upper()
        df = df[df['nome'].astype(str).str.upper().str.contains(t) | df['cpf'].astype(str).str.contains(t)]
    
    st.dataframe(df[['nome', 'email', 'tipo_usuario', 'faixa_atual']], use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🛠️ Editar")
    sel = st.selectbox("Usuário:", df.to_dict('records'), format_func=lambda x: f"{x.get('nome')} ({x.get('tipo_usuario')})")
    
    if sel:
        with st.form(f"edt_{sel['id']}"):
            c1, c2 = st.columns(2)
            nm = c1.text_input("Nome", sel.get('nome',''))
            em = c2.text_input("Email", sel.get('email',''))
            if st.form_submit_button("Salvar"):
                db.collection('usuarios').document(sel['id']).update({"nome": nm.upper(), "email": em})
                st.success("Salvo!"); time.sleep(1); st.rerun()

# =========================================
# GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes_tab():
    aplicar_estilos_admin()
    st.markdown(f"""<div class="admin-header"><h1>📝 Banco de Questões</h1></div>""", unsafe_allow_html=True)
    db = get_db()
    
    tab1, tab2 = st.tabs(["📚 Listar/Editar", "➕ Criar Nova"])
    
    # LISTAR
    with tab1:
        qs = list(db.collection('questoes').stream())
        termo = st.text_input("🔍 Buscar questão:")
        
        for doc in qs:
            q = doc.to_dict()
            if termo and termo.lower() not in q.get('pergunta','').lower(): continue
            
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                bdg = MAPA_NIVEL.get(q.get('dificuldade',1), "?")
                c1.markdown(f"**{bdg}** | {q.get('categoria','Geral')}")
                c1.markdown(f"##### {q.get('pergunta')}")
                
                with c1.expander("Ver Detalhes"):
                    alts = q.get('alternativas', {})
                    st.write(f"A) {alts.get('A')} | B) {alts.get('B')}")
                    st.write(f"C) {alts.get('C')} | D) {alts.get('D')}")
                    st.success(f"Gabarito: {q.get('resposta_correta')}")
                
                if c2.button("🗑️", key=f"dq_{doc.id}"):
                    db.collection('questoes').document(doc.id).delete(); st.rerun()

    # CRIAR
    with tab2:
        with st.form("nova_q"):
            perg = st.text_area("Enunciado *")
            c1, c2 = st.columns(2)
            dif = c1.selectbox("Nível", NIVEIS)
            cat = c2.text_input("Categoria", "Geral")
            
            aa = c1.text_input("A *"); ab = c2.text_input("B *")
            ac = c1.text_input("C"); ad = c2.text_input("D")
            corr = st.selectbox("Correta", ["A", "B", "C", "D"])
            
            if st.form_submit_button("💾 Salvar Questão"):
                if perg and aa and ab:
                    db.collection('questoes').add({
                        "pergunta": perg, "dificuldade": dif, "categoria": cat,
                        "alternativas": {"A":aa, "B":ab, "C":ac, "D":ad},
                        "resposta_correta": corr, "status": "aprovada",
                        "criado_por": st.session_state.usuario.get('nome'),
                        "data_criacao": firestore.SERVER_TIMESTAMP
                    })
                    st.success("Criada!"); time.sleep(1); st.rerun()
                else: st.error("Preencha os campos obrigatórios.")

# =========================================
# GESTÃO DE EXAMES
# =========================================
def gestao_exame_de_faixa_route():
    aplicar_estilos_admin()
    st.markdown(f"""<div class="admin-header"><h1>📜 Gerenciador de Exames</h1></div>""", unsafe_allow_html=True)
    db = get_db()
    
    tab1, tab2 = st.tabs(["📝 Configurar Prova", "✅ Autorizar Alunos"])
    
    # CONFIGURAR PROVA
    with tab1:
        fx = st.selectbox("Selecione a Faixa:", FAIXAS_COMPLETAS)
        
        # Busca config existente
        configs = list(db.collection('config_exames').where('faixa', '==', fx).limit(1).stream())
        conf_id = configs[0].id if configs else None
        conf_data = configs[0].to_dict() if configs else {}
        
        # Busca questões
        qs = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        
        st.markdown(f"### Seleção de Questões para {fx}")
        
        # Seleção
        sel_ids = set(conf_data.get('questoes_ids', []))
        
        # Renderiza lista simplificada para evitar erros
        with st.container(height=400, border=True):
            for doc in qs:
                d = doc.to_dict()
                chk = st.checkbox(f"{d.get('pergunta')[:50]}...", value=(doc.id in sel_ids), key=f"ex_{doc.id}")
                if chk: sel_ids.add(doc.id)
                elif doc.id in sel_ids: sel_ids.discard(doc.id)
        
        st.info(f"**{len(sel_ids)}** questões selecionadas.")
        
        c1, c2 = st.columns(2)
        tempo = c1.number_input("Tempo (min)", value=int(conf_data.get('tempo_limite', 45)))
        nota = c2.number_input("Aprovação (%)", value=int(conf_data.get('aprovacao_minima', 70)))
        
        if st.button("💾 Salvar Configuração de Exame"):
            dados = {
                "faixa": fx, "questoes_ids": list(sel_ids), 
                "qtd_questoes": len(sel_ids), "tempo_limite": tempo, 
                "aprovacao_minima": nota
            }
            if conf_id: db.collection('config_exames').document(conf_id).update(dados)
            else: db.collection('config_exames').add(dados)
            st.success("Configuração salva!"); time.sleep(1); st.rerun()

    # AUTORIZAR
    with tab2:
        st.markdown("### Liberar Exame para Alunos")
        # Lista segura de alunos
        alunos = [d for d in db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream()]
        
        for doc in alunos:
            d = doc.to_dict()
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.markdown(f"**{d.get('nome')}**")
                
                # Status
                status = d.get('status_exame', 'pendente')
                hab = d.get('exame_habilitado', False)
                
                cor = "green" if hab else "gray"
                txt = "🟢 Liberado" if hab else "⚪ Bloqueado"
                c2.markdown(f":{cor}[{txt}]")
                
                if hab:
                    if c3.button("⛔ Bloquear", key=f"b_{doc.id}"):
                        db.collection('usuarios').document(doc.id).update({"exame_habilitado": False})
                        st.rerun()
                else:
                    if c3.button("✅ Liberar", key=f"l_{doc.id}"):
                        # Libera para a próxima faixa ou a selecionada na tab1
                        db.collection('usuarios').document(doc.id).update({
                            "exame_habilitado": True, "faixa_exame": fx,
                            "exame_inicio": datetime.now().isoformat()
                        })
                        st.success("Liberado!"); st.rerun()

# =========================================
# ROUTER
# =========================================
def gestao_questoes(): gestao_questoes_tab()
def gestao_exame_de_faixa(): gestao_exame_de_faixa_route()
def gestao_usuarios(u): gestao_usuarios_tab()
