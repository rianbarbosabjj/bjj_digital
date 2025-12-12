"""
📊 Módulo Modernizado de Gestão de Usuários, Questões e Exames
Design: Clean & Professional
Funcionalidades: Dashboard interativo, IA integrada, UX aprimorada
"""

import streamlit as st
import pandas as pd
import numpy as np
import bcrypt
import time 
import io 
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, time as dtime 
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json

# Importações base
from database import get_db, OPCOES_SEXO
from firebase_admin import firestore

# =========================================
# CONFIGURAÇÃO DE ESTILO
# =========================================

def aplicar_estilos_admin():
    """Aplica estilos CSS modernos para a interface administrativa"""
    st.markdown("""
    <style>
    /* Tema Dark Elegante */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Cards modernos */
    .admin-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
    }
    
    .admin-card:hover {
        border-color: rgba(59, 130, 246, 0.5);
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    
    /* Badges elegantes */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 2px;
    }
    
    .badge-success {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
    }
    
    .badge-warning {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
    }
    
    .badge-danger {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white);
    }
    
    .badge-info {
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        color: white;
    }
    
    /* Botões modernos */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    /* Tabs estilizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        background: transparent;
    }
    
    /* Inputs modernos */
    .stTextInput > div > div > input,
    .stTextArea > div > textarea {
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        background: rgba(255, 255, 255, 0.05);
        color: white;
    }
    
    /* Métricas */
    .metric-card {
        background: linear-gradient(145deg, rgba(59, 130, 246, 0.1), rgba(16, 185, 129, 0.1));
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Animações */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .animate-fadeIn {
        animation: fadeIn 0.5s ease-out;
    }
    
    /* Scrollbars personalizadas */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #3b82f6, #10b981);
        border-radius: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================
# ENUMS E CONSTANTES
# =========================================

class StatusQuestao(str, Enum):
    APROVADA = "aprovada"
    PENDENTE = "pendente"
    CORRECAO = "correcao"
    REJEITADA = "rejeitada"
    RASCUNHO = "rascunho"

class StatusExame(str, Enum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    REPROVADO = "reprovado"
    EM_ANDAMENTO = "em_andamento"
    BLOQUEADO = "bloqueado"
    EXPIRADO = "expirado"

@dataclass
class QuestaoInfo:
    """DTO para informações da questão"""
    id: str
    pergunta: str
    dificuldade: int
    categoria: str
    alternativas: Dict[str, str]
    resposta_correta: str
    status: StatusQuestao
    criado_por: str
    data_criacao: datetime
    url_imagem: Optional[str]
    url_video: Optional[str]
    feedback_admin: Optional[str]

# Constantes
FAIXAS_COMPLETAS = [
    " ", "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]

NIVEIS_DIFICULDADE = [1, 2, 3, 4]
MAPA_NIVEIS = {
    1: "🟢 Fácil",
    2: "🔵 Médio", 
    3: "🟠 Difícil",
    4: "🔴 Muito Difícil"
}

TIPO_MAP = {
    "Aluno(a)": "aluno",
    "Professor(a)": "professor", 
    "Administrador(a)": "admin"
}
TIPO_MAP_INV = {v: k for k, v in TIPO_MAP.items()}

# =========================================
# COMPONENTES REUTILIZÁVEIS
# =========================================

def metric_card(title: str, value, change: str = None, icon: str = "📊"):
    """Componente de métrica personalizada"""
    with st.container():
        st.markdown("""
        <div class="metric-card">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="font-size: 2.5rem;">{}</div>
                <div>
                    <h3 style="margin: 0; font-size: 2rem;">{}</h3>
                    <div style="opacity: 0.8; margin-bottom: 0.5rem;">{}</div>
                    {}
                </div>
            </div>
        </div>
        """.format(icon, value, title, 
                   f"<small style='opacity:0.7;'>{change}</small>" if change else ""), 
        unsafe_allow_html=True)

def badge_nivel(nivel: int) -> str:
    """Retorna badge HTML para nível de dificuldade"""
    texto = MAPA_NIVEIS.get(nivel, "⚪ ?")
    cores = {
        1: "badge-success",
        2: "badge-info", 
        3: "badge-warning",
        4: "badge-danger"
    }
    cor = cores.get(nivel, "badge-info")
    return f"<span class='badge {cor}'>{texto}</span>"

def status_badge(status: str) -> str:
    """Badge para status"""
    status_config = {
        "aprovada": ("✅ Aprovada", "badge-success"),
        "pendente": ("⏳ Pendente", "badge-warning"),
        "correcao": ("🛠️ Correção", "badge-warning"),
        "rejeitada": ("❌ Rejeitada", "badge-danger"),
        "rascunho": ("📝 Rascunho", "badge-info")
    }
    texto, classe = status_config.get(status, ("⚪", "badge-info"))
    return f"<span class='badge {classe}'>{texto}</span>"

def card_usuario(usuario: dict, on_edit=None, on_delete=None):
    """Card moderno para exibição de usuário"""
    with st.container():
        st.markdown("""
        <div class="admin-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4 style="margin: 0;">{}</h4>
                    <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                        <small>📧 {}</small>
                        <small>👤 {}</small>
                        <small>🥋 {}</small>
                    </div>
                </div>
                <div style="display: flex; gap: 0.5rem;">
        """.format(
            usuario.get('nome', 'Sem Nome'),
            usuario.get('email', '-'),
            usuario.get('tipo_usuario', '-'),
            usuario.get('faixa_atual', '-')
        ), unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️", key=f"edit_{usuario.get('id')}", help="Editar usuário"):
                if on_edit:
                    on_edit(usuario)
        with col2:
            if st.button("🗑️", key=f"del_{usuario.get('id')}", type="secondary"):
                if on_delete:
                    on_delete(usuario)
        
        st.markdown("""
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# =========================================
# GESTÃO DE USUÁRIOS MODERNA
# =========================================

def gestao_usuarios_tab():
    """Interface moderna para gestão de usuários"""
    
    aplicar_estilos_admin()
    
    db = get_db()
    
    # Header com métricas
    st.markdown("""
    <div class="animate-fadeIn">
        <h1>👥 Gestão de Usuários</h1>
        <p style="opacity: 0.8;">Gerencie alunos, professores e administradores do sistema</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Carregar dados
    users_ref = list(db.collection('usuarios').stream())
    users = [d.to_dict() | {"id": d.id} for d in users_ref]
    
    # Métricas rápidas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total Usuários", len(users))
    with col2:
        alunos = len([u for u in users if u.get('tipo_usuario') == 'aluno'])
        metric_card("Alunos", alunos, f"{alunos/len(users)*100:.0f}%", "👨‍🎓")
    with col3:
        professores = len([u for u in users if u.get('tipo_usuario') == 'professor'])
        metric_card("Professores", professores, f"{professores/len(users)*100:.0f}%", "👨‍🏫")
    with col4:
        admins = len([u for u in users if u.get('tipo_usuario') == 'admin'])
        metric_card("Admins", admins, "Administradores", "🔧")
    
    st.markdown("---")
    
    # Filtros avançados
    with st.expander("🔍 Filtros Avançados", expanded=True):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            filtro_nome = st.text_input("Nome/E-mail", placeholder="Digite para buscar...")
        
        with col_f2:
            tipos = list(set([u.get('tipo_usuario', '') for u in users]))
            filtro_tipo = st.multiselect("Tipo", tipos, default=tipos)
        
        with col_f3:
            faixas = list(set([u.get('faixa_atual', '') for u in users if u.get('faixa_atual')]))
            filtro_faixa = st.multiselect("Faixa", faixas)
        
        with col_f4:
            equipes = list(set([u.get('equipe', '') for u in users if u.get('equipe')]))
            filtro_equipe = st.multiselect("Equipe", equipes)
    
    # Aplicar filtros
    usuarios_filtrados = users
    
    if filtro_nome:
        termo = filtro_nome.upper()
        usuarios_filtrados = [
            u for u in usuarios_filtrados 
            if termo in u.get('nome', '').upper() or 
               termo in u.get('email', '').upper()
        ]
    
    if filtro_tipo:
        usuarios_filtrados = [u for u in usuarios_filtrados if u.get('tipo_usuario') in filtro_tipo]
    
    if filtro_faixa:
        usuarios_filtrados = [u for u in usuarios_filtrados if u.get('faixa_atual') in filtro_faixa]
    
    if filtro_equipe:
        usuarios_filtrados = [u for u in usuarios_filtrados if u.get('equipe') in filtro_equipe]
    
    # Visualização
    st.markdown(f"### 📋 Usuários Encontrados ({len(usuarios_filtrados)})")
    
    # Opções de visualização
    view_mode = st.radio(
        "Visualização:",
        ["Cards", "Tabela"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if view_mode == "Cards":
        # Grid responsivo de cards
        cols = st.columns(2)
        for idx, usuario in enumerate(usuarios_filtrados):
            with cols[idx % 2]:
                card_usuario(
                    usuario,
                    on_edit=lambda u: st.session_state['edit_user'] = u,
                    on_delete=lambda u: deletar_usuario(u, db)
                )
    else:
        # Tabela interativa
        df = pd.DataFrame(usuarios_filtrados)
        if not df.empty:
            cols_to_show = ['nome', 'email', 'tipo_usuario', 'faixa_atual', 'sexo']
            df_display = df[cols_to_show].fillna('-')
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "nome": "Nome",
                    "email": "E-mail", 
                    "tipo_usuario": "Tipo",
                    "faixa_atual": "Faixa",
                    "sexo": "Sexo"
                }
            )
    
    # Modal de edição
    if 'edit_user' in st.session_state:
        _modal_editar_usuario(st.session_state['edit_user'], db)

def _modal_editar_usuario(usuario: dict, db):
    """Modal moderno para edição de usuário"""
    
    with st.dialog("✏️ Editar Usuário"):
        # Carregar dados complementares
        equipes_ref = list(db.collection('equipes').stream())
        mapa_equipes = {d.id: d.to_dict().get('nome', 'Sem Nome') for d in equipes_ref}
        lista_equipes = ["Sem Equipe"] + sorted(list(mapa_equipes.values()))
        
        # Formulário em abas
        tab1, tab2, tab3 = st.tabs(["👤 Dados Pessoais", "🥋 Perfil", "🔒 Segurança"])
        
        with tab1:
            st.markdown("#### Informações Básicas")
            
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome Completo *", value=usuario.get('nome', ''))
                email = st.text_input("E-mail *", value=usuario.get('email', ''))
                cpf = st.text_input("CPF *", value=usuario.get('cpf', ''))
            
            with col2:
                # Sexo
                idx_sexo = 0
                sexo_val = usuario.get('sexo')
                if sexo_val in OPCOES_SEXO:
                    idx_sexo = OPCOES_SEXO.index(sexo_val)
                sexo = st.selectbox("Sexo", OPCOES_SEXO, index=idx_sexo)
                
                # Data de nascimento
                val_nasc = None
                if usuario.get('data_nascimento'):
                    try:
                        val_nasc = datetime.fromisoformat(usuario.get('data_nascimento')).date()
                    except:
                        pass
                nascimento = st.date_input(
                    "Data de Nascimento",
                    value=val_nasc,
                    min_value=date(1940,1,1),
                    max_value=date.today(),
                    format="DD/MM/YYYY"
                )
        
        with tab2:
            st.markdown("#### Perfil e Vínculos")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Tipo de usuário
                tipo_atual = usuario.get('tipo_usuario', 'aluno')
                tipo_display = TIPO_MAP_INV.get(tipo_atual, "Aluno(a)")
                idx_tipo = 0
                if tipo_display in list(TIPO_MAP.keys()):
                    idx_tipo = list(TIPO_MAP.keys()).index(tipo_display)
                tipo_selecionado = st.selectbox(
                    "Tipo de Usuário",
                    list(TIPO_MAP.keys()),
                    index=idx_tipo,
                    help="Selecione o perfil do usuário"
                )
            
            with col2:
                # Faixa
                faixa_atual = str(usuario.get('faixa_atual') or 'Branca')
                idx_faixa = 0
                for i, f in enumerate(FAIXAS_COMPLETAS):
                    if f.strip().lower() == faixa_atual.strip().lower():
                        idx_faixa = i
                        break
                faixa = st.selectbox("Faixa", FAIXAS_COMPLETAS, index=idx_faixa)
            
            # Equipe
            equipe_atual = "Sem Equipe"
            for eq_id, eq_nome in mapa_equipes.items():
                if eq_id == usuario.get('equipe_id'):
                    equipe_atual = eq_nome
                    break
            
            nova_equipe = st.selectbox(
                "Equipe",
                lista_equipes,
                index=lista_equipes.index(equipe_atual) if equipe_atual in lista_equipes else 0
            )
        
        with tab3:
            st.markdown("#### Configurações de Acesso")
            
            senha = st.text_input(
                "Nova Senha (opcional)",
                type="password",
                help="Deixe em branco para manter a senha atual"
            )
            
            precisa_trocar_senha = st.checkbox(
                "Forçar troca de senha no próximo login",
                value=usuario.get('precisa_trocar_senha', False)
            )
        
        # Botões de ação
        st.markdown("---")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        
        with col_btn2:
            salvar = st.button("💾 Salvar Alterações", use_container_width=True, type="primary")
            cancelar = st.button("Cancelar", use_container_width=True)
        
        if salvar:
            # Validações
            erros = []
            if not nome.strip():
                erros.append("Nome é obrigatório")
            if not email.strip():
                erros.append("E-mail é obrigatório")
            if not cpf.strip():
                erros.append("CPF é obrigatório")
            
            if erros:
                for erro in erros:
                    st.error(f"⚠️ {erro}")
            else:
                try:
                    # Preparar dados de atualização
                    updates = {
                        "nome": nome.upper().strip(),
                        "email": email.lower().strip(),
                        "cpf": cpf.strip(),
                        "sexo": sexo,
                        "data_nascimento": nascimento.isoformat() if nascimento else None,
                        "tipo_usuario": TIPO_MAP[tipo_selecionado],
                        "faixa_atual": faixa,
                        "precisa_trocar_senha": precisa_trocar_senha
                    }
                    
                    # Atualizar senha se fornecida
                    if senha:
                        updates["senha"] = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                    
                    # Atualizar equipe
                    if nova_equipe != "Sem Equipe":
                        equipe_id = None
                        for eq_id, eq_nome in mapa_equipes.items():
                            if eq_nome == nova_equipe:
                                equipe_id = eq_id
                                break
                        if equipe_id:
                            updates["equipe_id"] = equipe_id
                    
                    # Salvar no banco
                    db.collection('usuarios').document(usuario['id']).update(updates)
                    
                    st.success("✅ Usuário atualizado com sucesso!")
                    time.sleep(1.5)
                    st.session_state.pop('edit_user', None)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Erro ao salvar: {str(e)}")
        
        if cancelar:
            st.session_state.pop('edit_user', None)
            st.rerun()

def deletar_usuario(usuario: dict, db):
    """Exclui usuário com confirmação"""
    if st.confirm(f"Tem certeza que deseja excluir {usuario.get('nome')}?"):
        try:
            db.collection('usuarios').document(usuario['id']).delete()
            st.success("✅ Usuário excluído!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erro ao excluir: {str(e)}")

# =========================================
# GESTÃO DE QUESTÕES MODERNA
# =========================================

def gestao_questoes_tab():
    """Interface moderna para gestão de questões"""
    
    aplicar_estilos_admin()
    
    db = get_db()
    user = st.session_state.usuario
    user_tipo = str(user.get("tipo_usuario", user.get("tipo", ""))).lower()
    
    # Verificar permissão
    if user_tipo not in ["admin", "professor"]:
        st.error("🚫 Acesso negado. Esta funcionalidade requer permissões de administrador ou professor.")
        return
    
    # Header
    st.markdown("""
    <div class="animate-fadeIn">
        <h1>📝 Banco de Questões</h1>
        <p style="opacity: 0.8;">Gerencie questões, avaliações e análise de conteúdo</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs principais
    tab_titles = ["📚 Questões Ativas", "➕ Criar Nova", "📤 Minhas Submissões"]
    if user_tipo == "admin":
        tab_titles.append("✅ Fila de Aprovação")
    
    tabs = st.tabs(tab_titles)
    
    # ========== TAB 1: QUESTÕES ATIVAS ==========
    with tabs[0]:
        st.markdown("### 📊 Banco de Questões Aprovadas")
        
        # Filtros avançados
        with st.expander("🔍 Filtros e Busca", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                termo_busca = st.text_input("Buscar por palavra-chave", placeholder="Digite termos...")
            
            with col2:
                niveis_filtro = st.multiselect(
                    "Níveis de Dificuldade",
                    NIVEIS_DIFICULDADE,
                    default=NIVEIS_DIFICULDADE,
                    format_func=lambda x: MAPA_NIVEIS.get(x, str(x))
                )
            
            with col3:
                categorias_ref = list(db.collection('questoes').select(['categoria']).stream())
                categorias = sorted(list(set([d.to_dict().get('categoria', 'Geral') for d in categorias_ref])))
                categorias_filtro = st.multiselect("Categorias", categorias, default=categorias)
        
        # Carregar questões
        questoes_ref = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        questoes = []
        
        for doc in questoes_ref:
            d = doc.to_dict()
            d['id'] = doc.id
            
            # Aplicar filtros
            if termo_busca and termo_busca.lower() not in d.get('pergunta', '').lower():
                continue
            
            if d.get('dificuldade', 1) not in niveis_filtro:
                continue
            
            if d.get('categoria', 'Geral') not in categorias_filtro:
                continue
            
            questoes.append(d)
        
        # Métricas
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            metric_card("Total Questões", len(questoes), "aprovadas", "📚")
        with col_m2:
            media_dificuldade = np.mean([q.get('dificuldade', 1) for q in questoes]) if questoes else 0
            metric_card("Dificuldade Média", f"{media_dificuldade:.1f}", "escala 1-4", "📊")
        with col_m3:
            categorias_count = len(set([q.get('categoria', 'Geral') for q in questoes]))
            metric_card("Categorias", categorias_count, "diferentes", "🏷️")
        with col_m4:
            autores_count = len(set([q.get('criado_por', '') for q in questoes]))
            metric_card("Autores", autores_count, "colaboradores", "👥")
        
        # Lista de questões
        if not questoes:
            st.info("🎯 Nenhuma questão encontrada com os filtros aplicados.")
        else:
            st.markdown(f"### 📋 Resultados ({len(questoes)})")
            
            for questao in questoes:
                with st.container():
                    st.markdown(f"""
                    <div class="admin-card">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <h4 style="margin: 0 0 0.5rem 0;">{questao.get('pergunta', '')}</h4>
                                <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
                                    {badge_nivel(questao.get('dificuldade', 1))}
                                    <span class="badge badge-info">{questao.get('categoria', 'Geral')}</span>
                                    <small style="opacity: 0.7;">✍️ {questao.get('criado_por', '?')}</small>
                                </div>
                            </div>
                            <div>
                    """, unsafe_allow_html=True)
                    
                    # Botões de ação
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("✏️", key=f"edit_q_{questao['id']}", help="Editar questão"):
                            st.session_state['edit_questao'] = questao
                    with col_btn2:
                        if st.button("👁️", key=f"view_q_{questao['id']}", help="Visualizar detalhes"):
                            st.session_state['view_questao'] = questao
                    
                    st.markdown("</div></div>", unsafe_allow_html=True)
        
        # Modal de visualização
        if 'view_questao' in st.session_state:
            _modal_ver_questao(st.session_state['view_questao'])
        
        # Modal de edição
        if 'edit_questao' in st.session_state:
            _modal_editar_questao(st.session_state['edit_questao'], db, user_tipo)
    
    # ========== TAB 2: CRIAR NOVA ==========
    with tabs[1]:
        st.markdown("### 🎯 Criar Nova Questão")
        
        subtabs_criar = st.tabs(["✍️ Manual", "📂 Importar em Lote"])
        
        with subtabs_criar[0]:
            with st.form("nova_questao_form"):
                st.markdown("#### Informações da Questão")
                
                pergunta = st.text_area(
                    "Enunciado *",
                    height=100,
                    placeholder="Digite o enunciado da questão...",
                    help="Seja claro e objetivo"
                )
                
                # Mídia
                st.markdown("#### 🖼️ Mídia (opcional)")
                col_media1, col_media2 = st.columns(2)
                
                with col_media1:
                    imagem = st.file_uploader(
                        "Upload de Imagem",
                        type=["jpg", "jpeg", "png", "gif"],
                        help="Suporte: JPG, PNG, GIF"
                    )
                
                with col_media2:
                    video = st.file_uploader(
                        "Upload de Vídeo",
                        type=["mp4", "mov", "avi"],
                        help="Suporte: MP4, MOV, AVI"
                    )
                    link_video = st.text_input("Link do Vídeo (YouTube/Vimeo)", placeholder="https://...")
                
                # Categoria e dificuldade
                st.markdown("#### 🏷️ Classificação")
                col_cat, col_dif = st.columns(2)
                
                with col_cat:
                    categoria = st.text_input("Categoria", value="Geral", placeholder="Ex: Guarda, Finalização")
                
                with col_dif:
                    dificuldade = st.select_slider(
                        "Nível de Dificuldade",
                        options=NIVEIS_DIFICULDADE,
                        value=2,
                        format_func=lambda x: MAPA_NIVEIS.get(x, str(x))
                    )
                
                # Alternativas
                st.markdown("#### 📝 Alternativas")
                
                cols_alt = st.columns(4)
                alternativas = {}
                
                with cols_alt[0]:
                    alternativas['A'] = st.text_input("Alternativa A *", placeholder="Opção A")
                with cols_alt[1]:
                    alternativas['B'] = st.text_input("Alternativa B *", placeholder="Opção B")
                with cols_alt[2]:
                    alternativas['C'] = st.text_input("Alternativa C", placeholder="Opção C")
                with cols_alt[3]:
                    alternativas['D'] = st.text_input("Alternativa D", placeholder="Opção D")
                
                # Resposta correta
                resposta_correta = st.radio(
                    "Resposta Correta *",
                    options=['A', 'B', 'C', 'D'],
                    horizontal=True
                )
                
                # Botão de envio
                submitted = st.form_submit_button(
                    "🚀 Enviar Questão",
                    type="primary",
                    use_container_width=True
                )
                
                if submitted:
                    if not pergunta or not alternativas['A'] or not alternativas['B']:
                        st.error("⚠️ Preencha os campos obrigatórios: enunciado e alternativas A e B.")
                    else:
                        try:
                            # Processar uploads (simulado - em produção, integrar com storage)
                            url_imagem = None
                            if imagem:
                                # Em produção: fazer_upload_midia(imagem)
                                url_imagem = "url_simulada_imagem"
                            
                            url_video = link_video
                            if video:
                                # Em produção: fazer_upload_midia(video)
                                url_video = "url_simulada_video"
                            
                            # Determinar status inicial
                            status_inicial = "aprovada" if user_tipo == "admin" else "pendente"
                            
                            # Salvar no banco
                            questao_data = {
                                "pergunta": pergunta,
                                "dificuldade": dificuldade,
                                "categoria": categoria,
                                "alternativas": alternativas,
                                "resposta_correta": resposta_correta,
                                "url_imagem": url_imagem,
                                "url_video": url_video,
                                "status": status_inicial,
                                "criado_por": user.get('nome', 'Admin'),
                                "data_criacao": firestore.SERVER_TIMESTAMP,
                                "feedback_admin": None
                            }
                            
                            db.collection('questoes').add(questao_data)
                            
                            if user_tipo == "admin":
                                st.success("✅ Questão criada e aprovada automaticamente!")
                            else:
                                st.success("📤 Questão enviada para análise do administrador!")
                            
                            time.sleep(1.5)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar questão: {str(e)}")
        
        with subtabs_criar[1]:
            if user_tipo != "admin":
                st.warning("🚫 Apenas administradores podem importar questões em lote.")
            else:
                st.markdown("#### 📥 Importação em Massa")
                
                # Template
                st.info("📋 Utilize o modelo abaixo para formatar suas questões")
                
                df_modelo = pd.DataFrame({
                    "pergunta": ["Qual a posição básica do Jiu-Jitsu?"],
                    "alt_a": ["Guarda"],
                    "alt_b": ["Montada"],
                    "alt_c": ["Quatro apoios"],
                    "alt_d": ["De pé"],
                    "correta": ["A"],
                    "dificuldade": [1],
                    "categoria": ["Fundamentos"]
                })
                
                csv_buffer = io.StringIO()
                df_modelo.to_csv(csv_buffer, index=False, sep=';')
                
                col_download, col_upload = st.columns(2)
                
                with col_download:
                    st.download_button(
                        "⬇️ Baixar Modelo CSV",
                        data=csv_buffer.getvalue(),
                        file_name="modelo_questoes.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_upload:
                    arquivo = st.file_uploader(
                        "Carregar arquivo",