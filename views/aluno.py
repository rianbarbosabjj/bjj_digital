import streamlit as st
import time
import random
import os
import json
import pandas as pd
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
    tempo = 45; nota = 70; qtd_alvo = 10
    
    configs = db.collection('config_exames').where('faixa', '==', faixa_alvo).limit(1).stream()
    config_doc = None
    for doc in configs: config_doc = doc.to_dict(); break
    
    if config_doc:
        tempo = int(config_doc.get('tempo_limite', 45))
        nota = int(config_doc.get('aprovacao_minima', 70))
        
        # MODO MANUAL
        if 'questoes_ids' in config_doc and config_doc['questoes_ids']:
            ids = config_doc['questoes_ids']
            for q_id in ids:
                q_snap = db.collection('questoes').document(q_id).get()
                if q_snap.exists:
                    d = q_snap.to_dict()
                    # Compatibilidade
                    if 'alternativas' not in d and 'opcoes' in d:
                        ops = d['opcoes']
                        d['alternativas'] = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                    questoes_finais.append(d)
            random.shuffle(questoes_finais)
            return questoes_finais, tempo, nota
        
        # MODO ANTIGO
        qtd_alvo = int(config_doc.get('qtd_questoes', 10))

    # FALLBACK (Busca genérica)
    if not questoes_finais:
        q_ref = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        pool = []
        for doc in q_ref:
            d = doc.to_dict()
            if 'alternativas' not in d and 'opcoes' in d:
                ops = d['opcoes']; d['alternativas'] = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
            pool.append(d)
        if pool:
            if len(pool) > qtd_alvo: questoes_finais = random.sample(pool, qtd_alvo)
            else: questoes_finais = pool

    return questoes_finais, tempo, nota

# =========================================
# MÓDULOS SECUNDÁRIOS
# =========================================
def modo_rola(usuario):
    st.markdown(f"## 🤼 Modo Rola (Treino Livre)")
    st.caption("Responda questões aleatórias sem pressão de tempo ou nota. Ideal para estudar!")
    
    if "treino_questoes" not in st.session_state:
        # Carrega 5 questões aleatórias de qualquer nível
        db = get_db()
        all_q = list(db.collection('questoes').where('status', '==', 'aprovada').limit(50).stream())
        if all_q:
            selecionados = random.sample(all_q, min(5, len(all_q)))
            dados_q = []
            for doc in selecionados:
                d = doc.to_dict()
                # Normaliza alternativas
                if 'alternativas' not in d and 'opcoes' in d:
                    ops = d['opcoes']
                    d['alternativas'] = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                dados_q.append(d)
            st.session_state.treino_questoes = dados_q
            st.session_state.treino_respostas = {}
            st.session_state.treino_finalizado = False
        else:
            st.warning("Banco de questões vazio.")
            return

    if st.button("🔄 Gerar Novo Treino"):
        del st.session_state.treino_questoes
        st.rerun()

    with st.form("form_treino"):
        acertos = 0
        for i, q in enumerate(st.session_state.treino_questoes):
            st.markdown(f"**{i+1}. {q.get('pergunta')}**")
            
            # --- MÍDIA NO MODO ROLA ---
            if q.get('url_imagem'): st.image(q.get('url_imagem'), use_container_width=True)
            if q.get('url_video'): st.video(q.get('url_video'))
            
            alts = q.get('alternativas', {})
            opts = [alts.get(k, '-') for k in ["A","B","C","D"]]
            
            resp = st.radio(f"Opções {i}", opts, key=f"t_q{i}", label_visibility="collapsed")
            st.markdown("---")

        if st.form_submit_button("Corrigir Treino"):
            st.session_state.treino_finalizado = True
            
    if st.session_state.treino_finalizado:
        st.markdown("### 📊 Resultado do Treino")
        nota_treino = 0
        for i, q in enumerate(st.session_state.treino_questoes):
            user_resp = st.session_state.get(f"t_q{i}")
            certa_letra = q.get('resposta_correta', 'A')
            alts = q.get('alternativas', {})
            texto_certo = alts.get(certa_letra, "").strip().lower()
            
            if str(user_resp).strip().lower() == texto_certo:
                st.success(f"Questão {i+1}: Correta! ✅")
                nota_treino += 1
            else:
                st.error(f"Questão {i+1}: Errou ❌. A correta era: **{texto_certo}**")
        
        st.metric("Total de Acertos", f"{nota_treino} / {len(st.session_state.treino_questoes)}")

def meus_certificados(usuario):
    if st.button("🏠 Voltar ao Início", key="btn_back_cert"):
        st.session_state.menu_selection = "Início"; st.rerun()
    st.markdown(f"## 🏅 Meus Certificados")
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

def ranking():
    st.markdown("## 🏆 Hall da Fama - Ranking")
    db = get_db()
    try:
        res_ref = db.collection('resultados').where('aprovado', '==', True).stream()
        placar = {}
        for doc in res_ref:
            d = doc.to_dict()
            aluno = d.get('usuario', 'Desconhecido')
            faixa = d.get('faixa', '?')
            if aluno not in placar: placar[aluno] = {"faixas": set(), "pontos": 0}
            if faixa not in placar[aluno]["faixas"]:
                placar[aluno]["faixas"].add(faixa)
                placar[aluno]["pontos"] += 100
        ranking_lista = []
        for nome, dados in placar.items():
            ranking_lista.append({"Aluno": nome, "Faixas": len(dados["faixas"]), "Pontos": dados["pontos"]})
        if not ranking_lista: st.info("Sem dados.")
        else:
            df = pd.DataFrame(ranking_lista).sort_values(by="Pontos", ascending=False).reset_index(drop=True)
            df.index += 1
            st.dataframe(df, use_container_width=True)
    except: pass

# =========================================
# EXAME DE FAIXA (PRINCIPAL)
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

    # Verificação de Timeout/Abandono
    if dados.get("status_exame") == "em_andamento" and not st.session_state.exame_iniciado:
        is_timeout = False
        try:
            start_str = dados.get("inicio_exame_temp")
            if start_str:
                start_dt = datetime.fromisoformat(start_str.replace('Z', '')) if isinstance(start_str, str) else start_str
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
        st.markdown(f"### 📋 Exame de Faixa **{dados.get('faixa_exame')}**")
        with st.container(border=True):
            st.markdown("#### 📜 Instruções")
            st.markdown("- **Tentativa Única.**\n- **Não recarregue (F5).**\n- **Reprovação:** aguardar 72h.")
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
        else: st.warning("Sem questões disponíveis.")

    else:
        qs = st.session_state.get('questoes_prova', [])
        restante = int(st.session_state.fim_prova_ts - time.time())
        if restante <= 0:
            st.error("⌛ Tempo esgotado!"); registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False; time.sleep(2); st.rerun()

        cor = "#FFD770" if restante > 300 else "#FF4B4B"
        st.components.v1.html(f"""<div style="border:2px solid {cor};border-radius:10px;padding:10px;text-align:center;background:rgba(0,0,0,0.3);"><span style="color:white;font-family:sans-serif;">TEMPO RESTANTE</span><br><span id="t" style="color:{cor};font-family:monospace;font-size:30px;font-weight:bold;">--:--</span></div><script>var t={restante};setInterval(function(){{var m=Math.floor(t/60),s=t%60;document.getElementById('t').innerHTML=m+":"+(s<10?"0"+s:s);if(t--<=0)window.parent.location.reload();}},1000);</script>""", height=100)

        with st.form("prova"):
            resps = {}
            for i, q in enumerate(qs):
                st.markdown(f"**{i+1}. {q.get('pergunta')}**")
                
                # --- EXIBIÇÃO DE MÍDIA ---
                # Aqui está o código que faz a imagem aparecer
                if q.get('url_imagem'):
                    st.image(q.get('url_imagem'), caption="Imagem de Apoio", use_container_width=True)
                
                if q.get('url_video'):
                    st.video(q.get('url_video'))
                # -------------------------

                opts = []
                if 'alternativas' in q and isinstance(q['alternativas'], dict):
                    opts = [q['alternativas'].get(k) for k in ["A","B","C","D"]]
                elif 'opcoes' in q: opts = q['opcoes']
                if not opts: opts = ["-", "-", "-", "-"]

                resps[i] = st.radio("R:", opts, key=f"q{i}", label_visibility="collapsed")
                st.markdown("---")
                
            if st.form_submit_button("Finalizar"):
                acertos = 0
                for i, q in enumerate(qs):
                    resp_aluno = str(resps.get(i)).strip().lower()
                    certa_bd = q.get('resposta_correta') or q.get('resposta') or q.get('correta')
                    certa_texto = ""
                    if str(certa_bd).upper() in ["A","B","C","D"] and 'alternativas' in q:
                        certa_texto = q['alternativas'].get(str(certa_bd).upper(), "").strip().lower()
                    elif 'opcoes' in q and str(certa_bd).upper() in ["A","B","C","D"]:
                        idx_map = {"A":0, "B":1, "C":2, "D":3}
                        try: certa_texto = q['opcoes'][idx_map[str(certa_bd).upper()]].strip().lower()
                        except: certa_texto = str(certa_bd).strip().lower()
                    else: certa_texto = str(certa_bd).strip().lower()
                    if resp_aluno == certa_texto: acertos += 1

                nota = (acertos/len(qs))*100
                aprovado = nota >= st.session_state.params_prova['min']
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                cod = gerar_codigo_verificacao() if aprovado else None
                if aprovado: st.session_state.resultado_prova = {"nota": nota, "aprovado": True, "faixa": dados.get('faixa_exame'), "acertos": acertos, "total": len(qs), "codigo": cod}
                try: db.collection('resultados').add({"usuario": usuario['nome'], "faixa": dados.get('faixa_exame'), "pontuacao": nota, "acertos": acertos, "total": len(qs), "aprovado": aprovado, "codigo_verificacao": cod, "data": firestore.SERVER_TIMESTAMP})
                except: pass
                if not aprovado: st.error(f"Reprovado. {nota:.0f}%"); time.sleep(3)
                st.rerun()
