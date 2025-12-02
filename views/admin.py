import streamlit as st
import pandas as pd
import bcrypt
import random
import time 
from datetime import datetime, time as dtime 
from database import get_db
from firebase_admin import firestore

try:
    from utils import carregar_todas_questoes, salvar_questoes
except ImportError:
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass

# Listas de Referência
FAIXAS_COMPLETAS = [
    "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]

NIVEIS_DIFICULDADE = [1, 2, 3, 4]

# =========================================
# 1. GESTÃO DE USUÁRIOS
# =========================================
def gestao_usuarios(usuario_logado):
    if st.button("🏠 Voltar ao Início", key="btn_voltar_adm"):
        st.session_state.menu_selection = "Início"; st.rerun()

    st.markdown("<h1 style='color:#FFD700;'>👥 Gestão de Usuários</h1>", unsafe_allow_html=True)
    db = get_db()
    
    users = [d.to_dict() | {"id": d.id} for d in db.collection('usuarios').stream()]
    if not users: st.warning("Vazio."); return

    df = pd.DataFrame(users)
    # Garante que as colunas existam mesmo se vazias
    cols = ['nome', 'email', 'tipo_usuario', 'faixa_atual']
    for c in cols:
        if c not in df.columns: df[c] = "-"
        
    st.dataframe(df[cols], use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🛠️ Editar")
    sel = st.selectbox("Usuário:", users, format_func=lambda x: f"{x.get('nome')} ({x.get('email')})")
    
    if sel:
        with st.form(f"edt_{sel['id']}"):
            nm = st.text_input("Nome:", value=sel.get('nome',''))
            tp = st.selectbox("Tipo:", ["aluno","professor","admin"], index=["aluno","professor","admin"].index(sel.get('tipo_usuario','aluno')))
            fx = st.selectbox("Faixa Atual:", ["Branca"] + FAIXAS_COMPLETAS, index=(["Branca"] + FAIXAS_COMPLETAS).index(sel.get('faixa_atual', 'Branca')) if sel.get('faixa_atual') in FAIXAS_COMPLETAS else 0)
            pwd = st.text_input("Nova Senha (opcional):", type="password")
            
            if st.form_submit_button("Salvar"):
                upd = {"nome": nm.upper(), "tipo_usuario": tp, "faixa_atual": fx}
                if pwd: upd["senha"] = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode(); upd["precisa_trocar_senha"] = True
                db.collection('usuarios').document(sel['id']).update(upd)
                st.success("Salvo!"); time.sleep(1); st.rerun()
                
        if st.button("🗑️ Excluir Usuário", key=f"del_{sel['id']}"):
            db.collection('usuarios').document(sel['id']).delete()
            st.warning("Excluído."); time.sleep(1); st.rerun()

# =========================================
# 2. GESTÃO DE QUESTÕES (COM NÍVEIS)
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>📝 Banco de Questões</h1>", unsafe_allow_html=True)
    db = get_db()
    
    user = st.session_state.usuario
    if str(user.get("tipo", "")).lower() not in ["admin", "professor"]:
        st.error("Acesso negado."); return

    tab1, tab2 = st.tabs(["📚 Listar/Editar", "➕ Adicionar Nova"])

    # --- TAB 1: LISTAR ---
    with tab1:
        # Carrega questões e trata compatibilidade (se tiver faixa antiga ou nivel novo)
        questoes_ref = list(db.collection('questoes').stream())
        lista_q = []
        for doc in questoes_ref:
            d = doc.to_dict()
            # Fallback visual: Se não tiver nível, mostra 'Antiga'
            nivel_show = d.get('dificuldade', d.get('faixa', '?'))
            lista_q.append({
                "id": doc.id,
                "Nível": nivel_show,
                "Categoria": d.get('categoria', d.get('tema', 'Geral')),
                "Pergunta": d.get('pergunta'),
                "Status": d.get('status', 'aprovada')
            })
            
        if not lista_q:
            st.info("Banco vazio.")
        else:
            df = pd.DataFrame(lista_q)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            q_sel_id = st.selectbox("Selecione para Editar/Excluir:", [q['id'] for q in lista_q], format_func=lambda x: next((item['Pergunta'] for item in lista_q if item['id'] == x), x))
            
            if q_sel_id:
                q_data = db.collection('questoes').document(q_sel_id).get().to_dict()
                with st.expander("✏️ Editar Questão", expanded=True):
                    with st.form(f"edit_{q_sel_id}"):
                        enunciado = st.text_area("Pergunta:", value=q_data.get('pergunta',''))
                        c1, c2 = st.columns(2)
                        
                        # Tenta pegar valor antigo (1-4) ou default 1
                        val_dif = q_data.get('dificuldade', 1)
                        if not isinstance(val_dif, int): val_dif = 1
                        
                        nv_dif = c1.selectbox("Nível de Dificuldade:", NIVEIS_DIFICULDADE, index=NIVEIS_DIFICULDADE.index(val_dif))
                        nv_cat = c2.text_input("Categoria:", value=q_data.get('categoria', q_data.get('tema','Geral')))
                        
                        # Alternativas
                        alts = q_data.get('alternativas', {})
                        if not alts and 'opcoes' in q_data: # Compatibilidade antiga
                            ops = q_data['opcoes']
                            alts = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                            
                        ca, cb = st.columns(2); cc, cd = st.columns(2)
                        rA = ca.text_input("A)", value=alts.get('A','')); rB = cb.text_input("B)", value=alts.get('B',''))
                        rC = cc.text_input("C)", value=alts.get('C','')); rD = cd.text_input("D)", value=alts.get('D',''))
                        
                        # Resposta
                        resp_atual = q_data.get('resposta_correta', q_data.get('correta','A'))
                        # Se estiver salva como texto completo (legado), tenta achar a letra
                        if len(resp_atual) > 1:
                            for l, txt in alts.items():
                                if txt == resp_atual: resp_atual = l; break
                        if resp_atual not in ["A","B","C","D"]: resp_atual = "A"
                            
                        corr = st.selectbox("Correta:", ["A","B","C","D"], index=["A","B","C","D"].index(resp_atual))
                        
                        if st.form_submit_button("💾 Atualizar"):
                            db.collection('questoes').document(q_sel_id).update({
                                "pergunta": enunciado, "dificuldade": nv_dif, "categoria": nv_cat,
                                "alternativas": {"A":rA, "B":rB, "C":rC, "D":rD},
                                "resposta_correta": corr, "faixa": firestore.DELETE_FIELD # Remove campo legado
                            })
                            st.success("Atualizado!"); time.sleep(1); st.rerun()
                            
                if st.button("🗑️ Excluir Definitivamente", type="primary"):
                    db.collection('questoes').document(q_sel_id).delete()
                    st.success("Deletado."); time.sleep(1); st.rerun()

    # --- TAB 2: CRIAR ---
    with tab2:
        with st.form("new_q"):
            st.markdown("#### Nova Questão")
            pergunta = st.text_area("Enunciado:")
            c1, c2 = st.columns(2)
            dificuldade = c1.selectbox("Nível de Dificuldade:", NIVEIS_DIFICULDADE, help="1=Fácil, 4=Muito Difícil")
            categoria = c2.text_input("Categoria:", "Geral")
            
            st.markdown("**Alternativas:**")
            col_a, col_b = st.columns(2)
            alt_a = col_a.text_input("A)")
            alt_b = col_b.text_input("B)")
            alt_c = col_a.text_input("C)")
            alt_d = col_b.text_input("D)")
            
            correta = st.selectbox("Alternativa Correta:", ["A", "B", "C", "D"])
            
            if st.form_submit_button("💾 Cadastrar Questão"):
                if pergunta and alt_a and alt_b:
                    payload = {
                        "pergunta": pergunta,
                        "dificuldade": dificuldade, # Salva Nível (1-4)
                        "categoria": categoria,
                        "alternativas": {"A": alt_a, "B": alt_b, "C": alt_c, "D": alt_d},
                        "resposta_correta": correta,
                        "status": "aprovada",
                        "criado_por": user.get('nome', 'Admin'),
                        "data_criacao": firestore.SERVER_TIMESTAMP
                    }
                    db.collection('questoes').add(payload)
                    st.success("Cadastrada com sucesso!"); time.sleep(1); st.rerun()
                else:
                    st.warning("Preencha enunciado e alternativas.")

# =========================================
# 3. GESTÃO DE EXAME (VINCULA FAIXA <-> DIFICULDADE)
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>⚙️ Configuração de Exames</h1>", unsafe_allow_html=True)
    db = get_db()

    tab1, tab2, tab3 = st.tabs(["📝 Regras da Prova", "👁️ Visualizar", "✅ Autorizar Alunos"])

    # --- ABA 1: REGRAS ---
    with tab1:
        st.subheader("Definir Regras por Faixa")
        faixa_sel = st.selectbox("Selecione a Prova de Faixa:", FAIXAS_COMPLETAS)
        
        # Carrega config atual
        configs = db.collection('config_exames').where('faixa', '==', faixa_sel).stream()
        conf_atual = {}
        doc_id = None
        for d in configs: conf_atual = d.to_dict(); doc_id = d.id; break
        
        st.info(f"Configurando regras para: **Exame de Faixa {faixa_sel.upper()}**")
        
        with st.form("conf_exame"):
            c1, c2 = st.columns(2)
            # AQUI ESTÁ A MUDANÇA: O professor escolhe qual nível de questão essa prova usa
            dif_alvo = c1.selectbox("Usar Questões de Nível:", NIVEIS_DIFICULDADE, index=NIVEIS_DIFICULDADE.index(conf_atual.get('dificuldade_alvo', 1)))
            qtd = c2.number_input("Quantidade de Questões:", 1, 50, int(conf_atual.get('qtd_questoes', 10)))
            
            c3, c4 = st.columns(2)
            tempo = c3.number_input("Tempo Limite (min):", 10, 180, int(conf_atual.get('tempo_limite', 45)))
            nota = c4.number_input("Aprovação Mínima (%):", 10, 100, int(conf_atual.get('aprovacao_minima', 70)))
            
            if st.form_submit_button("💾 Salvar Regras"):
                dados = {
                    "faixa": faixa_sel,
                    "dificuldade_alvo": dif_alvo, # Salva o vinculo
                    "qtd_questoes": qtd,
                    "tempo_limite": tempo,
                    "aprovacao_minima": nota,
                    "atualizado_em": firestore.SERVER_TIMESTAMP
                }
                if doc_id: db.collection('config_exames').document(doc_id).update(dados)
                else: db.collection('config_exames').add(dados)
                st.success(f"Regras salvas! A prova de {faixa_sel} usará questões Nível {dif_alvo}.")
                time.sleep(1.5); st.rerun()

    # --- ABA 2: VISUALIZAR ---
    with tab2:
        st.write("Resumo das configurações atuais:")
        alls = db.collection('config_exames').stream()
        for doc in alls:
            d = doc.to_dict()
            st.markdown(f"**{d.get('faixa')}** ➔ Nível {d.get('dificuldade_alvo', 1)} | {d.get('qtd_questoes')} questões | {d.get('tempo_limite')} min")
            st.markdown("---")

    # --- ABA 3: AUTORIZAR ---
    with tab3:
        with st.container(border=True):
            st.subheader("🗓️ Agendar Exame")
            c1, c2 = st.columns(2)
            d_ini = c1.date_input("Data Início:", datetime.now())
            d_fim = c2.date_input("Data Fim:", datetime.now())
            c3, c4 = st.columns(2)
            h_ini = c3.time_input("Hora Início:", dtime(0,0))
            h_fim = c4.time_input("Hora Fim:", dtime(23,59))
            dt_ini = datetime.combine(d_ini, h_ini)
            dt_fim = datetime.combine(d_fim, h_fim)

        st.markdown("### Alunos")
        users = db.collection('usuarios').where('tipo_usuario','==','aluno').stream()
        
        cols = st.columns([3,2,2,2,1])
        cols[0].write("**Nome**"); cols[1].write("**Equipe**"); cols[2].write("**Exame**"); cols[3].write("**Status**"); cols[4].write("**Ação**")
        st.divider()
        
        for u in users:
            d = u.to_dict(); uid = u.id
            # Busca equipe (simplificado)
            eq_nome = "-"
            al_ref = list(db.collection('alunos').where('usuario_id','==',uid).limit(1).stream())
            if al_ref:
                eid = al_ref[0].to_dict().get('equipe_id')
                if eid: 
                    eq = db.collection('equipes').document(eid).get()
                    if eq.exists: eq_nome = eq.to_dict().get('nome')

            c1, c2, c3, c4, c5 = st.columns([3,2,2,2,1])
            c1.write(d.get('nome'))
            c2.write(eq_nome)
            
            idx_f = FAIXAS_COMPLETAS.index(d.get('faixa_exame')) if d.get('faixa_exame') in FAIXAS_COMPLETAS else 0
            fx = c3.selectbox("Faixa", FAIXAS_COMPLETAS, index=idx_f, key=f"f_{uid}", label_visibility="collapsed")
            
            status = d.get('status_exame', 'pendente')
            hab = d.get('exame_habilitado', False)
            
            if hab:
                msg = "🟢 Liberado"
                if status == 'bloqueado': msg = "⛔ Bloqueado"
                elif status == 'reprovado': msg = "🔴 Reprovado"
                elif status == 'aprovado': msg = "🏆 Aprovado"
                elif status == 'em_andamento': msg = "🟡 Em curso"
                c4.write(msg)
                
                if c5.button("⛔", key=f"stop_{uid}"):
                    db.collection('usuarios').document(uid).update({
                        "exame_habilitado": False, "status_exame": "pendente",
                        "exame_inicio": firestore.DELETE_FIELD, "exame_fim": firestore.DELETE_FIELD,
                        "motivo_bloqueio": firestore.DELETE_FIELD
                    })
                    st.rerun()
            else:
                c4.write("⚪")
                if c5.button("✅", key=f"go_{uid}"):
                    db.collection('usuarios').document(uid).update({
                        "exame_habilitado": True, "faixa_exame": fx,
                        "exame_inicio": dt_ini.isoformat(), "exame_fim": dt_fim.isoformat(),
                        "status_exame": "pendente", "status_exame_em_andamento": False
                    })
                    st.success("OK!"); time.sleep(0.5); st.rerun()
            st.divider()
