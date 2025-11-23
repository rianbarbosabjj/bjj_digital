import streamlit as st
import base64
import os
import sqlite3
import bcrypt
from config import COR_DESTAQUE, COR_TEXTO, COR_FUNDO, DB_PATH
from utils import formatar_e_validar_cpf, formatar_cep, buscar_cep

# =========================================
# 🏠 TELA INÍCIO (DO SEU PROJETO ORIGINAL)
# =========================================
def tela_inicio():
    
    # 1. 👇 FUNÇÃO DE CALLBACK PARA NAVEGAÇÃO
    def navigate_to(page_name):
        st.session_state.menu_selection = page_name

    # Logo centralizado
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='width:180px;max-width:200px;height:auto;margin-bottom:10px;'/>"
    else:
        logo_html = "<p style='color:red;'>Logo não encontrada.</p>"

    st.markdown(f"""
        <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;margin-bottom:30px;'>
            {logo_html}
            <h2 style='color:{COR_DESTAQUE};text-align:center;'>Painel BJJ Digital</h2>
            <p style='color:{COR_TEXTO};text-align:center;font-size:1.1em;'>Bem-vindo(a), {st.session_state.usuario['nome'].title()}!</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Cartões Principais (Para todos) ---
    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("<h3>🤼 Modo Rola</h3>", unsafe_allow_html=True) 
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Treino livre com questões aleatórias de todos os temas.</p> """, unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_rola", on_click=navigate_to, args=("Modo Rola",), use_container_width=True)

    with col2:
        with st.container(border=True):
            st.markdown("<h3>🥋 Exame de Faixa</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Realize sua avaliação teórica oficial quando liberada.</p> """, unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_exame", on_click=navigate_to, args=("Exame de Faixa",), use_container_width=True)
            
    with col3:
        with st.container(border=True):
            st.markdown("<h3>🏆 Ranking</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Veja sua posição e a dos seus colegas no Modo Rola.</p> """, unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_ranking", on_click=navigate_to, args=("Ranking",), use_container_width=True)

    # --- Cartões de Gestão (Admin/Professor) ---
    if st.session_state.usuario["tipo"] in ["admin", "professor"]:
        st.markdown("---")
        st.markdown(f"<h2 style='color:{COR_DESTAQUE};text-align:center; margin-top:30px;'>Painel de Gestão</h2>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.markdown("<h3>🧠 Gestão de Questões</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Adicione, edite ou remova questões dos temas.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_questoes", on_click=navigate_to, args=("Gestão de Questões",), use_container_width=True)
        with c2:
            with st.container(border=True):
                st.markdown("<h3>🏛️ Gestão de Equipes</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Gerencie equipes, professores e alunos vinculados.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_equipes", on_click=navigate_to, args=("Gestão de Equipes",), use_container_width=True)
        with c3:
            with st.container(border=True):
                st.markdown("<h3>📜 Gestão de Exame</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Monte as provas oficiais selecionando questões.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_exame", on_click=navigate_to, args=("Gestão de Exame",), use_container_width=True)
                
def tela_meu_perfil(usuario_logado):
    """Página para o usuário editar seu próprio perfil e senha, incluindo o CPF e Endereço."""
    
    st.markdown("<h1 style='color:#FFD700;'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
    st.markdown("Atualize suas informações pessoais, CPF e gerencie seu endereço.")

    user_id_logado = usuario_logado["id"]
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Busca os dados mais recentes do usuário no banco
    cursor.execute("SELECT * FROM usuarios WHERE id=?", (user_id_logado,))
    user_data = cursor.fetchone()
    
    if not user_data:
        st.error("Erro: Não foi possível carregar os dados do seu perfil.")
        conn.close()
        return

    # --- Expander 1: Informações Pessoais e Endereço ---
    with st.expander("📝 Informações Pessoais e Endereço", expanded=True):
        with st.form(key="form_edit_perfil"):
            st.markdown("#### 1. Informações de Contato")
            
            col1, col2 = st.columns(2)
            novo_nome = col1.text_input("Nome de Usuário:", value=user_data['nome'])
            novo_email = col2.text_input("Email:", value=user_data['email'])
            
            # 📌 CPF com Máscara Visual
            cpf_limpo_db = user_data['cpf'] or ""
            novo_cpf_input = st.text_input("CPF (somente números):", value=cpf_limpo_db, key="perfil_cpf_input")
            cpf_display_limpo = formatar_e_validar_cpf(novo_cpf_input)
            if cpf_display_limpo:
                st.info(f"CPF Formatado: {cpf_display_limpo[:3]}.{cpf_display_limpo[3:6]}.{cpf_display_limpo[6:9]}-{cpf_display_limpo[9:]}")
            
            st.markdown("#### 2. Endereço")
            
            # Inicializa variáveis de endereço com dados do banco
            st.session_state.setdefault('endereco_cep', {
                'cep': user_data['cep'] or "", 
                'logradouro': user_data['logradouro'] or "", 
                'bairro': user_data['bairro'] or "", 
                'cidade': user_data['cidade'] or "", 
                'uf': user_data['uf'] or ""
            })
            
            # Sincroniza chaves dos widgets com o estado de sessão (necessário para edição manual e CEP)
            st.session_state.setdefault('perfil_logradouro', st.session_state.endereco_cep['logradouro'])
            st.session_state.setdefault('perfil_bairro', st.session_state.endereco_cep['bairro'])
            st.session_state.setdefault('perfil_cidade', st.session_state.endereco_cep['cidade'])
            st.session_state.setdefault('perfil_uf', st.session_state.endereco_cep['uf'])
            st.session_state.setdefault('perfil_cep_input', st.session_state.endereco_cep['cep'])


            col_cep, col_btn = st.columns([3, 1])
            with col_cep:
                # O input agora está ligado à sua chave de sessão
                novo_cep = st.text_input("CEP:", max_chars=9, key='perfil_cep_input')
                # 📌 Máscara Visual CEP
                cep_digitado_limpo = formatar_cep(novo_cep)
                if cep_digitado_limpo:
                     st.info(f"CEP Formatado: {cep_digitado_limpo[:5]}-{cep_digitado_limpo[5:]}")

            with col_btn:
                st.markdown("<div style='height: 29px;'></div>", unsafe_allow_html=True)
                if st.form_submit_button("Buscar CEP 🔍", type="secondary", use_container_width=True, help="Busca o endereço antes de salvar o perfil"):
                    cep_digitado = st.session_state.perfil_cep_input
                    endereco = buscar_cep(cep_digitado)
                    
                    if endereco:
                        st.session_state.endereco_cep = {
                            'cep': novo_cep,
                            **endereco
                        }
                        # AÇÃO CRÍTICA: Atualiza o valor interno de CADA WIDGET via chave de sessão
                        st.session_state['perfil_logradouro'] = endereco['logradouro']
                        st.session_state['perfil_bairro'] = endereco['bairro']
                        st.session_state['perfil_cidade'] = endereco['cidade']
                        st.session_state['perfil_uf'] = endereco['uf']
                        
                        st.success("Endereço encontrado e campos preenchidos! Preencha Número e Complemento.")
                    else:
                        st.error("CEP inválido ou não encontrado.")
                    st.rerun() 
            
            # CAMPOS HABILITADOS (Lendo diretamente da chave de sessão)
            col_logr, col_bairro = st.columns(2)
            novo_logradouro = col_logr.text_input("Logradouro:", key='perfil_logradouro')
            novo_bairro = col_bairro.text_input("Bairro:", key='perfil_bairro')

            col_cidade, col_uf = st.columns(2)
            novo_cidade = col_cidade.text_input("Cidade:", key='perfil_cidade')
            novo_uf = col_uf.text_input("UF:", key='perfil_uf')
            
            # Campos Número e Complemento (Opcionais)
            col_num, col_comp = st.columns(2)
            novo_numero = col_num.text_input("Número (Opcional):", value=user_data['numero'] or "", key='perfil_numero')
            novo_complemento = col_comp.text_input("Complemento (Opcional):", value=user_data['complemento'] or "", key='perfil_complemento')
            
            
            st.text_input("Tipo de Perfil:", value=user_data['tipo_usuario'].capitalize(), disabled=True)
            
            submitted_info = st.form_submit_button("💾 Salvar Alterações", use_container_width=True, type="primary")
            
            if submitted_info:
                
                # 🚨 Formatação e Validação Final
                cpf_final = formatar_e_validar_cpf(st.session_state.perfil_cpf_input)
                cep_final = formatar_cep(st.session_state.perfil_cep_input)

                if not (novo_nome and novo_email):
                    st.warning("Nome e Email são obrigatórios.")
                elif not cpf_final:
                    st.error("CPF inválido. Por favor, corrija o formato (11 dígitos).")
                else:
                    try:
                        cursor.execute(
                            """
                            UPDATE usuarios SET nome=?, email=?, cpf=?, cep=?, logradouro=?, numero=?, complemento=?, bairro=?, cidade=?, uf=? WHERE id=?
                            """,
                            (
                                novo_nome.upper(), # 👈 MAIÚSCULO
                                novo_email.upper(), # 👈 MAIÚSCULO
                                cpf_final, # 👈 FORMATADO
                                cep_final, # 👈 FORMATADO
                                novo_logradouro.upper(), # 👈 MAIÚSCULO
                                novo_numero.upper() if novo_numero else None, # 👈 MAIÚSCULO (Opcional)
                                novo_complemento.upper() if novo_complemento else None, # 👈 MAIÚSCULO (Opcional)
                                novo_bairro.upper(), # 👈 MAIÚSCULO
                                novo_cidade.upper(), # 👈 MAIÚSCULO
                                novo_uf.upper(), # 👈 MAIÚSCULO
                                user_id_logado
                            )
                        )
                        conn.commit()
                        st.success("Dados e Endereço atualizados com sucesso!")
                        
                        st.session_state.usuario['nome'] = novo_nome
                        st.rerun() 
                        
                    except sqlite3.IntegrityError:
                        st.error(f"Erro: O email '{novo_email}' ou o CPF já está em uso por outro usuário.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")

    # --- Expander 2: Alteração de Senha (Inalterada) ---
    if user_data['auth_provider'] == 'local':
        with st.expander("🔑 Alterar Senha", expanded=False):
            with st.form(key="form_change_pass"):
                st.markdown("#### Redefinir Senha")
                
                senha_atual = st.text_input("Senha Atual:", type="password")
                nova_senha = st.text_input("Nova Senha:", type="password")
                confirmar_senha = st.text_input("Confirmar Nova Senha:", type="password")
                
                submitted_pass = st.form_submit_button("🔑 Alterar Senha", use_container_width=True)
                
                if submitted_pass:
                    if not senha_atual or not nova_senha or not confirmar_senha:
                        st.warning("Por favor, preencha todos os campos de senha.")
                    elif nova_senha != confirmar_senha:
                        st.error("As novas senhas não coincidem.")
                    else:
                        # Verifica a senha atual
                        hash_atual_db = user_data['senha']
                        if bcrypt.checkpw(senha_atual.encode(), hash_atual_db.encode()):
                            # Se a senha atual estiver correta, atualiza
                            novo_hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
                            cursor.execute(
                                "UPDATE usuarios SET senha=? WHERE id=?",
                                (novo_hash, user_id_logado)
                            )
                            conn.commit()
                            st.success("Senha alterada com sucesso!")
                        else:
                            st.error("A 'Senha Atual' está incorreta.")
    else:
        st.info(f"Seu login é gerenciado pelo **{user_data['auth_provider'].capitalize()}**.")

    conn.close()
