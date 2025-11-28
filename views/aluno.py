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
# FUNÇÃO "SABUESO": BUSCA EXAME DE QUALQUER JEITO
# =========================================
def carregar_exame_inteligente(faixa_aluno):
    """
    Busca prova, tempo e nota mínima tentando várias fontes no banco.
    Retorna: (lista_questoes, tempo, nota_minima)
    """
    db = get_db()
    faixa_norm = faixa_aluno.strip().lower() # ex: "branca"
    
    questoes_finais = []
    tempo = 45 # Padrão
    nota = 70  # Padrão

    # --- ESTRATÉGIA 1: BUSCAR CONFIGURAÇÃO DE EXAME (Onde tem o tempo) ---
    # Tenta achar configurações salvas pelo professor
    configs = db.collection('config_exames').stream()
    config_achada = None
    
    for doc in configs:
        d = doc.to_dict()
        # Verifica se a faixa bate (ignorando maiusculas/minusculas)
        if d.get('faixa', '').strip().lower() == faixa_norm:
            config_achada = d
            tempo = int(d.get('tempo_limite', 45))
            nota = int(d.get('aprovacao_minima', 70))
            # Se o professor salvou as questões DENTRO da config
            if d.get('questoes'):
                questoes_finais = d.get('questoes')
            break
    
    # --- ESTRATÉGIA 2: SE NÃO ACHOU QUESTÕES NA CONFIG, BUSCA NA COLEÇÃO GERAL ---
    if not questoes_finais:
        # Busca na coleção 'questoes' onde o campo 'faixa' bate com a do aluno
        todas_refs = db.collection('questoes').stream()
        
        pool_questoes = []
        for doc in todas_refs:
            q = doc.to_dict()
            # Normaliza a faixa da questão para comparar
            q_faixa = q.get('faixa', '').strip().lower()
            
            # Se a faixa for igual OU se a questão for "Geral" (para todas)
            if q_faixa == faixa_norm or q_faixa == 'geral':
                pool_questoes.append(q)
        
        # Se achou questões soltas no banco
        if pool_questoes:
            # Se tiver configuração de quantidade, respeita. Senão pega 10.
            qtd = 10
            if config_achada:
                qtd = int(config_achada.get('qtd_questoes', 10))
            
            # Seleciona aleatoriamente se tiver muitas, ou todas se tiver poucas
            if len(pool_questoes) > qtd:
                questoes_finais = random.sample(pool_questoes, qtd)
            else:
                questoes_finais = pool_questoes

    # --- ESTRATÉGIA 3: FALLBACK LOCAL (Último recurso) ---
    if not questoes_finais:
        todas_json = carregar_todas_questoes()
        questoes_finais = [q for q in todas_json if q.get('faixa', '').lower() == faixa_norm]

    return questoes_finais, tempo, nota

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
# EXAME DE FAIXA (PRINCIPAL)
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    # 1. Busca dados frescos do aluno
    db = get_db()
    doc_usuario = db.collection('usuarios').document(usuario['id']).get()
    dados_usuario = doc_usuario.to_dict()
    faixa_aluno = dados_usuario.get('faixa_atual', 'Branca') # Faixa atual do aluno
    
    # 2. Verifica Elegibilidade
    pode_fazer, msg = verificar_elegibilidade_exame(dados_usuario)
    if not pode_fazer:
        st.warning(msg)
        return

    # 3. Anti-Fraude (Fuga)
    if dados_usuario.get("status_exame") == "em_andamento":
        bloquear_por_abandono(usuario['id'])
        st.error("🚨 DETECÇÃO DE INFRAÇÃO: Você saiu da página ou recarregou durante o exame.")
        st.warning("Seu exame foi bloqueado. Solicite o desbloqueio ao professor.")
        st.stop()

    # --- CARREGAMENTO INTELIGENTE ---
    lista_questoes, tempo_limite, min_aprovacao = carregar_exame_inteligente(faixa_aluno)
    
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
        
        # DEBUG VISUAL (APENAS PARA AJUDAR A VER O QUE ESTÁ ACONTECENDO, PODE REMOVER DEPOIS)
        # st.caption(f"Debug: Buscando prova para faixa '{faixa_aluno}'. Questões encontradas: {qtd_questoes}")

        st.markdown("### 📋 Leia atentamente as instruções antes de iniciar")
        
        with st.container(border=True):
            # Layout das Métricas
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd_questoes} Questões**")
            c2.markdown(f"⏱️ Tempo: **{tempo_limite} min**")
            c3.markdown(f"✅ Aprovação: **{min_aprovacao}%**")
            
            st.markdown("---")
            
            # Texto solicitado
            st.markdown(f"""
            * Sua prova contém **{qtd_questoes} Questões**
            * ⏱️ O tempo limite para finalização do exame é de **{tempo_limite} minutos**
            * ✅ Para ser aprovado, você precisa acertar no mínimo **{min_aprovacao}%** do exame
            
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

        # Só habilita o botão se tiver questões
        if qtd_questoes > 0:
            if st.button("✅ Li e Concordo. INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.now()
                st.session_state.questoes_prova = lista_questoes 
                st.session_state.params_prova = {"tempo": tempo_limite, "min_aprovacao": min_aprovacao}
                st.rerun()
        else:
            st.warning(f"⚠️ Nenhuma questão encontrada para a faixa **{faixa_aluno}**. Peça ao professor para cadastrar questões com a faixa correta.")

    # 5. O EXAME EM SI (QUANDO INICIADO)
    else:
        questoes = st.session_state.get('questoes_prova', [])
        params = st.session_state.get('params_prova', {"tempo": 45, "min_aprovacao": 70})
        
        # Lógica do Timer
        agora = datetime.now()
        inicio = st.session_state.get('inicio_prova', agora)
        decorrido = (agora - inicio).total_seconds() / 60
        tempo_restante = params['tempo'] - decorrido
        
        if tempo_restante <= 0:
            st.error("⌛ Tempo esgotado!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            time.sleep(3)
            st.rerun()

        cols = st.columns([3, 1])
        cols[0].info(f"📝 Prova Faixa {faixa_aluno} - **Não mude de aba!**")
        
        mins = int(tempo_restante)
        segs = int((tempo_restante - mins) * 60)
        cols[1].metric("Tempo Restante", f"{mins}:{segs:02d}")
        
        with st.form("form_exame"):
            respostas_usuario = {}
            
            for i, q in enumerate(questoes):
                # Tenta pegar pergunta, se não tiver, tenta 'enunciado'
                txt_pergunta = q.get('pergunta') or q.get('enunciado') or "Questão sem texto"
                st.markdown(f"**{i+1}. {txt_pergunta}**")
                
                if q.get('imagem'): st.image(q['imagem'])
                
                # Garante que opções existam
                opcoes = q.get('opcoes') or q.get('alternativas') or ['Verdadeiro', 'Falso']
                
                respostas_usuario[i] = st.radio("Resposta:", opcoes, key=f"q_{i}", index=None, label_visibility="collapsed")
                st.markdown("---")
            
            enviar = st.form_submit_button("Finalizar Prova", type="primary", use_container_width=True)
            
            if enviar:
                acertos = 0
                for i, q in enumerate(questoes):
                    # Tenta pegar a correta em vários formatos
                    correta = q.get('correta') or q.get('resposta') or q.get('gabarito')
                    
                    # Compara string com string (limpando espaços)
                    if str(respostas_usuario.get(i)).strip().lower() == str(correta).strip().lower():
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
