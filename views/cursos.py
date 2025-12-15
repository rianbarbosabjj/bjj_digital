"""
BJJ Digital - Sistema de Cursos (Versão Modernizada)
Integração com utils.py (Centralizado), Uploads, Editores e Design.
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import Optional, Dict, List

# Importa o motor centralizado (antigo courses_engine, agora utils)
import utils as ce 

# Importa a view de gerenciamento de aulas
import views.aulas as aulas_view 

# --- 1. CONFIGURAÇÃO DE CORES IGUAL AO APP.PY ---
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO = "#0e2d26"
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770"
    COR_BOTAO = "#078B6C" # Verde BJJ Digital
    COR_HOVER = "#FFD770" # Dourado

# ======================================================
# LÓGICAS DE CONSULTA DE PROGRESSO (Wrapper para UI)
# ======================================================

def obter_progresso_aula(user_id: str, curso_id: str, aula_id: str) -> bool:
    return ce.verificar_aula_concluida(user_id, aula_id)

def registrar_progresso_aula(user_id: str, curso_id: str, aula_id: str) -> int:
    ce.marcar_aula_concluida(user_id, aula_id) 
    inscricao_atualizada = ce.obter_inscricao(user_id, curso_id)
    if inscricao_atualizada:
        return inscricao_atualizada.get("progresso", 0)
    return 0

# ======================================================
# ESTILOS MODERNOS (CSS CORRIGIDO)
# ======================================================

def aplicar_estilos_cursos():
    """Aplica estilos modernos específicos para cursos."""
    
    # CSS usa chaves duplas {{ }} para evitar conflito com f-string
    st.markdown(f"""
    <style>
    /* CARDS */
    .curso-card-moderno {{
        background: linear-gradient(145deg, rgba(14, 45, 38, 0.9) 0%, rgba(9, 31, 26, 0.95) 100%);
        border: 1px solid rgba(255, 215, 112, 0.15);
        border-radius: 20px;
        padding: 1.5rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        position: relative;
        overflow: hidden;
        transition: transform 0.3s ease;
    }}
    .curso-card-moderno::before {{
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 4px;
        background: linear-gradient(90deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%);
    }}
    .curso-card-moderno:hover {{
        border-color: {COR_DESTAQUE};
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }}
    
    /* BADGES */
    .curso-badges {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0; }}
    .curso-badge {{
        padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
        border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.05);
    }}
    .curso-badge.gold {{ color: {COR_DESTAQUE}; border-color: {COR_DESTAQUE}; }}
    .curso-badge.green {{ color: {COR_BOTAO}; border-color: {COR_BOTAO}; }}
    
    /* BOTÕES */
    .stButton>button[kind="primary"], div.stButton > button[key^="btn_save"], div.stButton > button[key^="btn_create"] {{
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important;
        color: white !important; border: none !important;
    }}
    .stButton>button[kind="primary"]:hover, div.stButton > button[key^="btn_save"]:hover {{
        background: {COR_HOVER} !important; color: #0e2d26 !important;
    }}
    
    /* BOTÃO EXCLUIR */
    .stButton>button[key^="btn_delete_final"]:hover {{
        border-color: #ff4b4b !important; color: #ff4b4b !important;
        background: rgba(255, 75, 75, 0.1) !important;
    }}

    /* HEADER */
    .curso-header {{
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.8) 0%, rgba(9, 31, 26, 0.9) 100%);
        border-bottom: 1px solid rgba(255, 215, 112, 0.2);
        padding: 1.5rem; border-radius: 0 0 20px 20px; margin-bottom: 2rem;
    }}
    
    /* CUSTOM ICON */
    .curso-icon {{ font-size: 2.5rem; text-align: center; margin-bottom: 1rem; }}
    
    /* MATERIAL APOIO */
    .material-apoio-box {{
        margin-top: 1.5rem; padding: 1rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px; border: 1px solid rgba(255, 215, 112, 0.1);
    }}
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# LÓGICA DE NAVEGAÇÃO
# ======================================================

def navegar_para(view: str, curso: Optional[Dict] = None):
    st.session_state['cursos_view'] = view
    st.session_state['curso_selecionado'] = curso
    st.rerun()

def pagina_cursos(usuario: dict):
    aplicar_estilos_cursos()
    
    if 'cursos_view' not in st.session_state:
        st.session_state['cursos_view'] = 'lista'
        
    # Header
    st.markdown(f"""
    <div class="curso-header">
        <h1 style="margin:0; text-align:center; color:{COR_DESTAQUE};">🎓 BJJ DIGITAL CURSOS</h1>
        <p style="text-align:center; opacity:0.8;">Bem-vindo(a), <strong>{usuario.get('nome','').split()[0]}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Botão Voltar
    if st.session_state.get('cursos_view') != 'lista':
        if st.button("← Voltar à Lista", key="btn_back_list", type="secondary"):
            navegar_para('lista')
    else:
        if st.button("← Menu Principal", key="btn_back_home"):
            st.session_state.menu_selection = "Início"
            st.rerun()
            
    st.write("")

    # Router
    view = st.session_state.get('cursos_view')
    curso = st.session_state.get('curso_selecionado')
    tipo_user = usuario.get("tipo", "aluno")
    
    if view == 'lista':
        if tipo_user in ["admin", "professor"]:
            _interface_professor_moderna(usuario)
        else:
            _interface_aluno_moderna(usuario)
    elif view == 'detalhe' and curso:
        _exibir_detalhes_curso(curso, usuario)
    elif view == 'aulas' and curso:
        _pagina_aulas(curso, usuario)
    elif view == 'edicao' and curso and tipo_user in ["admin", "professor"]:
        _pagina_edicao_curso(curso, usuario)
    elif view == 'gerenciar_conteudo' and curso and tipo_user in ["admin", "professor"]:
        aulas_view.gerenciar_conteudo_curso(curso, usuario)
    else:
        st.session_state['cursos_view'] = 'lista'
        st.rerun()

# ======================================================
# VIEWS ESPECÍFICAS
# ======================================================

def _interface_professor_moderna(usuario):
    tab1, tab2, tab3 = st.tabs(["📘 Meus Cursos", "➕ Criar Novo", "📊 Dashboard"])
    with tab1: _professor_listar_cursos(usuario)
    with tab2: _pagina_criar_curso(usuario)
    with tab3: _professor_dashboard(usuario)

def _interface_aluno_moderna(usuario):
    tab1, tab2 = st.tabs(["🛒 Disponíveis", "🎓 Meus Cursos"])
    with tab1: _aluno_cursos_disponiveis(usuario)
    with tab2: _aluno_meus_cursos(usuario)

# --- CRIAÇÃO DE CURSO (SEM ST.FORM) ---
def _pagina_criar_curso(usuario):
    st.markdown("### 🚀 Criar Novo Curso")
    
    if "new_pago_toggle" not in st.session_state:
        st.session_state["new_pago_toggle"] = False
        
    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            titulo = st.text_input("Título *", key="new_titulo")
            desc = st.text_area("Descrição *", height=100, key="new_desc")
        with c2:
            mod = st.selectbox("Modalidade", ["EAD", "Presencial", "Híbrido"], key="new_mod")
            pub = st.selectbox("Público", ["geral", "equipe"], key="new_pub")
            eq = st.text_input("Nome da Equipe", key="new_eq") if pub == "equipe" else None

        # Multiselect de Editores com CPF
        st.markdown("#### 👥 Colaboração")
        users = ce.listar_todos_usuarios_para_selecao()
        # Cria mapa ID -> "Nome (CPF)"
        map_u = {u['id']: f"{u['nome']} (CPF: {u.get('cpf','N/A')})" for u in users}
        
        editores = st.multiselect(
            "Editores Colaboradores", 
            options=list(map_u.keys()), 
            format_func=lambda x: map_u.get(x,x), 
            key="new_editores",
            placeholder="Digite nome ou CPF..."
        )

        st.markdown("---")
        st.markdown("#### 💰 Financeiro")
        
        cf1, cf2 = st.columns(2)
        with cf1:
            # Toggle reativo (fora de st.form)
            pago = st.toggle("Curso Pago?", key="new_pago_toggle")
        with cf2:
            preco = st.number_input("Valor (R$)", min_value=0.0, disabled=not st.session_state["new_pago_toggle"], key="new_preco")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Botão salvar normal (não form_submit)
        if st.button("🚀 Criar Curso Agora", key="btn_create_course", use_container_width=True):
            if not titulo or not desc:
                st.error("Preencha título e descrição.")
            else:
                try:
                    ce.criar_curso(
                        usuario['id'], usuario.get('nome',''), titulo, desc, mod, pub, eq, 
                        pago, preco if pago else 0.0, 10, True, editores_ids=editores
                    )
                    st.success("Curso criado com sucesso!")
                    time.sleep(1)
                    navegar_para('lista')
                except Exception as e:
                    st.error(f"Erro: {e}")

# --- EDIÇÃO DE CURSO (SEM ST.FORM + ZONA DE PERIGO) ---
def _pagina_edicao_curso(curso, usuario):
    st.markdown(f"### ✏️ Editando: {curso.get('titulo')}")
    
    # Verifica permissão de editor
    if usuario['id'] in curso.get('editores_ids', []):
        st.info("ℹ️ Você é um **Editor Colaborador** neste curso.")

    k_pago = f"edit_pago_{curso['id']}"
    if k_pago not in st.session_state:
        st.session_state[k_pago] = curso.get('pago', False)
        
    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            nt = st.text_input("Título", value=curso.get('titulo',''), key=f"et_{curso['id']}")
            nd = st.text_area("Descrição", value=curso.get('descricao',''), height=100, key=f"ed_{curso['id']}")
        with c2:
            nm = st.selectbox("Modalidade", ["EAD", "Presencial", "Híbrido"], index=["EAD", "Presencial", "Híbrido"].index(curso.get('modalidade','EAD')), key=f"em_{curso['id']}")
            npub = st.selectbox("Público", ["geral", "equipe"], index=0 if curso.get('publico')=='geral' else 1, key=f"epub_{curso['id']}")
            neq = st.text_input("Equipe", value=curso.get('equipe_destino',''), key=f"eeq_{curso['id']}") if npub == 'equipe' else None

        # Editores
        st.markdown("#### 👥 Colaboração")
        users = ce.listar_todos_usuarios_para_selecao()
        map_u = {u['id']: f"{u['nome']} (CPF: {u.get('cpf','N/A')})" for u in users}
        
        # Filtra IDs válidos
        atuais = [uid for uid in curso.get('editores_ids', []) if uid in map_u]
        
        ne = st.multiselect(
            "Editores", list(map_u.keys()), default=atuais, 
            format_func=lambda x: map_u.get(x,x), key=f"ee_{curso['id']}"
        )
        
        st.markdown("---")
        
        cp1, cp2 = st.columns(2)
        with cp1:
            npago = st.toggle("Pago?", key=k_pago)
        with cp2:
            npreco = st.number_input("Valor", value=float(curso.get('preco',0)), disabled=not st.session_state[k_pago], key=f"epr_{curso['id']}")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("💾 Salvar Alterações", key=f"btn_save_{curso['id']}", use_container_width=True):
            dados = {
                "titulo": nt, "descricao": nd, "modalidade": nm, "publico": npub,
                "equipe_destino": neq, "editores_ids": ne, "pago": npago, 
                "preco": npreco if npago else 0.0, "atualizado_em": datetime.now()
            }
            if ce.editar_curso(curso['id'], dados):
                st.success("Atualizado!")
                time.sleep(1)
                navegar_para('detalhe', dados)
            else:
                st.error("Erro ao salvar.")

    # ZONA DE PERIGO
    is_owner = curso.get('professor_id') == usuario['id']
    is_admin = usuario.get('tipo') == 'admin'
    
    if is_owner or is_admin:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🗑️ Zona de Perigo"):
            st.warning("Atenção: A exclusão apaga todas as aulas e inscrições.")
            confirm = st.checkbox("Confirmo que desejo excluir.", key=f"del_{curso['id']}")
            
            if st.button("Excluir Curso Definitivamente", type="secondary", disabled=not confirm, key=f"btn_delete_final_{curso['id']}"):
                with st.spinner("Excluindo..."):
                    if ce.excluir_curso(curso['id']):
                        st.success("Curso excluído.")
                        time.sleep(1)
                        st.session_state['curso_selecionado'] = None
                        navegar_para('lista')
                    else:
                        st.error("Erro ao excluir. Verifique logs.")

# --- LISTAGEM DO PROFESSOR ---
def _professor_listar_cursos(usuario):
    cursos = ce.listar_cursos_do_professor(usuario['id'])
    if not cursos:
        st.info("Nenhum curso encontrado.")
        return
        
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
                <p style="opacity:0.7; font-size:0.9em;">{c.get('descricao','')[:80]}...</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("Editar", key=f"edt_{c['id']}", use_container_width=True): navegar_para('edicao', c)
            if c2.button("Ver", key=f"ver_{c['id']}", use_container_width=True): navegar_para('detalhe', c)

# --- PLAYER DE AULAS (COM UPLOAD/PDF) ---
def _pagina_aulas(curso, usuario):
    st.subheader(f"📺 {curso.get('titulo')}")
    modulos = ce.listar_modulos_e_aulas(curso['id'])
    
    if not modulos:
        st.warning("Sem aulas.")
        return

    c_video, c_lista = st.columns([3, 1])
    
    # Init aula atual
    if 'aula_atual' not in st.session_state:
        if modulos and modulos[0]['aulas']:
            st.session_state['aula_atual'] = modulos[0]['aulas'][0]
            
    aula = st.session_state.get('aula_atual')
    
    with c_lista:
        st.markdown("### Módulos")
        for m in modulos:
            with st.expander(m['titulo'], expanded=True):
                for a in m['aulas']:
                    concluida = ce.verificar_aula_concluida(usuario['id'], a['id'])
                    icon = "✅" if concluida else "⚪"
                    lbl = f"{icon} {a['titulo']}"
                    if st.button(lbl, key=f"nav_a_{a['id']}", use_container_width=True, type="secondary"):
                        st.session_state['aula_atual'] = a
                        st.rerun()

    with c_video:
        if aula:
            st.markdown(f"#### {aula['titulo']}")
            
            cont = aula.get('conteudo', {})
            tipo = aula.get('tipo')
            
            # -- VÍDEO --
            if tipo == 'video':
                t_vid = cont.get('tipo_video', 'link')
                if t_vid == 'link':
                    if cont.get('url'): st.video(cont['url'])
                    else: st.info("Link indisponível.")
                elif t_vid == 'upload':
                    if cont.get('arquivo_video'): st.video(cont['arquivo_video'])
                    else: st.info("Vídeo não encontrado.")
            
            # -- TEXTO --
            elif tipo == 'texto':
                st.markdown(cont.get('texto', ''))
            
            # -- MATERIAL APOIO --
            if cont.get('material_apoio'):
                st.markdown("<div class='material-apoio-box'>", unsafe_allow_html=True)
                st.markdown("#### 📎 Material de Apoio")
                st.download_button(
                    label=f"📥 Baixar {cont.get('nome_arquivo_pdf', 'Arquivo.pdf')}",
                    data=cont['material_apoio'], # Precisa ser bytes ou path
                    file_name=cont.get('nome_arquivo_pdf', 'material.pdf'),
                    mime="application/pdf",
                    key=f"dl_{aula['id']}"
                )
                st.markdown("</div>", unsafe_allow_html=True)
                
            st.markdown("---")
            # Conclusão
            if st.button("✅ Marcar como Concluída", key=f"conc_{aula['id']}", type="primary"):
                ce.marcar_aula_concluida(usuario['id'], aula['id'])
                st.success("Aula concluída!")
                time.sleep(0.5)
                st.rerun()

# --- DETALHES ---
def _exibir_detalhes_curso(curso, usuario):
    st.title(curso.get('titulo'))
    
    # Verifica permissão
    is_owner = curso.get('professor_id') == usuario['id']
    is_editor = usuario['id'] in curso.get('editores_ids', [])
    is_admin = usuario.get('tipo') == 'admin'
    
    if is_owner or is_editor or is_admin:
        c1, c2 = st.columns(2)
        if c1.button("✏️ Editar Curso", use_container_width=True): navegar_para('edicao', curso)
        if c2.button("➕ Gerenciar Aulas", type="primary", use_container_width=True): navegar_para('gerenciar_conteudo', curso)
    
    st.write(curso.get('descricao'))
    
    inscricao = ce.obter_inscricao(usuario['id'], curso['id'])
    if inscricao or is_owner or is_editor or is_admin:
        if st.button("🎬 Acessar Aulas", type="primary"): navegar_para('aulas', curso)
    else:
        lbl = "Inscrever-se Grátis"
        if curso.get('pago'): lbl = f"Comprar por R$ {curso.get('preco')}"
        
        if st.button(lbl, type="primary"):
            ce.inscrever_usuario_em_curso(usuario['id'], curso['id'])
            st.success("Inscrito com sucesso!")
            st.rerun()

# --- DASHBOARD VAZIO POR ENQUANTO ---
def _professor_dashboard(usuario):
    st.info("Painel estatístico em desenvolvimento.")

# --- ALUNO ---
def _aluno_cursos_disponiveis(usuario):
    cursos = ce.listar_cursos_disponiveis_para_usuario(usuario)
    if not cursos:
        st.info("Nenhum curso disponível.")
        return
        
    cols = st.columns(3)
    for i, c in enumerate(cursos):
        with cols[i%3]:
            with st.container(border=True):
                st.markdown(f"**{c['titulo']}**")
                if st.button("Ver Detalhes", key=f"vd_{c['id']}", use_container_width=True):
                    navegar_para('detalhe', c)

def _aluno_meus_cursos(usuario):
    # Lógica similar, filtra inscritos
    _aluno_cursos_disponiveis(usuario) # Placeholder
