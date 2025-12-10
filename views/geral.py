import streamlit as st
import base64
import os
import time
from datetime import datetime, date
from config import COR_DESTAQUE, COR_TEXTO, COR_FUNDO, COR_BOTAO
from utils import formatar_e_validar_cpf, buscar_cep
from database import get_db, OPCOES_SEXO

def render_card(titulo, descricao, texto_botao, chave_botao, pagina_destino):
    with st.container(border=True):
        st.markdown(f"<h3>{titulo}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; min-height: 60px;'>{descricao}</p>", unsafe_allow_html=True)
        if st.button(texto_botao, key=chave_botao, use_container_width=True):
            st.session_state.menu_selection = pagina_destino
            st.rerun()

def get_logo_path_geral():
    if os.path.exists("assets/logo.jpg"): return "assets/logo.jpg"
    if os.path.exists("logo.jpg"): return "logo.jpg"
    if os.path.exists("assets/logo.png"): return "assets/logo.png"
    if os.path.exists("logo.png"): return "logo.png"
    return None

def tela_inicio():
    logo_path = get_logo_path_geral()
    logo_html = ""
    
    if logo_path:
        with open(logo_path, "rb") as f: 
            b64 = base64.b64encode(f.read()).decode()
        mime = "image/png" if logo_path.endswith(".png") else "image/jpeg"
        logo_html = f"<img src='data:{mime};base64,{b64}' style='width:180px;max-width:200px;margin-bottom:10px;'/>"

    st.markdown(f"<div style='display:flex;flex-direction:column;align-items:center;margin-bottom:30px;'>{logo_html}<h2 style='color:{COR_DESTAQUE};text-align:center;'>Painel BJJ Digital</h2><p style='color:{COR_TEXTO};text-align:center;'>Bem-vindo(a), {st.session_state.usuario['nome'].title()}!</p></div>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1: render_card("🤼 Modo Rola", "Treino livre.", "Acessar", "n1", "Modo Rola")
    with col2: render_card("🥋 Exame de Faixa", "Avaliação teórica.", "Acessar", "n2", "Exame de Faixa")
    with col3: render_card("🏆 Ranking", "Posição no ranking.", "Acessar", "n3", "Ranking")

    tipo = str(st.session_state.usuario.get("tipo", "aluno")).lower()
    if tipo in ["admin", "professor"]:
        st.markdown("---"); st.markdown(f"<h2 style='color:{COR_DESTAQUE};text-align:center;'>Gestão</h2>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: render_card("🧠 Questões", "Editar banco.", "Gerenciar", "g1", "Gestão de Questões")
        with c2: render_card("🏛️ Equipes", "Gerenciar equipes.", "Gerenciar", "g2", "Gestão de Equipes")
        with c3: render_card("📜 Exames", "Montar provas.", "Gerenciar", "g3", "Gestão de Exame")

def tela_meu_perfil(usuario_logado):
    if st.button("🏠 Voltar ao Início", key="btn_voltar_perfil"):
        st.session_state.menu_selection = "Início"; st.rerun()

    st.markdown("<h1 style='color:#FFD700;'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
    db = get_db()
    
    # 1. Carrega Dados do Usuário
    user_ref = db.collection('usuarios').document(usuario_logado['id'])
    ud = user_ref.get().to_dict()
    if not ud: st.error("Erro ao carregar dados."); return

    # 2. Carrega Listas de Equipes e Professores (Para os Selectbox)
    equipes_ref = list(db.collection('equipes').stream())
    mapa_equipes = {d.id: d.to_dict().get('nome', 'Sem Nome') for d in equipes_ref} 
    mapa_equipes_inv = {v: k for k, v in mapa_equipes.items()} 
    lista_equipes = ["Sem Equipe"] + sorted(list(mapa_equipes.values()))

    # --- LÓGICA DE MAPA DE PROFESSORES (Carregamento Prévio) ---
    profs_users = list(db.collection('usuarios').where('tipo_usuario', '==', 'professor').stream())
    mapa_nomes_profs = {u.id: u.to_dict().get('nome', 'Sem Nome') for u in profs_users}
    mapa_nomes_profs_inv = {v: k for k, v in mapa_nomes_profs.items()} # Nome -> ID

    # Carrega vínculos ativos de professores com equipes
    vincs_profs = list(db.collection('professores').where('status_vinculo', '==', 'ativo').stream())
    
    # Dicionário: { 'ID_DA_EQUIPE': ['Nome Prof A', 'Nome Prof B'] }
    profs_por_equipe = {}
    
    for v in vincs_profs:
        d = v.to_dict()
        eid = d.get('equipe_id')
        uid = d.get('usuario_id')
        
        if eid and uid and uid in mapa_nomes_profs:
            if eid not in profs_por_equipe:
                profs_por_equipe[eid] = []
            profs_por_equipe[eid].append(mapa_nomes_profs[uid])
    # -----------------------------------------------------------

    # Busca Vínculo Atual do Usuário (Para pré-selecionar no form)
    tipo_user = ud.get('tipo_usuario', 'aluno')
    vinculo_equipe_id = None
    vinculo_prof_id = None
    doc_vinculo_id = None 

    if tipo_user == 'aluno':
        vincs = list(db.collection('alunos').where('usuario_id', '==', usuario_logado['id']).limit(1).stream())
        if vincs:
            doc_vinculo_id = vincs[0].id
            d_vinc = vincs[0].to_dict()
            vinculo_equipe_id = d_vinc.get('equipe_id')
            vinculo_prof_id = d_vinc.get('professor_id')

    elif tipo_user == 'professor':
        vincs = list(db.collection('professores').where('usuario_id', '==', usuario_logado['id']).limit(1).stream())
        if vincs:
            doc_vinculo_id = vincs[0].id
            d_vinc = vincs[0].to_dict()
            vinculo_equipe_id = d_vinc.get('equipe_id')

    # --- INÍCIO DO FORMULÁRIO ---
    with st.expander("📝 Editar Meus Dados", expanded=True):
        with st.form("f_p"):
            st.markdown("##### Informações Básicas")
            c1, c2 = st.columns(2)
            nm = c1.text_input("Nome:", value=ud.get('nome',''))
            c2.text_input("Email:", value=ud.get('email',''), disabled=True)
            
            c3, c4, c5 = st.columns([1.5, 1, 1])
            cpf_atual = ud.get('cpf', '')
            c3.text_input("CPF:", value=cpf_atual, disabled=True, help="Para alterar o CPF, contate o administrador.")
            
            # --- SEXO ---
            sexo_atual = ud.get('sexo', 'Masculino')
            idx_sexo = 0
            if sexo_atual in OPCOES_SEXO: idx_sexo = OPCOES_SEXO.index(sexo_atual)
            novo_sexo = c4.selectbox("Sexo:", OPCOES_SEXO, index=idx_sexo)

            # --- DATA DE NASCIMENTO ---
            nasc_str = ud.get('data_nascimento')
            val_nasc = None
            if nasc_str:
                try: val_nasc = datetime.fromisoformat(nasc_str).date()
                except: val_nasc = None
            
            nova_nasc = c5.date_input("Nascimento:", value=val_nasc, min_value=date(1940,1,1), max_value=date.today(), format="DD/MM/YYYY")

            st.markdown("---")
            st.markdown("##### Endereço")
            
            if 'p_cep' not in st.session_state: st.session_state.p_cep = ud.get('cep','')
            cc, cb = st.columns([3,1])
            n_cep = cc.text_input("CEP:", value=st.session_state.p_cep, key="k_cep")
            if cb.form_submit_button("🔍 Buscar"): 
                end = buscar_cep(n_cep)
                if end: st.session_state.p_end = end; st.rerun()
            
            e_b = st.session_state.get('p_end', ud)
            c_rua, c_bairro = st.columns(2)
            lg = c_rua.text_input("Logradouro:", value=e_b.get('logradouro',''))
            br = c_bairro.text_input("Bairro:", value=e_b.get('bairro',''))
            
            c_cid, c_uf = st.columns(2)
            cd = c_cid.text_input("Cidade:", value=e_b.get('cidade',''))
            uf = c_uf.text_input("UF:", value=e_b.get('uf',''))

            st.markdown("---")
            st.markdown("##### 🥋 Vínculo Acadêmico")
            
            v1, v2 = st.columns(2)
            
            # --- SELEÇÃO DE EQUIPE ---
            # Pré-seleciona a equipe do banco
            nome_eq_atual = mapa_equipes.get(vinculo_equipe_id, "Sem Equipe")
            idx_eq = lista_equipes.index(nome_eq_atual) if nome_eq_atual in lista_equipes else 0
            
            # O usuário escolhe a nova equipe aqui. Ao mudar, o Streamlit vai rodar tudo de novo.
            # E na próxima linha, usaremos essa 'nova_equipe_nome' para filtrar.
            nova_equipe_nome = v1.selectbox("Minha Equipe:", lista_equipes, index=idx_eq)
            
            # --- SELEÇÃO DE PROFESSOR (Dinâmica) ---
            novo_prof_display = "Sem Professor(a)"
            
            if tipo_user == 'aluno':
                # 1. Descobre o ID da equipe que o usuário ACABOU de escolher no selectbox acima
                id_equipe_selecionada = mapa_equipes_inv.get(nova_equipe_nome)
                
                # 2. Busca lista de professores DESSA equipe específica
                lista_profs_filtrada = ["Sem Professor(a)"]
                if id_equipe_selecionada in profs_por_equipe:
                    lista_profs_filtrada += sorted(profs_por_equipe[id_equipe_selecionada])
                
                # 3. Tenta manter o professor atual selecionado, MAS SÓ SE ele estiver na nova equipe
                nome_prof_atual_display = mapa_nomes_profs.get(vinculo_prof_id, "Sem Professor(a)")
                idx_prof = 0
                if nome_prof_atual_display in lista_profs_filtrada:
                    idx_prof = lista_profs_filtrada.index(nome_prof_atual_display)
                
                # 4. Renderiza o selectbox filtrado
                novo_prof_display = v2.selectbox("Meu Professor(a):", lista_profs_filtrada, index=idx_prof)
                
                if nova_equipe_nome == "Sem Equipe":
                    v2.caption("Selecione uma equipe para ver os professores.")
            else:
                v2.info("Professores gerenciam seus próprios alunos(as).")

            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- SALVAR ---
            if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                # 1. Atualiza Dados Pessoais (Usuario)
                updates = {
                    "nome": nm.upper(),
                    "sexo": novo_sexo,
                    "data_nascimento": nova_nasc.isoformat() if nova_nasc else None,
                    "cep": n_cep,
                    "logradouro": lg.upper(),
                    "bairro": br.upper(),
                    "cidade": cd.upper(),
                    "uf": uf.upper()
                }
                user_ref.update(updates)
                
                # 2. Atualiza Vínculos (Alunos/Professores)
                try:
                    novo_eq_id = mapa_equipes_inv.get(nova_equipe_nome)
                    
                    if tipo_user == 'aluno':
                        novo_p_id = mapa_nomes_profs_inv.get(novo_prof_display)
                        dados_vinc = {"equipe_id": novo_eq_id, "professor_id": novo_p_id}
                        
                        if doc_vinculo_id: # Atualiza existente
                            db.collection('alunos').document(doc_vinculo_id).update(dados_vinc)
                        else: # Cria novo
                            dados_vinc['usuario_id'] = usuario_logado['id']
                            dados_vinc['status_vinculo'] = 'ativo'
                            dados_vinc['faixa_atual'] = ud.get('faixa_atual', 'Branca')
                            db.collection('alunos').add(dados_vinc)
                            
                    elif tipo_user == 'professor':
                        dados_vinc = {"equipe_id": novo_eq_id}
                        if doc_vinculo_id:
                            db.collection('professores').document(doc_vinculo_id).update(dados_vinc)
                        else:
                            dados_vinc['usuario_id'] = usuario_logado['id']
                            dados_vinc['status_vinculo'] = 'ativo'
                            db.collection('professores').add(dados_vinc)

                    # Atualiza sessão local
                    st.session_state.usuario['nome'] = nm.upper()
                    st.success("✅ Perfil atualizado com sucesso!"); time.sleep(1.5); st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao salvar vínculos: {e}")
