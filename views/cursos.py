"""
BJJ Digital - Sistema de Cursos (Versão Final Fixada com Botões Alinhados)
"""
import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import Optional, Dict
import utils as ce 
import views.aulas as aulas_view 

try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"

# ======================================================
# ESTILOS
# ======================================================
def aplicar_estilos_cursos():
    st.markdown(f"""
    <style>
    /* CARDS */
    .curso-card-moderno {{
        background: linear-gradient(145deg, rgba(14, 45, 38, 0.95) 0%, rgba(9, 31, 26, 0.98) 100%);
        border: 1px solid rgba(255, 215, 112, 0.15); border-radius: 20px; padding: 1.5rem;
        height: 100%; min-height: 320px; /* Altura fixa para alinhar */
        display: flex; flex-direction: column; justify-content: space-between;
        position: relative; overflow: hidden; transition: transform 0.3s;
    }}
    .curso-card-moderno:hover {{
        border-color: {COR_DESTAQUE}; transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }}
    .curso-icon {{ font-size: 2.5rem; text-align: center; margin-bottom: 1rem; }}
    
    /* TEXTO DESCRIÇÃO (LIMITADO PARA ALINHAR) */
    .card-desc {{
        font-size: 0.85em; opacity: 0.7; flex-grow: 1;
        min-height: 60px; max-height: 60px; overflow: hidden;
        display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
    }}

    /* INFO EXTRA */
    .info-extra {{
        font-size: 0.8rem; opacity: 0.8; margin-bottom: 0.8rem;
        border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;
    }}
    /* BADGES */
    .curso-badges {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: auto; }}
    .curso-badge {{
        padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: bold;
        background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
    }}
    .green {{ color: #4ADE80; border-color: #4ADE80; }}
    .gold {{ color: {COR_DESTAQUE}; border-color: {COR_DESTAQUE}; }}
    .blue {{ color: #60A5FA; border-color: #60A5FA; }}
    
    /* BOTÕES */
    div.stButton > button, div.stFormSubmitButton > button {{ 
        width: 100%; border-radius: 8px; font-weight: 600;
    }}
    .stButton>button[kind="primary"] {{ background: linear-gradient(135deg, {COR_BOTAO}, #056853); color: white; border: none; }}
    .stButton>button[kind="secondary"] {{ background: transparent; border: 1px solid {COR_DESTAQUE}; color: {COR_DESTAQUE}; }}
    
    /* HEADER */
    .curso-header {{
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.9), rgba(9, 31, 26, 0.95));
        border-bottom: 1px solid {COR_DESTAQUE}; padding: 1.5rem; border-radius: 0 0 20px 20px; margin-bottom: 2rem;
    }}
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# SELETOR DE EDITORES
# ======================================================
def renderizar_seletor_editores(chave_unica, ids_iniciais=[]):
    key = f"lista_editores_{chave_unica}"
    if key not in st.session_state: st.session_state[key] = ids_iniciais.copy()

    st.markdown("###### 👥 Editores Colaboradores")
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        termo = c1.text_input("Buscar Nome/CPF", key=f"src_{chave_unica}")
        
        users = ce.listar_todos_usuarios_para_selecao()
        filtro = [u for u in users if termo.lower() in u['nome'].lower() or termo in str(u.get('cpf',''))] if termo else []
        
        sel = c1.selectbox("Selecione", filtro, format_func=lambda x: f"{x['nome']} (CPF: {x.get('cpf')})", key=f"sel_{chave_unica}", index=None, placeholder="Digite para buscar...")
        
        if c2.button("➕ Adicionar", key=f"add_{chave_unica}"):
            if sel and sel['id'] not in st.session_state[key]:
                st.session_state[key].append(sel['id']); st.rerun()

        st.markdown(f"**Selecionados ({len(st.session_state[key])})**")
        if not st.session_state[key]: st.caption("Nenhum.")
        else:
            mapa = {u['id']: u for u in users}
            for uid in st.session_state[key]:
                u = mapa.get(uid, {'nome':'?', 'cpf':'?'})
                xc, yc = st.columns([4,1])
                xc.info(f"{u['nome']} ({u.get('cpf')})")
                if yc.button("🗑️", key=f"del_{uid}_{chave_unica}"):
                    st.session_state[key].remove(uid); st.rerun()
    return st.session_state[key]

def navegar_para(view: str, curso: Optional[Dict] = None):
    st.session_state['cursos_view'] = view
    st.session_state['curso_selecionado'] = curso
    st.rerun()

def pagina_cursos(usuario: dict):
    aplicar_estilos_cursos()
    if 'cursos_view' not in st.session_state: st.session_state['cursos_view'] = 'lista'
        
    st.markdown(f"""<div class="curso-header"><h1 style="margin:0; text-align:center; color:{COR_DESTAQUE};">🎓 GERENCIE SEUS CURSOS</h1>
    
    if st.session_state.get('cursos_view') != 'lista':
        if st.button("← Voltar à Lista", key="btn_back_list"): navegar_para('lista')
    else:
        if st.button("← Menu Principal", key="btn_back_home"):
            st.session_state.menu_selection = "Início"; st.rerun()
    st.write("")

    view = st.session_state.get('cursos_view')
    curso = st.session_state.get('curso_selecionado')
    is_prof = str(usuario.get("tipo", "")).lower() in ["admin", "professor"]
    
    if view == 'lista':
        if is_prof: _interface_professor(usuario)
        else: _interface_aluno(usuario)
    elif view == 'detalhe' and curso:
        _exibir_detalhes(curso, usuario)
    elif view == 'aulas' and curso:
        _pagina_aulas(curso, usuario)
    elif view == 'edicao' and curso and is_prof:
        _pagina_edicao(curso, usuario)
    elif view == 'gerenciar_conteudo' and curso and is_prof:
        aulas_view.gerenciar_conteudo_curso(curso, usuario)
    else:
        st.session_state['cursos_view'] = 'lista'; st.rerun()

# ======================================================
# LISTAGEM (Card Alinhado)
# ======================================================
def render_card_curso(c, mode="professor"):
    ativo = c.get('ativo', True)
    pago = c.get('pago', False)
    icon = "💎" if pago else "🎓"
    if not ativo: icon = "⏸️"
    
    if pago:
        bruto = c.get('preco', 0.0)
        split = c.get('split_custom', 10)
        liq = bruto * (1 - split/100)
        txt_price = f"R$ {bruto:.2f}"
        if mode == "professor": txt_price += f" • Liq: R$ {liq:.2f}"
        cor_bdg = "gold"
    else:
        txt_price = "Grátis"
        cor_bdg = "green"

    prof = c.get('professor_nome', 'Instrutor').split()[0]
    eq = c.get('professor_equipe', '')
    txt_eq = f" | 🛡️ {eq}" if eq else ""
    role_badge = f"<span class='curso-badge blue' style='float:right;'>✏️ Editor</span>" if mode=="professor" and c.get('papel')=='Editor' else ""

    # HTML FLATTENED (Sem indentação para evitar bugs)
    html = f"""<div class="curso-card-moderno"><div style="display:flex; justify-content:space-between;"><div class="curso-icon">{icon}</div>{role_badge}</div><h4 style="margin:0.5rem 0; color:white;">{c.get('titulo')}</h4><div class="info-extra">👨‍🏫 {prof}{txt_eq}</div><p class="card-desc">{c.get('descricao','')[:90]}...</p><div class="curso-badges"><span class="curso-badge green">{c.get('modalidade','EAD')}</span><span class="curso-badge {cor_bdg}">{txt_price}</span></div></div>"""
    st.markdown(html, unsafe_allow_html=True)

def _interface_professor(usuario):
    tab1, tab2 = st.tabs(["📘 Meus Cursos", "➕ Criar Novo"])
    with tab1:
        cursos = ce.listar_cursos_do_professor(usuario['id'])
        if not cursos: st.info("Nenhum curso encontrado.")
        cols = st.columns(3)
        for i, c in enumerate(cursos):
            with cols[i%3]:
                render_card_curso(c, "professor")
                c1, c2 = st.columns(2)
                if c1.button("✏️ Editar", key=f"e_{c['id']}", use_container_width=True): navegar_para('edicao', c)
                if c2.button("👁️ Ver", key=f"v_{c['id']}", use_container_width=True): navegar_para('detalhe', c)
    with tab2: _pagina_criar(usuario)

def _interface_aluno(usuario):
    cursos = ce.listar_cursos_disponiveis_para_usuario(usuario)
    st.markdown("### 🛒 Cursos Disponíveis")
    if not cursos: st.info("Nada disponível.")
    cols = st.columns(3)
    for i, c in enumerate(cursos):
        with cols[i%3]:
            render_card_curso(c, "aluno")
            if st.button("Ver Detalhes", key=f"vd_{c['id']}", use_container_width=True): navegar_para('detalhe', c)

# ======================================================
# CRUD
# ======================================================
def _pagina_criar(usuario):
    st.markdown("### 🚀 Criar Curso")
    if "pg_tgl" not in st.session_state: st.session_state["pg_tgl"] = False
    with st.container(border=True):
        c1, c2 = st.columns([2,1])
        tit = c1.text_input("Título", key="n_t")
        desc = c1.text_area("Descrição", key="n_d")
        mod = c2.selectbox("Modalidade", ["EAD","Presencial"], key="n_m")
        pub = c2.selectbox("Público", ["geral","equipe"], key="n_p")
        eq_dest = c2.text_input("Equipe Destino", key="n_eq") if pub=="equipe" else None
        eds = renderizar_seletor_editores("new")
        st.markdown("---")
        cf1, cf2, cf3 = st.columns(3)
        pago = cf1.toggle("Pago?", key="pg_tgl")
        pr = cf2.number_input("Preço", 0.0, disabled=not pago, key="n_pr")
        sp = cf3.slider("Taxa %", 0, 100, 10, key="n_sp") if usuario.get('tipo')=='admin' else 10
        c_crt, c_dur, c_niv = st.columns(3)
        cert = c_crt.checkbox("Certificado?", True, key="n_c")
        dur = c_dur.text_input("Duração", "10h", key="n_dr")
        niv = c_niv.selectbox("Nível", ["Geral","Iniciante","Avançado"], key="n_nv")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Criar", type="primary", use_container_width=True):
            if not tit: st.error("Título obrigatório.")
            else:
                ce.criar_curso(usuario['id'], usuario.get('nome',''), usuario.get('equipe',''), tit, desc, mod, pub, eq_dest, pago, pr, sp, cert, dur, niv, eds)
                st.success("Criado!"); time.sleep(1); st.rerun()

def _pagina_edicao(c, u):
    st.markdown(f"### ✏️ Editando: {c.get('titulo')}")
    kp = f"ep_{c['id']}"
    if kp not in st.session_state: st.session_state[kp] = c.get('pago',False)
    with st.container(border=True):
        c1, c2 = st.columns([2,1])
        nt = c1.text_input("Título", c.get('titulo'), key=f"et_{c['id']}")
        nd = c1.text_area("Descrição", c.get('descricao'), key=f"ed_{c['id']}")
        nm = c2.selectbox("Modalidade", ["EAD","Presencial"], index=0 if c.get('modalidade')=='EAD' else 1, key=f"em_{c['id']}")
        eds = renderizar_seletor_editores(f"edt_{c['id']}", c.get('editores_ids',[]))
        st.markdown("---")
        cp1, cp2 = st.columns(2)
        npago = cp1.toggle("Pago?", key=kp)
        npr = cp2.number_input("Preço", value=float(c.get('preco',0)), disabled=not npago, key=f"epr_{c['id']}")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Salvar", type="primary", use_container_width=True, key=f"sv_{c['id']}"):
            upd = {"titulo":nt, "descricao":nd, "modalidade":nm, "pago":npago, "preco":npr, "editores_ids":eds}
            ce.editar_curso(c['id'], upd); st.success("Salvo!"); time.sleep(1); navegar_para('detalhe', upd)
    if u['id'] == c.get('professor_id'):
        with st.expander("🗑️ Zona de Perigo"):
            if st.button("Excluir Curso", type="secondary", key=f"del_{c['id']}"):
                ce.excluir_curso(c['id']); st.success("Excluído!"); time.sleep(1); navegar_para('lista')

def _exibir_detalhes(c, u):
    st.title(c.get('titulo'))
    can_edit = (u['id'] == c.get('professor_id')) or (u['id'] in c.get('editores_ids', []))
    if can_edit:
        c1, c2 = st.columns(2)
        if c1.button("✏️ Editar"): navegar_para('edicao', c)
        if c2.button("➕ Aulas", type="primary"): navegar_para('gerenciar_conteudo', c)
    st.write(c.get('descricao'))
    st.markdown(f"**Professor:** {c.get('professor_nome','-')} | **Equipe:** {c.get('professor_equipe','-')}")
    insc = ce.obter_inscricao(u['id'], c['id'])
    st.markdown("<br>", unsafe_allow_html=True)
    if insc or can_edit:
        if st.button("🎬 Acessar Aulas", type="primary"): navegar_para('aulas', c)
    else:
        lbl = f"Comprar R$ {c.get('preco')}" if c.get('pago') else "Inscrever-se Grátis"
        if st.button(lbl, type="primary"):
            ce.inscrever_usuario_em_curso(u['id'], c['id']); st.success("Inscrito!"); st.rerun()

def _pagina_aulas(c, u):
    st.subheader(f"📺 {c.get('titulo')}")
    modulos = ce.listar_modulos_e_aulas(c['id'])
    if not modulos: st.warning("Sem aulas."); return
    cv, cl = st.columns([3, 1])
    if 'aula_atual' not in st.session_state: st.session_state['aula_atual'] = modulos[0]['aulas'][0] if modulos and modulos[0]['aulas'] else None
    aula = st.session_state.get('aula_atual')
    with cl:
        for m in modulos:
            with st.expander(m['titulo'], expanded=True):
                for a in m['aulas']:
                    icon = "✅" if ce.verificar_aula_concluida(u['id'], a['id']) else "⭕"
                    if st.button(f"{icon} {a['titulo']}", key=f"nv_{a['id']}"):
                        st.session_state['aula_atual'] = a; st.rerun()
    with cv:
        if aula:
            st.markdown(f"#### {aula['titulo']}")
            ct = aula.get('conteudo', {})
            tp = aula.get('tipo')
            if tp == 'video':
                if ct.get('url'): st.video(ct['url'])
                elif ct.get('arquivo_video'): st.video(ct['arquivo_video'])
            elif tp == 'texto': st.markdown(ct.get('texto',''))
            st.markdown("---")
            if st.button("Concluir", key=f"ok_{aula['id']}", type="primary"):
                ce.marcar_aula_concluida(u['id'], aula['id']); st.success("Feito!"); st.rerun()
