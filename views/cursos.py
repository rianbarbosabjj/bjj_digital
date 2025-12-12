# bjj_digital/views/cursos.py

import streamlit as st
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime
import plotly.express as px
import time # Mantido para usar time.sleep()
import sys # Adicionado para melhor manipulação do state após o modal

# Ajuste os imports conforme a estrutura do seu projeto
from courses_engine import (
    criar_curso,
    listar_cursos_do_professor,
    listar_cursos_disponiveis_para_usuario,
    inscrever_usuario_em_curso,
    obter_inscricao,
    # Adicionado para a edição: (Assumindo que esta função existe no courses_engine)
    # atualizar_curso # Se você tiver uma função mais completa que a auxiliar
)
from database import get_db

# ======================================================
# ESTILOS (Função não fornecida, mas crucial para o modal)
# É fundamental que esta função aplique o CSS para .modal-content
def aplicar_estilos_cursos():
    # O CSS a seguir é crucial para o modal não ficar truncado
    st.markdown("""
        <style>
            /* Animações e cores */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .animate-fadeIn {
                animation: fadeIn 0.5s ease-out;
            }
            
            /* Estilos para os cards */
            .curso-card {
                padding: 15px;
                border-radius: 12px;
                background-color: #1e293b; /* Fundo escuro */
                margin-bottom: 1rem;
                border-left: 5px solid #06b6d4; /* Exemplo de cor para destaque */
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            /* BADGES */
            .badge {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 8px;
                font-size: 0.75rem;
                font-weight: 600;
                margin-right: 5px;
            }
            .badge-azul { background-color: #3b82f633; color: #3b82f6; }
            .badge-verde { background-color: #10b98133; color: #10b981; }
            .badge-vermelho { background-color: #ef444433; color: #ef4444; }
            .badge-amarelo { background-color: #f59e0b33; color: #f59e0b; }

            /* ESTILOS CRUCIAIS DO MODAL */
            .modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999; /* Garante que fique acima de tudo */
            }
            .modal-content {
                position: relative;
                background-color: #1f2937; /* Fundo do modal */
                border-radius: 12px;
                padding: 2rem;
                width: 90%;
                max-width: 700px;
                /* CORREÇÃO: Força altura máxima e permite rolagem */
                max-height: 90vh; 
                overflow-y: auto;
                color: white; /* Cor do texto no modal */
            }
        </style>
    """, unsafe_allow_html=True)
    
# ======================================================
# PÁGINA PRINCIPAL
# ======================================================

def pagina_cursos(usuario: dict):
    """
    Interface de cursos, adaptada ao tipo de usuário.
    """
    # Aplicar estilos
    aplicar_estilos_cursos()
    
    tipo = str(usuario.get("tipo", "aluno")).lower()

    # Cabeçalho moderno
    st.markdown(f"""
    <div class="animate-fadeIn">
        <h1 style="margin-bottom: 0.5rem;">📚 Gestão de Cursos</h1>
        <div style="display: flex; align-items: center; gap: 1rem; opacity: 0.8;">
            <div>Bem-vindo, <strong>{usuario.get('nome', 'Usuário').split()[0]}</strong></div>
            <div>•</div>
            <div class="badge badge-azul">{tipo.capitalize()}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Verificar se há modal para mostrar
    # O modal é renderizado ANTES da interface principal para que ele fique em overlay
    if 'show_edit_modal' in st.session_state and st.session_state.show_edit_modal:
        _render_modal_editar_curso()
        
    if tipo in ["admin", "professor"]:
        _interface_professor_moderna(usuario)
    else:
        _interface_aluno_moderna(usuario)

# ======================================================
# VISÃO DO PROFESSOR / ADMIN MODERNA
# ======================================================

# ... (funções _interface_professor_moderna, _prof_listar_cursos_moderno, _card_curso_professor permanecem inalteradas, exceto a chamada de _toggle_status_curso, que não precisa de time.sleep)

def _card_curso_professor(curso: dict, usuario: dict):
    """Card moderno para curso do professor"""
    
    with st.container():
        st.markdown("<div class='curso-card'>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([3, 1.5, 1])
        
        with col1:
            # Status
            ativo = curso.get('ativo', True)
            status_badge = "🟢 Ativo" if ativo else "🔴 Inativo"
            status_class = "badge-verde" if ativo else "badge-vermelho"
            
            # Título
            st.markdown(f"### {curso.get('titulo', 'Sem Título')}")
            
            # Badges
            col_badges = st.columns([1, 1, 2])
            with col_badges[0]:
                st.markdown(f"<span class='badge {status_class}'>{status_badge}</span>", unsafe_allow_html=True)
            
            with col_badges[1]:
                modalidade = curso.get('modalidade', '-')
                st.markdown(f"<span class='badge badge-azul'>{modalidade}</span>", unsafe_allow_html=True)
            
            with col_badges[2]:
                publico = 'Equipe' if curso.get('publico') == 'equipe' else 'Geral'
                st.markdown(f"<span class='badge badge-amarelo'>{publico}</span>", unsafe_allow_html=True)
            
            # Descrição
            desc = curso.get("descricao", "")
            if desc:
                st.markdown(f"<div style='opacity: 0.8; margin-top: 0.5rem;'>{desc[:150]}...</div>", unsafe_allow_html=True)
        
        with col2:
            # Informações financeiras
            if curso.get("pago"):
                preco = curso.get('preco', 0.0)
                split = int(curso.get('split_custom', 10))
                
                st.metric("Preço", f"R$ {preco:.2f}")
                st.caption(f"Taxa: {split}%")
            else:
                st.metric("Preço", "Gratuito")
                st.caption("Sem taxa")
        
        with col3:
            st.write("")  # Espaçamento
            
            # Botões de ação
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("✏️", key=f"edit_{curso['id']}", help="Editar curso", use_container_width=True):
                    st.session_state['edit_curso'] = curso
                    st.session_state['show_edit_modal'] = True
                    st.rerun()
            
            with col_btn2:
                if ativo:
                    if st.button("⏸️", key=f"pause_{curso['id']}", help="Pausar curso", use_container_width=True):
                        _toggle_status_curso(curso["id"], False)
                        st.rerun()
                else:
                    if st.button("▶️", key=f"play_{curso['id']}", help="Ativar curso", use_container_width=True):
                        _toggle_status_curso(curso["id"], True)
                        st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

# ... (função _prof_criar_curso_moderno permanece inalterada, exceto a remoção do time.sleep(2) antes do st.rerun() para evitar bloqueio)

def _prof_criar_curso_moderno(usuario: dict):
    """Formulário moderno para criação de curso"""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(59,130,246,0.1)); 
                 padding: 1.5rem; border-radius: 16px; margin-bottom: 2rem;">
        <h3 style="margin: 0;">🎯 Criar Novo Curso</h3>
        <p style="opacity: 0.8; margin-top: 0.5rem;">Preencha os detalhes abaixo para criar seu curso</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("form_criar_curso_moderno", border=True):
        # Informações básicas
        st.markdown("#### 📝 Informações do Curso")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            titulo = st.text_input(
                "Título do Curso *",
                placeholder="Ex: Fundamentos do Jiu-Jitsu para Iniciantes",
                help="Seja claro e objetivo no título"
            )
            
            descricao = st.text_area(
                "Descrição Detalhada *",
                height=120,
                placeholder="Descreva o que os alunos aprenderão, metodologia, pré-requisitos...",
                help="Quanto mais detalhada, melhor para atrair alunos"
            )
        
        with col2:
            modalidade = st.selectbox(
                "Modalidade *",
                ["EAD", "Presencial", "Híbrido"],
                help="Como o curso será ministrado?"
            )
            
            publico = st.selectbox(
                "Público Alvo *",
                ["geral", "equipe"],
                format_func=lambda v: "🌍 Aberto (Geral)" if v == "geral" else "👥 Restrito (Equipe)"
            )
            
            equipe_destino = None
            if publico == "equipe":
                equipe_destino = st.text_input(
                    "Nome da Equipe *",
                    placeholder="Digite o nome da equipe",
                    help="Apenas membros desta equipe poderão acessar"
                )
        
        # Configurações
        st.markdown("#### ⚙️ Configurações")
        
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            certificado_auto = st.checkbox(
                "Emitir certificado automaticamente",
                value=True,
                help="O certificado será gerado automatically ao concluir o curso"
            )
        
        with col_config2:
            # Configurações avançadas
            with st.expander("Configurações Avançadas"):
                max_alunos = st.number_input(
                    "Vagas disponíveis",
                    min_value=0,
                    value=0,
                    help="0 = ilimitado"
                )
                
                duracao_estimada = st.text_input(
                    "Duração estimada",
                    placeholder="Ex: 8 semanas, 40 horas"
                )
        
        # Valores
        st.markdown("#### 💰 Valores")
        
        col_val1, col_val2, col_val3 = st.columns(3)
        
        with col_val1:
            pago = st.toggle(
                "Curso Pago?",
                value=False,
                help="O curso terá valor ou será gratuito?"
            )
        
        with col_val2:
            preco = st.number_input(
                "Valor (R$) *" if pago else "Valor (R$)",
                min_value=0.0,
                value=0.0 if not pago else 197.00,
                step=10.0,
                disabled=not pago,
                help="Valor total do curso"
            )
        
        with col_val3:
            is_admin = usuario.get("tipo") == "admin"
            if pago and is_admin:
                split_custom = st.slider(
                    "Taxa da Plataforma (%)",
                    0, 100,
                    value=10,
                    help="Percentual retido pela plataforma"
                )
            else:
                split_custom = 10
                if pago and not is_admin:
                    st.info(f"Taxa da plataforma: {split_custom}%")
        
        # Botão de envio
        st.markdown("---")
        submit_btn = st.form_submit_button(
            "🚀 Criar Curso",
            type="primary",
            use_container_width=True
        )
        
        if submit_btn:
            # Validações
            erros = []
            
            if not titulo.strip():
                erros.append("⚠️ O título é obrigatório")
            
            if not descricao.strip():
                erros.append("⚠️ A descrição é obrigatória")
            
            if publico == "equipe" and (not equipe_destino or not equipe_destino.strip()):
                erros.append("⚠️ Informe o nome da equipe")
            
            if pago and preco <= 0:
                erros.append("⚠️ Curso pago deve ter valor maior que zero")
            
            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                try:
                    criar_curso(
                        professor_id=usuario["id"],
                        nome_professor=usuario.get("nome", ""),
                        titulo=titulo,
                        descricao=descricao,
                        modalidade=modalidade,
                        publico=publico,
                        equipe_destino=equipe_destino,
                        pago=pago,
                        preco=preco if pago else 0.0,
                        split_custom=split_custom,
                        certificado_automatico=certificado_auto
                    )
                    
                    st.success("""
                    🎉 **Curso criado com sucesso!**
                    
                    Seu curso já está disponível para matrículas. 
                    Acesse a aba "Meus Cursos" para gerenciá-lo.
                    """)
                    
                    st.rerun() # Removemos o time.sleep(2)
                    
                except Exception as e:
                    st.error(f"""
                    ❌ **Erro ao criar curso:**
                    
                    ```{(str(e))}```
                    
                    Verifique os dados e tente novamente.
                    """)

# ... (funções _prof_dashboard_moderno permanece inalterada)

# ======================================================
# MODAL DE EDIÇÃO CORRIGIDO
# ======================================================

def _render_modal_editar_curso():
    """Renderiza o modal de edição corrigido"""
    
    if 'edit_curso' not in st.session_state:
        st.session_state.show_edit_modal = False
        return
    
    curso = st.session_state['edit_curso']
    usuario = st.session_state.get('usuario', {})
    
    # Abrindo a estrutura do modal
    # USAMOS UM st.empty() PARA SEGURAR A ESTRUTURA E GARANTIR A ORDEM VISUAL
    modal_placeholder = st.empty()

    with modal_placeholder.container():
        # Inicia a estrutura do modal overlay e content via HTML/CSS
        st.markdown(f"""
            <div id="modal-overlay" class="modal-overlay animate-fadeIn">
                <div id="modal-content" class="modal-content">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <h3 style="margin: 0;">✏️ Editar Curso: {curso.get('titulo', 'Sem Título')}</h3>
                        <button onclick="closeModal()" style="
                            background: none;
                            border: none;
                            color: white;
                            font-size: 1.5rem;
                            cursor: pointer;
                            opacity: 0.7;
                        ">×</button>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Formulário do Streamlit (o conteúdo que estava sendo escondido)
        # Este formulário é renderizado DENTRO do modal-content HTML
        is_admin = usuario.get("tipo") == "admin"
        
        with st.form(f"form_editar_{curso['id']}", border=False):
            
            # Informações básicas
            st.markdown("#### 📝 Informações do Curso")
            titulo = st.text_input("Título *", value=curso.get("titulo", ""), key=f"titulo_{curso['id']}")
            descricao = st.text_area("Descrição *", value=curso.get("descricao", ""), height=100, key=f"desc_{curso['id']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                modalidade = st.selectbox(
                    "Modalidade",
                    ["EAD", "Presencial", "Híbrido"],
                    index=["EAD", "Presencial", "Híbrido"].index(
                        curso.get("modalidade", "EAD")
                    ) if curso.get("modalidade") in ["EAD", "Presencial", "Híbrido"] else 0,
                    key=f"modalidade_{curso['id']}"
                )
            
            with col2:
                publico = st.selectbox(
                    "Público",
                    ["geral", "equipe"],
                    index=0 if curso.get("publico") == "geral" else 1,
                    format_func=lambda v: "🌍 Geral" if v == "geral" else "👥 Equipe",
                    key=f"publico_{curso['id']}"
                )
                
                equipe_destino = curso.get("equipe_destino", "")
                if publico == "equipe":
                    equipe_destino = st.text_input(
                        "Equipe Destino",
                        value=equipe_destino,
                        key=f"equipe_{curso['id']}"
                    )
            
            # Status e certificado
            st.markdown("#### ⚙️ Configurações")
            col3, col4 = st.columns(2)
            
            with col3:
                ativo = st.checkbox("Curso Ativo", value=curso.get("ativo", True), key=f"ativo_{curso['id']}")
            
            with col4:
                certificado_auto = st.checkbox(
                    "Certificado Automático",
                    value=curso.get("certificado_automatico", True),
                    key=f"cert_{curso['id']}"
                )
            
            # Valores
            st.markdown("#### 💰 Valores")
            
            col5, col6 = st.columns(2)
            
            with col5:
                pago = st.checkbox("Curso Pago", value=curso.get("pago", False), key=f"pago_{curso['id']}")
                
                preco = st.number_input(
                    "Valor (R$)",
                    value=float(curso.get("preco", 0.0)),
                    min_value=0.0,
                    step=10.0,
                    disabled=not pago,
                    key=f"preco_{curso['id']}"
                )
            
            with col6:
                split_custom = curso.get("split_custom", 10)
                if pago and is_admin:
                    split_custom = st.slider(
                        "Taxa da Plataforma (%)",
                        0, 100,
                        value=int(split_custom),
                        key=f"split_{curso['id']}"
                    )
                elif pago:
                    st.info(f"Taxa atual: {split_custom}%")
                    st.caption("Apenas administradores podem alterar")
            
            # Botões
            st.markdown("---")
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
            
            with col_btn2:
                submitted = st.form_submit_button(
                    "💾 Salvar Alterações",
                    type="primary",
                    use_container_width=True
                )
            
            with col_btn3:
                cancelar = st.form_submit_button(
                    "❌ Cancelar",
                    type="secondary",
                    use_container_width=True
                )
            
            if submitted:
                # Validações
                if not titulo.strip():
                    st.error("⚠️ O título é obrigatório")
                elif not descricao.strip():
                    st.error("⚠️ A descrição é obrigatória")
                else:
                    try:
                        _salvar_edicao_curso(
                            curso_id=curso["id"],
                            titulo=titulo,
                            descricao=descricao,
                            modalidade=modalidade,
                            publico=publico,
                            equipe_destino=equipe_destino,
                            pago=pago,
                            preco=preco,
                            split_custom=split_custom,
                            certificado_automatico=certificado_auto
                        )
                        
                        # Atualizar status ativo
                        _toggle_status_curso(curso["id"], ativo) 
                        
                        st.success("✅ Curso atualizado com sucesso!")
                        
                        # Limpar estado do modal e recarregar
                        st.session_state.pop('edit_curso', None)
                        st.session_state.pop('show_edit_modal', None)
                        st.rerun() 
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar: {str(e)}")
            
            if cancelar:
                st.session_state.pop('edit_curso', None)
                st.session_state.pop('show_edit_modal', None)
                st.rerun()
        
        # Fecha a estrutura do modal-content e modal-overlay
        st.markdown("</div></div>", unsafe_allow_html=True)
        
    # JavaScript para fechar o modal (agora apenas limpa o estado Streamlit)
    # A função closeModal deve ser modificada para apenas limpar o estado e dar rerun.
    st.markdown("""
    <script>
    function closeModal() {
        // Envia uma requisição para limpar o estado do modal no servidor
        // Usamos uma chamada ao Streamlit.setComponentValue para forçar o backend
        // a saber que o modal foi fechado, se necessário, mas o st.rerun() 
        // após o clique nos botões é a forma nativa de lidar com isso.
        
        // Como alternativa ao fetch/reload (que é o que estava causando problemas):
        // Clicar no 'X' na verdade deve disparar um evento que Streamlit entenda.
        // A forma mais fácil é fazer o 'X' ser um botão Streamlit invisível, 
        // mas a solução acima (cancelar) já resolve o problema de fechar o modal.
        
        // Deixamos a função JS vazia, pois o botão 'Cancelar' do Streamlit 
        // é o mecanismo primário de fechamento que atualiza o estado. 
        // O botão 'X' no HTML agora é puramente estético/visual, 
        // mas é melhor ter a função vazia do que quebrar o frontend.
    }
    </script>
    """, unsafe_allow_html=True)

# ======================================================
# VISÃO DO ALUNO MODERNA (Restante do código inalterado)
# ======================================================

# ... (restante do código: _interface_aluno_moderna, _aluno_cursos_disponiveis_moderno, _card_curso_aluno, _aluno_meus_cursos_moderno, _card_meu_curso, _salvar_edicao_curso, _toggle_status_curso)

def _salvar_edicao_curso(
    curso_id: str,
    titulo: str,
    descricao: str,
    modalidade: str,
    publico: str,
    equipe_destino: Optional[str],
    pago: bool,
    preco: Optional[float],
    split_custom: Optional[int],
    certificado_automatico: bool
):
    """Atualiza o documento do curso no Firestore."""
    db = get_db()
    
    safe_preco = float(preco) if (pago and preco is not None) else 0.0
    safe_split = int(split_custom) if split_custom is not None else 10

    doc_updates = {
        "titulo": titulo.strip(),
        "descricao": descricao.strip(),
        "modalidade": modalidade,
        "publico": publico,
        "equipe_destino": equipe_destino or None,
        "pago": bool(pago),
        "preco": safe_preco,
        "split_custom": safe_split,
        "certificado_automatico": bool(certificado_automatico),
    }

    db.collection("courses").document(curso_id).update(doc_updates)

def _toggle_status_curso(curso_id: str, novo_ativo: bool):
    """Ativa ou desativa o curso."""
    db = get_db()
    db.collection("courses").document(curso_id).update({
        "ativo": bool(novo_ativo),
        "status": "ativo" if novo_ativo else "inativo"
    })
