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
    carregar_todas_questoes, # Certifique-se que essa função existe no utils
    normalizar_nome
)

def modo_rola(usuario):
    st.markdown(f"## 🥋 Modo Rola - Treino Livre")
    st.write("Em breve: Aqui você poderá treinar com questões aleatórias sem valer nota.")

def meus_certificados(usuario):
    st.markdown(f"## 🏅 Meus Certificados")
    db = get_db()
    
    # Busca se o aluno foi aprovado
    if usuario.get('status_exame') == 'aprovado':
        st.success(f"Parabéns! Você foi aprovado no exame de faixa {usuario.get('faixa_atual', 'N/A')}.")
        
        # Dados para o certificado
        nome = usuario['nome']
        faixa = usuario.get('faixa_atual', 'Branca')
        codigo = f"CERT-{usuario['id'][:5].upper()}-{datetime.now().year}" # Exemplo de código
        
        # Botão fictício de download (precisaria da função gerar_pdf completa no utils)
        st.info("O download do certificado oficial estará disponível após a graduação presencial.")
    else:
        st.info("Você ainda não possui certificados emitidos nesta plataforma.")

def ranking():
    st.markdown("## 🏆 Ranking da Equipe")
    st.info("O ranking será atualizado conforme os alunos realizarem os exames.")

# =========================================
# LÓGICA DO EXAME DE FAIXA
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    # 1. Busca dados frescos do banco
    db = get_db()
    doc = db.collection('usuarios').document(usuario['id']).get()
    dados_atualizados = doc.to_dict()
    
    # 2. Verifica regras (72h, Bloqueio, etc)
    pode_fazer, msg = verificar_elegibilidade_exame(dados_atualizados)
    
    if not pode_fazer:
        st.error(msg)
        st.info("Entre em contato com seu professor se achar que isso é um erro.")
        return

    # 3. Detector de "Fuga" (Anti-Cheat no carregamento)
    if dados_atualizados.get("status_exame") == "em_andamento":
        bloquear_por_abandono(usuario['id'])
        st.error("🚨 DETECÇÃO DE INFRAÇÃO: Você saiu da página ou recarregou durante o exame.")
        st.warning("Seu exame foi bloqueado. Solicite o desbloqueio ao professor.")
        st.stop()

    # --- JAVASCRIPT ANTI-FRAUDE (Visibilidade da Aba) ---
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

    # --- CARREGAMENTO DAS QUESTÕES (Para mostrar a contagem) ---
    # Aqui simulamos ou carregamos as questões reais
    todas_questoes = carregar_todas_questoes()
    
    # Filtra por faixa (Exemplo simples, adapte conforme sua lógica de JSON)
    faixa_aluno = dados_atualizados.get('faixa_atual', 'Branca')
    # Se não tiver filtro específico no JSON, pegamos uma amostra aleatória
    if len(todas_questoes) > 0:
        lista_questoes = todas_questoes[:10] # Exemplo: Pega 10 questões
    else:
        lista_questoes = []

    qtd_questoes = len(lista_questoes) if lista_questoes else 10 # Fallback visual
    tempo_limite = 45 # Minutos

    # 4. Tela de Início do Exame (Instruções)
    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado = False

    if not st.session_state.exame_iniciado:
        
        # --- BLOCO DE INFORMAÇÕES GERAIS ---
        with st.container(border=True):
            st.markdown("### 📋 Leia atentamente as instruções antes de iniciar")
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd_questoes} Questões**")
            c2.markdown(f"⏱️ Tempo: **{tempo_limite} min**")
            c3.markdown(f"✅ Aprovação: **70%**")
            
            st.markdown("---")
            
            st.markdown("""
            **ATENÇÃO:**
            * Após clicar em **Iniciar Exame**, não será possível pausar o cronômetro.
            * Se o tempo acabar, a prova será encerrada automaticamente.
            * Não é permitido consulta a materiais externos.
            * Esteja em um lugar confortável e silencioso.
            """)

        # --- BLOCO DE REGRAS RIGOROSAS (VERMELHO/AMARELO) ---
        st.error("🚨 **REGRAS DE SEGURANÇA (ANTI-FRAUDE):**")
        st.markdown("""
        1.  **NÃO SAIA DESTA TELA:** Se você mudar de aba, minimizar o navegador ou abrir outro programa, **a prova será bloqueada imediatamente**.
        2.  **Tentativa Única:** Se reprovar, você deverá aguardar **72 horas** para tentar novamente.
        3.  **Problemas Técnicos:** Se o computador desligar ou a internet cair, você precisará pedir desbloqueio ao professor.
        """)
        
        st.write("")
        if st.button("Li e Concordo. INICIAR EXAME AGORA", type="primary", use_container_width=True):
            if qtd_questoes == 0:
                st.warning("Erro: Nenhuma questão encontrada para sua faixa. Contate o suporte.")
            else:
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.now()
                # Salva as questões na sessão para não mudar se der reload acidental (embora o reload bloqueie)
                st.session_state.questoes_prova = lista_questoes 
                st.rerun()
    
    # 5. O Exame em Si
    else:
        questoes = st.session_state.get('questoes_prova', [])
        
        # Barra de Progresso / Timer (Visual)
        agora = datetime.now()
        inicio = st.session_state.get('inicio_prova', agora)
        decorrido = (agora - inicio).total_seconds() / 60
        tempo_restante = tempo_limite - decorrido
        
        if tempo_restante <= 0:
            st.error("Tempo esgotado!")
            registrar_fim_exame(usuario['id'], False) # Reprova por tempo
            st.session_state.exame_iniciado = False
            st.rerun()

        # Mostrador de tempo
        cols = st.columns([3, 1])
        cols[0].info("📝 Prova em Andamento... **Não saia desta tela!**")
        cols[1].metric("Tempo Restante", f"{int(tempo_restante)} min")
        
        with st.form("form_exame"):
            respostas_usuario = {}
            
            for i, q in enumerate(questoes):
                st.markdown(f"**{i+1}. {q.get('pergunta', 'Pergunta sem texto')}**")
                
                # Opções (Embaralhar visualmente se quiser)
                opcoes = q.get('opcoes', ['V', 'F'])
                
                # Chave única para cada radio
                respostas_usuario[i] = st.radio(
                    "Selecione:", 
                    opcoes, 
                    key=f"q_{i}", 
                    index=None, 
                    label_visibility="collapsed"
                )
                st.markdown("---")
            
            enviar = st.form_submit_button("Finalizar Prova", type="primary", use_container_width=True)
            
            if enviar:
                acertos = 0
                for i, q in enumerate(questoes):
                    if respostas_usuario.get(i) == q.get('correta'):
                        acertos += 1
                
                nota_final = (acertos / len(questoes)) * 100
                aprovado = nota_final >= 70
                
                # Salva no banco
                registrar_fim_exame(usuario['id'], aprovado)
                
                # Limpa sessão
                st.session_state.exame_iniciado = False
                
                if aprovado:
                    st.balloons()
                    st.success(f"PARABÉNS! Você foi APROVADO com {nota_final:.1f}% de acertos!")
                    st.info("Seu certificado já está disponível no menu 'Meus Certificados'.")
                else:
                    st.error(f"Reprovado. Sua nota foi {nota_final:.1f}%.")
                    st.warning("Conforme as regras, você precisa aguardar 72h para tentar novamente.")
                
                time.sleep(4)
                st.rerun()
