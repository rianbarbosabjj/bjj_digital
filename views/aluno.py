import streamlit as st
import time
import random
from datetime import datetime, timedelta
from database import get_db
from utils import (
    verificar_elegibilidade_exame, 
    registrar_inicio_exame, 
    registrar_fim_exame, 
    bloquear_por_abandono,
    carregar_todas_questoes,
    normalizar_nome
)

# =========================================
# FUNÇÃO AUXILIAR DE CARREGAMENTO (DO CÓDIGO ANTIGO)
# =========================================
def carregar_exame_do_professor(faixa):
    """
    Tenta buscar um exame configurado especificamente para esta faixa.
    Retorna: (lista_questoes, tempo_limite, aprovacao_minima)
    """
    db = get_db()
    
    # 1. Tenta buscar na coleção 'exames' (estrutura do código antigo)
    doc_ref = db.collection('exames').document(faixa)
    doc = doc_ref.get()
    
    if doc.exists:
        dados = doc.to_dict()
        return (
            dados.get('questoes', []), 
            int(dados.get('tempo_limite', 45)), 
            int(dados.get('aprovacao_minima', 70))
        )
    
    # 2. Tenta buscar na coleção 'config_exames' (estrutura alternativa)
    query = db.collection('config_exames').where('faixa', '==', faixa).limit(1).stream()
    for doc in query:
        dados = doc.to_dict()
        # Aqui assumimos que as questões podem estar salvas ou serem geradas
        # Se não tiver lista de questões fixa, pegamos do banco geral
        questoes = dados.get('questoes', [])
        if not questoes:
            todas = carregar_todas_questoes()
            questoes = [q for q in todas if q.get('faixa', '').lower() == faixa.lower()]
            # Se ainda assim vazio, pega aleatórias para preencher
            if not questoes and todas:
                qtd = int(dados.get('qtd_questoes', 10))
                questoes = random.sample(todas, min(qtd, len(todas)))
                
        return (
            questoes, 
            int(dados.get('tempo_limite', 45)), 
            int(dados.get('aprovacao_minima', 70))
        )

    # 3. Fallback Total (Se não achar nada configurado)
    # Retorna lista vazia para tratar na interface
    return [], 45, 70

# =========================================
# MÓDULOS SECUNDÁRIOS
# =========================================
def modo_rola(usuario):
    st.markdown(f"## 🥋 Modo Rola - Treino Livre")
    st.info("Em breve: Aqui você poderá treinar com questões aleatórias sem valer nota.")

def meus_certificados(usuario):
    st.markdown(f"## 🏅 Meus Certificados")
    if usuario.get('status_exame') == 'aprovado':
        st.success(f"Parabéns! Você foi aprovado no exame de faixa {usuario.get('faixa_atual', 'N/A')}.")
        st.info("O download do certificado oficial estará disponível após a graduação presencial.")
    else:
        st.info("Você ainda não possui certificados emitidos nesta plataforma.")

def ranking():
    st.markdown("## 🏆 Ranking da Equipe")
    st.info("O ranking será atualizado conforme os alunos realizarem os exames.")

# =========================================
# EXAME DE FAIXA (LÓGICA UNIFICADA)
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    # 1. Busca dados frescos do aluno
    db = get_db()
    doc_usuario = db.collection('usuarios').document(usuario['id']).get()
    dados_usuario = doc_usuario.to_dict()
    faixa_aluno = dados_usuario.get('faixa_atual', 'Branca')
    
    # 2. Verifica Elegibilidade (Regras de 72h e Bloqueio)
    pode_fazer, msg = verificar_elegibilidade_exame(dados_usuario)
    
    if not pode_fazer:
        st.warning(msg)
        return

    # 3. Anti-Fraude: Detector de Fuga (se já estava em andamento e recarregou)
    if dados_usuario.get("status_exame") == "em_andamento":
        bloquear_por_abandono(usuario['id'])
        st.error("🚨 DETECÇÃO DE INFRAÇÃO: Você saiu da página ou recarregou durante o exame.")
        st.warning("Seu exame foi bloqueado. Solicite o desbloqueio ao professor.")
        st.stop()

    # --- CARREGAMENTO DA PROVA ---
    # Aqui usamos a função que restaura a lógica antiga de buscar o exame exato
    lista_questoes, tempo_limite, min_aprovacao = carregar_exame_do_professor(faixa_aluno)
    
    # Se a lista vier vazia, tentamos um fallback de emergência para não mostrar "0"
    if not lista_questoes:
        # Tenta carregar qualquer coisa do JSON local como última esperança
        todas = carregar_todas_questoes()
        if todas:
            lista_questoes = todas[:10] # Pega 10 quaisquer
        else:
            # Se realmente não tiver nada, cria dummy para não quebrar layout
            lista_questoes = [{"pergunta": "Exemplo (Sem questões cadastradas)", "opcoes": ["V","F"], "correta": "V"}]

    qtd_questoes = len(lista_questoes)

    # --- JAVASCRIPT ANTI-COLA ---
    html_anti_cola = """
    <script>
    document.addEventListener("visibilitychange", function() {
        if (document.hidden) {
            document.body.innerHTML = "<h1 style='color:red; text-align:center; margin-top:20%; font-family:sans-serif;'>🚨 INFRAÇÃO DETECTADA 🚨<br><br>Você saiu da aba da prova.<br>Isso viola as regras de segurança.<br><br>Atualize a página para ver seu status.</h1>";
        }
    });
    </script>
    """
    st.components.v1.html(html_anti_cola, height=0, width=0)

    # 4. TELA DE INÍCIO (INSTRUÇÕES)
    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado = False

    if not st.session_state.exame_iniciado:
        
        st.markdown("### 📋 Leia atentamente as instruções antes de iniciar")
        
        with st.container(border=True):
            # Layout das Métricas
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd_questoes} Questões**")
            c2.markdown(f"⏱️ Tempo: **{tempo_limite} min**")
            c3.markdown(f"✅ Aprovação: **{min_aprovacao}%**")
            
            st.markdown("---")
          
           
            **ATENÇÃO:**
            * Após clicar em **✅ Iniciar exame**, não será possível pausar ou interromper o cronômetro.
            * Se o tempo acabar antes de você finalizar, você será considerado **reprovado**.
            * Não é permitido consulta a materiais externos.
            * Esteja em um lugar confortável e silencioso para ajudar na sua concentração.
            
            **REGRAS DE SEGURANÇA:**
            * 🚫 **Não saia desta tela:** Se mudar de aba ou minimizar, **a prova será bloqueada**.
            * ⏳ **Tentativa Única:** Se reprovar, aguarde **72 horas**.
            * 🔌 **Falhas:** Se o PC desligar, peça desbloqueio ao professor.

            **Boa prova!** 🥋
            """)

        if st.button("✅ Li e Concordo. INICIAR EXAME", type="primary", use_container_width=True):
            registrar_inicio_exame(usuario['id'])
            
            st.session_state.exame_iniciado = True
            st.session_state.inicio_prova = datetime.now()
            
            # Salva na sessão para persistência durante a prova
            st.session_state.questoes_prova = lista_questoes 
            st.session_state.params_prova = {
                "tempo": tempo_limite, 
                "min_aprovacao": min_aprovacao
            }
            st.rerun()
    
    # 5. O EXAME EM SI (QUANDO INICIADO)
    else:
        questoes = st.session_state.get('questoes_prova', [])
        params = st.session_state.get('params_prova', {"tempo": 45, "min_aprovacao": 70})
        
        # Lógica do Timer
        agora = datetime.now()
        inicio = st.session_state.get('inicio_prova', agora)
        decorrido = (agora - inicio).total_seconds() / 60
        tempo_restante = params['tempo'] - decorrido
        
        # Verifica estouro de tempo
        if tempo_restante <= 0:
            st.error("⌛ Tempo esgotado!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            time.sleep(3)
            st.rerun()

        # Cabeçalho da Prova
        cols = st.columns([3, 1])
        cols[0].info(f"📝 Prova Faixa {faixa_aluno} - **Não mude de aba!**")
        
        # Formatação do Timer
        mins = int(tempo_restante)
        segs = int((tempo_restante - mins) * 60)
        cols[1].metric("Tempo Restante", f"{mins}:{segs:02d}")
        
        with st.form("form_exame"):
            respostas_usuario = {}
            
            for i, q in enumerate(questoes):
                # Suporte para diferentes formatos de questão
                enunciado = q.get('pergunta') or q.get('enunciado') or "Questão sem texto"
                st.markdown(f"**{i+1}. {enunciado}**")
                
                # Suporte para imagem
                if q.get('imagem'):
                    st.image(q['imagem'])
                
                opcoes = q.get('opcoes', ['Verdadeiro', 'Falso'])
                
                respostas_usuario[i] = st.radio(
                    "Sua resposta:", 
                    opcoes, 
                    key=f"q_{i}", 
                    index=None, 
                    label_visibility="collapsed"
                )
                st.markdown("---")
            
            enviar = st.form_submit_button("Finalizar Prova", type="primary", use_container_width=True)
            
            if enviar:
                # Opcional: Bloquear envio vazio
                # if any(respostas_usuario.get(i) is None for i in range(len(questoes))):
                #     st.warning("Responda todas as questões.")
                #     st.stop()

                acertos = 0
                for i, q in enumerate(questoes):
                    # Tenta pegar a chave de resposta correta ('correta', 'resposta', 'gabarito')
                    gabarito = q.get('correta') or q.get('resposta') or q.get('gabarito')
                    
                    # Comparação robusta (string vs string)
                    if str(respostas_usuario.get(i)).strip() == str(gabarito).strip():
                        acertos += 1
                
                nota_final = (acertos / len(questoes)) * 100
                aprovado = nota_final >= params['min_aprovacao']
                
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                
                if aprovado:
                    st.balloons()
                    st.success(f"PARABÉNS! Aprovado com {nota_final:.1f}%!")
                    st.info("Seu certificado já está disponível no menu 'Meus Certificados'.")
                else:
                    st.error(f"Reprovado. Sua nota foi {nota_final:.1f}%.")
                    st.info("Aguarde 72h para nova tentativa.")
                
                time.sleep(5)
                st.rerun()
