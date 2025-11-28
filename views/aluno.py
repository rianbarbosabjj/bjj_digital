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

def modo_rola(usuario):
    st.markdown(f"## 🥋 Modo Rola - Treino Livre")
    st.info("Em breve: Aqui você poderá treinar com questões aleatórias sem valer nota.")

def meus_certificados(usuario):
    st.markdown(f"## 🏅 Meus Certificados")
    db = get_db()
    
    if usuario.get('status_exame') == 'aprovado':
        st.success(f"Parabéns! Você foi aprovado no exame de faixa {usuario.get('faixa_atual', 'N/A')}.")
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
        st.warning(msg)
        st.caption("Se precisar de ajuda, contate seu professor.")
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

    # --- PREPARAÇÃO DO CONTEÚDO (QUESTÕES) ---
    todas_questoes = carregar_todas_questoes()
    
    # Lógica de seleção (Exemplo: 10 questões aleatórias)
    if len(todas_questoes) > 0:
        # Se quiser fixo, remova o random.sample
        # lista_questoes = todas_questoes[:10] 
        # Se quiser aleatório a cada prova (mas perigoso se der refresh, melhor salvar na session):
        lista_questoes = todas_questoes[:10] 
    else:
        lista_questoes = []

    qtd_questoes = len(lista_questoes) if lista_questoes else 10 
    tempo_limite = 45 # Minutos

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
            c3.markdown(f"✅ Aprovação: **70%**")
            
            st.markdown("---")
            
            # Texto Personalizado + Regras Técnicas
            st.markdown(f"""
            **ATENÇÃO:**
            * Após clicar em **✅ Li e Concordo. INICIAR EXAME**, não será possível pausar ou interromper o cronômetro.
            * Se o tempo acabar antes de você finalizar, você será considerado **reprovado**.
            * Não é permitido consulta a materiais externos.
            * Esteja em um lugar confortável e silencioso para ajudar na sua concentração.
            
            **REGRAS DE SEGURANÇA DO SISTEMA:**
            * 🚫 **Não saia desta tela:** Se você mudar de aba ou minimizar o navegador, **a prova será bloqueada**.
            * ⏳ **Tentativa Única:** Se reprovar, você deverá aguardar **72 horas** para tentar novamente.
            * 🔌 **Falhas:** Se o computador desligar, você precisará pedir desbloqueio ao professor.

            **Boa prova!** 🥋
            """)

        # Botão de Início
        if st.button("✅ Li e Concordo. INICIAR EXAME", type="primary", use_container_width=True):
            if qtd_questoes == 0:
                st.warning("Erro: Nenhuma questão carregada. Contate o suporte.")
            else:
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.now()
                # Salva as questões na sessão para persistência
                st.session_state.questoes_prova = lista_questoes 
                st.rerun()
    
    # 5. O EXAME EM SI (QUANDO INICIADO)
    else:
        questoes = st.session_state.get('questoes_prova', [])
        
        # Timer
        agora = datetime.now()
        inicio = st.session_state.get('inicio_prova', agora)
        decorrido = (agora - inicio).total_seconds() / 60
        tempo_restante = tempo_limite - decorrido
        
        if tempo_restante <= 0:
            st.error("Tempo esgotado!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            st.rerun()

        # Cabeçalho do Exame
        cols = st.columns([3, 1])
        cols[0].info("📝 Prova em Andamento... **Não mude de aba!**")
        cols[1].metric("Tempo", f"{int(tempo_restante)} min")
        
        with st.form("form_exame"):
            respostas_usuario = {}
            
            for i, q in enumerate(questoes):
                st.markdown(f"**{i+1}. {q.get('pergunta', 'Pergunta sem texto')}**")
                
                opcoes = q.get('opcoes', ['V', 'F'])
                # Opcional: random.shuffle(opcoes) se quiser misturar alternativas
                
                respostas_usuario[i] = st.radio(
                    "Resposta:", 
                    opcoes, 
                    key=f"q_{i}", 
                    index=None, 
                    label_visibility="collapsed"
                )
                st.markdown("---")
            
            enviar = st.form_submit_button("Finalizar Prova", type="primary", use_container_width=True)
            
            if enviar:
                # Verificação se respondeu tudo (Opcional, pode deixar enviar em branco se quiser)
                if any(respostas_usuario.get(i) is None for i in range(len(questoes))):
                    st.warning("Por favor, responda todas as questões antes de finalizar.")
                else:
                    acertos = 0
                    for i, q in enumerate(questoes):
                        if respostas_usuario.get(i) == q.get('correta'):
                            acertos += 1
                    
                    nota_final = (acertos / len(questoes)) * 100
                    aprovado = nota_final >= 70
                    
                    registrar_fim_exame(usuario['id'], aprovado)
                    st.session_state.exame_iniciado = False
                    
                    if aprovado:
                        st.balloons()
                        st.success(f"PARABÉNS! Aprovado com {nota_final:.1f}%!")
                    else:
                        st.error(f"Reprovado. Nota: {nota_final:.1f}%.")
                        st.info("Aguarde 72h para nova tentativa.")
                    
                    time.sleep(4)
                    st.rerun()
