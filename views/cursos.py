"""
BJJ Digital - Sistema de Cursos (Versão Modernizada & Visual Premium)
Integração com utils.py, Uploads, Editores (Busca), Design Rico e Preços nos Cards.
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
    """Aplica o CSS completo e bonito novamente."""
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
        top: 0; left: 0; right: 0; height: 4px;
        background: linear-gradient(90deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%);
    }}
    
    .curso-card-moderno:hover {{
        border-color: {COR_DESTAQUE};
        transform: translateY(-8px);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
    }}
    
    .curso-icon {{
        font-size: 2.5rem; margin-bottom: 1rem; text-align: center;
        background: linear-gradient(135deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
    
    /* BADGES */
    .curso-badges {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0; }}
    .curso-badge {{
        padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600;
        background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2);
    }}
    .curso-badge.gold {{ background: rgba(255, 215, 112, 0.15); border-color: rgba(255, 215, 112, 0.3); color: {COR_DESTAQUE}; }}
    .curso-badge.green {{ background: rgba(7, 139, 108, 0.15); border-color: rgba(7, 139, 108, 0.3); color: {COR_BOTAO}; }}
    .curso-badge.blue {{ background: rgba(59, 130, 246, 0.15); border-color: rgba(59, 130, 246, 0.3); color: #60A5FA; }}
    
    /* PROGRESSO */
    .curso-progress {{ background: rgba(255, 255, 255, 0.05); border-radius: 10px; height: 10px; overflow: hidden; margin: 0.75rem 0; }}
    .curso-progress-fill {{ height: 100%; background: linear-gradient(90deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%); border-radius: 10px; }}
    
    /* DETALHES */
    .detalhes-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0 2rem 0; }}
    .detalhe-card {{
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid rgba(255, 215, 112, 0.15); border-radius: 16px; padding: 1.2rem;
        display: flex; align-items: center; backdrop-filter: blur(10px); transition: transform 0.3s ease;
    }}
    .detalhe-card:hover {{ border-color: rgba(255, 215, 112, 0.4); transform: translateY(-3px); }}
    .detalhe-icon {{ font-size: 2.2rem; margin-right: 1rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)); }}
    .detalhe-info {{ display: flex; flex-direction: column; }}
    .detalhe-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7; margin-bottom: 0.2rem; }}
    .detalhe-value {{ font-size: 1.1rem; font-weight: 700; color: white; }}

    /* MATERIAL APOIO */
    .material-apoio-box {{
        margin-top: 1.5rem; padding: 1rem;
        background: rgba(255, 255, 255, 0.05); border-radius: 12px; border: 1px solid rgba(255, 215, 112, 0.1);
    }}

    /* BOTÕES CUSTOMIZADOS */
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
# COMPONENTE DE SELEÇÃO DE EDITORES
# ======================================================
def renderizar_seletor_editores(chave_unica, ids_iniciais=[]):
    """Interface Busca -> Adiciona -> Lista para gerenciar editores."""
    session_key = f"lista_editores_{chave_unica}"
    if session_key not in st.session_state:
        st.session_state[session_key] = ids_iniciais.copy()

    st.markdown("###### 👥 Gerenciar Editores Colaboradores")
    with st.container(border=True):
        c_busca1, c_busca2 = st.columns([3, 1])
        with c_busca1:
            termo_busca = st.text_input("Buscar por Nome ou CPF", placeholder="Digite para buscar...", key=f"search_{chave_unica}")
        with c_busca2:
            st.write("") 
            st.write("") 
        
        todos_users = ce.listar_todos_usuarios_para_selecao()
        
        opcoes_filtradas = []
        if termo_busca:
            termo = termo_busca.lower()
            opcoes_filtradas = [
                u for u in todos_users 
                if termo in u['nome'].lower() or termo in str(u.get('cpf',''))
            ]

        if termo_busca and not opcoes_filtradas:
            st.warning("Nenhum usuário encontrado.")
        
        c_sel1, c_sel2 = st.columns([3, 1])
        with c_sel1:
            usuario_selecionado = st.selectbox(
                "Resultados da Busca",
                options=opcoes_filtradas,
                format_func=lambda x: f"{x['nome']} (CPF: {x.get('cpf','N/A')})",
                key=f"select_{chave_unica}",
                placeholder="Selecione um professor...",
                index=None
            )
        with c_sel2:
            st.write("")
            st.write("")
            if st.button("➕ Adicionar", key=f"btn_add_{chave_unica}", type="primary"):
                if usuario_selecionado:
                    if usuario_selecionado['id'] not in st.session_state[session_key]:
                        st.session_state[session_key].append(usuario_selecionado['id'])
                        st.rerun()
                    else:
                        st.warning("Já adicionado.")

        st.markdown("---")
        st.markdown(f"**Editores Selecionados ({len(st.session_state[session_key])})**")
        
        if not st.session_state[session_key]:
            st.caption("Nenhum editor adicional.")
        else:
            mapa_users = {u['id']: u for u in todos_users}
            for uid in st.session_state[session_key]:
                dados_user = mapa_users.get(uid, {'nome': 'Usuário Desconhecido', 'cpf': '?'})
                col_info, col_del = st.columns([4, 1])
                with col_info:
                    st.info(f"👤 **{dados_user['nome']}**\n\nCPF: {dados_user.get('cpf','N/A')}")
                with col_del:
                    st.write("")
                    if st.button("🗑️", key=f"rem_{uid}_{chave_unica}"):
                        st.session_state[session_key].remove(uid)
                        st.rerun()

    return st.session_state[session_key]

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
    with tab3: _professor_dashboard(usuario)

def _interface_aluno_moderna(usuario):
    tab1, tab2 = st.tabs(["🛒 Disponíveis", "🎓 Meus Cursos"])
    with tab1: _aluno_cursos_disponiveis(usuario)
    with tab2: _aluno_meus_cursos(usuario)

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

        # Colaboração
        editores_selecionados = renderizar_seletor_editores(chave_unica="criar", ids_iniciais=[])

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
        
        c_btn1, c_btn2 = st.columns([1, 3])
        with c_btn1:
            if st.button("❌ Limpar", key="btn_clear_create", type="secondary"):
                if "lista_editores_criar" in st.session_state: del st.session_state["lista_editores_criar"]
                st.rerun()
                
        with c_btn2:
            if st.button("🚀 Criar Curso", key="btn_create_course", use_container_width=True, type="primary"):
                if not titulo or not desc: st.error("Preencha título e descrição.")
                else:
                    ce.criar_curso(usuario['id'], usuario.get('nome',''), titulo, desc, mod, pub, eq, pago, preco if pago else 0.0, split, cert, dur, niv, editores_selecionados)
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

        # Colaboração
        editores_selecionados = renderizar_seletor_editores(
            chave_unica=f"editar_{curso['id']}", 
            ids_iniciais=curso.get('editores_ids', [])
        )

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
            dados = {"titulo": nt, "descricao": nd, "modalidade": nm, "publico": npub, "equipe_destino": neq, "editores_ids": editores_selecionados, "pago": npago, "preco": npr, "certificado_automatico": ncert, "ativo": natv, "duracao_estimada": ndur, "nivel": nniv, "atualizado_em": datetime.now()}
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

# --- LISTAGEM PROFESSOR (COM PREÇO) ---
def _professor_listar_cursos(usuario):
    cursos = ce.listar_cursos_do_professor(usuario['id'])
    if not cursos: st.info("Sem cursos."); return
    cols = st.columns(3)
    for i, c in enumerate(cursos):
        with cols[i%3]:
            # Dados Card
            ativo = c.get('ativo', True)
            icon = "🎓" if ativo else "⏸️"
            role = f"<span class='curso-badge blue'>✏️ Editor</span>" if c.get('papel') == 'Editor' else ""
            
            # Lógica do Preço
            if c.get('pago'):
                txt_preco = f"💰 R$ {c.get('preco', 0):.2f}"
                cor_preco = "gold"
            else:
                txt_preco = "🆓 Grátis"
                cor_preco = "green"
            
            badges_html = f"""
            <div class="curso-badges">
                <span class="curso-badge {'gold' if ativo else ''}">{'🟢 Ativo' if ativo else '🔴 Inativo'}</span>
                <span class="curso-badge green">{c.get('modalidade','EAD')}</span>
                <span class="curso-badge {cor_preco}">{txt_preco}</span>
            </div>
            """
            
            st.markdown(f"""
            <div class="curso-card-moderno">
                <div style="text-align:right;">{role}</div>
                <div class="curso-icon">{icon}</div>
                <h4 style="margin:0;">{c.get('titulo')}</h4>
                <p style="opacity:0.7; font-size:0.9em; flex-grow:1;">{c.get('descricao','')[:80]}...</p>
                {badges_html}
            </div>""", unsafe_allow_html=True)
            
            st.markdown(f'<div style="margin-top: -1rem; margin-bottom: 1rem;">', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️ Editar", key=f"e_{c['id']}", use_container_width=True): navegar_para('edicao', c)
            if c2.button("👁️ Ver", key=f"v_{c['id']}", use_container_width=True): navegar_para('detalhe', c)
            st.markdown('</div>', unsafe_allow_html=True)

# --- DETALHES ---
def _exibir_detalhes_curso(curso, usuario):
    st.title(curso.get('titulo'))
    can_edit = (usuario['id'] == curso.get('professor_id')) or (usuario['id'] in curso.get('editores_ids', [])) or (usuario.get('tipo') == 'admin')
    
    if can_edit:
        c1, c2 = st.columns(2)
        if c1.button("✏️ Editar", use_container_width=True): navegar_para('edicao', curso)
        if c2.button("➕ Aulas", type="primary", use_container_width=True): navegar_para('gerenciar_conteudo', curso)
    
    st.write(curso.get('descricao'))
    
    # Detalhes bonitos
    html_det = f"""
    <div class="detalhes-grid">
        <div class="detalhe-card"><div class="detalhe-icon">🥋</div><div class="detalhe-info"><span class="detalhe-label">Nível</span><span class="detalhe-value">{curso.get('nivel','Geral')}</span></div></div>
        <div class="detalhe-card"><div class="detalhe-icon">⏳</div><div class="detalhe-info"><span class="detalhe-label">Duração</span><span class="detalhe-value">{curso.get('duracao_estimada','-')}</span></div></div>
        <div class="detalhe-card"><div class="detalhe-icon">📜</div><div class="detalhe-info"><span class="detalhe-label">Certificado</span><span class="detalhe-value">{'Sim' if curso.get('certificado_automatico') else 'Não'}</span></div></div>
    </div>
    """
    st.markdown(html_det, unsafe_allow_html=True)

    insc = ce.obter_inscricao(usuario['id'], curso['id'])
    
    st.markdown("<br>", unsafe_allow_html=True)
    if insc or can_edit:
        if st.button("🎬 Acessar Aulas", type="primary", use_container_width=True): navegar_para('aulas', curso)
    else:
        lbl = f"Comprar R$ {curso.get('preco')}" if curso.get('pago') else "Inscrever-se Grátis"
        if st.button(lbl, type="primary", use_container_width=True):
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
                    concluida = ce.verificar_aula_concluida(usuario['id'], a['id'])
                    icon = "✅" if concluida else "⚪"
                    # Highlight aula atual
                    label = a['titulo']
                    if aula and a['id'] == aula['id']: label = f"**▶️ {label}**"
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

# --- ALUNO / DASHBOARD ---
def _professor_dashboard(usuario):
    st.markdown("### 📊 Dashboard do Instrutor")
    cursos = ce.listar_cursos_do_professor(usuario["id"])
    if not cursos: st.info("Sem dados."); return
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='stats-card-moderno'><div class='stats-value-moderno'>{len(cursos)}</div><div class='stats-label-moderno'>Total Cursos</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stats-card-moderno'><div class='stats-value-moderno'>{sum(1 for c in cursos if c.get('ativo'))}</div><div class='stats-label-moderno'>Ativos</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='stats-card-moderno'><div class='stats-value-moderno'>{sum(1 for c in cursos if c.get('pago'))}</div><div class='stats-label-moderno'>Pagos</div></div>", unsafe_allow_html=True)

def _aluno_cursos_disponiveis(usuario):
    cursos = ce.listar_cursos_disponiveis_para_usuario(usuario)
    if not cursos: st.info("Nada por aqui."); return
    cols = st.columns(3)
    for i, c in enumerate(cursos):
        with cols[i%3]:
            # Lógica do Preço
            if c.get('pago'):
                txt_preco = f"💰 R$ {c.get('preco', 0):.2f}"
                cor_preco = "gold"
            else:
                txt_preco = "🆓 Grátis"
                cor_preco = "green"
            
            # Card Reutilizado Visual
            st.markdown(f"""
            <div class="curso-card-moderno">
                <div class="curso-icon">🎓</div>
                <h4 style="margin:0;">{c.get('titulo')}</h4>
                <p style="opacity:0.7; font-size:0.9em; flex-grow:1;">{c.get('descricao','')[:80]}...</p>
                <div class="curso-badges">
                    <span class="curso-badge green">{c.get('modalidade','EAD')}</span>
                    <span class="curso-badge {cor_preco}">{txt_preco}</span>
                </div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown(f'<div style="margin-top: -1rem; margin-bottom: 1rem;">', unsafe_allow_html=True)
            if st.button("Ver Detalhes", key=f"vda_{c['id']}", use_container_width=True): navegar_para('detalhe', c)
            st.markdown('</div>', unsafe_allow_html=True)

def _aluno_meus_cursos(usuario):
    # Simplificado
    _aluno_cursos_disponiveis(usuario)
