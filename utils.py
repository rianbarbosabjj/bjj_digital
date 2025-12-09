import os
import re
import requests
import streamlit as st
import smtplib
import secrets
import string
import unicodedata
import random
import uuid
import qrcode
import json
from urllib.parse import quote
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from database import get_db
from firebase_admin import firestore, storage 

# =========================================
# CONFIGURAÇÃO DE CORES DAS FAIXAS (RGB)
# =========================================
CORES_FAIXAS = {
    "CINZA E BRANCA": (150, 150, 150), "CINZA": (128, 128, 128), "CINZA E PRETA": (100, 100, 100), 
    "AMARELA E BRANCA": (240, 230, 140), "AMARELA": (255, 215, 0), "AMARELA E PRETA": (184, 134, 11),
    "LARANJA E BRANCA": (255, 160, 122), "LARANJA": (255, 140, 0), "LARANJA E PRETA": (200, 100, 0),
    "VERDE e BRANCA": (144, 238, 144), "VERDE": (0, 128, 0), "VERDE E PRETA": (0, 100, 0),
    "AZUL": (0, 0, 205), "ROXA": (128, 0, 128), "MARROM": (139, 69, 19), "PRETA": (0, 0, 0)
}

def get_cor_faixa(nome_faixa):
    for chave, cor in CORES_FAIXAS.items():
        if chave in str(nome_faixa).upper():
            return cor
    return (20, 20, 20) # Preto padrão se não achar

# =========================================
# FUNÇÕES DE MÍDIA E UPLOAD
# =========================================
def normalizar_link_video(url):
    if not url: return None
    try:
        if "shorts/" in url:
            base = url.split("shorts/")[1]
            video_id = base.split("?")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        elif "youtu.be/" in url:
            base = url.split("youtu.be/")[1]
            video_id = base.split("?")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        return url
    except: return url

def fazer_upload_midia(arquivo):
    if not arquivo: return None
    try:
        bucket = storage.bucket()
        if not bucket.name:
            bucket_name = st.secrets.get("firebase", {}).get("storage_bucket")
            if not bucket_name: bucket_name = st.secrets.get("storage_bucket")
            if not bucket_name: return None
        
        ext = arquivo.name.split('.')[-1]
        blob_name = f"questoes/{uuid.uuid4()}.{ext}"
        blob = bucket.blob(blob_name)
        
        arquivo.seek(0)
        blob.upload_from_file(arquivo, content_type=arquivo.type)
        
        access_token = str(uuid.uuid4())
        metadata = {"firebaseStorageDownloadTokens": access_token}
        blob.metadata = metadata
        blob.patch()

        blob_path_encoded = quote(blob_name, safe='')
        return f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{blob_path_encoded}?alt=media&token={access_token}"
    except Exception as e:
        st.error(f"Erro Upload: {e}")
        return None

# =========================================
# IA ANTI-DUPLICIDADE (SAFE MODE)
# =========================================
IA_ATIVADA = False 
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    
    IA_ATIVADA = True

    @st.cache_resource
    def carregar_modelo_ia():
        return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    def verificar_duplicidade_ia(nova_pergunta, lista_existentes, threshold=0.75):
        if not lista_existentes: return False, None
        try:
            model = carregar_modelo_ia()
            embedding_novo = model.encode([nova_pergunta])
            textos_existentes = [str(q.get('pergunta', '')) for q in lista_existentes]
            if not textos_existentes: return False, None
            embeddings_existentes = model.encode(textos_existentes)
            scores = cosine_similarity(embedding_novo, embeddings_existentes)[0]
            max_score = np.max(scores)
            idx_max = np.argmax(scores)
            if max_score >= threshold:
                return True, f"{textos_existentes[idx_max]} ({max_score*100:.1f}%)"
            return False, None
        except Exception as e:
            print(f"Erro IA Duplicidade: {e}")
            return False, None

except ImportError:
    IA_ATIVADA = False
    def verificar_duplicidade_ia(n, l, t=0.75): 
        return False, "IA não instalada"

# =========================================
# AUDITORIA DE QUESTÕES (GEMINI - AUTO-DETECT)
# =========================================
def auditoria_ia_questao(pergunta, alternativas, correta):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ Chave GEMINI_API_KEY não configurada."

    prompt_text = f"""
    Atue como um Professor Sênior de Jiu-Jitsu. Analise esta questão:
    Enunciado: {pergunta}
    Alternativas: A) {alternativas.get('A')} | B) {alternativas.get('B')} | C) {alternativas.get('C')} | D) {alternativas.get('D')}
    Gabarito: {correta}
    
    Verifique erros de português, lógica e consistência técnica.
    Responda em 1 parágrafo curto. Inicie com '✅ Aprovada:' se estiver boa.
    """

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        try:
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            modelo_escolhido = modelos[0]
            for m in modelos:
                if 'flash' in m: modelo_escolhido = m; break
        except: modelo_escolhido = 'models/gemini-1.5-flash'

        model = genai.GenerativeModel(modelo_escolhido)
        response = model.generate_content(prompt_text)
        return response.text

    except:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                return f"❌ Erro Gemini: {response.text}"
        except Exception as e:
            return f"❌ Erro Crítico Gemini: {e}"

# =========================================
# AUDITORIA DE QUESTÕES (OPENAI - GPT)
# =========================================
def auditoria_ia_openai(pergunta, alternativas, correta):
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key: return "⚠️ Chave OPENAI_API_KEY ausente."
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = f"Audite: {pergunta}\nOpções: {alternativas}\nCorreta: {correta}"
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user", "content":prompt}])
        return response.choices[0].message.content
    except Exception as e:
        if "quota" in str(e): return "❌ Sem saldo na OpenAI."
        return f"Erro GPT: {e}"

# =========================================
# DEMAIS FUNÇÕES GERAIS
# =========================================
def carregar_todas_questoes(): return []
def salvar_questoes(t, q): pass

def normalizar_nome(nome):
    if not nome: return "sem_nome"
    return "_".join(unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode().split()).lower()

def formatar_e_validar_cpf(cpf):
    if not cpf: return None
    c = re.sub(r'\D', '', str(cpf))
    if len(c) != 11 or c == c[0]*11: return None
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"

def formatar_cep(cep):
    if not cep: return None
    c = ''.join(filter(str.isdigit, cep))
    return c if len(c) == 8 else None

def buscar_cep(cep):
    c = formatar_cep(cep)
    if not c: return None
    try:
        r = requests.get(f"https://viacep.com.br/ws/{c}/json/", timeout=3)
        if r.status_code == 200 and "erro" not in r.json():
            d = r.json()
            return {"logradouro": d.get("logradouro","").upper(), "bairro": d.get("bairro","").upper(), "cidade": d.get("localidade","").upper(), "uf": d.get("uf","").upper()}
    except: pass
    return None

def gerar_senha_temporaria(t=8):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(t))

# --- FUNÇÃO DE EMAIL (CONFIGURADA PARA ZOHO) ---
def enviar_email_recuperacao(dest, senha):
    try:
        s_email = st.secrets.get("EMAIL_SENDER")
        s_pwd = st.secrets.get("EMAIL_PASSWORD")
        
        if not s_email or not s_pwd: 
            st.error("❌ Erro Config: 'EMAIL_SENDER' ou 'EMAIL_PASSWORD' não configurados.")
            return False
            
        msg = MIMEMultipart()
        msg['Subject'] = "Recuperação de Senha - BJJ Digital"
        msg['From'] = s_email
        msg['To'] = dest
        
        corpo = f"""
        <html>
            <body>
                <h2>Recuperação de Acesso</h2>
                <p>Olá,</p>
                <p>Sua nova senha temporária é: <b>{senha}</b></p>
                <p>Recomendamos que você altere sua senha assim que fizer o login.</p>
                <p>Atenciosamente,<br>Equipe BJJ Digital</p>
            </body>
        </html>
        """
        msg.attach(MIMEText(corpo, 'html'))
        
        # --- CONFIGURAÇÃO ZOHO MAIL ---
        server = smtplib.SMTP("smtp.zoho.com", 587)
        server.starttls()
        server.login(s_email, s_pwd)
        server.sendmail(s_email, dest, msg.as_string())
        server.quit()
        return True

    except Exception as e:
        if "Authentication failed" in str(e) or "Username and Password not accepted" in str(e):
             st.error("❌ Erro de Login no Zoho: Verifique se o e-mail está correto e se a senha está certa (se tiver 2FA, use a Senha de Aplicativo).")
        else:
             st.error(f"❌ Erro ao enviar email: {e}")
        return False

def gerar_codigo_verificacao():
    try:
        db = get_db()
        aggregate_query = db.collection('resultados').count()
        snapshots = aggregate_query.get()
        total = int(snapshots[0][0].value)
        return f"BJJDIGITAL-{datetime.now().year}-{total+1:04d}"
    except:
        return f"BJJDIGITAL-{datetime.now().year}-{random.randint(1000,9999)}"

def gerar_qrcode(codigo):
    try:
        os.makedirs("temp", exist_ok=True)
        path = f"temp/qr_{codigo}.png"
        qr = qrcode.QRCode(box_size=10, border=1)
        qr.add_data(f"https://bjjdigital.streamlit.app/?validar={codigo}")
        qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(path)
        return path
    except: return None

# =========================================
# GERAÇÃO DE PDF (CORREÇÃO DE ARQUIVO VAZIO)
# Substitua a função gerar_pdf no utils.py por esta
# =========================================
@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor="Professor(a) Responsável"):
    try:
        def limpa(txt):
            if not txt: return ""
            return unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('ASCII')

        # Setup do PDF
        pdf = FPDF("L", "mm", "A4")
        pdf.add_page()
        
        # Cores
        C_BRANCO = (255, 255, 255)
        C_DOURADO = (218, 165, 32)
        C_PRETO = (0, 0, 0)
        
        # Fundo e Borda
        pdf.set_fill_color(*C_BRANCO)
        pdf.rect(0, 0, 297, 210, "F")
        pdf.set_draw_color(*C_DOURADO)
        pdf.set_line_width(2)
        pdf.rect(10, 10, 277, 190)

        # Logo
        if os.path.exists("assets/logo.png"):
            try: pdf.image("assets/logo.png", x=128, y=20, w=40)
            except: pass

        # Textos Principais (Usando Arial para evitar erros de fonte)
        pdf.set_y(60)
        pdf.set_font("Arial", "B", 24)
        pdf.set_text_color(*C_DOURADO)
        pdf.cell(0, 10, "CERTIFICADO DE APROVACAO", ln=True, align="C")
        
        pdf.ln(10)
        pdf.set_font("Arial", "", 16)
        pdf.set_text_color(*C_PRETO)
        pdf.cell(0, 10, "Certificamos que:", ln=True, align="C")
        
        # Nome
        nome = limpa(usuario_nome.upper())
        pdf.ln(5)
        pdf.set_font("Arial", "B", 30)
        pdf.cell(0, 15, nome, ln=True, align="C")
        
        # Faixa
        pdf.ln(10)
        pdf.set_font("Arial", "", 16)
        pdf.cell(0, 10, "Conquistou a graduacao de:", ln=True, align="C")
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 36)
        cor_fx = get_cor_faixa(faixa)
        pdf.set_text_color(*cor_fx)
        pdf.cell(0, 20, limpa(faixa.upper()), ln=True, align="C")
        
        # Rodapé
        pdf.set_y(160)
        pdf.set_font("Courier", "", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, f"Codigo: {codigo}", ln=True, align="C")
        pdf.cell(0, 5, f"Data: {datetime.now().strftime('%d/%m/%Y')} | Nota: {pontuacao:.1f}%", ln=True, align="C")

        # QR Code
        qr_path = gerar_qrcode(codigo)
        if qr_path and os.path.exists(qr_path):
            try: pdf.image(qr_path, x=250, y=160, w=30)
            except: pass

        # === SAÍDA SEGURA DO ARQUIVO ===
        try:
            # 1. Tenta gerar a saída
            buffer = pdf.output() 
            
            # 2. Se saiu vazio (None ou string vazia), força o modo string (dest='S')
            # Isso é comum em versões antigas do FPDF
            if not buffer:
                buffer = pdf.output(dest='S')

            # 3. Verificação Final: Se ainda estiver vazio, é erro real
            if not buffer:
                return None, "Erro: O PDF foi gerado com 0 bytes."

            # 4. Tratamento de Tipos (Bytes vs String)
            nome_arq = f"Certificado_{nome.split()[0]}.pdf"
            
            if isinstance(buffer, (bytes, bytearray)):
                return bytes(buffer), nome_arq
                
            if isinstance(buffer, str):
                return buffer.encode('latin-1'), nome_arq
                
            return None, "Erro: Tipo de retorno do PDF desconhecido."

        except Exception as e_out:
             # Fallback final se o output der erro de assinatura
             try:
                 return pdf.output(dest='S').encode('latin-1'), f"Certificado_{nome.split()[0]}.pdf"
             except Exception as e_final:
                 return None, f"Falha fatal na renderização: {str(e_final)}"

    except Exception as e:
        return None, f"Erro interno: {str(e)}"
# =========================================
# FUNÇÕES DE LÓGICA DE EXAME E BANCO DE DADOS
# =========================================
def verificar_elegibilidade_exame(dados_usuario):
    """
    Verifica se o aluno pode fazer a prova.
    """
    status = dados_usuario.get('status_exame', 'pendente')
    
    # 1. Bloqueio por Abandono ou Professor
    if status == 'bloqueado':
        return False, "Seu exame está bloqueado. Contate o professor."

    # 2. Regra de 3 dias para Reprovados
    if status == 'reprovado':
        try:
            ultimo_exame = dados_usuario.get('data_ultimo_exame')
            if ultimo_exame:
                if hasattr(ultimo_exame, 'date'): 
                    dt_last = ultimo_exame.replace(tzinfo=None)
                else: 
                    dt_last = datetime.fromisoformat(str(ultimo_exame).replace('Z',''))
                
                diferenca = datetime.now() - dt_last
                if diferenca.days < 3:
                    return False, f"Você precisa aguardar {3 - diferenca.days} dias para tentar novamente."
        except:
            pass 

    return True, "Autorizado"

def registrar_inicio_exame(uid):
    """Marca no banco que o aluno começou a prova."""
    try:
        db = get_db()
        db.collection('usuarios').document(uid).update({
            "status_exame": "em_andamento",
            "inicio_exame_temp": datetime.now().isoformat(),
            "status_exame_em_andamento": True
        })
    except Exception as e:
        print(f"Erro ao iniciar exame: {e}")

def registrar_fim_exame(uid, aprovado):
    """
    ATUALIZA O STATUS FINAL DO ALUNO.
    """
    try:
        db = get_db()
        novo_status = "aprovado" if aprovado else "reprovado"
        
        # Atualiza o documento do USUÁRIO (Onde o Admin/Professor lê o status)
        db.collection('usuarios').document(uid).update({
            "status_exame": novo_status,
            "exame_habilitado": False,
            "data_ultimo_exame": firestore.SERVER_TIMESTAMP,
            "status_exame_em_andamento": False
        })
        return True
    except Exception as e:
        print(f"Erro ao finalizar exame: {e}")
        return False

def bloquear_por_abandono(uid):
    """Bloqueia o aluno se ele tentar atualizar a página ou sair."""
    try:
        db = get_db()
        db.collection('usuarios').document(uid).update({
            "status_exame": "bloqueado",
            "exame_habilitado": False,
            "status_exame_em_andamento": False
        })
    except Exception as e:
        print(f"Erro ao bloquear aluno: {e}")
