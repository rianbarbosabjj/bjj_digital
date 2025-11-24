import streamlit as st
import pandas as pd
import bcrypt
from database import get_db
from utils import formatar_e_validar_cpf, carregar_questoes, salvar_questoes, carregar_todas_questoes
import os
import json
from datetime import datetime

# =========================================
# GESTÃO DE USUÁRIOS
# =========================================
def gestao_usuarios(usuario_logado):
    """Página de gerenciamento de usuários (Admin)."""
    
    # 🔒 Restrição de Acesso
    if usuario_logado["tipo"] != "admin":
        st.error("Acesso negado. Esta página é restrita aos administradores.")
        return

    st.markdown("<h1 style='color:#FFD700;'>🔑 Gestão de Usuários</h1>", unsafe_allow_html=True)
    st.markdown("Edite informações ou altere o tipo de perfil de um usuário.")

    db = get_db()
    
    # 1. Busca todos os usuários do Firestore
    docs = db.collection('usuarios').stream()
    lista_usuarios = []
    
    for doc in docs:
        d = doc.to_dict()
        d['id_doc'] = doc.id # Guarda o ID do documento para updates
        # Garante campos padrão para evitar erro no DataFrame
        d.setdefault('cpf', '')
        d.setdefault('tipo_usuario', 'aluno')
        d.setdefault('auth_provider', 'local')
        d.setdefault('perfil_completo', False)
        lista_usuarios.append(d)
        
    if not lista_usuarios:
        st.info("Nenhum usuário encontrado.")
        return

    # Cria DataFrame para exibição
    df = pd.DataFrame(lista_usuarios)
    
    st.subheader("Visão Geral dos Usuários")
    # Exibe apenas colunas relevantes
    colunas_exibir = ['nome', 'email', 'tipo_usuario', 'cpf', 'auth_provider']
    # Filtra colunas que existem no DF
    cols = [c for c in colunas_exibir if c in df.columns]
    st.dataframe(df[cols], use_container_width=True)
    st.markdown("---")

    st.subheader("Editar Usuário")
    
    # Seletor de usuário
    nomes = df["nome"].tolist()
    nome_selecionado = st.selectbox(
        "Selecione um usuário para gerenciar:",
        options=nomes,
        index=None,
        placeholder="Selecione..."
    )

    if nome_selecionado:
        # Pega os dados do usuário selecionado (usando o ID do doc para garantir unicidade)
        # Nota: Se tiver nomes iguais, isso pega o primeiro. O ideal seria selecionar por Email ou ID.
        user_row = df[df["nome"] == nome_selecionado].iloc[0]
        user_id = user_row['id_doc']
        
        # Busca dados frescos do banco
        user_ref = db.collection('usuarios').document(user_id)
        user_data = user_ref.get().to_dict()

        if not user_data:
            st.error("Erro ao carregar dados do usuário.")
            return

        with st.expander(f"Gerenciando: {user_data.get('nome')}", expanded=True):
            with st.form(key="form_edit_user_admin"):
                st.markdown("#### 1. Informações do Perfil")
                
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("Nome:", value=user_data.get('nome', ''))
                novo_email = c2.text_input("Email:", value=user_data.get('email', ''))
                
                novo_cpf = st.text_input("CPF:", value=user_data.get('cpf', ''))
                cpf_fmt = formatar_e_validar_cpf(novo_cpf)
                if cpf_fmt: st.caption(f"CPF Válido: {cpf_fmt}")
                
                tipo_atual = user_data.get('tipo_usuario', 'aluno')
                opcoes_tipo = ["aluno", "professor", "admin"]
                try: idx_tipo = opcoes_tipo.index(tipo_atual)
                except: idx_tipo = 0
                
                novo_tipo = st.selectbox("Tipo de Usuário:", options=opcoes_tipo, index=idx_tipo)
                
                st.text_input("Provedor:", value=user_data.get('auth_provider', 'local'), disabled=True)
                
                if st.form_submit_button("💾 Salvar Alterações"):
                    if novo_cpf and not cpf_fmt:
                        st.error("CPF inválido.")
                    else:
                        try:
                            user_ref.update({
                                "nome": novo_nome.upper(),
                                "email": novo_email.lower().strip(),
                                "cpf": cpf_fmt,
                                "tipo_usuario": novo_tipo
                            })
                            st.success("Usuário atualizado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar: {e}")

            st.markdown("---")

            # Reset de Senha (Apenas para contas locais)
            if user_data.get('auth_provider') == 'local':
                st.markdown("#### 2. Redefinição de Senha")
                with st.form(key="form_reset_pass_admin"):
                    nova_senha = st.text_input("Nova Senha:", type="password")
                    conf_senha = st.text_input("Confirmar Nova Senha:", type="password")
                    
                    if st.form_submit_button("🔑 Redefinir Senha"):
                        if not nova_senha or nova_senha != conf_senha:
                            st.error("Senhas inválidas ou não conferem.")
                        else:
                            hash_senha = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
                            user_ref.update({"senha": hash_senha})
                            st.success("Senha redefinida!")
            else:
                st.info(f"Este usuário faz login via {user_data.get('auth_provider')}, não é possível alterar a senha aqui.")

# =========================================
# GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes():
    """Adicionar, editar ou remover questões dos arquivos JSON."""
    
    usuario_logado = st.session_state.usuario
    
    # Verificação de permissão (Admin ou Professor Ativo)
    permitido = False
    if usuario_logado["tipo"] == "admin":
        permitido = True
    elif usuario_logado["tipo"] == "professor":
        # Verifica se professor está ativo no Firestore
        db = get_db()
        # A busca por professor é um pouco mais complexa pois o ID do usuário está dentro do documento
        prof_docs = db.collection('professores')\
                      .where('usuario_id', '==', usuario_logado['id'])\
                      .where('status_vinculo', '==', 'ativo').stream()
        if list(prof_docs): # Se encontrou algum registro ativo
            permitido = True
            
    if not permitido:
        st.error("Acesso negado. Apenas Admins ou Professores ativos.")
        return
    
    st.markdown("<h1 style='color:#FFD700;'>🧠 Gestão de Questões</h1>", unsafe_allow_html=True)

    # Listar temas (lê da pasta local 'questions')
    os.makedirs("questions", exist_ok=True)
    temas_existentes = [f.replace(".json", "") for f in os.listdir("questions") if f.endswith(".json")]
    
    c1, c2 = st.columns([3, 1])
    with c1:
        tema_selecionado = st.selectbox("Tema:", ["Novo Tema"] + temas_existentes)
    
    novo_tema_nome = ""
    if tema_selecionado == "Novo Tema":
        with c2:
            novo_tema_nome = st.text_input("Nome do novo tema:")
        tema_atual = novo_tema_nome
    else:
        tema_atual = tema_selecionado

    # Carrega questões do arquivo JSON
    questoes = carregar_questoes(tema_atual) if tema_atual else []

    st.markdown("### ✍️ Adicionar nova questão")
    with st.expander("Expandir para adicionar questão", expanded=False):
        with st.form(key="form_add_questao"):
            pergunta = st.text_area("Pergunta:")
            
            c_opts = st.columns(5)
            opcoes = []
            letras = ["A", "B", "C", "D", "E"]
            for i, l in enumerate(letras):
                opcoes.append(c_opts[i].text_input(f"Opção {l}:"))
                
            resposta = st.selectbox("Resposta Correta:", letras)
            
            c_midia = st.columns(2)
            imagem = c_midia[0].text_input("Caminho da Imagem (opcional):")
            video = c_midia[1].text_input("URL do Vídeo (opcional):")

            if st.form_submit_button("💾 Salvar Questão"):
                if pergunta.strip() and tema_atual.strip():
                    # Formata opções: "A) Texto"
                    opts_formatadas = [f"{l}) {txt}" for l, txt in zip(letras, opcoes) if txt.strip()]
                    
                    if len(opts_formatadas) < 2:
                        st.error("Adicione pelo menos 2 alternativas.")
                    else:
                        nova = {
                            "pergunta": pergunta.strip(),
                            "opcoes": opts_formatadas,
                            "resposta": resposta,
                            "imagem": imagem.strip(),
                            "video": video.strip(),
                        }
                        questoes.append(nova)
                        salvar_questoes(tema_atual, questoes)
                        st.success(f"Questão salva em '{tema_atual}'!")
                        st.rerun()
                else:
                    st.error("Preencha a pergunta e o nome do tema.")

    st.markdown("### 📚 Questões cadastradas neste tema")
    if not questoes:
        st.info("Nenhuma questão cadastrada.")
    else:
        for i, q in enumerate(questoes):
            with st.expander(f"{i+1}. {q['pergunta']}"):
                st.write(q['opcoes'])
                st.caption(f"Resposta: {q['resposta']}")
                if st.button("🗑️ Excluir", key=f"del_q_{i}"):
                    questoes.pop(i)
                    salvar_questoes(tema_atual, questoes)
                    st.rerun()

# =========================================
# GESTÃO DE EXAME DE FAIXA
# =========================================
def gestao_exame_de_faixa():
    """Montar provas selecionando questões dos temas."""
    
    st.markdown("<h1 style='color:#FFD700;'>🥋 Gestão de Exame de Faixa</h1>", unsafe_allow_html=True)

    os.makedirs("exames", exist_ok=True)
    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa = st.selectbox("Selecione a faixa para editar o exame:", faixas)

    exame_path = f"exames/faixa_{faixa.lower()}.json"
    
    # Carrega exame existente ou cria novo
    if os.path.exists(exame_path):
        try:
            with open(exame_path, "r", encoding="utf-8") as f: exame = json.load(f)
        except: exame = {}
    else:
        exame = {}

    # Estrutura base
    exame.setdefault("questoes", [])
    exame.setdefault("faixa", faixa)

    # Carrega TODAS as questões disponíveis nos arquivos de temas
    todas = carregar_todas_questoes()
    
    if not todas:
        st.warning("Nenhuma questão encontrada nos temas. Cadastre questões primeiro.")
        return

    # Filtro de visualização
    temas_disp = sorted(list(set(q["tema"] for q in todas)))
    filtro = st.selectbox("Filtrar questões disponíveis por tema:", ["Todos"] + temas_disp)
    
    if filtro != "Todos":
        questoes_exibir = [q for q in todas if q["tema"] == filtro]
    else:
        questoes_exibir = todas

    # Identifica quais já estão no exame (para não duplicar)
    perguntas_no_exame = [q['pergunta'] for q in exame['questoes']]
    
    st.markdown("### ✅ Adicionar Questões ao Exame")
    
    with st.form(key="form_add_exame"):
        selecionadas = []
        for i, q in enumerate(questoes_exibir):
            # Só mostra se não estiver no exame
            if q['pergunta'] not in perguntas_no_exame:
                if st.checkbox(f"{q['tema']} | {q['pergunta']}", key=f"chk_{i}"):
                    selecionadas.append(q)
        
        if st.form_submit_button("➕ Adicionar Selecionadas"):
            if selecionadas:
                exame['questoes'].extend(selecionadas)
                # Salva
                with open(exame_path, "w", encoding="utf-8") as f:
                    json.dump(exame, f, indent=4, ensure_ascii=False)
                st.success(f"{len(selecionadas)} questões adicionadas!")
                st.rerun()
            else:
                st.warning("Selecione pelo menos uma questão.")

    st.markdown("---")
    st.markdown(f"### 📋 Questões no Exame da Faixa {faixa} ({len(exame['questoes'])})")
    
    if not exame['questoes']:
        st.info("O exame está vazio.")
    else:
        for i, q in enumerate(exame['questoes']):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.write(f"**{i+1}.** [{q.get('tema','?')}] {q['pergunta']}")
            with c2:
                if st.button("Remover", key=f"rem_ex_{i}"):
                    exame['questoes'].pop(i)
                    with open(exame_path, "w", encoding="utf-8") as f:
                        json.dump(exame, f, indent=4, ensure_ascii=False)
                    st.rerun()
