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
    user_ref = db.collection('usuarios').document(usuario_logado['id'])
    ud = user_ref.get().to_dict()
    if not ud: st.error("Erro dados."); return

    with st.expander("📝 Dados Pessoais", expanded=True):
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
            
            # FORMATO DD/MM/YYYY
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

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
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
                st.session_state.usuario['nome'] = nm.upper()
                st.success("✅ Perfil atualizado!"); time.sleep(1); st.rerun()
