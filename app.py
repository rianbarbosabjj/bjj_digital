import streamlit as st
import os
import sys
from datetime import datetime

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

# ---------------------------------------------------------
# ESTILOS VISUAIS (PWA & TEMA)
# ---------------------------------------------------------
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)

from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');
.stButton>button {{ 
    background: linear-gradient(90deg, {COR_BOTAO}, #056853); 
    color: white; font-weight: bold; border: none; 
    padding: 0.6em 1.2em; border-radius: 10px; transition: 0.3s; 
}}
.stButton>button:hover {{ 
    background: {COR_HOVER}; color: {COR_FUNDO}; transform: scale(1.02); 
}}
h1, h2, h3 {{ color: {COR_DESTAQUE}; text-align: center; font-weight: 700; }}
div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {{ border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)

# Hack para Render/Railway
if "SECRETS_TOML" in os.environ:
    if not os.path.exists(".streamlit"): os.makedirs(".streamlit")
    with open(".streamlit/secrets.toml", "w") as f: f.write(os.environ["SECRETS_TOML"])

try:
    from streamlit_option_menu import option_menu
    from database import get_db 
    from views import login, geral, aluno, professor, admin
except ImportError as e:
    st.error(f"❌ Erro crítico: {e}")
    st.stop()

# =========================================
# TELA DE VERIFICAÇÃO PÚBLICA (HTML PERSONALIZADO)
# =========================================
def tela_verificacao(codigo):
    # Limpeza do código
    codigo_limpo = codigo.strip()
    
    # Busca no Firestore
    db = get_db()
    docs = list(db.collection('resultados').where('codigo_verificacao', '==', codigo_limpo).stream())
    
    if docs:
        dados = docs[0].to_dict()
        
        # Formata dados para exibição
        aluno_nome = dados.get('usuario', 'Desconhecido').upper()
        faixa = dados.get('faixa', 'N/A').upper()
        nota = dados.get('pontuacao', 0)
        
        data_raw = dados.get('data')
        data_str = "N/A"
        if data_raw:
            try:
                # Se for datetime (Firestore) ou string ISO
                if isinstance(data_raw, datetime):
                    data_str = data_raw.strftime("%d/%m/%Y às %H:%M")
                elif isinstance(data_raw, str):
                    data_str = datetime.fromisoformat(data_raw).strftime("%d/%m/%Y")
            except: pass

        # HTML/CSS Personalizado (Baseado no seu pedido)
        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
          <meta charset="UTF-8">
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');
            .verify-container {{
              font-family: 'Poppins', sans-serif;
              background-color: #0e2d26;
              color: #fff;
              text-align: center;
              padding: 40px 20px;
              border-radius: 15px;
              border: 1px solid #333;
            }}
            h1 {{ color: #FFD700; margin-bottom: 10px; }}
            .box {{
              border: 2px solid #FFD700;
              border-radius: 15px;
              display: inline-block;
              padding: 30px 50px;
              margin-top: 20px;
              background-color: #113830;
              box-shadow: 0 4px 15px rgba(0,0,0,0.3);
              max-width: 600px;
              width: 100%;
            }}
            .valid-icon {{ font-size: 40px; margin-bottom: 10px; display: block; }}
            .info-label {{ color: #aaa; font-size: 0.9em; margin-bottom: 2px; text-transform: uppercase; letter-spacing: 1px; }}
            .info-value {{ color: #fff; font-size: 1.2em; font-weight: bold; margin-bottom: 20px; }}
            .codigo {{ color: #FFD700; font-weight: bold; font-family: monospace; font-size: 1.1em; letter-spacing: 2px; }}
            .divider {{ border-top: 1px solid #3a5c53; margin: 20px 0; }}
          </style>
        </head>
        <body>
          <div class="verify-container">
            <h1>Certificado BJJ Digital</h1>
            
            <div class="box">
              <span class="valid-icon">✅</span>
              <p style="font-size: 1.1em; margin-bottom: 30px;">
                Este certificado é <strong>VÁLIDO</strong> e autêntico.
              </p>
              
              <div class="info-label">Aluno Certificado</div>
              <div class="info-value">{aluno_nome}</div>
              
              <div class="info-label">Faixa Conquistada</div>
              <div class="info-value" style="color: #FFD700;">{faixa}</div>
              
              <div class="divider"></div>
              
              <div style="display: flex; justify-content: space-around;">
                  <div>
                    <div class="info-label">Aproveitamento</div>
                    <div class="info-value">{nota}%</div>
                  </div>
                  <div>
                    <div class="info-label">Data do Exame</div>
                    <div class="info-value">{data_str}</div>
                  </div>
              </div>
              
              <div class="divider"></div>

              <p class="info-label">Código de Verificação</p>
              <p class="codigo">{codigo_limpo}</p>
            </div>
            
            <p style="margin-top: 30px; color: #888; font-size: 0.8em;">
              Verificado digitalmente em {datetime.now().strftime("%d/%m/%Y %H:%M")}
            </p>
          </div>
        </body>
        </html>
        """
        # Renderiza o HTML
        st.components.v1.html(html_content, height=800, scrolling=True)
        
        # Botão de voltar (Nativo do Streamlit para funcionar a navegação)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("Voltar para a Tela Inicial", use_container_width=True):
                st.query_params.clear()
                st.rerun()
                
    else:
        # HTML de Erro
        html_error = f"""
        <div style="font-family: 'Poppins', sans-serif; text-align: center; color: white; padding: 50px;">
            <h1 style="color: #ff4b4b;">❌ Certificado Não Encontrado</h1>
            <div style="background-color: #2d0e0e; border: 2px solid #ff4b4b; border-radius: 15px; padding: 30px; margin: 20px auto; max-width: 500px;">
                <p>O código <strong>{codigo_limpo}</strong> não consta em nossa base de dados.</p>
                <p>Verifique se foi digitado corretamente ou se o certificado foi revogado.</p>
            </div>
        </div>
        """
        st.components.v1.html(html_error, height=400)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("Tentar Novamente"):
                st.query_params.clear()
                st.rerun()

# =========================================
# FUNÇÃO PRINCIPAL (ROTEADOR)
# =========================================
def app_principal():
    if "usuario" not in st.session_state or not st.session_state.usuario:
        st.error("Sessão perdida.")
        st.session_state.usuario = None
        st.rerun()
        return

    usuario_logado = st.session_state.usuario
    tipo_usuario = str(usuario_logado.get("tipo", "aluno")).lower()

    def ir_para(pagina): st.session_state.menu_selection = pagina

    with st.sidebar:
        if os.path.exists("assets/logo.png"): st.image("assets/logo.png", use_container_width=True)
        st.markdown(f"<h3 style='color:{COR_DESTAQUE};'>{usuario_logado['nome'].title()}</h3>", unsafe_allow_html=True)
        st.markdown(f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>", unsafe_allow_html=True)
        
        if st.button("👤 Meu Perfil", use_container_width=True): ir_para("Meu Perfil")

        if tipo_usuario in ["admin", "professor"]:
            if st.button("👩‍🏫 Painel Professor", use_container_width=True): ir_para("Painel do Professor")

        if tipo_usuario == "admin":
            if st.button("🔑 Gestão Usuários", use_container_width=True): ir_para("Gestão de Usuários")

        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Início"
    pagina = st.session_state.menu_selection

    if pagina == "Meu Perfil":
        geral.tela_meu_perfil(usuario_logado)
        if st.button("⬅️ Voltar"): ir_para("Início")
    elif pagina == "Gestão de Usuários":
        admin.gestao_usuarios(usuario_logado)
        if st.button("⬅️ Voltar"): ir_para("Início")
    elif pagina == "Painel do Professor":
        professor.painel_professor()
        if st.button("⬅️ Voltar"): ir_para("Início")
    elif pagina == "Início":
        geral.tela_inicio()
    else:
        if tipo_usuario in ["admin", "professor"]:
            opcoes = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
            icons = ["house-fill", "people-fill", "journal-check", "trophy-fill", "cpu-fill", "building-fill", "file-earmark-check-fill"]
        else: 
            opcoes = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Meus Certificados"]
            icons = ["house-fill", "people-fill", "journal-check", "trophy-fill", "patch-check-fill"]

        try: index_atual = opcoes.index(pagina)
        except ValueError: index_atual = 0

        menu = option_menu(
            menu_title=None, options=opcoes, icons=icons, default_index=index_atual, orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": COR_FUNDO},
                "icon": {"color": COR_DESTAQUE, "font-size": "16px"},
                "nav-link": {"font-size": "14px", "margin": "0px", "color": COR_TEXTO},
                "nav-link-selected": {"background-color": COR_BOTAO, "color": COR_DESTAQUE},
            }
        )

        if menu != pagina:
            st.session_state.menu_selection = menu
            st.rerun()

        if menu == "Início": geral.tela_inicio()
        elif menu == "Modo Rola": aluno.modo_rola(usuario_logado)
        elif menu == "Exame de Faixa": aluno.exame_de_faixa(usuario_logado)
        elif menu == "Ranking": aluno.ranking()
        elif menu == "Gestão de Equipes": professor.gestao_equipes()
        elif menu == "Gestão de Questões": admin.gestao_questoes()
        elif menu == "Gestão de Exame": admin.gestao_exame_de_faixa()
        elif menu == "Meus Certificados": aluno.meus_certificados(usuario_logado)

# =========================================
# START
# =========================================
if __name__ == "__main__":
    # 🚨 LÓGICA DE VERIFICAÇÃO PÚBLICA 🚨
    query_params = st.query_params
    codigo_verificacao = query_params.get("code", None)

    if codigo_verificacao:
        tela_verificacao(codigo_verificacao)
    else:
        if "usuario" not in st.session_state: st.session_state.usuario = None
        if "token" not in st.session_state: st.session_state.token = None
        if "registration_pending" not in st.session_state: st.session_state.registration_pending = None

        try:
            if st.session_state.registration_pending:
                login.tela_completar_cadastro(st.session_state.registration_pending)
            elif st.session_state.usuario:
                app_principal()
            else:
                login.tela_login()
        except Exception as e:
            st.error(f"Erro inesperado: {e}")
