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
try:
    from utils import (
        carregar_todas_questoes, 
        salvar_questoes, 
        fazer_upload_midia, 
        normalizar_link_video, 
        verificar_duplicidade_ia,
        IA_ATIVADA 
    )
except ImportError:
    IA_ATIVADA = False
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass
    def fazer_upload_midia(f): return None
    def normalizar_link_video(u): return u
    def verificar_duplicidade_ia(n, l, t=0.85): return False, None

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

def get_badge_nivel(n): return MAPA_NIVEIS.get(n, "⚪ ?")

# =========================================
# GESTÃO DE USUÁRIOS (TAB INTERNA)
# =========================================
def gestao_usuarios_tab():
    db = get_db()
    
    # 1. Carregar Listas Auxiliares (Equipes e Professores)
    users_ref = list(db.collection('usuarios').stream())
    users = [d.to_dict() | {"id": d.id} for d in users_ref]
    
    # Lista de Equipes
    equipes_ref = list(db.collection('equipes').stream())
    mapa_equipes = {d.id: d.to_dict().get('nome', 'Sem Nome') for d in equipes_ref} # ID -> Nome
    mapa_equipes_inv = {v: k for k, v in mapa_equipes.items()} # Nome -> ID
    lista_equipes = ["Sem Equipe"] + sorted(list(mapa_equipes.values()))

    # Lista de Professores (Com Vínculo de Equipe)
    profs_vinc_ref = list(db.collection('professores').stream())
    mapa_prof_equipe = {} # ProfID -> NomeEquipe
    for pv in profs_vinc_ref:
        d = pv.to_dict()
        uid = d.get('usuario_id')
        eid = d.get('equipe_id')
        if uid and eid:
            mapa_prof_equipe[uid] = mapa_equipes.get(eid, "?")

    # Monta lista de nomes de professores com a equipe entre parênteses
    profs_users = [u for u in users if u.get('tipo_usuario') == 'professor']
    
    mapa_profs_display = {} # "Nome (Equipe)" -> ID
    mapa_profs_id_to_display = {} # ID -> "Nome (Equipe)"
    
    for p in profs_users:
        pid = p['id']
        pnome = p.get('nome', 'Sem Nome')
        pequipe = mapa_prof_equipe.get(pid, "Sem Equipe")
        label = f"{pnome} ({pequipe})"
        mapa_profs_display[label] = pid
        mapa_profs_id_to_display[pid] = label

    lista_profs_formatada = ["Sem Professor"] + sorted(list(mapa_profs_display.keys()))

    if not users: st.warning("Vazio."); return
    
    # 2. Tabela Principal
    df = pd.DataFrame(users)
    c1, c2 = st.columns(2)
    filtro_nome = c1.text_input("🔍 Buscar Nome/Email/CPF:")
    filtro_tipo = c2.multiselect("Filtrar Tipo:", df['tipo_usuario'].unique() if 'tipo_usuario' in df.columns else [])

    if filtro_nome:
        termo = filtro_nome.upper()
        df = df[
            df['nome'].str.upper().str.contains(termo) | 
            df['email'].str.upper().str.contains(termo) |
            df['cpf'].str.contains(termo)
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
        # --- Lógica para buscar vínculo atual ---
        vinculo_equipe_id = None
        vinculo_prof_id = None
        
        # Busca em alunos
        if sel.get('tipo_usuario') == 'aluno':
            vincs = list(db.collection('alunos').where('usuario_id', '==', sel['id']).limit(1).stream())
            if vincs:
                d_vinc = vincs[0].to_dict()
                vinculo_equipe_id = d_vinc.get('equipe_id')
                vinculo_prof_id = d_vinc.get('professor_id')
        
        # Busca em professores
        elif sel.get('tipo_usuario') == 'professor':
            vincs = list(db.collection('professores').where('usuario_id', '==', sel['id']).limit(1).stream())
            if vincs:
                d_vinc = vincs[0].to_dict()
                vinculo_equipe_id = d_vinc.get('equipe_id')

        # --- Início do Formulário ---
        with st.form(f"edt_{sel['id']}"):
            # BLOCO 1: DADOS PESSOAIS
            st.markdown("##### 👤 Dados Pessoais")
            c1, c2 = st.columns(2)
            nm = c1.text_input("Nome Completo:", value=sel.get('nome',''))
            email = c2.text_input("E-mail:", value=sel.get('email',''))
            
            c3, c4, c5 = st.columns([1.5, 1, 1])
            cpf = c3.text_input("CPF:", value=sel.get('cpf',''))
            
            idx_s = 0
            if sel.get('sexo') in OPCOES_SEXO: idx_s = OPCOES_SEXO.index(sel.get('sexo'))
            sexo_edit = c4.selectbox("Sexo:", OPCOES_SEXO, index=idx_s)
            
            val_n = None
            if sel.get('data_nascimento'):
                try: val_n = datetime.fromisoformat(sel.get('data_nascimento')).date()
                except: pass
            nasc_edit = c5.date_input("Nascimento:", value=val_n, min_value=date(1940,1,1), max_value=date.today(), format="DD/MM/YYYY")

            # BLOCO 2: ENDEREÇO
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

            # BLOCO 3: PERFIL E VÍNCULOS
            st.markdown("##### 🥋 Perfil e Vínculos")
            p1, p2 = st.columns(2)
            tp = p1.selectbox("Tipo:", ["aluno","professor","admin"], index=["aluno","professor","admin"].index(sel.get('tipo_usuario','aluno')))
            
            idx_fx = 0
            faixa_atual = sel.get('faixa_atual', 'Branca')
            if faixa_atual in FAIXAS_COMPLETAS: idx_fx = FAIXAS_COMPLETAS.index(faixa_atual)
            fx = p2.selectbox("Faixa:", FAIXAS_COMPLETAS, index=idx_fx)

            # --- SEÇÃO DE EQUIPE E PROFESSOR ---
            st.caption("Selecione a equipe e o professor responsável (para alunos).")
            v1, v2 = st.columns(2)
            
            # Equipe
            nome_eq_atual = mapa_equipes.get(vinculo_equipe_id, "Sem Equipe")
            idx_eq = lista_equipes.index(nome_eq_atual) if nome_eq_atual in lista_equipes else 0
            nova_equipe_nome = v1.selectbox("Equipe:", lista_equipes, index=idx_eq)
            
            # Professor (Sempre visível, mas rotulado)
            nome_prof_atual_display = mapa_profs_id_to_display.get(vinculo_prof_id, "Sem Professor")
            idx_prof = lista_profs_formatada.index(nome_prof_atual_display) if nome_prof_atual_display in lista_profs_formatada else 0
            novo_prof_display = v2.selectbox("Professor Responsável (se Aluno):", lista_profs_formatada, index=idx_prof)

            # BLOCO 4: SEGURANÇA
            st.markdown("##### 🔒 Segurança")
            pwd = st.text_input("Nova Senha (opcional):", type="password")
            
            # --- SALVAR ---
            if st.form_submit_button("💾 Salvar Todas as Alterações"):
                # 1. Atualiza Usuário
                upd = {
                    "nome": nm.upper(), "email": email.lower().strip(), "cpf": cpf,
                    "sexo": sexo_edit, "data_nascimento": nasc_edit.isoformat() if nasc_edit else None,
                    "cep": cep, "logradouro": logr.upper(), "numero": num, "complemento": comp.upper(),
                    "bairro": bairro.upper(), "cidade": cid.upper(), "uf": uf.upper(),
                    "tipo_usuario": tp, "faixa_atual": fx
                }
                if pwd: 
                    upd["senha"] = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
                    upd["precisa_trocar_senha"] = True
                
                try:
                    db.collection('usuarios').document(sel['id']).update(upd)
                    
                    # 2. Atualiza Vínculos
                    novo_eq_id = mapa_equipes_inv.get(nova_equipe_nome)
                    
                    if tp == 'aluno':
                        novo_p_id = mapa_profs_display.get(novo_prof_display) # Pega ID pelo nome formatado
                        
                        vincs = list(db.collection('alunos').where('usuario_id', '==', sel['id']).stream())
                        dados_vinc = {"equipe_id": novo_eq_id, "professor_id": novo_p_id, "faixa_atual": fx}
                        
                        if vincs:
                            db.collection('alunos').document(vincs[0].id).update(dados_vinc)
                        else:
                            dados_vinc['usuario_id'] = sel['id']
                            dados_vinc['status_vinculo'] = 'ativo'
                            db.collection('alunos').add(dados_vinc)
                            
                    elif tp == 'professor':
                        vincs = list(db.collection('professores').where('usuario_id', '==', sel['id']).stream())
                        dados_vinc = {"equipe_id": novo_eq_id}
                        
                        if vincs:
                            db.collection('professores').document(vincs[0].id).update(dados_vinc)
                        else:
                            dados_vinc['usuario_id'] = sel['id']
                            dados_vinc['status_vinculo'] = 'ativo'
                            db.collection('professores').add(dados_vinc)

                    st.success("✅ Cadastro e vínculos atualizados com sucesso!"); time.sleep(1.5); st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
                
        if st.button("🗑️ Excluir Usuário", key=f"del_{sel['id']}"):
            db.collection('usuarios').document(sel['id']).delete()
            st.warning("Usuário excluído."); time.sleep(1); st.rerun()

# =========================================
# GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes_tab():
    db = get_db()
    user = st.session_state.usuario
    tab1, tab2 = st.tabs(["📚 Listar/Editar", "➕ Adicionar Nova"])

    with tab1:
        q_ref = list(db.collection('questoes').stream())
        c1, c2 = st.columns(2)
        termo = c1.text_input("🔍 Buscar Questão:")
        filt_n = c2.multiselect("Nível:", NIVEIS_DIFICULDADE)
        
        q_filtro = []
        for doc in q_ref:
            d = doc.to_dict(); d['id'] = doc.id
            if termo and termo.lower() not in d.get('pergunta','').lower(): continue
            if filt_n and d.get('dificuldade',1) not in filt_n: continue
            q_filtro.append(d)
            
        if not q_filtro: st.info("Nada encontrado.")
        else:
            st.caption(f"{len(q_filtro)} questões encontradas")
            for q in q_filtro:
                with st.container(border=True):
                    ch, cb = st.columns([5, 1])
                    bdg = get_badge_nivel(q.get('dificuldade',1))
                    ch.markdown(f"**{bdg}** | {q.get('categoria','Geral')} | ✍️ {q.get('criado_por','?')}")
                    ch.markdown(f"##### {q.get('pergunta')}")
                    
                    if q.get('url_imagem'): ch.image(q.get('url_imagem'), width=150)
                    if cb.button("✏️", key=f"ed_{q['id']}"): st.session_state['edit_q'] = q['id']
                
                if st.session_state.get('edit_q') == q['id']:
                    with st.container(border=True):
                        st.markdown("#### ✏️ Editando")
                        with st.form(f"f_ed_{q['id']}"):
                            perg = st.text_area("Enunciado:", value=q.get('pergunta',''))
                            c_img, c_vid = st.columns(2)
                            up_img = c_img.file_uploader("Nova Imagem:", type=["jpg","png"], key=f"u_i_{q['id']}")
                            url_i_at = q.get('url_imagem','')
                            up_vid = c_vid.file_uploader("Novo Vídeo:", type=["mp4","mov"], key=f"u_v_{q['id']}")
                            url_v_manual = c_vid.text_input("Link Externo:", value=q.get('url_video',''))
                            c1, c2 = st.columns(2)
                            dif = c1.selectbox("Nível:", NIVEIS_DIFICULDADE, index=NIVEIS_DIFICULDADE.index(q.get('dificuldade',1)))
                            cat = c2.text_input("Categoria:", value=q.get('categoria','Geral'))
                            alts = q.get('alternativas',{})
                            ca, cb_col = st.columns(2); cc, cd = st.columns(2)
                            rA = ca.text_input("A)", alts.get('A','')); rB = cb_col.text_input("B)", alts.get('B',''))
                            rC = cc.text_input("C)", alts.get('C','')); rD = cd.text_input("D)", alts.get('D',''))
                            corr = st.selectbox("Correta:", ["A","B","C","D"], index=["A","B","C","D"].index(q.get('resposta_correta','A')))
                            
                            cols = st.columns(2)
                            if cols[0].form_submit_button("💾 Salvar"):
                                fin_img = url_i_at
                                if up_img: fin_img = fazer_upload_midia(up_img)
                                fin_vid = url_v_manual
                                if up_vid: fin_vid = fazer_upload_midia(up_vid)
                                db.collection('questoes').document(q['id']).update({
                                    "pergunta": perg, "dificuldade": dif, "categoria": cat,
                                    "url_imagem": fin_img, "url_video": fin_vid,
                                    "alternativas": {"A":rA, "B":rB, "C":rC, "D":rD},
                                    "resposta_correta": corr
                                })
                                st.session_state['edit_q'] = None; st.success("Salvo!"); time.sleep(1); st.rerun()
                            if cols[1].form_submit_button("Cancelar"):
                                st.session_state['edit_q'] = None; st.rerun()
                        
                        if st.button("🗑️ Deletar", key=f"del_q_{q['id']}", type="primary"):
                            db.collection('questoes').document(q['id']).delete()
                            st.session_state['edit_q'] = None; st.success("Deletado."); st.rerun()

    with tab2:
        sub_tab_manual, sub_tab_lote = st.tabs(["✍️ Manual (Uma)", "📂 Em Lote (Várias)"])
        with sub_tab_manual:
            with st.form("new_q"):
                st.markdown("#### Nova Questão")
                
                if IA_ATIVADA:
                    st.caption("🟢 IA de Anti-Duplicidade Ativada")
                else:
                    st.caption("🔴 IA Não Detectada (Instale sentence-transformers)")

                perg = st.text_area("Enunciado:")
                c1, c2 = st.columns(2)
                up_img = c1.file_uploader("Imagem:", type=["jpg","png"])
                up_vid = c2.file_uploader("Vídeo:", type=["mp4"])
                link_vid = c2.text_input("Link YouTube:")
                c3, c4 = st.columns(2)
                dif = c3.selectbox("Nível:", NIVEIS_DIFICULDADE)
                cat = c4.text_input("Categoria:", "Geral")
                ca, cb_col = st.columns(2); cc, cd = st.columns(2)
                alt_a = ca.text_input("A)"); alt_b = cb_col.text_input("B)")
                alt_c = cc.text_input("C)"); alt_d = cd.text_input("D)")
                correta = st.selectbox("Correta:", ["A","B","C","D"])
                
                if st.form_submit_button("💾 Cadastrar"):
                    if perg and alt_a and alt_b:
                        if IA_ATIVADA:
                            try:
                                with st.spinner("Estamos verificando se há outra questão igual em nosso banco..."):
                                    all_qs_snap = list(db.collection('questoes').stream())
                                    lista_qs = [d.to_dict() for d in all_qs_snap]
                                    is_dup, dup_msg = verificar_duplicidade_ia(perg, lista_qs, threshold=0.75)
                                    
                                    if is_dup:
                                        st.error("⚠️ Detectamos que há uma questão igual em nosso banco de questões")
                                        st.warning(f
