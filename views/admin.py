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

# Importa utils
import utils as ce

# --- CONFIGURAÇÃO DE CORES ---
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO = "#0e2d26"
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770"
    COR_BOTAO = "#078B6C" 
    COR_HOVER = "#FFD770"

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

# Mapeamento
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
    /* CARD ADMIN */
    .admin-card-moderno {{
        background: linear-gradient(145deg, rgba(14, 45, 38, 0.95) 0%, rgba(9, 31, 26, 0.98) 100%);
        border: 1px solid rgba(255, 215, 112, 0.15); border-radius: 20px; padding: 1.5rem;
        min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;
        position: relative; overflow: hidden; transition: transform 0.3s; margin-bottom: 1rem;
    }}
    .admin-card-moderno:hover {{
        border-color: {COR_DESTAQUE}; transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }}
    
    /* BADGES */
    .admin-badge {{
        padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: bold;
        background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); margin-right: 5px;
    }}
    .green {{ color: #4ADE80; border-color: #4ADE80; }}
    .gold {{ color: {COR_DESTAQUE}; border-color: {COR_DESTAQUE}; }}
    .blue {{ color: #60A5FA; border-color: #60A5FA; }}
    .red {{ color: #F87171; border-color: #F87171; }}
    
    /* BOTÕES */
    div.stButton > button, div.stFormSubmitButton > button {{ width: 100%; border-radius: 8px; font-weight: 600; }}
    .stButton>button[kind="primary"] {{ background: linear-gradient(135deg, {COR_BOTAO}, #056853); color: white; border: none; }}
    
    /* HEADER */
    .admin-header {{
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.9), rgba(9, 31, 26, 0.95));
        border-bottom: 1px solid {COR_DESTAQUE}; padding: 1.5rem; border-radius: 0 0 20px 20px; margin-bottom: 2rem;
    }}
    </style>
    """, unsafe_allow_html=True)

# =========================================
# 1. GESTÃO DE USUÁRIOS (COMPLETA)
# =========================================
def gestao_usuarios_tab():
    aplicar_estilos_admin()
    db = get_db()
    
    # Busca dados
    users_ref = list(db.collection('usuarios').stream())
    users = [d.to_dict() | {"id": d.id} for d in users_ref]
    
    # Busca Equipes para o formulário
    equipes_ref = list(db.collection('equipes').stream())
    mapa_equipes = {d.id: d.to_dict().get('nome', 'Sem Nome') for d in equipes_ref} 
    mapa_equipes_inv = {v: k for k, v in mapa_equipes.items()} 
    lista_equipes = ["Sem Equipe"] + sorted(list(mapa_equipes.values()))

    # Busca Professores para vínculo
    profs_users = list(db.collection('usuarios').where('tipo_usuario', '==', 'professor').stream())
    mapa_nomes_profs = {u.id: u.to_dict().get('nome', 'Sem Nome') for u in profs_users}
    mapa_nomes_profs_inv = {v: k for k, v in mapa_nomes_profs.items()}

    # Mapeamento Professor -> Equipe
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
    
    # Tabela com Filtros
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

    st.dataframe(df[['nome', 'email', 'tipo_usuario', 'faixa_atual', 'sexo']], use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🛠️ Editar Cadastro Completo")
    
    opcoes = df.to_dict('records')
    sel = st.selectbox("Selecione o usuário:", opcoes, format_func=lambda x: f"{x.get('nome')} ({x.get('tipo_usuario')})")
    
    if sel:
        # Busca vínculos atuais
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

        # FORMULÁRIO DE EDIÇÃO
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
            
            # Tipo e Faixa
            tipo_atual_display = TIPO_MAP_INV.get(sel.get('tipo_usuario', 'aluno'), "Aluno(a)")
            idx_tipo = LISTA_TIPOS_DISPLAY.index(tipo_atual_display) if tipo_atual_display in LISTA_TIPOS_DISPLAY else 0
            tipo_sel_display = p1.selectbox("Tipo:", LISTA_TIPOS_DISPLAY, index=idx_tipo)
            tipo_sel_valor = TIPO_MAP[tipo_sel_display]
            
            idx_fx = 0
            faixa_banco = str(sel.get('faixa_atual') or 'Branca')
            for i, f in enumerate(FAIXAS_COMPLETAS):
                if f.strip().lower() == faixa_banco.strip().lower():
                    idx_fx = i; break
            fx = p2.selectbox("Faixa:", FAIXAS_COMPLETAS, index=idx_fx)

            # Equipe e Professor
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
                idx_prof = lista_profs_inclusiva.index(nome_prof_atual_display) if nome_prof_atual_display in lista_profs_inclusiva else 0
                novo_prof_display = v2.selectbox("Professor(a) Responsável:", lista_profs_inclusiva, index=idx_prof)

            st.markdown("##### 🔒 Segurança")
            pwd = st.text_input("Nova Senha (opcional):", type="password")
            
            submit_btn = st.form_submit_button("💾 Salvar Todas as Alterações", type="primary")

        if submit_btn:
            upd = {
                "nome": nm.upper(), "email": email.lower().strip(), "cpf": cpf,
                "sexo": sexo_edit, "data_nascimento": nasc_edit.isoformat() if nasc_edit else None,
                "cep": cep, "logradouro": logr.upper(), "numero": num, "complemento": comp.upper(),
                "bairro": bairro.upper(), "cidade": cid.upper(), "uf": uf.upper(),
                "tipo_usuario": tipo_sel_valor, "faixa_atual": fx
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
# 2. GESTÃO DE QUESTÕES (COMPLETA COM IMPORTAÇÃO E IA)
# =========================================
def gestao_questoes_tab():
    aplicar_estilos_admin()
    st.markdown(f"""<div class="admin-header"><h1 style="margin:0; text-align:center; color:{COR_DESTAQUE};">📝 Banco de Questões</h1></div>""", unsafe_allow_html=True)
    db = get_db()
    user = st.session_state.usuario
    user_tipo = str(user.get("tipo_usuario", "aluno")).lower()
    
    if user_tipo not in ["admin", "professor"]: st.error("Acesso negado."); return

    titulos = ["📚 Listar/Editar", "➕ Criar Nova", "📥 Importar", "🔎 Meus Envios", "⏳ Aprovações (Admin)"]
    if user_tipo != "admin": titulos.pop() # Remove aba admin se não for
    
    tabs = st.tabs(titulos)

    # --- LISTAR ---
    with tabs[0]:
        q_ref = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        termo = st.text_input("🔍 Buscar aprovadas:")
        
        for doc in q_ref:
            q = doc.to_dict()
            if termo and termo.lower() not in q.get('pergunta','').lower(): continue
            
            stt = q.get('status', 'aprovada')
            cor = "green" if stt=='aprovada' else "orange"
            
            # CARD VISUAL
            st.markdown(f"""
            <div class="admin-card-moderno">
                <div style="display:flex; justify-content:space-between;">
                    <span class="admin-badge {cor}">{stt.upper()}</span>
                    <span class="admin-badge blue">✍️ {q.get('criado_por','?')}</span>
                </div>
                <h4 style="color:white; margin:10px 0;">{q.get('pergunta')}</h4>
                <div class="curso-badges">
                    <span class="admin-badge green">{q.get('categoria','Geral')}</span>
                    <span class="admin-badge gold">Nível {q.get('dificuldade',1)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("✏️ Editar", key=f"ed_{doc.id}"): st.session_state['edit_q'] = doc.id
            if c2.button("🗑️", key=f"del_{doc.id}"): 
                db.collection('questoes').document(doc.id).delete(); st.rerun()
            
            # MODO EDIÇÃO
            if st.session_state.get('edit_q') == doc.id:
                with st.container(border=True):
                    with st.form(f"fe_{doc.id}"):
                        np = st.text_area("Enunciado", q.get('pergunta'))
                        nc = st.text_input("Categoria", q.get('categoria'))
                        if st.form_submit_button("Salvar"):
                            db.collection('questoes').document(doc.id).update({"pergunta": np, "categoria": nc})
                            st.session_state['edit_q'] = None; st.rerun()

    # --- CRIAR ---
    with tabs[1]:
        with st.form("new_q"):
            st.markdown("#### Nova Questão")
            if ce.IA_ATIVADA: st.caption("🟢 IA Verificação Ativada")
            
            perg = st.text_area("Enunciado *")
            c1, c2 = st.columns(2)
            up_img = c1.file_uploader("Imagem:", type=["jpg","png"])
            up_vid = c2.file_uploader("Vídeo:", type=["mp4"])
            link_vid = c2.text_input("Link YouTube:")
            
            c3, c4 = st.columns(2)
            dif = c3.selectbox("Nível:", NIVEIS_DIFICULDADE)
            cat = c4.text_input("Categoria:", "Geral")
            
            ca, cb = st.columns(2); cc, cd = st.columns(2)
            aa = ca.text_input("A *"); ab = cb.text_input("B *")
            ac = cc.text_input("C"); ad = cd.text_input("D")
            correta = st.selectbox("Correta", ["A","B","C","D"])
            
            if st.form_submit_button("💾 Cadastrar"):
                if perg and aa and ab:
                    # IA Check
                    if ce.IA_ATIVADA:
                        dup, msg = ce.verificar_duplicidade_ia(perg, [d.to_dict() for d in q_ref])
                        if dup: st.error(f"Duplicidade suspeita: {msg}"); st.stop()
                    
                    # Uploads
                    f_img = ce.fazer_upload_midia(up_img) if up_img else None
                    f_vid = ce.fazer_upload_midia(up_vid) if up_vid else link_vid
                    
                    status = "aprovada" if user_tipo == "admin" else "pendente"
                    db.collection('questoes').add({
                        "pergunta": perg, "dificuldade": dif, "categoria": cat,
                        "url_imagem": f_img, "url_video": f_vid,
                        "alternativas": {"A":aa, "B":ab, "C":ac, "D":ad},
                        "resposta_correta": correta, "status": status,
                        "criado_por": user.get('nome','Admin'), "data_criacao": firestore.SERVER_TIMESTAMP
                    })
                    st.success("Criada com sucesso!" if status=="aprovada" else "Enviada para aprovação!"); st.rerun()
                else: st.warning("Preencha campos obrigatórios.")

    # --- IMPORTAR ---
    with tabs[2]:
        if user_tipo == "admin":
            st.info("Importe CSV ou Excel. Colunas: pergunta, alt_a, alt_b, alt_c, alt_d, correta, dificuldade, categoria")
            arquivo = st.file_uploader("Arquivo:", type=["csv", "xlsx"])
            if arquivo and st.button("🚀 Processar"):
                try:
                    if arquivo.name.endswith('.csv'): df = pd.read_csv(arquivo, sep=';')
                    else: df = pd.read_excel(arquivo)
                    
                    prog = st.progress(0)
                    for i, row in df.iterrows():
                        db.collection('questoes').add({
                            "pergunta": str(row['pergunta']), "status": "aprovada",
                            "alternativas": {"A":str(row['alt_a']), "B":str(row['alt_b']), "C":str(row.get('alt_c','')), "D":str(row.get('alt_d',''))},
                            "resposta_correta": str(row['correta']), "dificuldade": int(row.get('dificuldade',1)),
                            "categoria": str(row.get('categoria','Geral')), "criado_por": "Import"
                        })
                        prog.progress((i+1)/len(df))
                    st.success("Importado!"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Erro: {e}")
        else: st.warning("Apenas Admin.")

    # --- MEUS ENVIOS ---
    with tabs[3]:
        nome = user.get('nome', 'Admin')
        meus = list(db.collection('questoes').where('criado_por', '==', nome).stream())
        if not meus: st.info("Sem envios.")
        for doc in meus:
            q = doc.to_dict()
            stt = q.get('status', 'aprovada')
            cor = "green" if stt=='aprovada' else "orange" if stt=='correcao' else "red"
            st.markdown(f"<div class='admin-card-moderno'><h4 style='color:white;'>{q.get('pergunta')}</h4><span class='admin-badge {cor}'>{stt}</span></div>", unsafe_allow_html=True)
            if stt == 'correcao': st.error(f"Motivo: {q.get('feedback_admin')}")

    # --- APROVAÇÕES (ADMIN) ---
    if user_tipo == "admin":
        with tabs[4]:
            pend = list(db.collection('questoes').where('status', '==', 'pendente').stream())
            if not pend: st.success("Nada pendente!")
            for doc in pend:
                q = doc.to_dict()
                with st.container(border=True):
                    st.markdown(f"**{q.get('criado_por')}** enviou:")
                    st.markdown(f"#### {q.get('pergunta')}")
                    
                    # IA Auditoria
                    if st.button("🤖 Auditar com IA", key=f"ia_{doc.id}"):
                        res = ce.auditoria_ia_questao(q.get('pergunta'), q.get('alternativas'), q.get('resposta_correta'))
                        st.info(res)

                    c1, c2 = st.columns(2)
                    if c1.button("✅ Aprovar", key=f"ok_{doc.id}", type="primary"):
                        db.collection('questoes').document(doc.id).update({"status":"aprovada"})
                        st.rerun()
                    
                    fb = st.text_input("Motivo correção:", key=f"fb_{doc.id}")
                    if c2.button("🟠 Pedir Correção", key=f"fix_{doc.id}"):
                        db.collection('questoes').document(doc.id).update({"status":"correcao", "feedback_admin": fb})
                        st.rerun()

# =========================================
# 3. GESTÃO DE EXAMES (COMPLETA E CORRIGIDA)
# =========================================
def gestao_exame_de_faixa_route():
    aplicar_estilos_admin()
    st.markdown(f"""<div class="admin-header"><h1>📜 Gerenciador de Exames</h1></div>""", unsafe_allow_html=True)
    db = get_db()
    tab1, tab2 = st.tabs(["📝 Configurar Prova", "✅ Autorizar Alunos"])
    
    # CONFIGURAR
    with tab1:
        fx = st.selectbox("Faixa:", FAIXAS_COMPLETAS)
        configs = list(db.collection('config_exames').where('faixa', '==', fx).limit(1).stream())
        conf_data = configs[0].to_dict() if configs else {}
        sel_ids = set(conf_data.get('questoes_ids', []))
        
        # Filtros de Questões
        c1, c2 = st.columns(2)
        niv = c1.multiselect("Nível:", NIVEIS_DIFICULDADE, default=[1,2,3,4])
        
        qs = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        cats = sorted(list(set([d.to_dict().get('categoria','Geral') for d in qs])))
        tema = c2.multiselect("Tema:", cats, default=cats)

        with st.container(height=400, border=True):
            for doc in qs:
                d = doc.to_dict()
                if d.get('dificuldade',1) in niv and d.get('categoria','Geral') in tema:
                    chk = st.checkbox(f"{d.get('pergunta')}", value=(doc.id in sel_ids), key=f"x_{doc.id}")
                    if chk: sel_ids.add(doc.id)
                    elif doc.id in sel_ids: sel_ids.discard(doc.id)
        
        st.info(f"**{len(sel_ids)}** questões selecionadas.")
        
        c1, c2 = st.columns(2)
        tm = c1.number_input("Tempo (min)", value=int(conf_data.get('tempo_limite', 45)))
        nt = c2.number_input("Aprovação (%)", value=int(conf_data.get('aprovacao_minima', 70)))
        
        if st.button("💾 Salvar Configuração"):
            data = {"faixa": fx, "questoes_ids": list(sel_ids), "tempo_limite": tm, "aprovacao_minima": nt}
            if configs: db.collection('config_exames').document(configs[0].id).update(data)
            else: db.collection('config_exames').add(data)
            st.success("Configuração salva!"); time.sleep(1); st.rerun()

    # AUTORIZAR
    with tab2:
        st.markdown("### Liberar Exame para Alunos")
        # Correção do erro eq_doc: Busca segura
        alunos = list(db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream())
        
        if not alunos: st.info("Nenhum aluno encontrado.")
        
        for doc in alunos:
            d = doc.to_dict()
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                
                # Busca Equipe com try/except para evitar o NameError
                nome_eq = "Sem Equipe"
                try:
                    vincs = list(db.collection('alunos').where('usuario_id', '==', doc.id).limit(1).stream())
                    if vincs:
                        eid = vincs[0].to_dict().get('equipe_id')
                        if eid:
                            eq_snap = db.collection('equipes').document(eid).get()
                            if eq_snap.exists: nome_eq = eq_snap.to_dict().get('nome', 'Sem Nome')
                except: pass
                
                c1.markdown(f"**{d.get('nome')}**")
                c1.caption(f"Equipe: {nome_eq}")
                
                hab = d.get('exame_habilitado', False)
                cor = "green" if hab else "gray"
                msg = "Liberado" if hab else "Bloqueado"
                c2.markdown(f":{cor}[{msg}]")
                
                if hab:
                    if c3.button("⛔ Bloquear", key=f"b_{doc.id}"):
                        db.collection('usuarios').document(doc.id).update({"exame_habilitado": False})
                        st.rerun()
                else:
                    if c3.button("✅ Liberar", key=f"l_{doc.id}"):
                        db.collection('usuarios').document(doc.id).update({
                            "exame_habilitado": True, 
                            "faixa_exame": fx,
                            "exame_inicio": datetime.now().isoformat()
                        })
                        st.success("Liberado!"); st.rerun()

# =========================================
# ROUTER
# =========================================
def gestao_questoes(): gestao_questoes_tab()
def gestao_exame_de_faixa(): gestao_exame_de_faixa_route()
def gestao_usuarios(u): gestao_usuarios_tab()
