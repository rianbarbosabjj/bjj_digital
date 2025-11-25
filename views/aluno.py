import streamlit as st
import random
import os
import json
import time # Para calculos de tempo
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from database import get_db
from utils import gerar_codigo_verificacao, gerar_pdf
from firebase_admin import firestore

# =========================================
# MODO ROLA (Treino Livre)
# =========================================
def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)
    db = get_db()

    # 1. Carrega TEMAS (Tenta Firestore, senão JSON)
    todas_questoes = []
    
    # Tentativa 1: Firestore
    try:
        docs_questoes = list(db.collection('questoes').stream())
        if docs_questoes:
            todas_questoes = [d.to_dict() for d in docs_questoes]
    except: pass
    
    # Tentativa 2: JSON Local (Fallback)
    if not todas_questoes and os.path.exists("questions"):
        for f in os.listdir("questions"):
            if f.endswith(".json"):
                try:
                    with open(f"questions/{f}", "r", encoding="utf-8") as file:
                        q_list = json.load(file)
                        tema_nome = f.replace(".json", "")
                        for q in q_list:
                            q['tema'] = tema_nome
                            todas_questoes.append(q)
                except: continue

    if not todas_questoes:
        st.warning("O banco de questões está vazio. Peça ao professor para cadastrar perguntas.")
        return

    temas = sorted(list(set(q.get('tema', 'Geral') for q in todas_questoes)))
    temas.insert(0, "Todos os Temas")

    col1, col2 = st.columns(2)
    with col1:
        tema = st.selectbox("Selecione o tema:", temas)
    with col2:
        faixa = st.selectbox("Sua faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])

    if st.button("Iniciar Treino 🤼", use_container_width=True):
        if tema == "Todos os Temas":
            questoes_selecionadas = todas_questoes
        else:
            questoes_selecionadas = [q for q in todas_questoes if q.get('tema') == tema]

        if not questoes_selecionadas:
            st.error("Nenhuma questão encontrada para este tema.")
            return

        random.shuffle(questoes_selecionadas)
        questoes_treino = questoes_selecionadas[:10] 
        
        acertos = 0
        respostas_usuario = {}
        
        st.markdown("---")
        with st.form("form_treino"):
            for i, q in enumerate(questoes_treino, 1):
                st.markdown(f"**{i}.** {q['pergunta']}")
                
                if q.get("imagem"):
                    st.image(q["imagem"])
                
                opcoes = q.get('opcoes', [])
                respostas_usuario[i] = st.radio(f"Opções {i}", options=opcoes, key=f"q_{i}", index=None)
                st.markdown("---")
            
            enviar = st.form_submit_button("Finalizar Treino")

        if enviar:
            total = len(questoes_treino)
            for i, q in enumerate(questoes_treino, 1):
                resp = respostas_usuario.get(i)
                if resp and resp == q.get('resposta'):
                    acertos += 1
            
            percentual = int((acertos / total) * 100) if total > 0 else 0
            
            # Salva no Firestore
            try:
                db.collection('rola_resultados').add({
                    "usuario": usuario_logado["nome"],
                    "faixa": faixa,
                    "tema": tema,
                    "acertos": acertos,
                    "total": total,
                    "percentual": percentual,
                    "data": firestore.SERVER_TIMESTAMP
                })
            except:
                st.warning("Erro de conexão ao salvar resultado. Mas parabéns pelo treino!")
            
            st.balloons()
            st.success(f"Treino concluído! Você acertou {acertos} de {total} ({percentual}%).")

# =========================================
# EXAME DE FAIXA (COM CRONÔMETRO)
# =========================================
def exame_de_faixa(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🥋 Exame de Faixa</h1>", unsafe_allow_html=True)
    db = get_db()

    # --- VERIFICAÇÃO DE PERMISSÃO ---
    if usuario_logado["tipo"] == "aluno":
        alunos_query = db.collection('alunos').where('usuario_id', '==', usuario_logado['id']).stream()
        aluno_doc = next(alunos_query, None)
        
        permitido = False
        msg_bloqueio = "Seu exame ainda não foi liberado pelo professor."
        
        if aluno_doc:
            dados = aluno_doc.to_dict()
            if dados.get('exame_habilitado'):
                agora = datetime.now()
                inicio = dados.get('exame_inicio')
                fim = dados.get('exame_fim')
                
                if inicio and fim:
                    try:
                        ini_tz = inicio.replace(tzinfo=None)
                        fim_tz = fim.replace(tzinfo=None)
                        if ini_tz <= agora <= fim_tz:
                            permitido = True
                        else:
                            msg_bloqueio = f"Fora do período. Disponível entre {ini_tz.strftime('%d/%m %H:%M')} e {fim_tz.strftime('%d/%m %H:%M')}."
                    except:
                        permitido = True
                else:
                    permitido = True 
            
        if not permitido:
            st.warning(f"🚫 {msg_bloqueio}")
            return

    # --- SELEÇÃO DE FAIXA ---
    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa_sel = st.selectbox("Selecione a faixa do exame:", faixas)
    
    # --- INICIALIZA ESTADO DE "PROVA EM ANDAMENTO" ---
    if 'prova_iniciada' not in st.session_state:
        st.session_state.prova_iniciada = False
        st.session_state.fim_prova = None # Armazena datetime de fim
    
    # Se mudou a faixa, reseta (apenas se não estiver no meio da prova daquela faixa)
    if 'ultima_faixa_sel' not in st.session_state:
        st.session_state.ultima_faixa_sel = faixa_sel
    elif st.session_state.ultima_faixa_sel != faixa_sel:
        st.session_state.prova_iniciada = False
        st.session_state.fim_prova = None
        st.session_state.ultima_faixa_sel = faixa_sel

    # --- BUSCA A PROVA (Firestore ou Local) ---
    dados_exame = {}
    doc_ref = db.collection('exames').document(faixa_sel)
    doc_exame = doc_ref.get()
    
    if doc_exame.exists:
        dados_exame = doc_exame.to_dict()
    else:
        # Fallback busca por query
        query = db.collection('exames').where('faixa', '==', faixa_sel).stream()
        results = list(query)
        if results: dados_exame = results[0].to_dict()

    # Fallback JSON local
    if not dados_exame:
        json_path = f"exames/faixa_{faixa_sel.lower()}.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f: dados_exame = json.load(f)
            except: pass

    if not dados_exame:
        st.info(f"Ainda não há prova cadastrada para a faixa {faixa_sel}.")
        return

    lista_questoes_prova = dados_exame.get('questoes', [])
    tempo_limite = dados_exame.get('tempo_limite', 60) # Pega do banco ou default 60 min

    if not lista_questoes_prova:
        st.warning("Esta prova existe mas está vazia.")
        return

    # --- TELA DE INSTRUÇÕES (ANTES DA PROVA) ---
    if not st.session_state.prova_iniciada:
        st.markdown("---")
        with st.container(border=True):
            st.markdown(f"### 📜 Instruções para o Exame de Faixa {faixa_sel}")
            st.markdown(f"""
            Você está prestes a iniciar sua avaliação teórica.
            
            * **Total de Questões:** {len(lista_questoes_prova)} perguntas.
            * **Tempo Limite:** ⏱️ **{tempo_limite} minutos**.
            * **Nota Mínima:** 70% para aprovação.
            
            Ao clicar no botão abaixo, o cronômetro iniciará e não poderá ser pausado.
            """)
            
            if st.button("✅ Começar Agora (Inicia Cronômetro)", type="primary", use_container_width=True):
                st.session_state.prova_iniciada = True
                # Define o horário de fim: Agora + Tempo Limite
                st.session_state.fim_prova = datetime.now() + timedelta(minutes=tempo_limite)
                st.rerun()
        return 

    # --- APLICAÇÃO DA PROVA (COM CRONÔMETRO) ---
    
    # 1. Lógica do Tempo
    agora = datetime.now()
    tempo_restante = st.session_state.fim_prova - agora
    
    # Se o tempo acabou (negativo)
    tempo_esgotado = tempo_restante.total_seconds() <= 0

    # Exibe cronômetro no topo (Sticky se possível, mas aqui simples)
    if not tempo_esgotado:
        minutos = int(tempo_restante.total_seconds() // 60)
        segundos = int(tempo_restante.total_seconds() % 60)
        
        # Estilo do relógio
        cor_relogio = "#FFD700" # Amarelo
        if minutos < 5: cor_relogio = "#FF4B4B" # Vermelho se < 5 min
        
        st.markdown(
            f"""
            <div style='padding: 10px; background-color: #262730; border-radius: 5px; text-align: center; border: 1px solid {cor_relogio}; margin-bottom: 20px;'>
                <h3 style='color: {cor_relogio}; margin:0;'>⏱️ Tempo Restante: {minutos:02d}:{segundos:02d}</h3>
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        st.error("⌛ TEMPO ESGOTADO! O exame será finalizado automaticamente.")

    st.markdown(f"### 📝 Prova de Faixa {faixa_sel}")
    
    # Formulário da Prova
    respostas = {}
    
    # Se o tempo acabou, desabilita o form (ou força envio)
    # No Streamlit, não conseguimos submeter o form via código facilmente sem JS.
    # Então, se o tempo acabou, mostramos apenas um botão de "Ver Resultado" fora do form,
    # ou bloqueamos as opções.
    
    if not tempo_esgotado:
        with st.form(key=f"form_prova_{faixa_sel}"):
            for i, q in enumerate(lista_questoes_prova, 1):
                st.markdown(f"**{i}.** {q['pergunta']}")
                
                if q.get("imagem"):
                    st.image(q["imagem"])
                
                respostas[i] = st.radio("Selecione:", q.get('opcoes', []), key=f"resp_{i}", index=None)
                st.markdown("---")
                
            finalizar = st.form_submit_button("Finalizar Exame 🏁", use_container_width=True)
    else:
        # Tempo esgotado: O usuário perdeu a chance de enviar pelo form normal.
        # Podemos dar uma chance de "Entregar o que fez" ou considerar zero.
        # Vamos considerar que ele "Finaliza" agora com o que tiver no estado (se tiver algo salvo, o que é difícil no form).
        # Simplificação: Tempo esgotado = Reprovado ou Zero, pois o form não salva estado parcial sem submissão.
        finalizar = True 
        respostas = {} # Infelizmente, sem session state por questão, perde-se as respostas no timeout
        st.warning("Como o tempo acabou, a prova foi encerrada. Se você não clicou em enviar, suas respostas não foram salvas.")

    # 5. CORREÇÃO E SALVAMENTO
    if finalizar:
        acertos = 0
        total = len(lista_questoes_prova)
        
        # Só corrige se tiver respostas (tempo não esgotado)
        if not tempo_esgotado:
            for i, q in enumerate(lista_questoes_prova, 1):
                resp_user = respostas.get(i)
                resp_certa = q.get('resposta')
                
                if resp_user:
                    if resp_user == resp_certa or resp_user.startswith(f"{resp_certa})"):
                        acertos += 1
        
        percentual = int((acertos / total) * 100) if total > 0 else 0
        
        # Limpa estado de prova
        st.session_state.prova_iniciada = False
        st.session_state.fim_prova = None

        if percentual >= 70:
            st.balloons()
            st.success(f"🎉 APROVADO! Nota: {percentual}% ({acertos}/{total})")
            codigo = gerar_codigo_verificacao()
            
            db.collection('resultados').add({
                "usuario": usuario_logado["nome"],
                "modo": "Exame de Faixa",
                "faixa": faixa_sel,
                "pontuacao": percentual,
                "acertos": acertos,
                "total_questoes": total,
                "data": firestore.SERVER_TIMESTAMP,
                "codigo_verificacao": codigo
            })
            
            st.session_state['certificado_temp'] = {
                "usuario": usuario_logado["nome"], "faixa": faixa_sel,
                "acertos": acertos, "total": total, "codigo": codigo
            }
        else:
            if tempo_esgotado:
                st.error(f"Reprovado por Tempo Esgotado. Nota: {percentual}%.")
            else:
                st.error(f"Reprovado. Nota: {percentual}%. Mínimo: 70%.")
    
    if 'certificado_temp' in st.session_state:
        dados = st.session_state['certificado_temp']
        if dados['faixa'] == faixa_sel:
            try:
                pdf_path = gerar_pdf(dados['usuario'], dados['faixa'], dados['acertos'], dados['total'], dados['codigo'])
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 Baixar Certificado", f.read(), os.path.basename(pdf_path), "application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")

# =========================================
# RANKING
# =========================================
def ranking():
    st.markdown("<h1 style='color:#FFD700;'>🏆 Ranking</h1>", unsafe_allow_html=True)
    db = get_db()
    
    docs = db.collection('rola_resultados').stream()
    data = [d.to_dict() for d in docs]
    
    if not data:
        st.info("O Ranking ainda está vazio. Bora treinar!")
        return

    df = pd.DataFrame(data)
    
    if 'usuario' in df.columns and 'percentual' in df.columns:
        ranking_df = df.groupby("usuario", as_index=False).agg(
            media_percentual=("percentual", "mean"),
            total_treinos=("usuario", "count")
        ).sort_values(by="media_percentual", ascending=False)

        ranking_df["media_percentual"] = ranking_df["media_percentual"].round(1)
        
        st.dataframe(
            ranking_df, 
            column_config={
                "media_percentual": st.column_config.ProgressColumn("Aproveitamento Médio", format="%f%%", min_value=0, max_value=100),
                "total_treinos": st.column_config.NumberColumn("Treinos Realizados")
            },
            use_container_width=True
        )
    else:
        st.error("Dados insuficientes para gerar ranking.")

# =========================================
# MEUS CERTIFICADOS
# =========================================
def meus_certificados(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>📜 Meus Certificados</h1>", unsafe_allow_html=True)
    db = get_db()
    
    docs = db.collection('resultados')\
             .where('usuario', '==', usuario_logado['nome'])\
             .where('modo', '==', 'Exame de Faixa').stream()
             
    certificados = [d.to_dict() for d in docs]

    if not certificados:
        st.info("Você ainda não possui certificados.")
        return

    for i, cert in enumerate(certificados):
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"### 🥋 Faixa {cert.get('faixa')}")
            c1.write(f"**Nota:** {cert.get('pontuacao')}% | **Código:** {cert.get('codigo_verificacao')}")
            
            try:
                path = gerar_pdf(
                    usuario_logado['nome'], cert.get('faixa'), 
                    cert.get('acertos', 0), cert.get('total_questoes', 10), 
                    cert.get('codigo_verificacao')
                )
                with open(path, "rb") as f:
                    c2.download_button("📥 Baixar", f.read(), os.path.basename(path), "application/pdf", key=f"dn_{i}")
            except:
                c2.error("Erro PDF")
