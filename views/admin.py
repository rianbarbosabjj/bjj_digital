import streamlit as st
import pandas as pd
import bcrypt
from database import get_db
from utils import formatar_e_validar_cpf, carregar_questoes, salvar_questoes, carregar_todas_questoes
import os
import json
from datetime import datetime, time

# ... (código existente: gestao_usuarios, gestao_questoes) ...

# =========================================
# GESTÃO DE EXAME DE FAIXA (ATUALIZADO)
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    
    user_logado = st.session_state.usuario
    if user_logado["tipo"] not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return

    tab_prova, tab_alunos = st.tabs(["📝 Montar Prova", "✅ Habilitar Alunos"])

    # ... (código existente: ABA 1: MONTAR PROVA) ...

    # ---------------------------------------------------------
    # ABA 2: HABILITAR ALUNOS
    # ---------------------------------------------------------
    with tab_alunos:
        st.subheader("Autorizar Alunos para o Exame")
        db = get_db()

        # ... (código existente: carregar equipes_permitidas) ...

        alunos_ref = db.collection('alunos')
        if equipes_permitidas:
            query = alunos_ref.where('equipe_id', 'in', equipes_permitidas[:10])
        else:
            query = alunos_ref

        docs_alunos = list(query.stream())
        
        if not docs_alunos:
            st.info("Nenhum aluno encontrado nas suas equipes.")
        else:
            users_map = {d.id: d.to_dict().get('nome','?') for d in db.collection('usuarios').stream()}
            equipes_map = {d.id: d.to_dict().get('nome','?') for d in db.collection('equipes').stream()}
            
            # Configuração Global de Datas (Opcional: pode ser individual)
            st.markdown("#### Configurar Período do Exame")
            c_ini, c_fim = st.columns(2)
            data_inicio = c_ini.date_input("Data Início:", value=datetime.now())
            hora_inicio = c_ini.time_input("Hora Início:", value=time(0, 0))
            data_fim = c_fim.date_input("Data Fim:", value=datetime.now())
            hora_fim = c_fim.time_input("Hora Fim:", value=time(23, 59))
            
            dt_inicio_comb = datetime.combine(data_inicio, hora_inicio)
            dt_fim_comb = datetime.combine(data_fim, hora_fim)

            if dt_inicio_comb >= dt_fim_comb:
                st.warning("A data de fim deve ser posterior à data de início.")

            st.markdown("---")
            
            # Tabela de Habilitação
            # Adicionar colunas para datas
            header = st.columns([3, 2, 2, 3, 2]) 
            header[0].markdown("**Aluno**")
            header[1].markdown("**Equipe**")
            header[2].markdown("**Faixa**")
            header[3].markdown("**Período Habilitado**") # Nova coluna
            header[4].markdown("**Ação**")
            st.markdown("---")
            
            for doc in docs_alunos:
                d = doc.to_dict()
                uid = d.get('usuario_id')
                eid = d.get('equipe_id')
                
                if equipes_permitidas is None or eid in equipes_permitidas:
                    nome_aluno = users_map.get(uid, "Desconhecido")
                    nome_equipe = equipes_map.get(eid, "Sem Equipe")
                    habilitado = d.get('exame_habilitado', False)
                    
                    # Formata datas salvas para exibição
                    inicio_salvo = d.get('exame_inicio')
                    fim_salvo = d.get('exame_fim')
                    
                    periodo_str = "-"
                    if inicio_salvo and fim_salvo:
                        # Firestore retorna datetime com timezone, precisamos converter para string simples
                        # ou garantir que estamos lidando com objetos datetime
                        try:
                            # Remove timezone info para simplificar visualização local
                            ini_str = inicio_salvo.replace(tzinfo=None).strftime("%d/%m %H:%M")
                            fim_str = fim_salvo.replace(tzinfo=None).strftime("%d/%m %H:%M")
                            periodo_str = f"{ini_str} até {fim_str}"
                        except:
                            periodo_str = "Data Inválida"

                    cols = st.columns([3, 2, 2, 3, 2])
                    cols[0].write(nome_aluno)
                    cols[1].write(nome_equipe)
                    cols[2].write(d.get('faixa_atual'))
                    cols[3].write(periodo_str) # Exibe período
                    
                    if habilitado:
                        if cols[4].button("⛔ Bloquear", key=f"bloq_{doc.id}"):
                            db.collection('alunos').document(doc.id).update({
                                "exame_habilitado": False,
                                "exame_inicio": None, # Limpa datas ao bloquear
                                "exame_fim": None
                            })
                            st.rerun()
                    else:
                        # Botão Habilitar usa as datas configuradas acima
                        if cols[4].button("✅ Habilitar", key=f"hab_{doc.id}"):
                            if dt_inicio_comb < dt_fim_comb:
                                db.collection('alunos').document(doc.id).update({
                                    "exame_habilitado": True,
                                    "exame_inicio": dt_inicio_comb,
                                    "exame_fim": dt_fim_comb
                                })
                                st.rerun()
                            else:
                                st.error("Datas inválidas.")
            
            st.caption("Nota: Configure as datas no topo antes de clicar em 'Habilitar'.")
