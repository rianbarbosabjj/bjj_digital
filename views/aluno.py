import streamlit as st
import random
import os
import json
import time
import uuid
from datetime import datetime, timedelta
import pandas as pd
import streamlit.components.v1 as components 
from database import get_db
from utils import gerar_codigo_verificacao, gerar_pdf
from firebase_admin import firestore

# =========================================
# FUNÇÕES AUXILIARES COM CACHE
# =========================================
@st.cache_data(ttl=300) 
def carregar_questoes_firestore():
    db = get_db()
    todas_questoes = []
    try:
        # Filtra apenas questões APROVADAS
        docs_questoes = list(db.collection('questoes').stream())
        if docs_questoes:
            for d in docs_questoes:
                q = d.to_dict()
                if q.get('status', 'aprovada') == 'aprovada':
                    todas_questoes.append(q)
    except: pass
    
    # Fallback local para testes
    if not todas_questoes and os.path.exists("questions"):
        for f in os.listdir("questions"):
            if f.endswith(".json"):
                try:
                    with open(f"questions/{f}", "r", encoding="utf-8") as file:
                        q_list = json.load(file)
                        tema_nome = f.replace(".json", "")
                        for q in q_list: q['tema'] = tema_nome; todas_questoes.append(q)
                except: continue
    return todas_questoes

@st.cache_data(ttl=300)
def carregar_exame_firestore(faixa_sel):
    db = get_db()
    doc_ref = db.collection('exames').document(faixa_sel)
    doc_exame = doc_ref.get()
    dados_exame = doc_exame.to_dict() if doc_exame.exists else {}
    
    if not dados_exame:
        json_path = f"exames/faixa_{faixa_sel.lower()}.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f: dados_exame = json.load(f)
            except: pass
    return dados_exame

# =========================================
# MODO ROLA (Treino Livre)
# =========================================
def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)
    db = get_db()

    todas_questoes = carregar_questoes_firestore()

    if not todas_questoes:
        st.warning("Banco de questões vazio.")
        return

    temas = sorted(list(set(q.get('tema', 'Geral') for q in todas_questoes)))
    temas.insert(0, "Todos os Temas")

    col1, col2 = st.columns(2)
    with col1: tema = st.selectbox("Selecione o tema:", temas)
    with col2: faixa = st.selectbox("Sua faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])

    if st.button("Iniciar Treino 🤼", use_container_width=True):
        if tema == "Todos os Temas":
            questoes_selecionadas = todas_questoes
        else:
            questoes_selecionadas = [q for q in todas_questoes if q.get('tema') == tema]

        if not questoes_selecionadas:
            st.error("Nenhuma questão encontrada.")
            return

        random.shuffle(questoes_selecionadas)
        questoes_treino = questoes_selecionadas[:10] 
        
        st.markdown("---")
        respostas_usuario = {}
        with st.form("form_treino"):
            for i, q in enumerate(questoes_treino, 1):
                st.markdown(f"**{i}.** {q['pergunta']}")
                
                # Mostra autor discretamente
                autor = q.get('criado_por', 'Desconhecido').title()
                
                if q.get("imagem"): st.image(q["imagem"])
                respostas_usuario[i] = st.radio(f"Opções {i}", options=q.get('opcoes', []), key=f"q_{i}", index=None)
                
                st.caption(f"Questão elaborada por: {autor}")
                st.markdown("---")
            enviar = st.form_submit_button("Finalizar Treino")

        if enviar:
            acertos = 0
            for i, q in enumerate(questoes_treino, 1):
                resp = respostas_usuario.get(i)
                if resp and resp == q.get('resposta'): acertos += 1
            
            total = len(questoes_treino)
            percentual = int((acertos / total) * 100) if total > 0 else 0
            
            try:
                db.collection('rola_resultados').add({
                    "usuario": usuario_logado["nome"], "faixa": faixa, "tema": tema,
                    "acertos": acertos, "total": total, "percentual": percentual,
                    "data": firestore.SERVER_TIMESTAMP
                })
            except: pass
            
            st.balloons()
            st.success(f"Treino concluído! {acertos}/{total} ({percentual}%).")

# =========================================
# EXAME DE FAIXA (CRONÔMETRO JS CORRIGIDO)
# =========================================
def exame_de_faixa(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🥋 Exame de Faixa</h1>", unsafe_allow_html=True)
    db = get_db()

    # --- 1. PERMISSÃO ---
    faixa_sel = None
    permitido = False
    msg_bloqueio = "Acesso não autorizado."

    if usuario_logado["tipo"] == "aluno":
        alunos_query = db.collection('alunos').where('usuario_id', '==', usuario_logado['id']).stream()
        aluno_doc = next(alunos_query, None)
        
        if aluno_doc:
            dados = aluno_doc.to_dict()
            faixa_liberada = dados.get('faixa_exame_liberado') # Faixa definida pelo prof
            
            if dados.get('exame_habilitado') and faixa_liberada:
                agora = datetime.now()
                ini = dados.get('exame_inicio')
                fim = dados.get('exame_fim')
                
                # Checa validade da data
                if ini and fim:
                    try:
                        if isinstance(ini, datetime): ini = ini.replace(tzinfo=None)
                        if isinstance(fim, datetime): fim = fim.replace(tzinfo=None)
                        if ini <= agora <= fim: 
                            permitido = True
                            faixa_sel = faixa_liberada
                        else: 
                            msg_bloqueio = f"Fora do prazo. Disponível entre {ini.strftime('%d/%m %H:%M')} e {fim.strftime('%d/%m %H:%M')}."
                    except: 
                        # Se der erro de data mas estiver habilitado, libera (fallback)
                        permitido = True
                        faixa_sel = faixa_liberada
                else:
                    permitido = True 
                    faixa_sel = faixa_liberada
            elif not faixa_liberada:
                msg_bloqueio = "Seu professor ainda não definiu qual exame você deve fazer."
            else:
                msg_bloqueio = "Seu exame ainda não foi habilitado pelo professor."
        else:
            msg_bloqueio = "Perfil de aluno não encontrado."

    elif usuario_logado["tipo"] in ["admin", "professor"]:
        # Admin/Prof pode testar qualquer faixa
        faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
        faixa_sel = st.selectbox("Modo Teste - Selecione a faixa:", faixas)
        permitido = True

    if not permitido:
        st.warning(f"🚫 {msg_bloqueio}")
        return
        
    # Se chegou aqui, o aluno está liberado para a faixa 'faixa_sel'
    if usuario_logado["tipo"] == "aluno":
        st.info(f"📝 Você está realizando o **Exame de Faixa {faixa_sel}**.")

    # --- 2. GESTÃO DE ESTADO ---
    if 'prova_iniciada' not in st.session_state: st.session_state.prova_iniciada = False
    if 'prova_concluida' not in st.session_state: st.session_state.prova_concluida = False
    if 'resultado_final' not in st.session_state: st.session_state.resultado_final = {}
    
    # Reset se mudar faixa (segurança para admin/prof testando várias)
    if 'ultima_faixa_sel' not in st.session_state: st.session_state.ultima_faixa_sel = faixa_sel
    elif st.session_state.ultima_faixa_sel != faixa_sel:
        st.session_state.prova_iniciada = False
        st.session_state.prova_concluida = False
        st.session_state.ultima_faixa_sel = faixa_sel

    # --- 3. RESULTADOS (Se já acabou) ---
    if st.session_state.prova_concluida:
        res = st.session_state.resultado_final
        # Verifica se o resultado armazenado corresponde à faixa atual selecionada
        if res.get('faixa') == faixa_sel:
            st.markdown("---")
            if res['aprovado']:
                st.balloons()
                st.success(f"🎉 APROVADO! Nota: {res['percentual']}% ({res['acertos']}/{res['total']})")
                st.info("Seu certificado foi gerado.")
                
                # Tenta pegar PDF do cache da sessão
                pdf_bytes = res.get('pdf_bytes')
                pdf_name = res.get('pdf_name', 'certificado.pdf')
                
                # Se não tiver (raro), gera de novo e guarda
                if not pdf_bytes:
                    try:
                        # ATENÇÃO: Agora gerar_pdf retorna (bytes, nome) diretamente
                        pdf_bytes, pdf_name = gerar_pdf(
                            usuario_logado['nome'], res['faixa'], 
                            res['acertos'], res['total'], res['codigo']
                        )
                        st.session_state.resultado_final['pdf_bytes'] = pdf_bytes
                        st.session_state.resultado_final['pdf_name'] = pdf_name
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF: {e}")

                if pdf_bytes:
                    st.download_button(
                        label="📥 BAIXAR CERTIFICADO AGORA",
                        data=pdf_bytes,
                        file_name=pdf_name,
                        mime="application/pdf",
                        use_container_width=True,
                        key="btn_dl_final"
                    )
            else:
                msg = "Tempo Esgotado. " if res.get('tempo_esgotado') else ""
                st.error(f"Reprovado. {msg}Nota: {res['percentual']}%. Mínimo: 70%.")
            
            if st.button("🔄 Voltar ao Início"):
                st.session_state.prova_iniciada = False
                st.session_state.prova_concluida = False
                st.rerun()
            return

    # --- 4. CARREGA PROVA ---
    dados_exame = carregar_exame_firestore(faixa_sel)
    if not dados_exame:
        st.error(f"A prova da Faixa {faixa_sel} ainda não foi criada no sistema.")
        return

    lista_questoes = dados_exame.get('questoes', [])
    tempo_limite = dados_exame.get('tempo_limite', 60)

    if not lista_questoes:
        st.warning("Esta prova está vazia. Avise seu professor.")
        return

    # --- 5. INSTRUÇÕES ---
    if not st.session_state.prova_iniciada:
        st.markdown("---")
        with st.container(border=True):
            st.markdown(f"### 📜 Instruções - Faixa {faixa_sel}")
            # Instruções atualizadas conforme solicitado
            st.markdown(f"""
            * Sua prova contém **{len(lista_questoes)} Questões:**
            * ⏱️ O tempo limote para finalização do exame é de **{tempo_limite} minutos**
            * ✅ Para ser aprovado, voê precisa acertar no mínimo **70%** do exame
            
            **ATENÇÃO:** * Após clicar em **✅ Iniciar exame**, não será possível pausar ou interromper o cronômetro.
            * Se o tempo acabar antes de você finalizar, você será considerado **reprovado**.
            * Não é permitido consulta a materiais externos.
            * Esteja em um lugar confortável e silencioso para ajudar na sua concentração.
            
            **Boa prova!** 🥋
            """)
            
            if st.button("✅ Iniciar Exame", type="primary", use_container_width=True):
                st.session_state.prova_iniciada = True
                st.session_state.prova_concluida = False
                # Define o timestamp de fim da prova (tempo absoluto)
                # time.time() retorna segundos desde epoch (UTC)
                st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
                st.rerun()
        return 

    # --- 6. PROVA EM ANDAMENTO ---
    
    # Tempo Restante (em segundos)
    agora_ts = time.time()
    restante_sec = int(st.session_state.fim_prova_ts - agora_ts)
    tempo_esgotado = restante_sec <= 0

    if not tempo_esgotado:
        # CRONÔMETRO JAVASCRIPT ROBUSTO
        # Passamos o tempo restante inicial para o JS começar a contar imediatamente
        # O JS fará a contagem regressiva visualmente sem depender do Python
        timer_id = f"timer_{uuid.uuid4()}"
        
        # Componente HTML que contém o script do cronômetro
        # A variável 'timeLeft' é inicializada com os segundos restantes calculados no Python
        st.components.v1.html(
            f"""
            <div style="
                display: flex; 
                justify-content: center; 
                align-items: center;
                background-color: #0e2d26; 
                border: 2px solid #FFD700; 
                border-radius: 10px; 
                padding: 10px; 
                margin-bottom: 10px;
                font-family: sans-serif;
            ">
                <span id="clock_display" style="
                    font-size: 24px; 
                    font-weight: bold; 
                    color: #FFD700;
                ">
                    Carregando tempo...
                </span>
            </div>
            <script>
                // Tempo restante em segundos vindo do Python
                var timeLeft = {restante_sec};
                var timerElem = document.getElementById('clock_display');
                
                function updateDisplay() {{
                    if (timeLeft <= 0) {{
                        timerElem.innerHTML = "⌛ TEMPO ESGOTADO";
                        timerElem.style.color = "#ff4b4b"; // Vermelho
                        return;
                    }}
                    
                    var m = Math.floor(timeLeft / 60);
                    var s = timeLeft % 60;
                    
                    // Formata com zero à esquerda
                    var mStr = m < 10 ? "0" + m : m;
                    var sStr = s < 10 ? "0" + s : s;
                    
                    timerElem.innerHTML = "⏱️ " + mStr + ":" + sStr;
                    timeLeft -= 1;
                }}
                
                // Executa uma vez agora para tirar o "Carregando..."
                updateDisplay();
                
                // Atualiza a cada segundo
                setInterval(updateDisplay, 1000);
            </script>
            """,
            height=85 # Altura suficiente para o componente não cortar
        )
    else:
        st.error("⌛ TEMPO ESGOTADO! O exame foi encerrado.")

    respostas = {}
    finalizar = False
    
    # Se o tempo não acabou, mostra as questões
    if not tempo_esgotado:
        with st.form(key=f"form_prova_{faixa_sel}"):
            for i, q in enumerate(lista_questoes, 1):
                st.markdown(f"**{i}.** {q['pergunta']}")
                if q.get("imagem"): st.image(q["imagem"])
                respostas[i] = st.radio("Alternativa:", q.get('opcoes', []), key=f"resp_{i}", index=None)
                
                # Autor Discreto
                autor_q = q.get('criado_por', 'BJJ Digital').title()
                st.caption(f"Questão por: {autor_q}")
                st.markdown("---")
                
            finalizar = st.form_submit_button("Finalizar Exame 🏁", use_container_width=True)
    else:
        # Se o tempo acabou, forçamos a finalização na próxima recarga da página
        finalizar = True 
        
    # --- 7. PROCESSAMENTO FINAL ---
    if finalizar:
        with st.spinner("Processando resultados e gerando certificado..."):
            acertos = 0
            total = len(lista_questoes)
            
            # Se o tempo não esgotou, corrige as respostas
            if not tempo_esgotado:
                for i, q in enumerate(lista_questoes, 1):
                    resp_user = respostas.get(i)
                    resp_certa = q.get('resposta')
                    # Verifica resposta
                    if resp_user:
                        if resp_user == resp_certa or resp_user.startswith(f"{resp_certa})"):
                            acertos += 1
            
            percentual = int((acertos / total) * 100) if total > 0 else 0
            aprovado = percentual >= 70
            
            codigo = None
            pdf_bytes = None
            pdf_name = ""

            if aprovado:
                try: codigo = gerar_codigo_verificacao()
                except: 
                    import random
                    codigo = f"BJJ-{random.randint(1000,9999)}"

                try:
                    db.collection('resultados').add({
                        "usuario": usuario_logado["nome"], "modo": "Exame de Faixa",
                        "faixa": faixa_sel, "pontuacao": percentual,
                        "acertos": acertos, "total_questoes": total,
                        "data": firestore.SERVER_TIMESTAMP, "codigo_verificacao": codigo
                    })
                except Exception as e: print(f"Erro save: {e}")
                
                # GERA PDF
                try:
                    pdf_bytes, pdf_name = gerar_pdf(
                        usuario_logado['nome'], faixa_sel, 
                        acertos, total, codigo
                    )
                except Exception as e: st.error(f"Erro PDF: {e}")
            else:
                # Salva reprovação
                try:
                    db.collection('resultados').add({
                        "usuario": usuario_logado["nome"], "modo": "Exame de Faixa",
                        "faixa": faixa_sel, "pontuacao": percentual,
                        "acertos": acertos, "total_questoes": total,
                        "data": firestore.SERVER_TIMESTAMP, "codigo_verificacao": None
                    })
                except: pass
            
            # Atualiza o estado da sessão
            st.session_state.prova_concluida = True
            st.session_state.resultado_final = {
                "usuario": usuario_logado["nome"], "faixa": faixa_sel,
                "acertos": acertos, "total": total, "percentual": percentual,
                "codigo": codigo, "aprovado": aprovado, "tempo_esgotado": tempo_esgotado,
                "pdf_bytes": pdf_bytes, "pdf_name": pdf_name
            }
            st.rerun()

# =========================================
# RANKING e CERTIFICADOS (MANTIDOS)
# =========================================
def ranking():
    st.markdown("<h1 style='color:#FFD700;'>🏆 Ranking</h1>", unsafe_allow_html=True)
    db = get_db()
    docs = db.collection('rola_resultados').stream()
    data = [d.to_dict() for d in docs]
    if not data: st.info("Ranking vazio."); return
    df = pd.DataFrame(data)
    if 'usuario' in df.columns:
        rdf = df.groupby("usuario", as_index=False).agg(media=("percentual", "mean"), total=("usuario", "count")).sort_values("media", ascending=False)
        st.dataframe(rdf, use_container_width=True)

def meus_certificados(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>📜 Meus Certificados</h1>", unsafe_allow_html=True)
    db = get_db()
    docs = db.collection('resultados').where('usuario', '==', usuario_logado['nome']).where('modo', '==', 'Exame de Faixa').stream()
    lista = [d.to_dict() for d in docs]
    if not lista: st.info("Sem certificados."); return

    for i, c in enumerate(lista):
        with st.container(border=True):
            st.write(f"**{c['faixa']}** | {c['pontuacao']}% | {c.get('codigo_verificacao')}")
            try:
                p_bytes, p_name = gerar_pdf(
                    usuario_logado['nome'], c['faixa'], 
                    c.get('acertos',0), c.get('total_questoes',10), 
                    c.get('codigo_verificacao','-')
                )
                st.download_button("Baixar", p_bytes, p_name, "application/pdf", key=f"d{i}")
            except: pass
