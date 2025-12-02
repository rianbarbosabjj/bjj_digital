import streamlit as st
import time
import random
import pandas as pd # Adicionado para o Ranking
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
# MODO ROLA (CRONÔMETRO) - NOVO!
# =========================================
def modo_rola(usuario):
    st.markdown("<h1 style='color:#FFD770; text-align:center'>⏱️ Modo Rola</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Cronômetro oficial para treinos no dojo.</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Configuração
    with st.expander("⚙️ Configurar Tempos", expanded=True):
        c1, c2 = st.columns(2)
        tempo_luta = c1.number_input("Tempo de Luta (minutos):", 1, 60, 5)
        tempo_descanso = c2.number_input("Tempo de Descanso (segundos):", 0, 300, 30)

    # Estado do Timer
    if 'timer_running' not in st.session_state: st.session_state.timer_running = False
    
    # Botões de Controle
    col_b1, col_b2, col_b3 = st.columns([1, 1, 1])
    
    iniciar = col_b2.button("▶️ INICIAR ROLA", use_container_width=True, type="primary")
    
    # Área do Mostrador Gigante
    timer_placeholder = st.empty()

    if iniciar:
        st.session_state.timer_running = True
        total_segundos = tempo_luta * 60
        
        # Loop do Tempo de Luta
        timer_placeholder.markdown(f"<div style='background-color:#078B6C; padding:20px; border-radius:15px; text-align:center'><h1 style='font-size:80px; color:white; margin:0'>PREPARAR...</h1></div>", unsafe_allow_html=True)
        time.sleep(2)
        
        for i in range(total_segundos, -1, -1):
            if not st.session_state.timer_running: break
            m, s = divmod(i, 60)
            # Visual do Timer
            cor_fundo = "#0e2d26"
            cor_texto = "#FFD770"
            if i < 30: cor_texto = "#FF4B4B" # Fica vermelho no final
            
            timer_placeholder.markdown(
                f"<div style='border: 4px solid {cor_texto}; border-radius: 20px; padding: 40px; text-align: center; background-color: rgba(0,0,0,0.3);'>"
                f"<h1 style='font-size: 100px; margin: 0; color: {cor_texto}; font-family: monospace;'>{m:02d}:{s:02d}</h1>"
                f"<h3 style='color: white;'>🤼 LUTANDO</h3>"
                f"</div>", 
                unsafe_allow_html=True
            )
            time.sleep(1)
        
        # Alerta de Fim de Luta
        if st.session_state.timer_running:
            for _ in range(3): # Pisca 3 vezes
                timer_placeholder.markdown(f"<div style='background-color:#FF4B4B; padding:20px; border-radius:15px; text-align:center'><h1 style='font-size:80px; color:white; margin:0'>ACABOU!</h1></div>", unsafe_allow_html=True)
                time.sleep(0.5)
                timer_placeholder.empty()
                time.sleep(0.2)

            # Loop do Descanso
            if tempo_descanso > 0:
                for i in range(tempo_descanso, -1, -1):
                    timer_placeholder.markdown(
                        f"<div style='border: 4px solid #00CC96; border-radius: 20px; padding: 40px; text-align: center; background-color: rgba(0,0,0,0.3);'>"
                        f"<h1 style='font-size: 100px; margin: 0; color: #00CC96; font-family: monospace;'>{i}s</h1>"
                        f"<h3 style='color: white;'>🥤 DESCANSO</h3>"
                        f"</div>", 
                        unsafe_allow_html=True
                    )
                    time.sleep(1)
            
            timer_placeholder.success("Próximo Round!")
            st.session_state.timer_running = False

# =========================================
# RANKING (LEADERBOARD) - NOVO!
# =========================================
def ranking():
    st.markdown("<h1 style='color:#FFD770; text-align:center'>🏆 Ranking do Dojo</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Os melhores desempenhos nos exames teóricos.</p>", unsafe_allow_html=True)
    
    db = get_db()
    with st.spinner("Calculando pontuações..."):
        # Busca apenas resultados aprovados
        res_ref = list(db.collection('resultados').where('aprovado', '==', True).stream())
        
        if not res_ref:
            st.info("Nenhum resultado registrado para o ranking ainda.")
            return

        data = [d.to_dict() for d in res_ref]
        df = pd.DataFrame(data)

    # Processamento dos dados
    if not df.empty:
        # Agrupa por usuário e calcula métricas
        ranking_df = df.groupby('usuario').agg(
            Exames_Aprovados=('aprovado', 'count'),
            Media_Notas=('pontuacao', 'mean'),
            Ultima_Faixa=('faixa', 'max') # Pega a "maior" string (não ideal para faixas, mas serve para exibir)
        ).reset_index()

        # Ordena: Quem tem maior média de notas vence
        ranking_df = ranking_df.sort_values(by=['Media_Notas', 'Exames_Aprovados'], ascending=[False, False])
        
        # Adiciona coluna de Medalhas
        medals = ['🥇', '🥈', '🥉'] + [''] * (len(ranking_df) - 3)
        ranking_df['Pos'] = medals[:len(ranking_df)]
        
        # Reordena colunas para exibição
        ranking_df = ranking_df[['Pos', 'usuario', 'Media_Notas', 'Exames_Aprovados', 'Ultima_Faixa']]
        ranking_df.columns = ['#', 'Atleta', 'Média Geral', 'Exames Concluídos', 'Última Graduação']

        # Exibição do Pódio (Top 3 Cards)
        top3 = ranking_df.head(3)
        cols = st.columns(3)
        for i, (idx, row) in enumerate(top3.iterrows()):
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"<h1 style='text-align:center'>{row['#']}</h1>", unsafe_allow_html=True)
                    st.markdown(f"<h3 style='text-align:center; color:#FFD770'>{row['Atleta'].split()[0]}</h3>", unsafe_allow_html=True)
                    st.metric("Média", f"{row['Média Geral']:.1f}%")
        
        st.markdown("---")
        
        # Tabela Completa
        st.dataframe(
            ranking_df,
            column_config={
                "Média Geral": st.column_config.ProgressColumn(
                    "Média Geral",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
                "Exames Concluídos": st.column_config.NumberColumn(
                    "Aprovações",
                    format="%d 🏆"
                )
            },
            hide_index=True,
            use_container_width=True
        )
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
