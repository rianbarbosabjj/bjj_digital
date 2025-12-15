"""
BJJ Digital - Sistema de Cursos (Versão Modernizada)
Integração com aulas, design atualizado, Colaboração (CPF) e Uploads.
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import Optional, Dict, List

# Importações internas
from database import get_db

# Importa o módulo completo com alias para chamadas genéricas
import utils as ce 

# Importa a view de gerenciamento de aulas
import views.aulas as aulas_view 

# --- 1. CONFIGURAÇÃO DE CORES ---
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO = "#0e2d26"
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770"
    COR_BOTAO = "#078B6C" # Verde BJJ Digital
    COR_HOVER = "#FFD770" # Dourado

# ======================================================
# LÓGICAS DE CONSULTA (Wrapper)
# ======================================================
def obter_progresso_aula(user_id: str, curso_id: str, aula_id: str) -> bool:
    return ce.verificar_aula_concluida(user_id, aula_id)

def registrar_progresso_aula(user_id: str, curso_id: str, aula_id: str) -> int:
    ce.marcar_aula_concluida(user_id, aula_id) 
    inscricao = ce.obter_inscricao(user_id, curso_id)
    return inscricao.get("progresso", 0) if inscricao else 0

# ======================================================
# ESTILOS E NAVEGAÇÃO
# ======================================================
def aplicar_estilos_cursos():
    st.markdown(f"""
    <style>
    .curso-card-moderno {{
        background: linear-gradient(145deg, rgba(14, 45, 38, 0.9) 0%, rgba(9, 31, 26, 0.95) 100%);
        border: 1px solid rgba(255, 215, 112, 0.15); border-radius: 20px; padding: 1.5rem;
        height: 100%; display: flex; flex-direction: column; position: relative; overflow: hidden;
        transition: all 0.3s ease;
    }}
    .curso-card-moderno:hover {{
        border-color: {COR_DESTAQUE}; transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }}
    .curso-icon {{ font-size: 2.5rem; text-align: center; margin-bottom: 1rem; }}
    .curso-badges {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0; }}
    .curso-badge {{
        padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
        border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.05);
    }}
    .curso-badge.blue {{ color: #60A5FA; border-color: #60A5FA; }}
    
    /* Botões */
    div.stButton > button, div.stFormSubmitButton > button {{ 
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important; 
        color: white !important; border: 1px solid rgba(255,255,255,0.1) !important; 
        border-radius: 8px !important; transition: all 0.3s ease !important;
    }}
    div.stButton > button:hover {{ 
        background: {COR_HOVER} !important; color: #0e2d26 !important; transform: translateY(-2px);
    }}
    .stButton>button[kind="secondary"] {{ background: transparent !important; color: {COR_DESTAQUE} !important; border: 1px solid {COR_DESTAQUE} !important; }}
    .stButton>button[kind="secondary"]:hover {{ background: {COR_DESTAQUE} !important; color: #0e2d26 !important; }}
    .stButton>button[key^="btn_delete_final"]:hover {{ border-color: #ff4b4b !important; color: #ff4b4b !important; background: rgba(255, 75, 75, 0.1) !important; }}
    
    /* Header */
    .curso-header {{
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.8) 0%, rgba(9, 31, 26, 0.9) 100%);
        border-bottom: 1px solid rgba(255, 215, 112, 0.2); padding: 1.5rem; border-radius: 0 0 20px 20px; margin-bottom: 2rem;
    }}
    </style>
    """, unsafe_allow_html=True)

def navegar_para(view: str, curso: Optional[Dict] = None):
    st.session_state['cursos_view'] = view
    st.session_state['curso_selecionado'] = curso
    st.rerun()

def pagina_cursos(usuario: dict):
    aplicar_estilos_cursos()
    if 'cursos_view' not in st.session_state: st.session_state['cursos_view'] = 'lista'
        
    st.markdown(f"""
    <div class="curso-header">
        <h1 style="margin:0; text-align:center; color:{COR_DESTAQUE};">🎓 BJJ DIGITAL CURSOS</h1>
        <p style="text-align:center; opacity:0.8;">Bem-vindo(a), <strong>{usuario.get('nome','').split()[0]}</strong></p>
    </div>""", unsafe_allow_html=True)
    
    if st.session_state.get('cursos_view') != 'lista':
        if st.button("← Voltar à Lista", key="btn_back_list", type="secondary"): navegar_para('lista')
    else:
        if st.button("← Menu Principal", key="btn_back_home"):
            st.session_state.menu_selection = "Início"; st.rerun()
    st.write("")

    view = st.session_state.get('cursos_view')
    curso = st.session_state.get('curso_selecionado')
    tipo_user = str(usuario.get("tipo", "aluno")).lower()
    is_prof_admin = tipo_user in ["admin", "professor"]
    
    if view == 'lista':
        _interface_professor_moderna(usuario) if is_prof_admin else _interface_aluno_moderna(usuario)
    elif view == 'detalhe' and curso:
        _exibir_detalhes_curso(curso, usuario)
    elif view == 'aulas' and curso:
        _pagina_aulas(curso, usuario)
    elif view == 'edicao' and curso and is_prof_admin:
        _pagina_edicao_curso(curso, usuario)
    elif view == 'gerenciar_conteudo' and curso and is_prof_admin:
        aulas_view.gerenciar_conteudo_curso(curso, usuario)
    else:
        st.session_state['cursos_view'] = 'lista'; st.rerun()

# ======================================================
# INTERFACES
# ======================================================
def _interface_professor_moderna(usuario):
    tab1, tab2, tab3 = st.tabs(["📘 Meus Cursos", "➕ Criar Novo", "📊 Dashboard"])
    with tab1: _professor_listar_cursos(usuario)
    with tab2: _pagina_criar_curso(usuario)
    with tab3: st.info("Dashboard em desenvolvimento.")

def _interface_aluno_moderna(usuario):
    tab1, tab2 = st.tabs(["🛒 Disponíveis", "🎓 Meus Cursos"])
    with tab1: _aluno_cursos_disponiveis(usuario)
    with tab2: _aluno_meus_cursos(usuario)

# --- LISTAR COLABORADORES COM DEBUG ---
def _render_colaboracao_debug():
    st.markdown("### 👥 Colaboração")
    
    # ------------------ DEBUGGER ------------------
    with st.expander("🕵️ DEBUG: Por que a lista está vazia?"):
        st.warning("Esta ferramenta mostra o que está no banco para você ajustar o filtro.")
        try:
            db = ce.get_db()
            docs = db.collection('usuarios').limit(5).stream()
            found = False
            for d in docs:
                found = True
                dd = d.to_dict()
                st.code(f"Nome: {dd.get('nome')}\nTipo: '{dd.get('tipo')}'\nCPF: {dd.get('cpf')}")
            if not found: st.error("Coleção 'usuarios' vazia.")
            else: st.success("Usuários encontrados! Verifique se o 'Tipo' está escrito como 'professor' ou 'admin'.")
        except Exception as e:
            st.error(f"Erro ao conectar: {e}")
    # ----------------------------------------------

    users = ce.listar_todos_usuarios_para_selecao()
    map_u = {u['id']: f"{u['nome']} (CPF: {u.get('cpf','N/A')})" for u in users}
    return map_u

# --- CRIAÇÃO DE CURSO ---
def _pagina_criar_curso(usuario):
    st.markdown("### 🚀 Criar Novo Curso")
    if "new_pago_toggle" not in st.session_state: st.session_state["new_pago_toggle"] = False
        
    with st.container(border=True):
        st.markdown("#### 📝 Básico")
        c1, c2 = st.columns([2, 1])
        with c1:
            titulo = st.text_input("Título *", key="new_titulo")
            desc = st.text_area("Descrição *", height=100, key="new_desc")
        with c2:
            mod = st.selectbox("Modalidade", ["EAD", "Presencial", "Híbrido"], key="new_mod")
            pub = st.selectbox("Público", ["geral", "equipe"], key="new_pub")
            eq = st.text_input("Nome da Equipe", key="new_eq") if pub == "equipe" else None

        # Colaboração com Debug
        map_u = _render_colaboracao_debug()
        editores = st.multiselect("Editores", list(map_u.keys()), format_func=lambda x: map_u.get(x,x), key="new_eds")

        st.markdown("---")
        st.markdown("#### ⚙️ Configs")
        cc1, cc2 = st.columns(2)
        with cc1: cert = st.checkbox("Certificado Automático", True, key="new_cert")
        with cc2:
            dur = st.text_input("Duração", "10h", key="new_dur")
            niv = st.selectbox("Nível", ["Todos os Níveis", "Iniciante", "Avançado"], key="new_niv")

        st.markdown("---")
        st.markdown("#### 💰 Financeiro")
        cf1, cf2, cf3 = st.columns([1,1,1])
        with cf1: pago = st.toggle("Curso Pago?", key="new_pago_toggle")
        with cf2: preco = st.number_input("Valor (R$)", 0.0, disabled=not pago, key="new_pr")
        with cf3: 
            split = 10
            if usuario.get('tipo')=='admin' and pago: split = st.slider("Taxa %", 0, 100, 10, key="new_sp")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Criar Curso", type="primary", use_container_width=True):
            if not titulo or not desc: st.error("Preencha título e descrição.")
            else:
                ce.criar_curso(usuario['id'], usuario.get('nome',''), titulo, desc, mod, pub, eq, pago, preco, split, cert, dur, niv, editores)
                st.success("Criado!"); time.sleep(1); navegar_para('lista')

# --- EDIÇÃO DE CURSO ---
def _pagina_edicao_curso(curso, usuario):
    st.markdown(f"### ✏️ Editando: {curso.get('titulo')}")
    if usuario['id'] in curso.get('editores_ids', []): st.info("ℹ️ Você é um Editor.")
    
    k_pg = f"edt_pg_{curso['id']}"
    if k_pg not in st.session_state: st.session_state[k_pg] = curso.get('pago', False)

    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            nt = st.text_input("Título", value=curso.get('titulo',''), key=f"et_{curso['id']}")
            nd = st.text_area("Descrição", value=curso.get('descricao',''), height=100, key=f"ed_{curso['id']}")
        with c2:
            nm = st.selectbox("Modalidade", ["EAD", "Presencial", "Híbrido"], index=["EAD","Presencial","Híbrido"].index(curso.get('modalidade','EAD')), key=f"em_{curso['id']}")
            npub = st.selectbox("Público", ["geral", "equipe"], index=0 if curso.get('publico')=='geral' else 1, key=f"ep_{curso['id']}")
            neq = st.text_input("Equipe", value=curso.get('equipe_destino',''), key=f"eeq_{curso['id']}") if npub=='equipe' else None

        # Colaboração com Debug
        map_u = _render_colaboracao_debug()
        cur_eds = [u for u in curso.get('editores_ids',[]) if u in map_u]
        ne = st.multiselect("Editores", list(map_u.keys()), default=cur_eds, format_func=lambda x: map_u.get(x,x), key=f"ee_{curso['id']}")

        st.markdown("---")
        cc1, cc2 = st.columns(2)
        with cc1:
            ncert = st.checkbox("Certificado", value=curso.get('certificado_automatico', True), key=f"ec_{curso['id']}")
            natv = st.checkbox("Ativo", value=curso.get('ativo', True), key=f"ea_{curso['id']}")
        with cc2:
            ndur = st.text_input("Duração", value=curso.get('duracao_estimada',''), key=f"edur_{curso['id']}")
            ops_n = ["Todos os Níveis", "Iniciante", "Avançado"]
            nniv = st.selectbox("Nível", ops_n, index=ops_n.index(curso.get('nivel', "Todos os Níveis")) if curso.get('nivel') in ops_n else 0, key=f"en_{curso['id']}")

        st.markdown("---")
        cf1, cf2 = st.columns(2)
        with cf1: npago = st.toggle("Pago?", key=k_pg)
        with cf2: npr = st.number_input("Valor", value=float(curso.get('preco',0)), disabled=not npago, key=f"epr_{curso['id']}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Salvar", type="primary", use_container_width=True, key=f"bs_{curso['id']}"):
            dados = {"titulo": nt, "descricao": nd, "modalidade": nm, "publico": npub, "equipe_destino": neq, "editores_ids": ne, "pago": npago, "preco": npr, "certificado_automatico": ncert, "ativo": natv, "duracao_estimada": ndur, "nivel": nniv, "atualizado_em": datetime.now()}
            ce.editar_curso(curso['id'], dados)
            st.success("Salvo!"); time.sleep(1); navegar_para('detalhe', dados)

    # Zona de Perigo
    if usuario['id'] == curso.get('professor_id') or usuario.get('tipo') == 'admin':
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🗑️ Zona de Perigo"):
            st.warning("Excluir apaga tudo.")
            if st.button("Excluir Definitivamente", type="secondary", key=f"bdel_{curso['id']}"):
                if ce.excluir_curso(curso['id']):
                    st.success("Excluído!"); time.sleep(1); st.session_state['curso_selecionado']=None; navegar_para('lista')
                else: st.error("Erro ao excluir.")

# --- LISTAGEM PROFESSOR ---
def _professor_listar_cursos(usuario):
    cursos = ce.listar_cursos_do_professor(usuario['id'])
    if not cursos: st.info("Sem cursos."); return
    cols = st.columns(3)
    for i, c in enumerate(cursos):
        with cols[i%3]:
            # Card
            ativo = c.get('ativo', True)
            icon = "🎓" if ativo else "⏸️"
            is_editor = c.get('papel') == 'Editor'
            badge = f"<span class='curso-badge blue'>✏️ Editor</span>" if is_editor else ""
            
            st.markdown(f"""
            <div class="curso-card-moderno">
                <div style="text-align:right;">{badge}</div>
                <div class="curso-icon">{icon}</div>
                <h4>{c.get('titulo')}</h4>
            </div>""", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("Editar", key=f"e_{c['id']}", use_container_width=True): navegar_para('edicao', c)
            if c2.button("Ver", key=f"v_{c['id']}", use_container_width=True): navegar_para('detalhe', c)

# --- DETALHES ---
def _exibir_detalhes_curso(curso, usuario):
    st.title(curso.get('titulo'))
    can_edit = (usuario['id'] == curso.get('professor_id')) or (usuario['id'] in curso.get('editores_ids', [])) or (usuario.get('tipo') == 'admin')
    
    if can_edit:
        c1, c2 = st.columns(2)
        if c1.button("✏️ Editar", use_container_width=True): navegar_para('edicao', curso)
        if c2.button("➕ Aulas", type="primary", use_container_width=True): navegar_para('gerenciar_conteudo', curso)
    
    st.write(curso.get('descricao'))
    insc = ce.obter_inscricao(usuario['id'], curso['id'])
    
    if insc or can_edit:
        if st.button("🎬 Acessar Aulas", type="primary"): navegar_para('aulas', curso)
    else:
        lbl = f"Comprar R$ {curso.get('preco')}" if curso.get('pago') else "Inscrever-se Grátis"
        if st.button(lbl, type="primary"):
            ce.inscrever_usuario_em_curso(usuario['id'], curso['id'])
            st.success("Inscrito!"); st.rerun()

# --- PLAYER AULAS ---
def _pagina_aulas(curso, usuario):
    st.subheader(f"📺 {curso.get('titulo')}")
    modulos = ce.listar_modulos_e_aulas(curso['id'])
    if not modulos: st.warning("Sem aulas."); return
    
    c_vid, c_list = st.columns([3, 1])
    if 'aula_atual' not in st.session_state and modulos and modulos[0]['aulas']:
        st.session_state['aula_atual'] = modulos[0]['aulas'][0]
    aula = st.session_state.get('aula_atual')
    
    with c_list:
        for m in modulos:
            with st.expander(m['titulo'], expanded=True):
                for a in m['aulas']:
                    icon = "✅" if ce.verificar_aula_concluida(usuario['id'], a['id']) else "⭕"
                    if st.button(f"{icon} {a['titulo']}", key=f"nav_{a['id']}", use_container_width=True):
                        st.session_state['aula_atual'] = a; st.rerun()

    with c_vid:
        if aula:
            st.markdown(f"#### {aula['titulo']}")
            cont = aula.get('conteudo', {})
            tipo = aula.get('tipo')
            
            if tipo == 'video':
                tv = cont.get('tipo_video', 'link')
                if tv == 'link' and cont.get('url'): st.video(cont['url'])
                elif tv == 'upload' and cont.get('arquivo_video'): st.video(cont['arquivo_video'])
                else: st.info("Vídeo indisponível.")
            elif tipo == 'texto': st.markdown(cont.get('texto', ''))
            
            if cont.get('material_apoio'):
                st.download_button("📥 Baixar Material", data=cont['material_apoio'], file_name="material.pdf")
            
            st.markdown("---")
            if st.button("Concluir Aula", key=f"ok_{aula['id']}", type="primary"):
                ce.marcar_aula_concluida(usuario['id'], aula['id'])
                st.success("Concluída!"); time.sleep(0.5); st.rerun()

# --- ALUNO ---
def _aluno_cursos_disponiveis(usuario):
    cursos = ce.listar_cursos_disponiveis_para_usuario(usuario)
    if not cursos: st.info("Nada por aqui."); return
    cols = st.columns(3)
    for i, c in enumerate(cursos):
        with cols[i%3]:
            with st.container(border=True):
                st.markdown(f"**{c['titulo']}**")
                if st.button("Ver", key=f"vda_{c['id']}", use_container_width=True): navegar_para('detalhe', c)

def _aluno_meus_cursos(usuario):
    # Simplificado - mesma lógica visual
    _aluno_cursos_disponiveis(usuario)
