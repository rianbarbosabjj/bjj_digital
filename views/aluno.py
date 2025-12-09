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

# --- IMPORTAÇÃO DIRETA (PARA MOSTRAR ERRO SE FALHAR) ---
# Se der erro aqui, significa que falta instalar 'fpdf' ou 'qrcode'
from utils import (
    registrar_inicio_exame, 
    registrar_fim_exame, 
    bloquear_por_abandono,
    verificar_elegibilidade_exame,
    carregar_todas_questoes,
    gerar_codigo_verificacao,
    gerar_pdf,
    normalizar_link_video 
)

# =========================================
# CARREGADOR DE EXAME
# =========================================
def carregar_exame_especifico(faixa_alvo):
    db = get_db()
    questoes_finais = []
    tempo = 45; nota = 70; qtd_alvo = 10
    
    try:
        configs = db.collection('config_exames').where('faixa', '==', faixa_alvo).limit(1).stream()
        config_doc = None
        for doc in configs: 
            config_doc = doc.to_dict()
            break
        
        if config_doc:
            tempo = int(config_doc.get('tempo_limite', 45))
            nota = int(config_doc.get('aprovacao_minima', 70))
            
            # MODO MANUAL
            if config_doc.get('questoes_ids'):
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
            
            qtd_alvo = int(config_doc.get('qtd_questoes', 10))
    except: pass

    # FALLBACK
    if not questoes_finais:
        try:
            q_ref = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
            pool = []
            for doc in q_ref:
                d = doc.to_dict()
                if 'alternativas' not in d and 'opcoes' in d:
                    ops = d['opcoes']
                    d['alternativas'] = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                pool.append(d)
            if pool:
                if len(pool) > qtd_alvo:
                    questoes_finais = random.sample(pool, qtd_alvo)
                else:
                    questoes_finais = pool
        except: pass

    return questoes_finais, tempo, nota

# =========================================
# TELAS SECUNDÁRIAS
# =========================================
def modo_rola(usuario):
    st.markdown("## 🥋 Modo Rola"); st.info("Em breve.")

def meus_certificados(usuario):
    if st.button("🏠 Voltar ao Início", key="btn_back_cert"):
        st.session_state.menu_selection = "Início"
        st.rerun()
        
    st.markdown("## 🏅 Meus Certificados")
    
    try:
        db = get_db()
        docs = db.collection('resultados').where('usuario', '==', usuario['nome']).where('aprovado', '==', True).stream()
        lista = [d.to_dict() for d in docs]
        
        if not lista:
            st.info("Nenhum certificado disponível.")
            return

        for i, cert in enumerate(lista):
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**Faixa {cert.get('faixa')}**")
                # Tratamento de data seguro
                data_raw = cert.get('data')
                d_str = "-"
                if data_raw:
                    try: d_str = data_raw.strftime('%d/%m/%Y')
                    except: d_str = str(data_raw)[:10]
                
                c1.caption(f"Data: {d_str} | Nota: {cert.get('pontuacao', 0):.1f}% | Ref: {cert.get('codigo_verificacao')}")
                
                # Gera PDF na hora
                pdf_bytes, pdf_name = gerar_pdf(
                    usuario['nome'], cert.get('faixa'), 
                    cert.get('pontuacao', 0), cert.get('total', 10), 
                    cert.get('codigo_verificacao')
                )
                
                if pdf_bytes:
                    c2.download_button("📄 Baixar PDF", pdf_bytes, pdf_name, "application/pdf", key=f"d_{i}")
                else:
                    c2.error("Erro ao gerar")
    except Exception as e: 
        st.error(f"Erro ao carregar certificados: {e}")

def ranking(): st.markdown("## 🏆 Ranking"); st.info("Em breve.")

# =========================================
# EXAME PRINCIPAL
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
    
    # === TELA DE RESULTADO (APÓS FINALIZAR) ===
    if st.session_state.resultado_prova:
        res = st.session_state.resultado_prova
        st.balloons()
        
        with st.container(border=True):
            st.markdown(f"<h2 style='text-align:center; color:green'>APROVADO! 🥋</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align:center'>Nota Final: {res['nota']:.1f}%</h3>", unsafe_allow_html=True)
            st.divider()
            st.info("O seu certificado já foi gerado. Clique abaixo para baixar.")
            
            # GERAÇÃO DO CERTIFICADO
            try:
                with st.spinner("Gerando certificado oficial..."):
                    p_b, p_n = gerar_pdf(usuario['nome'], res['faixa'], res['nota'], res['total'], res['codigo'])
                
                if p_b: 
                    st.download_button("🏆 BAIXAR CERTIFICADO OFICIAL", p_b, p_n, "application/pdf", key="dl_res_main", type="primary", use_container_width=True)
                else:
                    st.error("Erro na geração do arquivo PDF. Tente novamente na aba 'Meus Certificados'.")
            except Exception as e: 
                st.error(f"Erro técnico ao criar PDF: {e}")
            
        if st.button("Voltar ao Início"):
            st.session_state.resultado_prova = None
            st.rerun()
        return

    # CHECAGEM DE ABANDONO / TIMEOUT
    if dados.get("status_exame") == "em_andamento" and not st.session_state.exame_iniciado:
        # Lógica de timeout omitida para brevidade, mantendo bloqueio padrão
        # Se quiser liberar sempre para teste, comente a linha abaixo
        bloquear_por_abandono(usuario['id'])
        st.error("🚨 O exame foi interrompido ou a página foi recarregada.")
        st.caption("Por segurança, o exame foi bloqueado. Contate seu professor.")
        return

    if not dados.get('exame_habilitado'):
        status_atual = dados.get('status_exame', 'pendente')
        if status_atual == 'aprovado':
             st.success("✅ Você já foi aprovado neste exame!")
             st.info("Acesse a aba 'Meus Certificados' no menu lateral para baixar seu diploma.")
        elif status_atual == 'bloqueado':
             st.error("🔒 Exame Bloqueado.")
        else:
             st.warning("🔒 Exame não autorizado. Solicite ao seu professor.")
        return

    elegivel, motivo = verificar_elegibilidade_exame(dados)
    if not elegivel: st.error(f"🚫 {motivo}"); return

    # CARREGAMENTO DAS QUESTÕES
    qs, tempo_limite, min_aprovacao = carregar_exame_especifico(dados.get('faixa_exame'))
    qtd = len(qs)

    # === TELA DE INÍCIO ===
    if not st.session_state.exame_iniciado:
        st.markdown(f"### 📋 Exame de Faixa **{dados.get('faixa_exame')}**")
        
        with st.container(border=True):
            st.markdown("#### 📜 Instruções")
            st.warning("⚠️ Não recarregue a página (F5) durante a prova, ou você será bloqueado.")
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Questões", qtd)
            c2.metric("Tempo", f"{tempo_limite} min")
            c3.metric("Mínimo", f"{min_aprovacao}%")
        
        if qtd > 0:
            if st.button("✅ INICIAR AGORA", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
                st.session_state.questoes_prova = qs
                st.session_state.params_prova = {"tempo": tempo_limite, "min": min_aprovacao}
                st.rerun()
        else: st.warning("Erro: Nenhuma questão encontrada para esta faixa.")

    # === TELA DA PROVA ===
    else:
        qs = st.session_state.get('questoes_prova', [])
        restante = int(st.session_state.fim_prova_ts - time.time())
        
        if restante <= 0:
            st.error("⌛ Tempo Esgotado!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            time.sleep(2); st.rerun()

        # Timer
        cor = "#FFD770" if restante > 300 else "#FF4B4B"
        components.html(f"""
        <div style="padding:10px;text-align:center;color:{cor};font-family:sans-serif;font-weight:bold;font-size:24px;">
            ⏱️ <span id="t">--:--</span>
        </div>
        <script>
            var t={restante};
            setInterval(function(){{
                var m=Math.floor(t/60),s=t%60;
                document.getElementById('t').innerHTML=m+":"+(s<10?"0"+s:s);
                if(t--<=0)window.parent.location.reload();
            }},1000);
        </script>
        """, height=60)

        with st.form("prova"):
            resps = {}
            for i, q in enumerate(qs):
                st.markdown(f"**{i+1}. {q.get('pergunta')}**")
                
                if q.get('url_imagem'): st.image(q.get('url_imagem'), use_container_width=True)
                if q.get('url_video'):
                    vid = normalizar_link_video(q.get('url_video'))
                    st.video(vid)

                opts = []
                if 'alternativas' in q:
                    opts = [q['alternativas'].get(k) for k in ["A","B","C","D"]]
                
                resps[i] = st.radio("R:", opts, key=f"q{i}", index=None, label_visibility="collapsed")
                st.divider()
                
            if st.form_submit_button("Finalizar Exame", type="primary"):
                acertos = 0
                for i, q in enumerate(qs):
                    resp = str(resps.get(i) or "").strip().lower()
                    certa = q.get('resposta_correta', 'A')
                    txt_certo = q.get('alternativas', {}).get(certa, "").strip().lower()
                    if resp == txt_certo: acertos += 1

                nota = (acertos/len(qs))*100
                aprovado = nota >= st.session_state.params_prova['min']
                
                # GRAVA NO BANCO
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                
                # PREPARA TELA DE RESULTADO
                cod = None
                if aprovado:
                    cod = gerar_codigo_verificacao()
                    # Salva histórico
                    try:
                        db.collection('resultados').add({
                            "usuario": usuario['nome'], "faixa": dados.get('faixa_exame'),
                            "pontuacao": nota, "acertos": acertos, "total": len(qs),
                            "aprovado": aprovado, "codigo_verificacao": cod, "data": firestore.SERVER_TIMESTAMP
                        })
                    except: pass
                    
                    st.session_state.resultado_prova = {
                        "nota": nota, "aprovado": True, "faixa": dados.get('faixa_exame'), 
                        "total": len(qs), "codigo": cod
                    }
                else:
                    st.error(f"Reprovado. Nota: {nota:.1f}%")
                    time.sleep(3)
                
                st.rerun()
