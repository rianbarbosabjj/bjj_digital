"""
BJJ Digital - Sistema de Cursos (Versão Modernizada)
Integração com aulas, design atualizado, Colaboração (CPF) e Uploads.
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime, MINYEAR
from typing import Optional, Dict, List
import plotly.express as px

# Importações internas
from database import get_db

# Importa o módulo completo com alias para chamadas genéricas
import utils as ce 

# Importa a nova view de gerenciamento de aulas
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
    """Função wrapper para verificar se a aula está concluída, usando o Engine."""
    return ce.verificar_aula_concluida(user_id, aula_id)

def registrar_progresso_aula(user_id: str, curso_id: str, aula_id: str) -> int:
    """Marca a aula como concluída e retorna o novo progresso total."""
    ce.marcar_aula_concluida(user_id, aula_id) 
    inscricao_atualizada = ce.obter_inscricao(user_id, curso_id)
    
    if inscricao_atualizada:
        return inscricao_atualizada.get("progresso", 0)
    else:
        return 0

# ======================================================
# ESTILOS MODERNOS PARA CURSOS
# ======================================================

def aplicar_estilos_cursos():
    """Aplica estilos modernos específicos para cursos, ALINHADO COM APP.PY"""
    
    st.markdown(f"""
    <style>
    /* CARDS DE CURSO MODERNOS */
    .curso-card-moderno {{
        background: linear-gradient(145deg, rgba(14, 45, 38, 0.9) 0%, rgba(9, 31, 26, 0.95) 100%);
        border: 1px solid rgba(255, 215, 112, 0.15);
        border-radius: 20px;
        padding: 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        height: 100%;
        display: flex;
        flex-direction: column;
        position: relative;
        overflow: hidden;
    }}
    
    .curso-card-moderno::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%);
        border-radius: 20px 20px 0 0;
    }}
    
    .curso-card-moderno:hover {{
        border-color: {COR_DESTAQUE};
        transform: translateY(-8px);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
    }}
    
    .curso-icon {{
        font-size: 2.5rem;
        margin-bottom: 1rem;
        text-align: center;
        background: linear-gradient(135deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    
    /* BADGES */
    .curso-badges {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0; }}
    .curso-badge {{
        padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600;
        background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2);
    }}
    .curso-badge.gold {{ color: {COR_DESTAQUE}; border-color: {COR_DESTAQUE}; }}
    .curso-badge.green {{ color: {COR_BOTAO}; border-color: {COR_BOTAO}; }}
    .curso-badge.blue {{ color: #60A5FA; border-color: #60A5FA; }}
    
    /* PROGRESS BAR */
    .curso-progress {{ background: rgba(255, 255, 255, 0.05); border-radius: 10px; height: 10px; overflow: hidden; margin: 0.75rem 0; }}
    .curso-progress-fill {{ height: 100%; background: linear-gradient(90deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%); border-radius: 10px; }}
    
    /* AULA COMPLETA */
    .aula-completa {{
        background-color: rgba(7, 139, 108, 0.1); border-left: 5px solid {COR_BOTAO};
        padding: 0.5rem; border-radius: 8px; color: #34D399; margin-bottom: 0.5rem; display: flex; align-items: center;
    }}
    
    /* AREA MATERIAL DE APOIO */
    .material-apoio-box {{
        margin-top: 1.5rem; padding: 1rem;
        background: rgba(255, 255, 255, 0.05); border-radius: 12px; border: 1px solid rgba(255, 215, 112, 0.1);
    }}

    /* BOTÕES */
    div.stButton > button, div.stFormSubmitButton > button {{ 
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important; 
        color: white !important; border: 1px solid rgba(255,255,255,0.1) !important; 
        padding: 0.6em 1.5em !important; font-weight: 600 !important; border-radius: 8px !important; 
        transition: all 0.3s ease !important;
    }}
    div.stButton > button:hover {{ 
        background: {COR_HOVER} !important; color: #0e2d26 !important; 
        transform: translateY(-2px); box-shadow: 0 4px 12px rgba(255, 215, 112, 0.3);
    }}
    
    .stButton>button[kind="secondary"] {{ background: transparent !important; color: {COR_DESTAQUE} !important; border: 1px solid {COR_DESTAQUE} !important; }}
    .stButton>button[kind="secondary"]:hover {{ background: {COR_DESTAQUE} !important; color: #0e2d26 !important; transform: translateY(-2px); }}
    
    .stButton>button[key^="btn_delete_final"]:hover {{ border-color: #ff4b4b !important; color: #ff4b4b !important; background: rgba(255, 75, 75, 0.1) !important; }}

    /* HEADER */
    .curso-header {{
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.8) 0%, rgba(9, 31, 26, 0.9) 100%);
        border-bottom: 1px solid rgba(255, 215, 112, 0.2); padding: 1.5rem; border-radius: 0 0 20px 20px; margin-bottom: 2rem;
    }}
    
    /* STATS */
    .stats-card-moderno {{ background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; padding: 1.5rem; text-align: center; }}
    .stats-value-moderno {{ font-size: 2.5rem; font-weight: 700; color: {COR_DESTAQUE}; margin: 0.5rem 0; }}
    .stats-label-moderno {{ color: rgba(255, 255, 255, 0.7); font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }}
    
    /* EMPTY STATE */
    .empty-state {{ text-align: center; padding: 4rem 2rem; border-radius: 20px; background: rgba(255,255,255,0.02); border: 2px dashed rgba(255,215,112,0.2); }}
    .empty-state-icon {{ font-size: 4rem; margin-bottom: 1rem; opacity: 0.5; }}
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# LÓGICAS DE ROTEAMENTO E NAVEGAÇÃO
# ======================================================

def navegar_para(view: str, curso: Optional[Dict] = None):
    st.session_state['cursos_view'] = view
    st.session_state['curso_selecionado'] = curso
    st.rerun()

def pagina_cursos(usuario: dict):
    aplicar_estilos_cursos()
    
    if 'cursos_view' not in st.session_state:
        st.session_state['cursos_view'] = 'lista'
        
    st.markdown(f"""
    <div class="curso-header">
        <h1 style="margin:0; text-align:center; color:{COR_DESTAQUE};">🎓 BJJ DIGITAL CURSOS</h1>
        <p style="text-align:center; opacity:0.8;">Bem-vindo, <strong>{usuario.get('nome','').split()[0]}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.get('cursos_view') != 'lista':
        if st.button("← Voltar à Lista", key="btn_back_list", type="secondary"):
            navegar_para('lista')
    else:
        if st.button("← Menu Principal", key="btn_back_home"):
            st.session_state.menu_selection = "Início"
            st.rerun()
    st.write("")

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

# --- CRIAÇÃO DE CURSO (COMPLETA E IGUAL À EDIÇÃO) ---
def _pagina_criar_curso(usuario):
    st.markdown("### 🚀 Criar Novo Curso")
    
    if "new_pago_toggle" not in st.session_state:
        st.session_state["new_pago_toggle"] = False
        
    with st.container(border=True):
        st.markdown("### 📝 Informações Básicas")
        col1, col2 = st.columns([2, 1])
        with col1:
            titulo = st.text_input("Título *", key="new_titulo")
            desc = st.text_area("Descrição Detalhada *", height=100, key="new_desc")
        with col2:
            mod = st.selectbox("Modalidade", ["EAD", "Presencial", "Híbrido"], key="new_mod")
            pub = st.selectbox("Público Alvo", ["geral", "equipe"], key="new_pub")
            eq = st.text_input("Nome da Equipe", key="new_eq") if pub == "equipe" else None

        # Multiselect de Editores
        st.markdown("### 👥 Colaboração")
        users = ce.listar_todos_usuarios_para_selecao()
        map_u = {u['id']: f"{u['nome']} (CPF: {u.get('cpf','N/A')})" for u in users}
        
        editores = st.multiselect(
            "Editores Colaboradores", 
            options=list(map_u.keys()), 
            format_func=lambda x: map_u.get(x,x), 
            key="new_editores",
            placeholder="Digite nome ou CPF..."
        )

        st.markdown("---")
        st.markdown("### ⚙️ Configurações")
        c_conf1, c_conf2 = st.columns(2)
        with c_conf1:
            cert_auto = st.checkbox("Emitir certificado automaticamente", value=True, key="new_cert")
        with c_conf2:
            duracao = st.text_input("Duração Estimada", placeholder="Ex: 10 horas", key="new_duracao")
            nivel = st.selectbox("Nível", ["Iniciante", "Intermediário", "Avançado", "Todos os Níveis"], key="new_nivel")

        st.markdown("---")
        st.markdown("### 💰 Configurações Financeiras")
        
        cf1, cf2, cf3 = st.columns([1, 1, 1])
        with cf1:
            pago = st.toggle("Curso Pago?", key="new_pago_toggle")
        with cf2:
            preco = st.number_input("Valor (R$)", min_value=0.0, disabled=not st.session_state["new_pago_toggle"], key="new_preco")
        with cf3:
            is_admin = usuario.get("tipo") == "admin"
            split = 10
            if is_admin and pago:
                split = st.slider("Taxa Plataforma (%)", 0, 100, value=10, key="new_split")
            elif pago:
                st.caption(f"Taxa Plataforma: {split}%")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        c_btn1, c_btn2 = st.columns([1, 3])
        with c_btn1:
            if st.button("❌ Limpar", key="btn_clear_create", type="secondary"):
                st.rerun()
                
        with c_btn2:
            if st.button("🚀 Criar Curso Agora", key="btn_create_course", use_container_width=True, type="primary"):
                if not titulo or not desc:
                    st.error("Preencha título e descrição.")
                else:
                    try:
                        ce.criar_curso(
                            usuario['id'], usuario.get('nome',''), titulo, desc, mod, pub, eq, 
                            pago, preco if pago else 0.0, split, cert_auto, 
                            duracao_estimada=duracao, nivel=nivel, editores_ids=editores
                        )
                        st.success("Curso criado com sucesso!")
                        st.balloons()
                        time.sleep(1)
                        navegar_para('lista')
                    except Exception as e:
                        st.error(f"Erro: {e}")

# --- EDIÇÃO DE CURSO (SEM ST.FORM) ---
def _pagina_edicao_curso(curso, usuario):
    st.markdown(f"### ✏️ Editando: {curso.get('titulo')}")
    
    if usuario['id'] in curso.get('editores_ids', []):
        st.info("ℹ️ Você é um **Editor Colaborador**.")

    k_pago = f"edit_pago_{curso['id']}"
    if k_pago not in st.session_state:
        st.session_state[k_pago] = curso.get('pago', False)
        
    with st.container(border=True):
        st.markdown("### 📝 Informações Básicas")
        c1, c2 = st.columns([2, 1])
        with c1:
            nt = st.text_input("Título", value=curso.get('titulo',''), key=f"et_{curso['id']}")
            nd = st.text_area("Descrição", value=curso.get('descricao',''), height=100, key=f"ed_{curso['id']}")
        with c2:
            nm = st.selectbox("Modalidade", ["EAD", "Presencial", "Híbrido"], index=["EAD", "Presencial", "Híbrido"].index(curso.get('modalidade','EAD')), key=f"em_{curso['id']}")
            npub = st.selectbox("Público", ["geral", "equipe"], index=0 if curso.get('publico')=='geral' else 1, key=f"epub_{curso['id']}")
            neq = st.text_input("Equipe", value=curso.get('equipe_destino',''), key=f"eeq_{curso['id']}") if npub == 'equipe' else None

        st.markdown("### 👥 Colaboração")
        users = ce.listar_todos_usuarios_para_selecao()
        map_u = {u['id']: f"{u['nome']} (CPF: {u.get('cpf','N/A')})" for u in users}
        atuais = [uid for uid in curso.get('editores_ids', []) if uid in map_u]
        ne = st.multiselect("Editores", list(map_u.keys()), default=atuais, format_func=lambda x: map_u.get(x,x), key=f"ee_{curso['id']}")
        
        st.markdown("---")
        st.markdown("### ⚙️ Configurações")
        cc1, cc2 = st.columns(2)
        with cc1:
            ncert = st.checkbox("Certificado Automático", value=curso.get('certificado_automatico', True), key=f"ec_{curso['id']}")
            nativo = st.checkbox("Curso Ativo", value=curso.get('ativo', True), key=f"ea_{curso['id']}")
        with cc2:
            nduracao = st.text_input("Duração", value=curso.get('duracao_estimada',''), key=f"edur_{curso['id']}")
            nivels = ["Iniciante", "Intermediário", "Avançado", "Todos os Níveis"]
            idx_n = nivels.index(curso.get('nivel', "Todos os Níveis")) if curso.get('nivel') in nivels else 3
            nnivel = st.selectbox("Nível", nivels, index=idx_n, key=f"eniv_{curso['id']}")

        st.markdown("---")
        st.markdown("### 💰 Financeiro")
        cp1, cp2, cp3 = st.columns([1,1,1])
        with cp1:
            npago = st.toggle("Pago?", key=k_pago)
        with cp2:
            npreco = st.number_input("Valor", value=float(curso.get('preco',0)), disabled=not st.session_state[k_pago], key=f"ep_{curso['id']}")
        with cp3:
            nsplit = curso.get('split_custom', 10)
            if usuario.get('tipo') == 'admin' and npago:
                nsplit = st.slider("Taxa (%)", 0, 100, value=nsplit, key=f"esp_{curso['id']}")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        c_act1, c_act2 = st.columns([1, 3])
        with c_act1:
             if st.button("❌ Cancelar", key=f"btn_canc_{curso['id']}", type="secondary"): navegar_para('lista')
        with c_act2:
            if st.button("💾 Salvar Alterações", type="primary", key=f"btn_save_{curso['id']}", use_container_width=True):
                dados = {
                    "titulo": nt, "descricao": nd, "modalidade": nm, "publico": npub,
                    "equipe_destino": neq, "editores_ids": ne, "pago": npago, 
                    "preco": npreco if npago else 0, "split_custom": nsplit,
                    "certificado_automatico": ncert, "ativo": nativo,
                    "duracao_estimada": nduracao, "nivel": nnivel,
                    "atualizado_em": datetime.now()
                }
                if ce.editar_curso(curso['id'], dados):
                    st.success("Atualizado!")
                    time.sleep(1)
                    navegar_para('detalhe', dados)
                else:
                    st.error("Erro ao salvar.")

    # ZONA DE PERIGO
    if usuario['id'] == curso.get('professor_id') or usuario.get('tipo') == 'admin':
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🗑️ Zona de Perigo"):
            st.warning("Atenção: A exclusão apaga todas as aulas e inscrições.")
            confirm = st.checkbox("Confirmar exclusão", key=f"del_{curso['id']}")
            if st.button("Excluir Definitivamente", type="secondary", disabled=not confirm, key=f"btn_delete_final_{curso['id']}"):
                if ce.excluir_curso(curso['id']):
                    st.success("Excluído.")
                    time.sleep(1)
                    st.session_state['curso_selecionado'] = None
                    navegar_para('lista')
                else:
                    st.error("Erro ao excluir.")

# --- LISTAGEM PROFESSOR ---
def _professor_listar_cursos(usuario):
    cursos = ce.listar_cursos_do_professor(usuario['id'])
    if not cursos:
        st.info("Nenhum curso encontrado.")
        return
        
    cols = st.columns(3)
    for i, c in enumerate(cursos):
        with cols[i%3]:
            ativo = c.get('ativo', True)
            icon = "🎓" if ativo else "⏸️"
            role = f"<span class='curso-badge blue'>Editor</span>" if c.get('papel') == 'Editor' else ""
            
            st.markdown(f"""
            <div class="curso-card-moderno">
                <div style="text-align:right;">{role}</div>
                <div class="curso-icon">{icon}</div>
                <h4>{c.get('titulo')}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("Editar", key=f"ed_{c['id']}", use_container_width=True): navegar_para('edicao', c)
            if c2.button("Ver", key=f"ve_{c['id']}", use_container_width=True): navegar_para('detalhe', c)

# --- DETALHES ---
def _exibir_detalhes_curso(curso, usuario):
    st.title(curso.get('titulo'))
    
    can_edit = (usuario['id'] == curso.get('professor_id')) or \
               (usuario['id'] in curso.get('editores_ids', [])) or \
               (usuario.get('tipo') == 'admin')
                  
    if can_edit:
        c1, c2 = st.columns(2)
        if c1.button("✏️ Editar Curso", use_container_width=True): navegar_para('edicao', curso)
        if c2.button("➕ Gerenciar Conteúdo", type="primary", use_container_width=True): navegar_para('gerenciar_conteudo', curso)
    
    st.markdown("### Sobre este curso")
    st.write(curso.get('descricao'))
    
    # Detalhes técnicos
    c_det1, c_det2, c_det3 = st.columns(3)
    c_det1.metric("Nível", curso.get('nivel', 'Geral'))
    c_det2.metric("Duração", curso.get('duracao_estimada', '-'))
    c_det3.metric("Certificado", "Sim" if curso.get('certificado_automatico') else "Não")

    inscricao = ce.obter_inscricao(usuario['id'], curso['id'])
    
    st.markdown("<br>", unsafe_allow_html=True)
    if inscricao or can_edit:
        if st.button("🎬 Acessar Aulas", type="primary", use_container_width=True): navegar_para('aulas', curso)
    else:
        lbl = "Inscrever-se Grátis"
        if curso.get('pago'): lbl = f"Comprar por R$ {curso.get('preco'):.2f}"
        if st.button(lbl, type="primary", use_container_width=True):
            ce.inscrever_usuario_em_curso(usuario['id'], curso['id'])
            st.success("Inscrito!")
            time.sleep(1)
            navegar_para('aulas', curso)

# --- PLAYER AULAS ---
def _pagina_aulas(curso, usuario):
    st.subheader(f"📺 {curso.get('titulo')}")
    modulos = ce.listar_modulos_e_aulas(curso['id'])
    
    if not modulos:
        st.warning("Este curso ainda não tem aulas.")
        return

    c_video, c_lista = st.columns([3, 1])
    
    if 'aula_atual' not in st.session_state:
        if modulos and modulos[0]['aulas']:
            st.session_state['aula_atual'] = modulos[0]['aulas'][0]
            
    aula = st.session_state.get('aula_atual')
    
    with c_lista:
        st.markdown("### Conteúdo")
        for m in modulos:
            with st.expander(m['titulo'], expanded=True):
                for a in m['aulas']:
                    concluida = ce.verificar_aula_concluida(usuario['id'], a['id'])
                    icon = "✅" if concluida else "⭕"
                    if st.button(f"{icon} {a['titulo']}", key=f"nav_{a['id']}", use_container_width=True):
                        st.session_state['aula_atual'] = a
                        st.rerun()

    with c_video:
        if aula:
            st.markdown(f"#### {aula['titulo']}")
            cont = aula.get('conteudo', {})
            tipo = aula.get('tipo')
            
            if tipo == 'video':
                t_vid = cont.get('tipo_video', 'link')
                if t_vid == 'link' and cont.get('url'): st.video(cont['url'])
                elif t_vid == 'upload' and cont.get('arquivo_video'): st.video(cont['arquivo_video'])
                else: st.info("Vídeo indisponível.")
            elif tipo == 'texto':
                st.markdown(cont.get('texto', ''))
                
            if cont.get('material_apoio'):
                st.markdown("<div class='material-apoio-box'>", unsafe_allow_html=True)
                st.markdown("#### 📎 Material de Apoio")
                st.download_button(
                    label=f"📥 Baixar {cont.get('nome_arquivo_pdf', 'Arquivo')}",
                    data=cont['material_apoio'],
                    file_name=cont.get('nome_arquivo_pdf', 'material.pdf'),
                    mime="application/pdf"
                )
                st.markdown("</div>", unsafe_allow_html=True)
                
            st.markdown("---")
            if st.button("Concluir Aula", key=f"conc_{aula['id']}", type="primary"):
                ce.marcar_aula_concluida(usuario['id'], aula['id'])
                st.success("Concluída!")
                time.sleep(0.5)
                st.rerun()

# --- ALUNO / DASHBOARD ---
def _professor_dashboard(usuario): st.info("Painel em desenvolvimento.")

def _aluno_cursos_disponiveis(usuario):
    cursos = ce.listar_cursos_disponiveis_para_usuario(usuario)
    if not cursos: st.info("Nenhum curso disponível."); return
    cols = st.columns(3)
    for i, c in enumerate(cursos):
        with cols[i%3]:
            st.markdown(f"**{c['titulo']}**")
            if st.button("Ver Detalhes", key=f"vd_{c['id']}"): navegar_para('detalhe', c)

def _aluno_meus_cursos(usuario): _aluno_cursos_disponiveis(usuario)
