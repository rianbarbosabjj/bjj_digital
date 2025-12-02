import streamlit as st
import time
import random
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components 
from database import get_db
from firebase_admin import firestore

from utils import (
    registrar_inicio_exame, 
    registrar_fim_exame, 
    bloquear_por_abandono,
    verificar_elegibilidade_exame,
    carregar_todas_questoes,
    gerar_codigo_verificacao,
    gerar_pdf
)

# =========================================
# CARREGADOR DE EXAME
# =========================================
def carregar_exame_especifico(faixa_alvo):
    db = get_db()
    questoes_finais = []
    tempo = 45
    nota = 70
    
    configs = db.collection('config_exames').where('faixa', '==', faixa_alvo).limit(1).stream()
    config_doc = None
    for doc in configs: 
        config_doc = doc.to_dict()
        break
    
    if config_doc:
        tempo = int(config_doc.get('tempo_limite', 45))
        nota = int(config_doc.get('aprovacao_minima', 70))
        ids_salvos = config_doc.get('questoes_ids', [])
        
        if ids_salvos and len(ids_salvos) > 0:
            for q_id in ids_salvos:
                doc_q = db.collection('questoes').document(q_id).get()
                if doc_q.exists:
                    d = doc_q.to_dict()
                    d['id'] = doc_q.id 
                    if 'alternativas' not in d and 'opcoes' in d:
                        ops = d['opcoes']
                        d['alternativas'] = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                    questoes_finais.append(d)
        else:
            qtd_alvo = int(config_doc.get('qtd_questoes', 10))
            dificuldade_alvo = int(config_doc.get('dificuldade_alvo', 1))
            q_ref = list(db.collection('questoes').where('dificuldade', '==', dificuldade_alvo).where('status', '==', 'aprovada').stream())
            pool = []
            for doc in q_ref:
                d = doc.to_dict(); d['id'] = doc.id
                if 'alternativas' not in d and 'opcoes' in d:
                    ops = d['opcoes']
                    d['alternativas'] = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                pool.append(d)
            if pool:
                questoes_finais = random.sample(pool, qtd_alvo) if len(pool) > qtd_alvo else pool
    else:
        st.error(f"Prova da faixa {faixa_alvo} não configurada pelo Mestre.")

    return questoes_finais, tempo, nota

# =========================================
# MODO ROLA (QUIZ DE TREINO)
# =========================================
def modo_rola(usuario):
    st.markdown("<h1 style='color:#FFD770; text-align:center'>🤼 Modo Rola (Treino Rápido)</h1>", unsafe_allow_html=True)
    st.info("Responda 5 questões aleatórias para somar pontos no Ranking!")

    if "rola_iniciado" not in st.session_state: st.session_state.rola_iniciado = False
    
    if not st.session_state.rola_iniciado:
        c1, c2, c3 = st.columns([1, 2, 1])
        if c2.button("🔥 COMEÇAR ROLA", type="primary", use_container_width=True):
            db = get_db()
            all_q = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
            
            if len(all_q) < 5:
                st.warning("Banco de questões insuficiente para um rola (mínimo 5).")
            else:
                pool = []
                for doc in all_q:
                    d = doc.to_dict(); d['id'] = doc.id
                    if 'alternativas' not in d and 'opcoes' in d:
                        ops = d['opcoes']
                        d['alternativas'] = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                    pool.append(d)
                
                st.session_state.questoes_rola = random.sample(pool, 5)
                st.session_state.rola_iniciado = True
                st.rerun()
    else:
        qs = st.session_state.questoes_rola
        
        with st.form("form_rola"):
            respostas = {}
            for i, q in enumerate(qs):
                st.markdown(f"**{i+1}. {q.get('pergunta')}**")
                opts = []
                if 'alternativas' in q and isinstance(q['alternativas'], dict):
                    opts = [f"{k}) {q['alternativas'][k]}" for k in ["A","B","C","D"] if k in q['alternativas']]
                elif 'opcoes' in q:
                    opts = q['opcoes']
                if not opts: opts = ["Erro"]
                respostas[i] = st.radio("R:", opts, key=f"r_rola_{i}", label_visibility="collapsed")
                st.divider()
            
            if st.form_submit_button("🥋 Finalizar Treino"):
                acertos = 0
                detalhes = []
                
                for i, q in enumerate(qs):
                    resp_full = str(respostas.get(i))
                    if ")" in resp_full[:2]:
                         resp_letra = resp_full.split(")")[0].strip().upper()
                    else:
                         resp_letra = resp_full.strip()

                    certa = str(q.get('resposta_correta') or 'A').strip().upper()
                    is_correct = (resp_letra == certa)
                    if is_correct: acertos += 1
                    
                    detalhes.append({
                        "questao_id": q.get('id'),
                        "acertou": is_correct,
                        "dificuldade": q.get('dificuldade', 1),
                        "categoria": q.get('categoria', 'Geral')
                    })
                
                nota = (acertos / 5) * 100
                
                db = get_db()
                db.collection('resultados').add({
                    "usuario": usuario['nome'],
                    "faixa": "Modo Rola", 
                    "pontuacao": nota,
                    "acertos": acertos,
                    "total": 5,
                    "aprovado": True, 
                    "codigo_verificacao": None,
                    "detalhes": detalhes,
                    "data": firestore.SERVER_TIMESTAMP
                })
                
                st.balloons()
                if nota == 100: st.success(f"OSS! Gabaritou! Nota: {nota:.0f}")
                elif nota >= 60: st.success(f"Bom treino! Nota: {nota:.0f}")
                else: st.warning(f"Mais estudo na próxima! Nota: {nota:.0f}")
                
                time.sleep(3)
                st.session_state.rola_iniciado = False
                st.rerun()

# =========================================
# RANKING (ATUALIZADO: SEPARADO POR FAIXA)
# =========================================
def ranking():
    st.markdown("<h1 style='color:#FFD770; text-align:center'>🏆 Ranking do Dojo</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Pontuação baseada em Exames Oficiais e Modo Rola.</p>", unsafe_allow_html=True)
    
    db = get_db()
    
    with st.spinner("Atualizando placar..."):
        # 1. Buscar todos os Usuários para mapear a faixa atual
        # Isso permite que Admin, Professor e Aluno entrem no ranking com sua faixa correta
        users_ref = list(db.collection('usuarios').stream())
        mapa_faixas = {}
        for u in users_ref:
            d = u.to_dict()
            # Mapeia Nome -> Faixa Atual
            # Se a faixa for complexa (ex: "Cinza e Preta"), simplificamos para "Cinza" na lógica de abas,
            # ou usamos a string completa se preferir. Aqui usaremos a string da faixa.
            mapa_faixas[d.get('nome')] = d.get('faixa_atual', 'Branca')

        # 2. Buscar Resultados
        res_ref = list(db.collection('resultados').where('aprovado', '==', True).stream())
        
        if not res_ref:
            st.info("Nenhum resultado registrado ainda.")
            return

        data = [d.to_dict() for d in res_ref]
        df = pd.DataFrame(data)

    if not df.empty:
        # Adiciona a coluna 'faixa_do_atleta' cruzando com o mapa
        df['faixa_atleta'] = df['usuario'].map(mapa_faixas).fillna('Desconhecido')

        # Agrupa por usuário e calcula métricas
        ranking_geral = df.groupby(['usuario', 'faixa_atleta']).agg(
            Exames_Aprovados=('aprovado', 'count'),
            Media_Notas=('pontuacao', 'mean')
        ).reset_index()

        # Função auxiliar para renderizar tabela
        def renderizar_tabela(dataframe_filtrado):
            if dataframe_filtrado.empty:
                st.caption("Nenhum atleta pontuou nesta categoria ainda.")
                return

            # Ordena
            df_final = dataframe_filtrado.sort_values(by=['Media_Notas', 'Exames_Aprovados'], ascending=[False, False])
            
            # Medalhas
            medals = ['🥇', '🥈', '🥉'] + [''] * (len(df_final) - 3)
            df_final['Pos'] = medals[:len(df_final)]
            
            # Formata
            df_final = df_final[['Pos', 'usuario', 'Media_Notas', 'Exames_Aprovados', 'faixa_atleta']]
            df_final.columns = ['#', 'Atleta', 'Média Geral', 'Atividades', 'Graduação']

            # Top 3 Cards
            top3 = df_final.head(3)
            cols = st.columns(3)
            for i, (idx, row) in enumerate(top3.iterrows()):
                with cols[i]:
                    with st.container(border=True):
                        st.markdown(f"<h1 style='text-align:center'>{row['#']}</h1>", unsafe_allow_html=True)
                        st.markdown(f"<h3 style='text-align:center; color:#FFD770'>{row['Atleta'].split()[0]}</h3>", unsafe_allow_html=True)
                        st.caption(f"{row['Graduação']}")
                        st.metric("Média", f"{row['Média Geral']:.1f}%")
            
            st.markdown("---")
            
            # Tabela
            st.dataframe(
                df_final,
                column_config={
                    "Média Geral": st.column_config.ProgressColumn("Média", format="%.1f%%", min_value=0, max_value=100),
                    "Atividades": st.column_config.NumberColumn("Exames/Rolas", format="%d 🏆")
                },
                hide_index=True,
                use_container_width=True
            )

        # --- ABAS POR FAIXA ---
        # Definindo as categorias principais
        abas = ["🌍 Geral", "⚪ Branca", "🔘 Cinza", "🟡 Amarela", "🟠 Laranja", "🟢 Verde", "🔵 Azul", "🟣 Roxa", "🟤 Marrom", "⚫ Preta"]
        tabs = st.tabs(abas)

        with tabs[0]: # Geral
            renderizar_tabela(ranking_geral)

        # Lógica para filtrar por cor (contém a string)
        # Ex: "Cinza e Branca" entra na aba "Cinza"
        categorias_map = {
            "⚪ Branca": "Branca",
            "🔘 Cinza": "Cinza",
            "🟡 Amarela": "Amarela",
            "🟠 Laranja": "Laranja",
            "🟢 Verde": "Verde",
            "🔵 Azul": "Azul",
            "🟣 Roxa": "Roxa",
            "🟤 Marrom": "Marrom",
            "⚫ Preta": "Preta"
        }

        for i, (nome_aba, termo_busca) in enumerate(categorias_map.items(), 1):
            with tabs[i]:
                # Filtra se a faixa do atleta contém o termo (ex: "Amarela" pega "Amarela e Preta")
                df_filt = ranking_geral[ranking_geral['faixa_atleta'].str.contains(termo_busca, na=False, case=False)]
                renderizar_tabela(df_filt)

    else:
        st.warning("Dados insuficientes para gerar o ranking.")

# =========================================
# OUTRAS TELAS (MEUS CERTIFICADOS)
# =========================================
def meus_certificados(usuario):
    if st.button("🏠 Voltar ao Início", key="btn_back_cert"):
        st.session_state.menu_selection = "Início"; st.rerun()

    st.markdown("## 🏅 Meus Certificados")
    db = get_db()
    docs = db.collection('resultados').where('usuario', '==', usuario['nome']).where('aprovado', '==', True).stream()
    lista = [d.to_dict() for d in docs]
    
    if not lista: st.info("Nenhum certificado disponível."); return

    for i, cert in enumerate(lista):
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**Faixa {cert.get('faixa')}**")
            d_str = cert.get('data').strftime('%d/%m/%Y') if cert.get('data') else "-"
            c1.caption(f"Data: {d_str} | Nota: {cert.get('pontuacao')}%")
            try:
                pdf_bytes, pdf_name = gerar_pdf(usuario['nome'], cert.get('faixa'), cert.get('acertos'), cert.get('total'), cert.get('codigo_verificacao'))
                if pdf_bytes: c2.download_button("📄 PDF", pdf_bytes, pdf_name, "application/pdf", key=f"d_{i}")
            except: pass

# =========================================
# EXAME DE FAIXA (LÓGICA PRINCIPAL)
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    if "exame_iniciado" not in st.session_state: st.session_state.exame_iniciado = False
    if "resultado_prova" not in st.session_state: st.session_state.resultado_prova = None

    db = get_db()
    doc_ref = db.collection('usuarios').document(usuario['id'])
    doc = doc_ref.get()
    if not doc.exists: st.error("Erro perfil."); return
    dados = doc.to_dict()
    
    if st.session_state.resultado_prova:
        res = st.session_state.resultado_prova
        st.balloons(); st.success(f"Aprovado! Nota: {res['nota']:.1f}%")
        p_b, p_n = gerar_pdf(usuario['nome'], res['faixa'], res['acertos'], res['total'], res['codigo'])
        if p_b: st.download_button("📥 Baixar Certificado", p_b, p_n, "application/pdf")
        if st.button("Voltar"): st.session_state.resultado_prova = None; st.rerun()
        return

    # Verificação de Abandono / Timeout
    if dados.get("status_exame") == "em_andamento" and not st.session_state.exame_iniciado:
        is_timeout = False
        try:
            start_str = dados.get("inicio_exame_temp")
            if start_str:
                if isinstance(start_str, str): start_dt = datetime.fromisoformat(start_str.replace('Z', ''))
                else: start_dt = start_str
                _, t_lim, _ = carregar_exame_especifico(dados.get('faixa_exame'))
                limit_dt = start_dt + timedelta(minutes=t_lim)
                if datetime.utcnow() > limit_dt.replace(tzinfo=None): is_timeout = True
        except: pass

        if is_timeout:
            registrar_fim_exame(usuario['id'], False)
            st.error("⌛ TEMPO ESGOTADO!"); st.warning("Reprovado por tempo."); return
        else:
            bloquear_por_abandono(usuario['id'])
            st.error("🚨 BLOQUEADO!"); st.warning("Página recarregada ou fechada."); return

    if not dados.get('exame_habilitado') or not dados.get('faixa_exame'):
        st.warning("🔒 Exame não autorizado."); return

    elegivel, motivo = verificar_elegibilidade_exame(dados)
    if not elegivel:
        st.error(f"🚫 {motivo}") if "bloqueado" in motivo.lower() or "reprovado" in motivo.lower() else st.success(motivo)
        return

    try:
        dt_ini = dados.get('exame_inicio')
        if isinstance(dt_ini, str): dt_ini = datetime.fromisoformat(dt_ini.replace('Z',''))
        if dt_ini: dt_ini = dt_ini.replace(tzinfo=None)
        if dt_ini and datetime.utcnow() < dt_ini: st.warning(f"⏳ Início em: {dt_ini}"); return
    except: pass

    qs, tempo_limite, min_aprovacao = carregar_exame_especifico(dados.get('faixa_exame'))
    qtd = len(qs)

    if not st.session_state.exame_iniciado:
        st.markdown(f"### Faixa **{dados.get('faixa_exame')}**")
        with st.container(border=True):
            st.markdown("#### Regras"); st.markdown("- Tentativa Única.\n- Não recarregue (F5).\n- Reprovação: aguardar 72h.")
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd} Questões**")
            c2.markdown(f"<div style='text-align:center'>⏱️ <b>{tempo_limite} min</b></div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='text-align:right'>✅ Min: <b>{min_aprovacao}%</b></div>", unsafe_allow_html=True)
        
        if qtd > 0:
            if st.button("✅ INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
                st.session_state.questoes_prova = qs
                st.session_state.params_prova = {"tempo": tempo_limite, "min": min_aprovacao}
                st.rerun()
        else: st.warning("Sem questões disponíveis para este nível.")

    else:
        qs = st.session_state.get('questoes_prova', [])
        restante = int(st.session_state.fim_prova_ts - time.time())
        if restante <= 0:
            st.error("Tempo esgotado!"); registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False; time.sleep(2); st.rerun()

        cor = "#FFD770" if restante > 300 else "#FF4B4B"
        st.components.v1.html(f"""<div style="border:2px solid {cor};border-radius:10px;padding:10px;text-align:center;background:rgba(0,0,0,0.3);"><span style="color:white;font-family:sans-serif;">TEMPO RESTANTE</span><br><span id="t" style="color:{cor};font-family:monospace;font-size:30px;font-weight:bold;">--:--</span></div><script>var t={restante};setInterval(function(){{var m=Math.floor(t/60),s=t%60;document.getElementById('t').innerHTML=m+":"+(s<10?"0"+s:s);if(t--<=0)window.parent.location.reload();}},1000);</script>""", height=100)

        with st.form("prova"):
            resps = {}
            for i, q in enumerate(qs):
                st.markdown(f"**{i+1}. {q.get('pergunta')}**")
                opts = []
                if 'alternativas' in q and isinstance(q['alternativas'], dict):
                    opts = [f"{k}) {q['alternativas'][k]}" for k in ["A","B","C","D"] if k in q['alternativas']]
                elif 'opcoes' in q:
                    opts = q['opcoes']
                if not opts: opts = ["Erro carregamento"]
                resps[i] = st.radio("R:", opts, key=f"q{i}", label_visibility="collapsed")
                st.markdown("---")
                
            if st.form_submit_button("Finalizar"):
                acertos = 0
                detalhes_questoes = []

                for i, q in enumerate(qs):
                    resp_aluno_full = str(resps.get(i))
                    if ")" in resp_aluno_full[:2]:
                         resp_aluno_letra = resp_aluno_full.split(")")[0].strip().upper()
                    else:
                         resp_aluno_letra = resp_aluno_full.strip()

                    certa_bd = str(q.get('resposta_correta') or q.get('resposta') or q.get('correta')).strip().upper()
                    
                    is_correct = False
                    if resp_aluno_letra == certa_bd:
                        acertos += 1
                        is_correct = True
                    elif resp_aluno_full == certa_bd:
                        acertos += 1
                        is_correct = True
                    
                    detalhes_questoes.append({
                        "questao_id": q.get('id'),
                        "acertou": is_correct,
                        "dificuldade": q.get('dificuldade', 1),
                        "categoria": q.get('categoria', 'Geral')
                    })

                nota = (acertos/len(qs))*100
                aprovado = nota >= st.session_state.params_prova['min']
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                cod = gerar_codigo_verificacao() if aprovado else None
                if aprovado: st.session_state.resultado_prova = {"nota": nota, "aprovado": True, "faixa": dados.get('faixa_exame'), "acertos": acertos, "total": len(qs), "codigo": cod}
                try: db.collection('resultados').add({
                    "usuario": usuario['nome'], 
                    "faixa": dados.get('faixa_exame'), 
                    "pontuacao": nota, 
                    "acertos": acertos, 
                    "total": len(qs), 
                    "aprovado": aprovado, 
                    "codigo_verificacao": cod, 
                    "detalhes": detalhes_questoes,
                    "data": firestore.SERVER_TIMESTAMP
                })
                except: pass
                
                if not aprovado: st.error(f"Reprovado. {nota:.0f}%"); time.sleep(3)
                st.rerun()
