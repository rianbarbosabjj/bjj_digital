import streamlit as st
import time
import random
import os
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components 
from database import get_db
from firebase_admin import firestore

# Importações do Utils
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
    """
    Busca a prova específica configurada pelo professor.
    Prioridade: 1. Configuração Manual -> 2. Sorteio no Banco -> 3. Fallback
    """
    db = get_db()
    
    questoes_finais = []
    tempo = 45
    nota = 70
    qtd_alvo = 10

    # 1. Tenta buscar a CONFIGURAÇÃO DO EXAME para essa faixa
    configs = db.collection('config_exames').where('faixa', '==', faixa_alvo).limit(1).stream()
    
    config_doc = None
    for doc in configs:
        config_doc = doc.to_dict()
        break
    
    if config_doc:
        tempo = int(config_doc.get('tempo_limite', 45))
        nota = int(config_doc.get('aprovacao_minima', 70))
        qtd_alvo = int(config_doc.get('qtd_questoes', 10))
        
        if config_doc.get('questoes') and len(config_doc.get('questoes')) > 0:
            questoes_finais = config_doc.get('questoes')
            return questoes_finais, tempo, nota

    # 2. SE FOR MODO ALEATÓRIO
    if not questoes_finais:
        q_spec = list(db.collection('questoes').where('faixa', '==', faixa_alvo).where('status', '==', 'aprovada').stream())
        q_geral = list(db.collection('questoes').where('faixa', '==', 'Geral').where('status', '==', 'aprovada').stream())
        
        pool = []
        ids_vistos = set()
        
        for doc in q_spec + q_geral:
            if doc.id not in ids_vistos:
                pool.append(doc.to_dict())
                ids_vistos.add(doc.id)
        
        if pool:
            if len(pool) > qtd_alvo:
                questoes_finais = random.sample(pool, qtd_alvo)
            else:
                questoes_finais = pool

    # 3. FALLBACK
    if not questoes_finais:
        todas_json = carregar_todas_questoes()
        faixa_norm = faixa_alvo.strip().lower()
        pool_json = [q for q in todas_json if q.get('faixa', '').strip().lower() in [faixa_norm, 'geral']]
        if pool_json:
            questoes_finais = pool_json[:qtd_alvo]

    return questoes_finais, tempo, nota

# =========================================
# MÓDULOS SECUNDÁRIOS
# =========================================
def modo_rola(usuario):
    st.markdown(f"## 🥋 Modo Rola - Treino Livre")
    st.info("Em breve: Aqui você poderá treinar com questões aleatórias sem valer nota.")

def meus_certificados(usuario):
    st.markdown(f"## 🏅 Meus Certificados")
    db = get_db()
    
    docs = db.collection('resultados').where('usuario', '==', usuario['nome']).where('aprovado', '==', True).stream()
    lista_cert = [d.to_dict() for d in docs]
    
    if not lista_cert:
        st.info("Você ainda não possui certificados emitidos.")
        return

    for i, cert in enumerate(lista_cert):
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**Faixa {cert.get('faixa')}**")
            
            d_str = "-"
            if cert.get('data'):
                try: d_str = cert.get('data').strftime('%d/%m/%Y')
                except: pass
            
            c1.caption(f"Data: {d_str} | Nota: {cert.get('pontuacao')}%")
            
            try:
                pdf_bytes, pdf_name = gerar_pdf(
                    usuario['nome'], cert.get('faixa'), 
                    cert.get('acertos', 0), cert.get('total', 10), 
                    cert.get('codigo_verificacao')
                )
                if pdf_bytes:
                    c2.download_button("📄 Baixar PDF", pdf_bytes, pdf_name, "application/pdf", key=f"btn_{i}")
            except: pass

def ranking():
    st.markdown("## 🏆 Ranking da Equipe")
    st.info("O ranking será atualizado em breve.")

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
    
    # --- 0. RESULTADO IMEDIATO ---
    if st.session_state.resultado_prova:
        res = st.session_state.resultado_prova
        st.balloons()
        st.success(f"PARABÉNS! Aprovado com {res['nota']:.1f}%!")
        p_bytes, p_name = gerar_pdf(usuario['nome'], res['faixa'], res['acertos'], res['total'], res['codigo'])
        if p_bytes:
            st.download_button("📥 BAIXAR CERTIFICADO AGORA", p_bytes, p_name, "application/pdf", use_container_width=True)
        if st.button("Voltar ao Início"):
            st.session_state.resultado_prova = None; st.rerun()
        return

    # --- 1. VERIFICAÇÃO DE ABANDONO (Somente Refresh ou Fechar) ---
    if dados.get("status_exame") == "em_andamento" and not st.session_state.exame_iniciado:
        bloquear_por_abandono(usuario['id'])
        st.error("🚨 ALERTA DE SEGURANÇA: EXAME BLOQUEADO!")
        st.warning("Detectamos que a página foi recarregada ou fechada durante a prova.")
        st.info("Regra: Se a conexão for interrompida ou a página atualizada (F5), a prova é bloqueada.")
        return

    # --- 2. PERMISSÕES BÁSICAS ---
    esta_habilitado = dados.get('exame_habilitado', False)
    faixa_alvo = dados.get('faixa_exame', None)
    
    if not esta_habilitado or not faixa_alvo:
        st.warning("🔒 Nenhum exame autorizado pelo professor.")
        return

    # --- 3. VERIFICAÇÃO DAS 3 REGRAS ---
    elegivel, motivo = verificar_elegibilidade_exame(dados)
    if not elegivel:
        if "reprovado" in motivo.lower(): st.error(f"⏳ {motivo}")
        elif "bloqueado" in motivo.lower(): st.error(f"🚫 {motivo}")
        else: st.success(f"✅ {motivo}")
        return

    # --- 4. DATAS ---
    try:
        data_inicio = dados.get('exame_inicio')
        data_fim = dados.get('exame_fim')
        agora_comparacao = datetime.utcnow()
        if isinstance(data_inicio, str): 
            try: data_inicio = datetime.fromisoformat(data_inicio.replace('Z', ''))
            except: pass
        if isinstance(data_fim, str): 
            try: data_fim = datetime.fromisoformat(data_fim.replace('Z', ''))
            except: pass
        if data_inicio: data_inicio = data_inicio.replace(tzinfo=None)
        if data_fim: data_fim = data_fim.replace(tzinfo=None)
        if data_inicio and agora_comparacao < data_inicio:
            st.warning(f"⏳ O exame começa em: **{data_inicio.strftime('%d/%m/%Y %H:%M')}**")
            return  
        if data_fim and agora_comparacao > data_fim:
            st.error(f"🚫 O prazo expirou em: **{data_fim.strftime('%d/%m/%Y %H:%M')}**")
            return
    except Exception as e: pass

    # --- 5. CARREGAMENTO ---
    lista_questoes, tempo_limite, min_aprovacao = carregar_exame_especifico(faixa_alvo)
    qtd = len(lista_questoes)

    # --- 6. TELA DE INÍCIO (AJUSTE DE ALINHAMENTO) ---
if not st.session_state.exame_iniciado:
    st.markdown(f"### 📋 Exame de Faixa **{faixa_alvo.upper()}**")
    
    with st.container(border=True):
        st.markdown("#### 📜 Instruções para a realização do Exame")
        st.markdown("""
- Após clicar em **✅ Iniciar exame**, não será possível pausar ou interromper o cronômetro.
- Se o tempo acabar antes de você finalizar, você será considerado **reprovado**.
- **Não é permitido** consultar materiais externos de qualquer tipo.
- Em caso de reprovação, você poderá realizar o exame novamente somente após **3 dias**.
- Realize o exame em um local confortável e silencioso para garantir sua concentração.
- Não atualize a página, não feche o navegador e não troque de dispositivo durante a prova — isso pode encerrar o exame automaticamente.
- Utilize um dispositivo com bateria suficiente ou mantido na energia.
- O exame é **individual**. Qualquer tentativa de fraude resultará em reprovação imediata.
- Leia cada questão com atenção antes de responder.
- Se aprovado, você poderá baixar seu certificado na aba *Meus Certificados*.

**Boa prova!** 🥋
        """)
        
        st.markdown("---")

            
            # --- ALINHAMENTO SIMÉTRICO AQUI ---
            c1, c2, c3 = st.columns(3)
            
            # Esquerda
            c1.markdown(f"📝 **{qtd} Questões**")
            
            # Centro
            c2.markdown(f"<div style='text-align: center'>⏱️ <b>{tempo_limite} min</b></div>", unsafe_allow_html=True)
            
            # Direita
            c3.markdown(f"<div style='text-align: right'>✅ Mínimo: <b>{min_aprovacao}%</b></div>", unsafe_allow_html=True)
        
        if qtd > 0:
            if st.button("✅ (Estou Ciente) INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.utcnow()
                st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
                st.session_state.questoes_prova = lista_questoes
                st.session_state.params_prova = {"tempo": tempo_limite, "min": min_aprovacao}
                st.rerun()
        else:
            st.warning(f"⚠️ Sem questões encontradas para **{faixa_alvo}**.")

    # --- 7. PROVA ---
    else:
        questoes = st.session_state.get('questoes_prova', [])
        params = st.session_state.get('params_prova', {})
        
        # --- LÓGICA DE TEMPO (BACKEND) ---
        agora_ts = time.time()
        fim_ts = st.session_state.fim_prova_ts
        restante_segundos = int(fim_ts - agora_ts)
        
        if restante_segundos <= 0:
            st.error("Tempo esgotado!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            time.sleep(3)
            st.rerun()

        # =========================================================
        # CRONÔMETRO VISUAL DINÂMICO (JS)
        # =========================================================
        cor_timer = "#FFD770" if restante_segundos > 300 else "#FF4B4B"
        
        cronometro_html = f"""
        <div style="
            border: 2px solid {cor_timer};
            border-radius: 12px;
            padding: 10px;
            text-align: center;
            background-color: rgba(0,0,0,0.3);
            margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        ">
            <span style="color:white; font-family:sans-serif; font-size:14px; letter-spacing:1px;">TEMPO RESTANTE</span><br>
            <span id="timer_display" style="color:{cor_timer}; font-family:monospace; font-size:36px; font-weight:bold;">
                --:--
            </span>
        </div>

        <script>
            var time_left = {restante_segundos};
            
            function updateTimer() {{
                var minutes = Math.floor(time_left / 60);
                var seconds = Math.floor(time_left % 60);
                
                if (seconds < 10) seconds = "0" + seconds;
                if (minutes < 10) minutes = "0" + minutes;
                
                var display = document.getElementById('timer_display');
                if(display) {{
                    display.innerHTML = minutes + ":" + seconds;
                }}
                
                if (time_left <= 0) {{
                    window.parent.location.reload();
                }}
                time_left = time_left - 1;
            }}
            
            updateTimer();
            setInterval(updateTimer, 1000);
        </script>
        """
        components.html(cronometro_html, height=110)
        
        with st.form("prova"):
            respostas = {}
            for i, q in enumerate(questoes):
                st.markdown(f"**{i+1}. {q.get('pergunta','?')}**")
                if q.get('imagem'): st.image(q['imagem'])
                respostas[i] = st.radio("R:", q.get('opcoes',['V','F']), key=f"q{i}", label_visibility="collapsed")
                st.markdown("---")
            
            if st.form_submit_button("Finalizar Exame", type="primary", use_container_width=True):
                acertos = 0
                for i, q in enumerate(questoes):
                    certa = q.get('correta') or q.get('resposta')
                    if str(respostas.get(i)).strip().lower() == str(certa).strip().lower(): acertos += 1
                
                nota = (acertos/len(questoes))*100
                aprovado = nota >= params['min']
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                
                cod = None
                if aprovado:
                    cod = gerar_codigo_verificacao()
                    st.session_state.resultado_prova = {"nota": nota, "aprovado": True, "faixa": faixa_alvo, "acertos": acertos, "total": len(questoes), "codigo": cod}
                
                try:
                    db.collection('resultados').add({
                        "usuario": usuario['nome'], "faixa": faixa_alvo, "pontuacao": nota,
                        "acertos": acertos, "total": len(questoes), "aprovado": aprovado,
                        "codigo_verificacao": cod, "data": firestore.SERVER_TIMESTAMP
                    })
                except: pass
                
                if not aprovado: st.error(f"Reprovado. {nota:.0f}%"); time.sleep(4)
                st.rerun()
