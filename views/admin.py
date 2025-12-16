import streamlit as st
import pandas as pd
import bcrypt
import time 
import io 
from datetime import datetime, date, time as dtime 
from database import get_db, OPCOES_SEXO
from firebase_admin import firestore

# Tenta importar o dashboard
try:
    from views.dashboard_admin import render_dashboard_geral
except ImportError:
    def render_dashboard_geral(): st.warning("Dashboard não encontrado.")

# Importa utils com tratamento de erro
try:
    from utils import (
        carregar_todas_questoes, 
        salvar_questoes, 
        fazer_upload_midia, 
        normalizar_link_video, 
        verificar_duplicidade_ia,
        auditoria_ia_questao,    
        auditoria_ia_openai,     
        IA_ATIVADA 
    )
except ImportError:
    IA_ATIVADA = False
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass
    def fazer_upload_midia(f): return None
    def normalizar_link_video(u): return u
    def verificar_duplicidade_ia(n, l, t=0.85): return False, None
    def auditoria_ia_questao(p, a, c): return "Indisponível"
    def auditoria_ia_openai(p, a, c): return "Indisponível"

# --- CONFIGURAÇÃO DE CORES ---
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO = "#0e2d26"
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770"
    COR_BOTAO = "#078B6C" # Verde BJJ Digital
    COR_HOVER = "#FFD770" # Dourado

# --- CONSTANTES ---
FAIXAS_COMPLETAS = [
    " ", "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]
NIVEIS_DIFICULDADE = [1, 2, 3, 4]
MAPA_NIVEIS = {1: "🟢 Fácil", 2: "🔵 Médio", 3: "🟠 Difícil", 4: "🔴 Muito Difícil"}

TIPO_MAP = {"Aluno(a)": "aluno", "Professor(a)": "professor", "Administrador(a)": "admin"}
TIPO_MAP_INV = {v: k for k, v in TIPO_MAP.items()}
LISTA_TIPOS_DISPLAY = list(TIPO_MAP.keys())

def get_badge_nivel(n): return MAPA_NIVEIS.get(n, "⚪ ?")

# =========================================
# ESTILOS VISUAIS
# =========================================
def aplicar_estilos_admin():
    st.markdown(f"""
    <style>
    /* CARDS MODERNOS */
    .admin-card-moderno {{
        background: linear-gradient(145deg, rgba(14, 45, 38, 0.95) 0%, rgba(9, 31, 26, 0.98) 100%);
        border: 1px solid rgba(255, 215, 112, 0.15); border-radius: 20px; padding: 1.5rem;
        min-height: 200px; display: flex; flex-direction: column; justify-content: space-between;
        position: relative; overflow: hidden; transition: transform 0.3s;
    }}
    .admin-card-moderno:hover {{
        border-color: {COR_DESTAQUE}; transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }}
    .admin-card-moderno::before {{
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
        background: linear-gradient(90deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%);
    }}
    
    /* BADGES */
    .admin-badge {{
        padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: bold;
        background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
    }}
    .green {{ color: #4ADE80; border-color: #4ADE80; }}
    .gold {{ color: {COR_DESTAQUE}; border-color: {COR_DESTAQUE}; }}
    
    /* BOTÕES */
    div.stButton > button, div.stFormSubmitButton > button {{ 
        width: 100%; border-radius: 8px; font-weight: 600;
    }}
    .stButton>button[kind="primary"] {{ background: linear-gradient(135deg, {COR_BOTAO}, #056853); color: white; border: none; }}
    .stButton>button[kind="secondary"] {{ background: transparent; border: 1px solid {COR_DESTAQUE}; color: {COR_DESTAQUE}; }}
    
    /* HEADER */
    .admin-header {{
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.9), rgba(9, 31, 26, 0.95));
        border-bottom: 1px solid {COR_DESTAQUE}; padding: 1.5rem; border-radius: 0 0 20px 20px; margin-bottom: 2rem;
    }}
    </style>
    """, unsafe_allow_html=True)

# =========================================
# GESTÃO DE USUÁRIOS
# =========================================
def gestao_usuarios_tab():
    db = get_db()
    users_ref = list(db.collection('usuarios').stream())
    users = [d.to_dict() | {"id": d.id} for d in users_ref]
    
    equipes_ref = list(db.collection('equipes').stream())
    mapa_equipes = {d.id: d.to_dict().get('nome', 'Sem Nome') for d in equipes_ref} 
    mapa_equipes_inv = {v: k for k, v in mapa_equipes.items()} 
    lista_equipes = ["Sem Equipe"] + sorted(list(mapa_equipes.values()))

    profs_users = list(db.collection('usuarios').where('tipo_usuario', '==', 'professor').stream())
    mapa_nomes_profs = {u.id: u.to_dict().get('nome', 'Sem Nome') for u in profs_users}
    mapa_nomes_profs_inv = {v: k for k, v in mapa_nomes_profs.items()}

    vincs_profs = list(db.collection('professores').where('status_vinculo', '==', 'ativo').stream())
    profs_por_equipe = {}
    for v in vincs_profs:
        d = v.to_dict()
        eid = d.get('equipe_id')
        uid = d.get('usuario_id')
        if eid and uid and uid in mapa_nomes_profs:
            if eid not in profs_por_equipe: profs_por_equipe[eid] = []
            profs_por_equipe[eid].append(mapa_nomes_profs[uid])

    if not users: st.warning("Vazio."); return
    
    df = pd.DataFrame(users)
    c1, c2 = st.columns(2)
    filtro_nome = c1.text_input("🔍 Buscar Nome/Email/CPF:")
    filtro_tipo = c2.multiselect("Filtrar Tipo:", df['tipo_usuario'].unique() if 'tipo_usuario' in df.columns else [])

    if filtro_nome:
        termo = filtro_nome.upper()
        df = df[
            df['nome'].astype(str).str.upper().str.contains(termo) | 
            df['email'].astype(str).str.upper().str.contains(termo) |
            df['cpf'].astype(str).str.contains(termo)
        ]
    if filtro_tipo:
        df = df[df['tipo_usuario'].isin(filtro_tipo)]

    cols_show = ['nome', 'email', 'tipo_usuario', 'faixa_atual', 'sexo']
    for c in cols_show: 
        if c not in df.columns: df[c] = "-"
    
    st.dataframe(df[cols_show], use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🛠️ Editar Cadastro Completo")
    
    opcoes = df.to_dict('records')
    sel = st.selectbox("Selecione o usuário:", opcoes, format_func=lambda x: f"{x.get('nome')} ({x.get('tipo_usuario')})")
    
    if sel:
        # Busca vínculos
        vinculo_equipe_id = None
        vinculo_prof_id = None
        doc_vinculo_id = None
        
        if sel.get('tipo_usuario') == 'aluno':
            vincs = list(db.collection('alunos').where('usuario_id', '==', sel['id']).limit(1).stream())
            if vincs:
                doc_vinculo_id = vincs[0].id
                d_vinc = vincs[0].to_dict()
                vinculo_equipe_id = d_vinc.get('equipe_id')
                vinculo_prof_id = d_vinc.get('professor_id')
        
        elif sel.get('tipo_usuario') == 'professor':
            vincs = list(db.collection('professores').where('usuario_id', '==', sel['id']).limit(1).stream())
            if vincs:
                doc_vinculo_id = vincs[0].id
                d_vinc = vincs[0].to_dict()
                vinculo_equipe_id = d_vinc.get('equipe_id')

        # --- FORM CORRIGIDO ---
        with st.form(f"edt_{sel['id']}"):
            st.markdown("##### 👤 Dados Pessoais")
            c1, c2 = st.columns(2)
            nm = c1.text_input("Nome Completo *", value=sel.get('nome',''))
            email = c2.text_input("E-mail *", value=sel.get('email',''))
            
            c3, c4, c5 = st.columns([1.5, 1, 1])
            cpf = c3.text_input("CPF *", value=sel.get('cpf',''))
            
            idx_s = 0
            sexo_val = sel.get('sexo')
            if sexo_val in OPCOES_SEXO: idx_s = OPCOES_SEXO.index(sexo_val)
            sexo_edit = c4.selectbox("Sexo:", OPCOES_SEXO, index=idx_s)
            
            val_n = None
            if sel.get('data_nascimento'):
                try: val_n = datetime.fromisoformat(sel.get('data_nascimento')).date()
                except: pass
            nasc_edit = c5.date_input("Nascimento:", value=val_n, min_value=date(1940,1,1), max_value=date.today(), format="DD/MM/YYYY")

            st.markdown("##### 📍 Endereço")
            e1, e2 = st.columns([1, 3])
            cep = e1.text_input("CEP:", value=sel.get('cep',''))
            logr = e2.text_input("Logradouro:", value=sel.get('logradouro',''))
            e3, e4, e5 = st.columns([1, 2, 2])
            num = e3.text_input("Número:", value=sel.get('numero',''))
            comp = e4.text_input("Complemento:", value=sel.get('complemento',''))
            bairro = e5.text_input("Bairro:", value=sel.get('bairro',''))
            e6, e7 = st.columns(2)
            cid = e6.text_input("Cidade:", value=sel.get('cidade',''))
            uf = e7.text_input("UF:", value=sel.get('uf',''))

            st.markdown("##### 🥋 Perfil e Vínculos")
            p1, p2 = st.columns(2)
            
            # Tipo
            tipo_atual_banco = sel.get('tipo_usuario', 'aluno')
            tipo_atual_display = TIPO_MAP_INV.get(tipo_atual_banco, "Aluno(a)")
            idx_tipo = 0
            if tipo_atual_display in LISTA_TIPOS_DISPLAY:
                idx_tipo = LISTA_TIPOS_DISPLAY.index(tipo_atual_display)
            tipo_sel_display = p1.selectbox("Tipo:", LISTA_TIPOS_DISPLAY, index=idx_tipo)
            tipo_sel_valor = TIPO_MAP[tipo_sel_display]
            
            # Faixa
            idx_fx = 0
            faixa_banco = str(sel.get('faixa_atual') or 'Branca') # Garante string
            for i, f in enumerate(FAIXAS_COMPLETAS):
                if f.strip().lower() == faixa_banco.strip().lower():
                    idx_fx = i
                    break
            fx = p2.selectbox("Faixa:", FAIXAS_COMPLETAS, index=idx_fx)

            v1, v2 = st.columns(2)
            nome_eq_atual = mapa_equipes.get(vinculo_equipe_id, "Sem Equipe")
            idx_eq = lista_equipes.index(nome_eq_atual) if nome_eq_atual in lista_equipes else 0
            nova_equipe_nome = v1.selectbox("Equipe:", lista_equipes, index=idx_eq)
            
            novo_prof_display = "Sem Professor(a)"
            lista_profs_inclusiva = ["Sem Professor(a)"]
            
            if tipo_sel_valor == 'aluno':
                id_equipe_selecionada = mapa_equipes_inv.get(nova_equipe_nome)
                if id_equipe_selecionada in profs_por_equipe:
                    lista_profs_inclusiva += sorted(profs_por_equipe[id_equipe_selecionada])
                
                nome_prof_atual_display = mapa_nomes_profs.get(vinculo_prof_id, "Sem Professor(a)")
                if nome_prof_atual_display == "Sem Professor": nome_prof_atual_display = "Sem Professor(a)"

                idx_prof = 0
                if nome_prof_atual_display in lista_profs_inclusiva:
                    idx_prof = lista_profs_inclusiva.index(nome_prof_atual_display)
                
                novo_prof_display = v2.selectbox("Professor(a) Responsável:", lista_profs_inclusiva, index=idx_prof)
                if nova_equipe_nome == "Sem Equipe":
                    v2.caption("Selecione uma equipe para ver os professores.")

            st.markdown("##### 🔒 Segurança")
            pwd = st.text_input("Nova Senha (opcional):", type="password")
            
            submit_btn = st.form_submit_button("💾 Salvar Todas as Alterações", type="primary")

        # Lógica de processamento
        if submit_btn:
            upd = {
                "nome": nm.upper(), "email": email.lower().strip(), "cpf": cpf,
                "sexo": sexo_edit, "data_nascimento": nasc_edit.isoformat() if nasc_edit else None,
                "cep": cep, "logradouro": logr.upper(), "numero": num, "complemento": comp.upper(),
                "bairro": bairro.upper(), "cidade": cid.upper(), "uf": uf.upper(),
                "tipo_usuario": tipo_sel_valor, 
                "faixa_atual": fx
            }
            if pwd: 
                upd["senha"] = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
                upd["precisa_trocar_senha"] = True
            
            try:
                db.collection('usuarios').document(sel['id']).update(upd)
                
                novo_eq_id = mapa_equipes_inv.get(nova_equipe_nome)
                
                if tipo_sel_valor == 'aluno':
                    novo_p_id = mapa_nomes_profs_inv.get(novo_prof_display)
                    dados_vinc = {"equipe_id": novo_eq_id, "professor_id": novo_p_id, "faixa_atual": fx}
                    if doc_vinculo_id: db.collection('alunos').document(doc_vinculo_id).update(dados_vinc)
                    else:
                        dados_vinc['usuario_id'] = sel['id']; dados_vinc['status_vinculo'] = 'ativo'
                        db.collection('alunos').add(dados_vinc)
                        
                elif tipo_sel_valor == 'professor':
                    dados_vinc = {"equipe_id": novo_eq_id}
                    if doc_vinculo_id: db.collection('professores').document(doc_vinculo_id).update(dados_vinc)
                    else:
                        dados_vinc['usuario_id'] = sel['id']; dados_vinc['status_vinculo'] = 'ativo'
                        db.collection('professores').add(dados_vinc)

                st.success("✅ Atualizado com sucesso!"); time.sleep(1.5); st.rerun()
            except Exception as e: st.error(f"Erro ao salvar: {e}")
                
        if st.button("🗑️ Excluir Usuário", key=f"del_{sel['id']}"):
            db.collection('usuarios').document(sel['id']).delete()
            st.warning("Usuário excluído."); time.sleep(1); st.rerun()

# =========================================
# GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes_tab():
    aplicar_estilos_admin()
    st.markdown(f"""<div class="admin-header"><h1 style="margin:0; text-align:center; color:{COR_DESTAQUE};">📝 Banco de Questões</h1></p></div>""", unsafe_allow_html=True)
    db = get_db()
    user = st.session_state.usuario
    
    user_tipo = str(user.get("tipo_usuario", user.get("tipo", ""))).lower()
    if user_tipo not in ["admin", "professor"]:
        st.error("Acesso negado."); return

    titulos = ["📚 Listar/Editar", "➕ Criar Questões", "🔎 Minhas Submissões"]
    if user_tipo == "admin":
        titulos.append("⏳ Aprovações (Admin)")
    
    tabs = st.tabs(titulos)

    # --- ABA 1: LISTAR ---
    with tabs[0]:
        q_ref = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        c1, c2 = st.columns(2)
        termo = c1.text_input("🔍 Buscar (Aprovadas):")
        filt_n = c2.multiselect("Nível:", NIVEIS_DIFICULDADE)
        
        q_filtro = []
        for doc in q_ref:
            d = doc.to_dict(); d['id'] = doc.id
            if termo and termo.lower() not in d.get('pergunta','').lower(): continue
            if filt_n and d.get('dificuldade',1) not in filt_n: continue
            q_filtro.append(d)
            
        if not q_filtro: st.info("Nenhuma questão aprovada encontrada.")
        else:
            st.caption(f"{len(q_filtro)} questões ativas")
            for q in q_filtro:
                stt = q.get('status', 'aprovada')
                cor_st = "green" if stt=='aprovada' else "orange" if stt=='correcao' else "gray"
                
                with st.container(border=True):
                    ch, cb = st.columns([5, 1])
                    bdg = get_badge_nivel(q.get('dificuldade',1))
                    ch.markdown(f"**{bdg}** | :{cor_st}[{stt.upper()}] | ✍️ {q.get('criado_por','?')}")
                    ch.markdown(f"##### {q.get('pergunta')}")
                    
                    if q.get('url_imagem'): ch.image(q.get('url_imagem'), width=150)
                    if q.get('url_video'):
                        vid_url = q.get('url_video')
                        link_limpo = normalizar_link_video(vid_url)
                        try: ch.video(link_limpo)
                        except: pass
                        ch.markdown(f"<small>🔗 [Abrir vídeo]({vid_url})</small>", unsafe_allow_html=True)
                    
                    with ch.expander("Alternativas"):
                        alts = q.get('alternativas', {})
                        st.write(f"A) {alts.get('A','')} | B) {alts.get('B','')}")
                        st.write(f"C) {alts.get('C','')} | D) {alts.get('D','')}")
                        st.success(f"Correta: {q.get('resposta_correta')}")
                    
                    if cb.button("✏️", key=f"ed_{q['id']}"): st.session_state['edit_q'] = q['id']
                
                # --- EDITAR ---
                if st.session_state.get('edit_q') == q['id']:
                    with st.container(border=True):
                        st.markdown("#### ✏️ Editando")
                        with st.form(f"f_ed_{q['id']}"):
                            perg = st.text_area("Enunciado *", value=q.get('pergunta',''))
                            st.markdown("🖼️ **Mídia**")
                            c_img, c_vid = st.columns(2)
                            up_img = c_img.file_uploader("Nova Imagem:", type=["jpg","png"], key=f"u_i_{q['id']}")
                            url_i_at = q.get('url_imagem','')
                            if url_i_at: c_img.caption("Imagem atual salva.")
                            up_vid = c_vid.file_uploader("Novo Vídeo (MP4):", type=["mp4","mov"], key=f"u_v_{q['id']}")
                            url_v_at = q.get('url_video','')
                            url_v_manual = c_vid.text_input("Ou Link Externo:", value=url_v_at)
                            c1, c2 = st.columns(2)
                            dif = c1.selectbox("Nível:", NIVEIS_DIFICULDADE, index=NIVEIS_DIFICULDADE.index(q.get('dificuldade',1)))
                            cat = c2.text_input("Categoria:", value=q.get('categoria','Geral'))
                            alts = q.get('alternativas',{})
                            ca, cb = st.columns(2); cc, cd = st.columns(2)
                            rA = ca.text_input("A) *", alts.get('A','')); rB = cb.text_input("B) *", alts.get('B',''))
                            rC = cc.text_input("C)", alts.get('C','')); rD = cd.text_input("D)", alts.get('D',''))
                            corr = st.selectbox("Correta:", ["A","B","C","D"], index=["A","B","C","D"].index(q.get('resposta_correta','A')))
                            
                            justificativa_edicao = ""
                            if user_tipo != "admin":
                                st.markdown("---")
                                justificativa_edicao = st.text_area("📝 Justificativa da Edição (Obrigatório) *:")

                            cols = st.columns(2)
                            if cols[0].form_submit_button("💾 Salvar Alterações"):
                                if user_tipo != "admin" and not justificativa_edicao.strip():
                                    st.error("⚠️ Professores devem justificar a edição!")
                                else:
                                    fin_img = url_i_at
                                    if up_img:
                                        with st.spinner("Subindo imagem..."): fin_img = fazer_upload_midia(up_img)
                                    fin_vid = url_v_manual
                                    if up_vid:
                                        with st.spinner("Subindo vídeo..."): fin_vid = fazer_upload_midia(up_vid)
                                    
                                    novo_status = "aprovada" if user_tipo == "admin" else "pendente"
                                    
                                    dados_upd = {
                                        "pergunta": perg, "dificuldade": dif, "categoria": cat,
                                        "url_imagem": fin_img, "url_video": fin_vid,
                                        "alternativas": {"A":rA, "B":rB, "C":rC, "D":rD},
                                        "resposta_correta": corr,
                                        "status": novo_status,
                                        "feedback_admin": firestore.DELETE_FIELD 
                                    }
                                    
                                    if justificativa_edicao:
                                        dados_upd["ultima_justificativa"] = justificativa_edicao

                                    db.collection('questoes').document(q['id']).update(dados_upd)
                                    st.session_state['edit_q'] = None
                                    if novo_status == "pendente": st.info("✏️ Edição enviada para análise!")
                                    else: st.success("✅ Salvo!")
                                    time.sleep(1.5); st.rerun()

                            if cols[1].form_submit_button("Cancelar"):
                                st.session_state['edit_q'] = None; st.rerun()
                        if st.button("🗑️ Deletar", key=f"del_q_{q['id']}", type="primary"):
                            db.collection('questoes').document(q['id']).delete()
                            st.session_state['edit_q'] = None; st.success("Deletado."); st.rerun()

    # --- ABA 2: ADICIONAR ---
    with tabs[1]:
        sub_tab_manual, sub_tab_lote = st.tabs(["✍️ Manual", "📂 Lote"])
        with sub_tab_manual:
            with st.form("new_q"):
                st.markdown("#### Nova Questão")
                if IA_ATIVADA: st.caption("🟢 IA Ativada")
                else: st.caption("🔴 IA Off")
                perg = st.text_area("Enunciado *")
                c1, c2 = st.columns(2)
                up_img = c1.file_uploader("Imagem:", type=["jpg","png"])
                up_vid = c2.file_uploader("Vídeo:", type=["mp4"])
                link_vid = c2.text_input("Link YouTube:")
                c3, c4 = st.columns(2)
                dif = c3.selectbox("Nível:", NIVEIS_DIFICULDADE)
                cat = c4.text_input("Categoria:", "Geral")
                ca, cb = st.columns(2); cc, cd = st.columns(2)
                alt_a = ca.text_input("A) *"); alt_b = cb.text_input("B) *")
                alt_c = cc.text_input("C)"); alt_d = cd.text_input("D)")
                correta = st.selectbox("Correta *", ["A","B","C","D"])
                
                if st.form_submit_button("💾 Cadastrar"):
                    if perg and alt_a and alt_b:
                        pode_salvar = True
                        if IA_ATIVADA:
                            try:
                                with st.spinner("Verificando duplicidade..."):
                                    all_qs_snap = list(db.collection('questoes').stream())
                                    lista_qs = [d.to_dict() for d in all_qs_snap]
                                    res_ia = verificar_duplicidade_ia(perg, lista_qs, threshold=0.75)
                                    if res_ia and isinstance(res_ia, tuple) and res_ia[0]:
                                        st.error("⚠️ Questão similar detectada!")
                                        st.warning(f"Existente: {res_ia[1]}")
                                        pode_salvar = False
                            except: pass

                        if pode_salvar:
                            f_img = fazer_upload_midia(up_img) if up_img else None
                            f_vid = fazer_upload_midia(up_vid) if up_vid else link_vid
                            
                            status_ini = "aprovada" if user_tipo == "admin" else "pendente"
                            msg_sucesso = "✅ Cadastrada!" if user_tipo == "admin" else "⏳ Enviada para aprovação!"
                            
                            db.collection('questoes').add({
                                "pergunta": perg, "dificuldade": dif, "categoria": cat,
                                "url_imagem": f_img, "url_video": f_vid,
                                "alternativas": {"A":alt_a, "B":alt_b, "C":alt_c, "D":alt_d},
                                "resposta_correta": correta, "status": status_ini,
                                "criado_por": user.get('nome', 'Admin'), "data_criacao": firestore.SERVER_TIMESTAMP
                            })
                            st.success(msg_sucesso); time.sleep(1.5); st.rerun()
                        else: st.stop()
                    else: st.warning("Preencha dados básicos.")

        with sub_tab_lote:
            if user_tipo == "admin":
                st.markdown("#### 📥 Importação em Massa")
                st.info("Carregue Excel ou CSV.")
                col_info, col_btn = st.columns([3, 1])
                df_modelo = pd.DataFrame({
                    "pergunta": ["Exemplo 1"], "alt_a": ["A"], "alt_b": ["B"], "alt_c": ["C"], "alt_d": ["D"],
                    "correta": ["A"], "dificuldade": [1], "categoria": ["Geral"]
                })
                csv_buffer = io.StringIO()
                df_modelo.to_csv(csv_buffer, index=False, sep=';')
                col_btn.download_button("⬇️ Modelo", data=csv_buffer.getvalue(), file_name="modelo.csv", mime="text/csv")
                
                arquivo = st.file_uploader("Arquivo:", type=["csv", "xlsx"])
                if arquivo and st.button("🚀 Importar"):
                     # Lógica real de importação
                     try:
                         if arquivo.name.endswith('.csv'):
                             try: df = pd.read_csv(arquivo, sep=';')
                             except: df = pd.read_csv(arquivo, sep=',')
                         else: df = pd.read_excel(arquivo)
                         
                         prog = st.progress(0)
                         for i, row in df.iterrows():
                             db.collection('questoes').add({
                                 "pergunta": str(row['pergunta']), "status": "aprovada",
                                 "alternativas": {"A": str(row['alt_a']), "B": str(row['alt_b']), "C": str(row.get('alt_c','')), "D": str(row.get('alt_d',''))},
                                 "resposta_correta": str(row['correta']), "dificuldade": int(row.get('dificuldade',1)),
                                 "categoria": str(row.get('categoria','Geral')), "criado_por": f"{user.get('nome')} (Import)"
                             })
                             prog.progress((i+1)/len(df))
                         st.success("Importado!"); time.sleep(2); st.rerun()
                     except Exception as e: st.error(f"Erro: {e}")
            else: st.warning("Restrito a Admin.")

    # --- ABA 3: MINHAS SUBMISSÕES ---
    with tabs[2]:
        st.markdown("#### 🔎 Meus Envios")
        nome_atual = user.get('nome', 'Admin')
        minhas = list(db.collection('questoes').where('criado_por', '==', nome_atual).stream())
        if not minhas: st.info("Você não enviou questões.")
        else:
            st.caption(f"Total: {len(minhas)}")
            for doc in minhas:
                q = doc.to_dict()
                stt = q.get('status', 'aprovada')
                cor, icon = "gray", "⏳"
                if stt == 'aprovada': cor, icon = "green", "✅"
                elif stt == 'correcao': cor, icon = "orange", "🟠"
                elif stt == 'rejeitada': cor, icon = "red", "❌"
                
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"**{q.get('pergunta')}**")
                    c1.caption(f"{stt.upper()}")
                    c2.markdown(f":{cor}[{icon}]")
                    if stt == 'correcao':
                        st.error(f"📢 Motivo: {q.get('feedback_admin', '-')}")
                        if c2.button("✏️ Corrigir", key=f"fix_btn_{doc.id}"):
                            st.session_state['edit_my_mode'] = doc.id
                    if stt != 'aprovada':
                         if c2.button("🗑️", key=f"del_my_{doc.id}"):
                            db.collection('questoes').document(doc.id).delete(); st.rerun()
                
                if st.session_state.get('edit_my_mode') == doc.id:
                    with st.form(f"fix_form_{doc.id}"):
                        st.markdown("##### 🛠️ Corrigir e Reenviar")
                        n_perg = st.text_area("Enunciado *", q.get('pergunta'))
                        n_cat = st.text_input("Categoria:", q.get('categoria'))
                        if st.form_submit_button("🚀 Reenviar"):
                            db.collection('questoes').document(doc.id).update({
                                "pergunta": n_perg, "categoria": n_cat, "status": "pendente", "feedback_admin": firestore.DELETE_FIELD
                            })
                            st.session_state['edit_my_mode'] = None; st.success("Enviado!"); st.rerun()

    # --- ABA 4: APROVAÇÕES (SÓ ADMIN) ---
    if user_tipo == "admin":
        with tabs[3]:
            st.markdown("#### ⏳ Fila de Aprovação")
            pendentes = list(db.collection('questoes').where('status', '==', 'pendente').stream())
            if not pendentes: st.success("🎉 Nenhuma pendência!")
            else:
                for doc in pendentes:
                    q = doc.to_dict()
                    with st.container(border=True):
                        st.markdown(f"👤 **{q.get('criado_por')}** enviou:")
                        st.markdown(f"##### {q.get('pergunta')}")
                        if q.get('ultima_justificativa'):
                            st.info(f"📝 Nota do Professor: {q.get('ultima_justificativa')}")
                        
                        # --- ALTERNATIVAS VISÍVEIS ---
                        with st.expander("Ver Detalhes e Alternativas"):
                            if q.get('url_imagem'): st.image(q.get('url_imagem'), width=150)
                            alts = q.get('alternativas', {})
                            st.write(f"A) {alts.get('A','')} | B) {alts.get('B','')}")
                            st.write(f"C) {alts.get('C','')} | D) {alts.get('D','')}")
                            st.success(f"Gabarito: {q.get('resposta_correta')}")

                        c1, c2 = st.columns(2)
                        if c1.button("✅ Aprovar", key=f"app_{doc.id}", type="primary", use_container_width=True):
                            db.collection('questoes').document(doc.id).update({"status": "aprovada"})
                            st.toast("Aprovada!"); time.sleep(1); st.rerun()
                        
                        with c2.expander("🤖 Auditoria & Correção"):
                            col_gem, col_gpt = st.columns(2)
                            if col_gem.button("Gemini", key=f"gem_{doc.id}", use_container_width=True):
                                with st.spinner("Analisando..."):
                                    res = auditoria_ia_questao(q.get('pergunta'), q.get('alternativas',{}), q.get('resposta_correta'))
                                    st.info(res)
                            
                            if col_gpt.button("GPT-4o", key=f"gpt_{doc.id}", use_container_width=True):
                                with st.spinner("Analisando..."):
                                    res = auditoria_ia_openai(q.get('pergunta'), q.get('alternativas',{}), q.get('resposta_correta'))
                                    st.info(res)

                            st.markdown("---")
                            fb_txt = st.text_area("Justificativa (Obrigatória) *", key=f"fb_{doc.id}", height=80)
                            
                            if st.button("Enviar para Correção", key=f"send_fb_{doc.id}"):
                                if not fb_txt.strip():
                                    st.error("⚠️ Escreva a justificativa!")
                                else:
                                    db.collection('questoes').document(doc.id).update({
                                        "status": "correcao", "feedback_admin": fb_txt
                                    })
                                    st.toast("Enviado!"); time.sleep(1); st.rerun()
                            
                            if st.button("🗑️ Rejeitar Definitivamente", key=f"kill_{doc.id}"):
                                db.collection('questoes').document(doc.id).delete(); st.rerun()

# =========================================
# GESTÃO DE EXAMES (CARD ESTILIZADO)
# =========================================
def gestao_exame_de_faixa_route():
    aplicar_estilos_admin()
    st.markdown(f"""<div class="admin-header"><h1 style="margin:0; text-align:center; color:{COR_DESTAQUE};">📝 GERENCIADOR DE EXAMES</h1></p></div>""", unsafe_allow_html=True)
    db = get_db()
    tab1, tab2, tab3 = st.tabs(["📝 Criar/Editar Exames", "👁️ Visualizar Exames", "✅ Autorizar Exames"])

    with tab1:
        st.subheader("1. Selecione a Faixa")
        faixa_sel = st.selectbox("Prova de Faixa:", FAIXAS_COMPLETAS)
        if 'last_faixa_sel' not in st.session_state or st.session_state.last_faixa_sel != faixa_sel:
            configs = list(db.collection('config_exames').where('faixa', '==', faixa_sel).limit(1).stream())
            conf_atual = configs[0].to_dict() if configs else {}
            doc_id = configs[0].id if configs else None
            st.session_state.conf_atual = conf_atual; st.session_state.doc_id = doc_id
            st.session_state.selected_ids = set(conf_atual.get('questoes_ids', []))
            st.session_state.last_faixa_sel = faixa_sel
        conf_atual = st.session_state.conf_atual
        todas_questoes = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        
        st.markdown("### 2. Selecione as Questões")
        c_f1, c_f2 = st.columns(2)
        filtro_nivel = c_f1.multiselect("Filtrar Nível:", NIVEIS_DIFICULDADE, default=[1,2,3,4], format_func=lambda x: MAPA_NIVEIS.get(x, str(x)))
        cats = sorted(list(set([d.to_dict().get('categoria', 'Geral') for d in todas_questoes])))
        filtro_tema = c_f2.multiselect("Filtrar Tema:", cats, default=cats)
        
        with st.container(height=500, border=True):
            count_visible = 0
            for doc in todas_questoes:
                d = doc.to_dict(); niv = d.get('dificuldade', 1); cat = d.get('categoria', 'Geral')
                if niv in filtro_nivel and cat in filtro_tema:
                    count_visible += 1
                    c_chk, c_content = st.columns([1, 15])
                    is_checked = doc.id in st.session_state.selected_ids
                    def update_selection(qid=doc.id):
                        if st.session_state[f"chk_{qid}"]: st.session_state.selected_ids.add(qid)
                        else: st.session_state.selected_ids.discard(qid)
                    c_chk.checkbox("", value=is_checked, key=f"chk_{doc.id}", on_change=update_selection)
                    with c_content:
                        badge = get_badge_nivel(niv); autor = d.get('criado_por', '?')
                        st.markdown(f"**{badge}** | {cat} | ✍️ {autor}")
                        st.markdown(f"{d.get('pergunta')}")
                        if d.get('url_imagem'): st.image(d.get('url_imagem'), width=150)
                        if d.get('url_video'):
                            vid_url = d.get('url_video')
                            link_limpo = normalizar_link_video(vid_url)
                            try: st.video(link_limpo)
                            except: pass
                            st.markdown(f"<small>🔗 [Ver vídeo]({vid_url})</small>", unsafe_allow_html=True)
                        with st.expander("Ver Detalhes"):
                            alts = d.get('alternativas', {})
                            st.markdown(f"**A)** {alts.get('A','')} | **B)** {alts.get('B','')}")
                            st.markdown(f"**C)** {alts.get('C','')} | **D)** {alts.get('D','')}")
                            st.info(f"✅ Correta: {d.get('resposta_correta') or 'A'}")
                    st.divider()
            if count_visible == 0: st.warning("Nada encontrado.")
        
        total_sel = len(st.session_state.selected_ids)
        c_res1, c_res2 = st.columns([3, 1])
        c_res1.success(f"**{total_sel}** questões selecionadas.")
        if total_sel > 0:
            if c_res2.button("🗑️ Limpar", key="clean_sel"): st.session_state.selected_ids = set(); st.rerun()
        
        st.markdown("### 3. Regras")
        with st.form("save_conf"):
            c1, c2 = st.columns(2)
            tempo = c1.number_input("Tempo (min):", 10, 180, int(conf_atual.get('tempo_limite', 45)))
            nota = c2.number_input("Aprovação (%):", 10, 100, int(conf_atual.get('aprovacao_minima', 70)))
            if st.form_submit_button("💾 Salvar Prova"):
                if total_sel == 0: st.error("Selecione questões.")
                else:
                    try:
                        dados = {"faixa": faixa_sel, "questoes_ids": list(st.session_state.selected_ids), "qtd_questoes": total_sel, "tempo_limite": tempo, "aprovacao_minima": nota, "modo_selecao": "Manual", "atualizado_em": firestore.SERVER_TIMESTAMP}
                        if st.session_state.doc_id:
                            try: db.collection('config_exames').document(st.session_state.doc_id).update(dados)
                            except: db.collection('config_exames').add(dados)
                        else: db.collection('config_exames').add(dados)
                        st.success("Salvo!"); time.sleep(1.5); st.rerun()
                    except Exception as e: st.error(f"Erro ao salvar: {e}")

    with tab2:
        st.subheader("Status das Provas")
        configs_stream = db.collection('config_exames').stream()
        mapa_configs = {d.to_dict().get('faixa'): d.to_dict() | {'id': d.id} for d in configs_stream}
        grupos = {"🔘 Cinza": ["Cinza e Branca", "Cinza", "Cinza e Preta"], "🟡 Amarela": ["Amarela e Branca", "Amarela", "Amarela e Preta"], "🟠 Laranja": ["Laranja e Branca", "Laranja", "Laranja e Preta"], "🟢 Verde": ["Verde e Branca", "Verde", "Verde e Preta"], "🔵 Azul": ["Azul"], "🟣 Roxa": ["Roxa"], "🟤 Marrom": ["Marrom"], "⚫ Preta": ["Preta"]}
        sub_tabs = st.tabs(list(grupos.keys()))
        for i, (g, fxs) in enumerate(grupos.items()):
            with sub_tabs[i]:
                cols = st.columns(len(fxs))
                for j, fx in enumerate(fxs):
                    conf = mapa_configs.get(fx)
                    with cols[j]:
                        # --- CARD ESTILIZADO DE EXAME ---
                        if conf:
                            html_card = f"""
                            <div class="admin-card-moderno">
                                <div style="font-size:2rem;text-align:center;">📜</div>
                                <h4 style="margin:0; text-align:center; color:white;">{fx}</h4>
                                <div style="text-align:center; margin-top:10px;">
                                    <span class="admin-badge green">✅ {conf.get('qtd_questoes')} Questões</span>
                                    <br><br>
                                    <span class="admin-badge gold">⏱️ {conf.get('tempo_limite')} min</span>
                                </div>
                            </div>
                            """
                            st.markdown(html_card, unsafe_allow_html=True)
                            
                            st.markdown(f'<div style="margin-top: -1rem;">', unsafe_allow_html=True)
                            if st.button("🗑️ Deletar", key=f"del_ex_{conf['id']}", use_container_width=True):
                                db.collection('config_exames').document(conf['id']).delete(); st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="admin-card-moderno" style="opacity:0.5; border:1px dashed white;">
                                <div style="font-size:2rem;text-align:center;">🚫</div>
                                <h4 style="text-align:center;">{fx}</h4>
                                <p style="text-align:center;">Não configurado</p>
                            </div>
                            """, unsafe_allow_html=True)

    with tab3:
        with st.container(border=True):
            st.subheader("🗓️ Configurar Período")
            c1, c2 = st.columns(2)
            d_ini = c1.date_input("Início:", datetime.now(), key="d_ini_ex", format="DD/MM/YYYY")
            d_fim = c2.date_input("Fim:", datetime.now(), key="d_fim_ex", format="DD/MM/YYYY")
            c3, c4 = st.columns(2); h_ini = c3.time_input("Hora Ini:", dtime(0,0)); h_fim = c4.time_input("Hora Fim:", dtime(23,59))
            dt_ini = datetime.combine(d_ini, h_ini); dt_fim = datetime.combine(d_fim, h_fim)
        
        st.write(""); st.subheader("Lista de Alunos(as)")
        # REMOVIDO O TRY GERAL
        alunos_ref = db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream()
        lista_alunos = []
        for doc in alunos_ref:
            d = doc.to_dict(); d['id'] = doc.id
            
            # PROTEÇÃO CONTRA CAMPOS VAZIOS
            nome = d.get('nome', 'Sem Nome')
            faixa = d.get('faixa_atual', '-')
            
            nome_eq = "Sem Equipe"
            try:
                # Tenta buscar equipe (opcional)
                vinculos = list(db.collection('alunos').where('usuario_id', '==', d['id']).limit(1).stream())
                if vinculos:
                    eq_id = vinculos[0].to_dict().get('equipe_id')
                    if eq_id:
                        eq_doc = db.collection('equipes').document(eq_id).get()
                        if eq_doc.exists: nome_eq = eq_doc.to_dict().get('nome', 'Sem Nome')
            except: pass
            
            # Renderiza linha
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 1])
            c1.write(f"**{nome}**")
            c2.write(nome_eq)
            
            fx_banco = d.get('faixa_exame')
            idx = 0
            if fx_banco in FAIXAS_COMPLETAS: idx = FAIXAS_COMPLETAS.index(fx_banco)
            
            fx_sel = c3.selectbox("Faixa", FAIXAS_COMPLETAS, index=idx, key=f"fx_s_{d['id']}", label_visibility="collapsed")
            
            hab = d.get('exame_habilitado', False)
            status = d.get('status_exame', 'pendente')
            
            msg_status = "⚪ Não autorizado"
            if status == 'aprovado': msg_status = "🏆 Aprovado"
            elif status == 'reprovado': msg_status = "🔴 Reprovado"
            elif status == 'bloqueado': msg_status = "⛔ Bloqueado"
            elif status == 'em_andamento': msg_status = "🟡 Em Andamento"
            elif hab:
                try:
                    raw_fim = d.get('exame_fim')
                    if raw_fim:
                        dt_fim = datetime.fromisoformat(str(raw_fim).replace('Z', ''))
                        if datetime.now() > dt_fim: msg_status = "⏰ Expirado"
                        else: msg_status = f"🟢 Até {dt_fim.strftime('%d/%m %H:%M')}"
                    else: msg_status = "🟢 Liberado"
                except: msg_status = "🟢 Liberado"
            
            c4.write(msg_status)
            
            if hab:
                if c5.button("⛔", key=f"blk_{d['id']}"):
                    db.collection('usuarios').document(d['id']).update({"exame_habilitado": False, "status_exame": "pendente"})
                    st.rerun()
            else:
                if c5.button("✅", key=f"lib_{d['id']}"):
                    db.collection('usuarios').document(d['id']).update({
                        "exame_habilitado": True, "faixa_exame": fx_sel,
                        "exame_inicio": dt_ini.isoformat(), "exame_fim": dt_fim.isoformat(),
                        "status_exame": "pendente", "status_exame_em_andamento": False
                    })
                    st.success("Liberado!"); time.sleep(0.5); st.rerun()
            st.divider()

# =========================================
# CONTROLADOR PRINCIPAL
# =========================================
def gestao_questoes(): gestao_questoes_tab()
def gestao_exame_de_faixa(): gestao_exame_de_faixa_route()

def gestao_usuarios(usuario_logado):
    aplicar_estilos_admin()
    st.markdown(f"<h1 style='color:#FFD700;'>Gestão e Estatísticas</h1>", unsafe_allow_html=True)
    if st.button("🏠 Voltar ao Início", key="btn_back_admin_main"):
        st.session_state.menu_selection = "Início"; st.rerun()
    menu = st.radio("", ["👥 Gestão de Usuários", "📊 Dashboard"], horizontal=True, label_visibility="collapsed")
    st.markdown("---")
    if menu == "📊 Dashboard": render_dashboard_geral()
    elif menu == "👥 Gestão de Usuários": gestao_usuarios_tab()
