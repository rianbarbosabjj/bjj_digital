import streamlit as st
import time
import pandas as pd
from datetime import datetime
import utils as ce
import views.aulas as aulas_view 

try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"

def pagina_cursos(usuario):
    if 'cursos_view' not in st.session_state:
        st.session_state['cursos_view'] = 'lista'
    if 'curso_selecionado' not in st.session_state:
        st.session_state['curso_selecionado'] = None
    if 'editando_curso' not in st.session_state:
        st.session_state['editando_curso'] = False

    # Roteamento
    if st.session_state['cursos_view'] == 'conteudo':
        if st.session_state['curso_selecionado']:
            aulas_view.gerenciar_conteudo_curso(st.session_state['curso_selecionado'], usuario)
        else:
            st.session_state['cursos_view'] = 'lista'
            st.rerun()

    elif st.session_state['cursos_view'] == 'detalhe':
        exibir_detalhes_curso(usuario)

    else:
        listar_cursos(usuario)

def listar_cursos(usuario):
    st.subheader("Meus Cursos")
    
    # --- FORMULÁRIO DE CRIAÇÃO ---
    if usuario.get('tipo') in ['admin', 'professor', 'mestre']:
        with st.expander("Novo Curso"):
            with st.form("form_curso"):
                titulo = st.text_input("Título")
                desc = st.text_area("Descrição")
                
                # Novas Colunas para Modalidade e Público
                c1, c2 = st.columns(2)
                modalidade = c1.selectbox("Modalidade", ["EAD", "Presencial", "Híbrido"])
                publico_sel = c2.selectbox("Público Alvo", ["Aberto a Todos", "Restrito à Minha Equipe"])
                
                # Seleção de Editores (Outros Professores)
                st.markdown("---")
                st.markdown("###### Gestão Compartilhada")
                
                # Busca lista de usuários para seleção
                todos_usuarios = ce.listar_todos_usuarios_para_selecao()
                # Cria um dicionário {Nome: ID} para facilitar, removendo o próprio usuário da lista
                mapa_profs = {u['nome']: u['id'] for u in todos_usuarios if u['id'] != usuario['id']}
                lista_nomes_profs = list(mapa_profs.keys())
                
                editores_selecionados = st.multiselect(
                    "Professores Auxiliares (Editores)", 
                    options=lista_nomes_profs,
                    help="Selecione outros professores que poderão editar este curso."
                )
                
                # Converte os nomes selecionados de volta para IDs
                ids_editores = [mapa_profs[nome] for nome in editores_selecionados]
                
                st.markdown("---")
                preco = st.number_input("Preço (R$)", 0.0, step=10.0)
                
                if st.form_submit_button("Criar Curso"):
                    publico_val = 'equipe' if "Restrito" in publico_sel else 'todos'
                    equipe_dest = usuario.get('equipe', '') if publico_val == 'equipe' else ''
                    
                    ce.criar_curso(
                        usuario['id'], 
                        usuario['nome'], 
                        usuario.get('equipe',''), 
                        titulo, 
                        desc, 
                        modalidade,     
                        publico_val,    
                        equipe_dest,    
                        True, 
                        preco, 
                        False, 
                        False, 
                        10, 
                        'iniciante',
                        editores_ids=ids_editores # Passando a lista de editores
                    )
                    st.success("Curso criado com sucesso!")
                    time.sleep(1)
                    st.rerun()
    
    st.markdown("---")
    
    # --- LISTAGEM ---
    cursos = ce.listar_cursos_do_professor(usuario['id'])
    
    if not cursos:
        st.info("Nenhum curso encontrado.")
        return

    for c in cursos:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                # Mostra badges
                mod_badge = f"<span style='background:#333; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-right:5px'>{c.get('modalidade','EAD')}</span>"
                role_badge = ""
                if c.get('papel') == 'Editor':
                    role_badge = f"<span style='background:{COR_DESTAQUE}; color:#000; padding:2px 6px; border-radius:4px; font-size:0.7em'>Editor Convidado</span>"
                
                st.markdown(f"### {c.get('titulo')} {mod_badge} {role_badge}", unsafe_allow_html=True)
                st.caption(c.get('descricao', '')[:100] + "...")
            with col2:
                if st.button("Ver Detalhes", key=f"btn_ver_{c['id']}", use_container_width=True):
                    st.session_state['curso_selecionado'] = c
                    st.session_state['cursos_view'] = 'detalhe'
                    st.session_state['editando_curso'] = False
                    st.rerun()

def exibir_detalhes_curso(usuario):
    curso = st.session_state['curso_selecionado']
    
    if st.button("← Voltar à Lista"):
        st.session_state['cursos_view'] = 'lista'
        st.rerun()

    st.title(curso.get('titulo', 'Curso Sem Nome'))
    
    tab_sobre, tab_alunos = st.tabs(["📝 Visão Geral", "👥 Alunos & Rendimento"])
    
    # --- ABA GERAL ---
    with tab_sobre:
        col_actions, col_info = st.columns([1, 2])
        
        with col_actions:
            st.markdown("#### Ações")
            if st.button("➕ Gerenciar Conteúdo/Aulas", type="primary", use_container_width=True):
                st.session_state['cursos_view'] = 'conteudo'
                st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Botão Editar
            if st.button("✏️ Editar Informações", use_container_width=True):
                st.session_state['editando_curso'] = not st.session_state['editando_curso']
                st.rerun()
            
            # Botão Excluir (Só o dono pode excluir, editores não)
            eh_dono = curso.get('professor_id') == usuario['id']
            if eh_dono:
                if st.button("🗑️ Excluir Curso", type="secondary", use_container_width=True):
                     if ce.excluir_curso(curso['id']):
                         st.session_state['cursos_view'] = 'lista'
                         st.rerun()
            else:
                st.info("Apenas o dono pode excluir o curso.")

        with col_info:
            # === MODO DE EDIÇÃO ===
            if st.session_state['editando_curso']:
                with st.container(border=True):
                    st.markdown("##### ✏️ Editando Curso")
                    with st.form("form_editar_curso"):
                        novo_titulo = st.text_input("Título", value=curso.get('titulo', ''))
                        nova_desc = st.text_area("Descrição", value=curso.get('descricao', ''))
                        
                        c_ed1, c_ed2 = st.columns(2)
                        
                        # Modalidade
                        opcoes_mod = ["EAD", "Presencial", "Híbrido"]
                        idx_mod = 0
                        if curso.get('modalidade') in opcoes_mod:
                            idx_mod = opcoes_mod.index(curso.get('modalidade'))
                        nova_mod = c_ed1.selectbox("Modalidade", opcoes_mod, index=idx_mod)
                        
                        # Público
                        opcoes_pub = ["Aberto a Todos", "Restrito à Minha Equipe"]
                        idx_pub = 1 if curso.get('publico') == 'equipe' else 0
                        novo_pub_sel = c_ed2.selectbox("Público", opcoes_pub, index=idx_pub)
                        
                        # --- Edição de Editores ---
                        st.markdown("---")
                        st.markdown("###### Gestão Compartilhada")
                        todos_usuarios = ce.listar_todos_usuarios_para_selecao()
                        mapa_profs = {u['nome']: u['id'] for u in todos_usuarios if u['id'] != curso.get('professor_id')} # Exclui o dono da lista
                        
                        # Descobre quais nomes já são editores
                        editores_atuais_ids = curso.get('editores_ids', [])
                        nomes_pre_selecionados = [nome for nome, uid in mapa_profs.items() if uid in editores_atuais_ids]
                        
                        novos_editores_nomes = st.multiselect(
                            "Professores Auxiliares", 
                            options=list(mapa_profs.keys()),
                            default=nomes_pre_selecionados
                        )
                        novos_ids_editores = [mapa_profs[nome] for nome in novos_editores_nomes]
                        
                        st.markdown("---")
                        novo_preco = st.number_input("Preço (R$)", value=float(curso.get('preco', 0.0)), step=10.0)
                        
                        if st.form_submit_button("💾 Salvar Alterações"):
                            novo_pub_val = 'equipe' if "Restrito" in novo_pub_sel else 'todos'
                            equipe_dest = usuario.get('equipe', '') if novo_pub_val == 'equipe' else ''

                            dados_atualizados = {
                                "titulo": novo_titulo,
                                "descricao": nova_desc,
                                "modalidade": nova_mod,
                                "publico": novo_pub_val,
                                "equipe_destino": equipe_dest,
                                "preco": novo_preco,
                                "pago": novo_preco > 0,
                                "editores_ids": novos_ids_editores # Atualiza a lista de editores
                            }
                            
                            sucesso = ce.editar_curso(curso['id'], dados_atualizados)
                            if sucesso:
                                st.success("Curso atualizado!")
                                curso.update(dados_atualizados)
                                st.session_state['curso_selecionado'] = curso
                                st.session_state['editando_curso'] = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Erro ao atualizar.")
            
            # === MODO DE VISUALIZAÇÃO ===
            else:
                st.markdown(f"**Descrição:**\n{curso.get('descricao', 'Sem descrição')}")
                st.markdown("---")
                
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Professor:** {curso.get('professor_nome', '-')}")
                c2.markdown(f"**Equipe:** {curso.get('professor_equipe', '-')}")
                c3.markdown(f"**Preço:** R$ {curso.get('preco', 0):.2f}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                c4, c5 = st.columns(3)[:2]
                c4.markdown(f"**Modalidade:** {curso.get('modalidade', 'EAD')}")
                publico_display = "Restrito à Equipe" if curso.get('publico') == 'equipe' else "Aberto a Todos"
                c5.markdown(f"**Público:** {publico_display}")
                
                # Mostra quem são os editores (se houver)
                if curso.get('editores_ids'):
                    st.markdown("---")
                    st.markdown("**Professores Auxiliares:**")
                    # Busca os nomes apenas para exibir (opcional, requer query extra ou cache, 
                    # aqui simplificamos mostrando apenas quantidade ou se tivesse os nomes cacheados)
                    st.caption(f"{len(curso['editores_ids'])} professor(es) auxiliando neste curso.")

    # --- ABA FINANCEIRO ---
    with tab_alunos:
        st.markdown("### 📊 Indicadores")
        
        with st.spinner("Carregando dados..."):
            alunos = ce.listar_alunos_inscritos(curso['id'])
        
        total_alunos = len(alunos)
        preco_curso = float(curso.get('preco', 0))
        is_pago = curso.get('pago', False) or (preco_curso > 0)
        
        col_metrics = st.columns(3)
        col_metrics[0].metric("Total de Alunos", total_alunos, border=True)
        
        if is_pago:
            rendimento_real = total_alunos * preco_curso
            col_metrics[1].metric("Valor Unitário", f"R$ {preco_curso:.2f}", border=True)
            col_metrics[2].metric("Rendimento Alcançado", f"R$ {rendimento_real:,.2f}", border=True)
        else:
            col_metrics[1].metric("Tipo", "Gratuito", border=True)
            col_metrics[2].metric("Rendimento", "R$ 0,00", border=True)

        st.markdown("---")
        st.markdown("### 📋 Lista de Chamada")
        
        if alunos:
            df_alunos = pd.DataFrame(alunos)
            st.dataframe(
                df_alunos, 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Ainda não há alunos inscritos.")
