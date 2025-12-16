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
import json
from urllib.parse import quote
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from database import get_db
from firebase_admin import firestore, storage 

# ==============================================================================
# 1. CONFIGURAÇÃO GERAL E CORES
# ==============================================================================
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
    return (0, 0, 0) 

# ==============================================================================
# 2. FUNÇÕES DE UTILIDADE
# ==============================================================================
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
        if r.status_code == 200:
            d = r.json()
            if "erro" not in d:
                return {"logradouro": d.get("logradouro","").upper(), "bairro": d.get("bairro","").upper(), "cidade": d.get("localidade","").upper(), "uf": d.get("uf","").upper()}
    except: pass
    return None

def gerar_senha_temporaria(t=8):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(t))

def enviar_email_recuperacao(dest, senha):
    try:
        s_email = st.secrets.get("EMAIL_SENDER")
        s_pwd = st.secrets.get("EMAIL_PASSWORD")
        if not s_email or not s_pwd: return False
        msg = MIMEMultipart()
        msg['Subject'] = "Recuperação de Senha - BJJ Digital"
        msg['From'] = s_email
        msg['To'] = dest
        corpo = f"<html><body><h2>Recuperação</h2><p>Senha: <b>{senha}</b></p></body></html>"
        msg.attach(MIMEText(corpo, 'html'))
        server = smtplib.SMTP("smtp.zoho.com", 587)
        server.starttls()
        server.login(s_email, s_pwd)
        server.sendmail(s_email, dest, msg.as_string())
        server.quit()
        return True
    except: return False

# ==============================================================================
# 3. MÍDIA E UPLOAD
# ==============================================================================
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

# ==============================================================================
# 4. INTELIGÊNCIA ARTIFICIAL
# ==============================================================================
IA_ATIVADA = False 
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    IA_ATIVADA = True
    @st.cache_resource
    def carregar_modelo_ia():
        return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    def verificar_duplicidade_ia(nova_pergunta, lista_existentes, threshold=0.65):
        try:
            if not lista_existentes: return False, None
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
        except: return False, None
except ImportError:
    IA_ATIVADA = False
    def verificar_duplicidade_ia(n, l, t=0.75): return False, "IA não instalada"

def auditoria_ia_questao(pergunta, alternativas, correta):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return "⚠️ Chave GEMINI_API_KEY não configurada."
    prompt = f"Analise: {pergunta} | {alternativas} | Gabarito: {correta}"
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Erro na IA: {e}"

def auditoria_ia_openai(pergunta, alternativas, correta):
    return "Função desativada temporariamente."

def carregar_todas_questoes(): return []
def salvar_questoes(t, q): pass

# ==============================================================================
# 5. GERAÇÃO DE CERTIFICADOS E QR CODE
# ==============================================================================
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
    pasta = "qrcodes"
    os.makedirs(pasta, exist_ok=True)
    caminho = f"{pasta}/{codigo}.png"
    url = f"https://bjjdigital.com.br/verificar.html?codigo={codigo}"
    if not os.path.exists(caminho):
        img = qrcode.make(url)
        img.save(caminho)
    return caminho

@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor="Professor(a) Responsavel"):
    def limpa(txt):
        if not txt: return ""
        return unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('ASCII')

    pdf = FPDF("L", "mm", "A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    L, H = 297, 210
    
    bg_path = "assets/fundo_certificado_bjj.png" if os.path.exists("assets/fundo_certificado_bjj.png") else None
    if bg_path: pdf.image(bg_path, x=0, y=0, w=L, h=H)
    else: pdf.set_fill_color(252, 252, 252); pdf.rect(0, 0, L, H, "F")

    titulo = "CERTIFICADO DE EXAME TEORICO"
    pdf.set_y(28); pdf.set_font("Helvetica", "B", 32); pdf.set_text_color(200, 180, 100)
    pdf.cell(0, 16, titulo, ln=False, align="C")
    pdf.set_y(26.8); pdf.set_text_color(218, 165, 32)
    pdf.cell(0, 16, titulo, ln=True, align="C")

    pdf.set_y(90); pdf.set_font("Helvetica", "", 14); pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 8, "Certificamos que o aluno(a):", ln=True, align="C")

    nome = limpa(usuario_nome.upper().strip())
    pdf.set_font("Helvetica", "B", 42); pdf.set_text_color(218, 165, 32)
    pdf.cell(0, 20, nome, ln=True, align="C")

    pdf.ln(2); pdf.set_font("Helvetica", "", 14); pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 8, "foi aprovado(a) no exame teórico para a faixa:", ln=True, align="C")

    pdf.ln(4); cor_fx = get_cor_faixa(faixa); pdf.set_font("Helvetica", "B", 38); pdf.set_text_color(*cor_fx)
    pdf.cell(0, 18, limpa(faixa.upper()), ln=True, align="C")

    # Assinatura
    y_base = 151
    pdf.set_xy(0, y_base + 4); pdf.set_font("Helvetica", "I", 20); pdf.set_text_color(218, 165, 32)
    pdf.cell(0, 14, limpa(professor), ln=True, align="C")
    
    x_start = (L/2) - 40
    pdf.set_draw_color(60, 60, 60)
    pdf.line(x_start, pdf.get_y() + 1, x_start + 80, pdf.get_y() + 1)
    
    pdf.ln(4); pdf.set_font("Helvetica", "", 9); pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "Professor(a) Responsavel", align="C")

    # QR Code
    qr_path = gerar_qrcode(codigo)
    if qr_path and os.path.exists(qr_path):
        pdf.image(qr_path, x=L-56, y=y_base, w=32)
        pdf.set_xy(L-64, y_base + 32); pdf.set_font("Courier", "", 8)
        pdf.cell(45, 4, f"Ref: {codigo}", align="C")

    return pdf.output(dest="S").encode("latin-1"), f"Certificado_{nome.split()[0]}.pdf"

# ==============================================================================
# 6. GESTÃO DE EXAMES
# ==============================================================================
def verificar_elegibilidade_exame(dados_usuario):
    status = dados_usuario.get('status_exame', 'pendente')
    if status == 'bloqueado': return False, "Exame bloqueado. Contate o professor."
    if status == 'reprovado':
        try:
            last = dados_usuario.get('data_ultimo_exame')
            if last:
                dt_last = last.replace(tzinfo=None) if hasattr(last, 'date') else datetime.fromisoformat(str(last).replace('Z',''))
                if (datetime.now() - dt_last).days < 3: return False, "Aguarde 3 dias."
        except: pass
    return True, "Autorizado"

def registrar_inicio_exame(uid):
    try: get_db().collection('usuarios').document(uid).update({"status_exame": "em_andamento", "inicio_exame_temp": datetime.now().isoformat(), "status_exame_em_andamento": True})
    except: pass

def registrar_fim_exame(uid, aprovado):
    try:
        stt = "aprovado" if aprovado else "reprovado"
        get_db().collection('usuarios').document(uid).update({"status_exame": stt, "exame_habilitado": False, "data_ultimo_exame": firestore.SERVER_TIMESTAMP, "status_exame_em_andamento": False})
        return True
    except: return False

def bloquear_por_abandono(uid):
    try: get_db().collection('usuarios').document(uid).update({"status_exame": "bloqueado", "exame_habilitado": False, "status_exame_em_andamento": False})
    except: pass

# ==============================================================================
# 7. MOTOR DE CURSOS E AULAS
# ==============================================================================

def listar_todos_usuarios_para_selecao():
    """Retorna lista de usuários. Aceita 'none', 'aluno' e vazio para testes."""
    db = get_db()
    try:
        users = db.collection('usuarios').stream()
        lista = []
        for u in users:
            dados = u.to_dict()
            tipo_usuario = str(dados.get('tipo', '')).lower().strip()
            # Lista ampliada para pegar seus usuários de teste
            tipos_permitidos = ['professor', 'admin', 'mestre', 'instrutor', 'prof', 'teacher', 'none', 'aluno', '', 'null']
            
            if tipo_usuario in tipos_permitidos:
                lista.append({
                    'id': u.id, 
                    'nome': dados.get('nome', 'Sem Nome'), 
                    'email': dados.get('email'), 
                    'cpf': dados.get('cpf', 'N/A')
                })
        lista.sort(key=lambda x: x['nome'])
        return lista
    except Exception as e:
        print(f"Erro ao listar: {e}")
        return []

def criar_curso(professor_id, nome_professor, professor_equipe, titulo, descricao, modalidade, publico, equipe_destino, pago, preco, split_custom, certificado_automatico, duracao_estimada, nivel, editores_ids=[]):
    """Cria um novo curso salvando equipe."""
    db = get_db()
    novo_curso = {
        "professor_id": professor_id, "professor_nome": nome_professor, "professor_equipe": professor_equipe,
        "editores_ids": editores_ids, "titulo": titulo, "descricao": descricao, "modalidade": modalidade,
        "publico": publico, "equipe_destino": equipe_destino, "pago": pago, "preco": float(preco),
        "split_custom": split_custom, "certificado_automatico": certificado_automatico, "ativo": True,
        "criado_em": datetime.now(), "duracao_estimada": duracao_estimada, "nivel": nivel
    }
    _, doc_ref = db.collection('cursos').add(novo_curso)
    return doc_ref.id

def editar_curso(curso_id, dados_atualizados):
    db = get_db()
    try:
        db.collection('cursos').document(curso_id).update(dados_atualizados)
        return True
    except: return False

def excluir_curso(curso_id: str) -> bool:
    db = get_db()
    if not db: return False
    try:
        modulos_ref = db.collection('modulos').where('curso_id', '==', curso_id).stream()
        for mod in modulos_ref:
            aulas_ref = db.collection('aulas').where('modulo_id', '==', mod.id).stream()
            for aula in aulas_ref: db.collection('aulas').document(aula.id).delete()
            db.collection('modulos').document(mod.id).delete()
        inscricoes_ref = db.collection('inscricoes').where('curso_id', '==', curso_id).stream()
        for insc in inscricoes_ref: db.collection('inscricoes').document(insc.id).delete()
        db.collection('cursos').document(curso_id).delete()
        return True
    except: return False

def listar_cursos_do_professor(usuario_id):
    db = get_db()
    lista_cursos = []
    try:
        cursos_dono = db.collection('cursos').where('professor_id', '==', usuario_id).stream()
        for doc in cursos_dono:
            c = doc.to_dict(); c['id'] = doc.id; c['papel'] = 'Dono'
            lista_cursos.append(c)
        cursos_editor = db.collection('cursos').where('editores_ids', 'array_contains', usuario_id).stream()
        ids_existentes = [c['id'] for c in lista_cursos]
        for doc in cursos_editor:
            if doc.id not in ids_existentes:
                c = doc.to_dict(); c['id'] = doc.id; c['papel'] = 'Editor'
                lista_cursos.append(c)
    except: pass
    return lista_cursos

def listar_cursos_disponiveis_para_usuario(usuario):
    db = get_db()
    cursos_ref = db.collection('cursos').where('ativo', '==', True).stream()
    lista_cursos = []
    equipe_usuario = usuario.get('equipe', '').lower().strip()
    for doc in cursos_ref:
        curso = doc.to_dict(); curso['id'] = doc.id
        if curso.get('publico') == 'equipe':
            equipe_curso = str(curso.get('equipe_destino', '')).lower().strip()
            if usuario.get('tipo') != 'admin' and equipe_curso != equipe_usuario: continue 
        lista_cursos.append(curso)
    return lista_cursos

def listar_modulos_e_aulas(curso_id):
    db = get_db()
    try:
        modulos = db.collection('modulos').where('curso_id', '==', curso_id).order_by('ordem').stream()
        estrutura = []
        for m in modulos:
            mod_data = m.to_dict(); mod_data['id'] = m.id
            aulas_ref = db.collection('aulas').where('modulo_id', '==', m.id).stream()
            aulas = [{"id": a.id, **a.to_dict()} for a in aulas_ref]
            aulas.sort(key=lambda x: x.get('titulo', '')) 
            mod_data['aulas'] = aulas
            estrutura.append(mod_data)
        return estrutura
    except: return []

def criar_modulo(curso_id, titulo, descricao, ordem):
    conn = sqlite3.connect('banco.db') # ou sua conexão
    cursor = conn.cursor()
    
    query = "INSERT INTO modulos (curso_id, titulo, descricao, ordem) VALUES (?, ?, ?, ?)"
    cursor.execute(query, (curso_id, titulo, descricao, ordem))
    
    conn.commit()  # <--- ESSE É O COMANDO QUE GRAVA DE VERDADE
    conn.close()

def criar_aula(module_id, titulo, tipo, conteudo, duracao_min):
    db = get_db()
    conteudo_safe = conteudo.copy()
    
    # Tratamento de uploads no backend (simulação para Cloud Storage)
    if 'arquivo_video' in conteudo_safe:
        url = fazer_upload_midia(conteudo_safe['arquivo_video'])
        del conteudo_safe['arquivo_video']
        if url: conteudo_safe['arquivo_video'] = url
        
    if 'arquivo_imagem' in conteudo_safe:
        url = fazer_upload_midia(conteudo_safe['arquivo_imagem'])
        del conteudo_safe['arquivo_imagem']
        if url: conteudo_safe['arquivo_imagem'] = url

    if 'material_apoio' in conteudo_safe:
        url = fazer_upload_midia(conteudo_safe['material_apoio'])
        del conteudo_safe['material_apoio']
        if url: conteudo_safe['material_apoio'] = url

    db.collection('aulas').add({"modulo_id": module_id, "titulo": titulo, "tipo": tipo, "conteudo": conteudo_safe, "duracao_min": duracao_min, "criado_em": datetime.now()})

def obter_inscricao(user_id, curso_id):
    db = get_db()
    docs = db.collection('inscricoes').where('usuario_id', '==', user_id).where('curso_id', '==', curso_id).stream()
    for doc in docs: return doc.to_dict()
    return None

def inscrever_usuario_em_curso(user_id, curso_id):
    if obter_inscricao(user_id, curso_id): return
    get_db().collection('inscricoes').add({"usuario_id": user_id, "curso_id": curso_id, "progresso": 0, "aulas_concluidas": [], "criado_em": datetime.now(), "status": "ativo"})

def verificar_aula_concluida(user_id, aula_id):
    db = get_db()
    inscricoes = db.collection('inscricoes').where('usuario_id', '==', user_id).stream()
    for insc in inscricoes:
        if aula_id in insc.to_dict().get('aulas_concluidas', []): return True
    return False

def marcar_aula_concluida(user_id, aula_id):
    db = get_db()
    aula_ref = db.collection('aulas').document(aula_id).get()
    if not aula_ref.exists: return
    mod_id = aula_ref.to_dict().get('modulo_id')
    curso_id = db.collection('modulos').document(mod_id).get().to_dict().get('curso_id')
    insc_query = db.collection('inscricoes').where('usuario_id', '==', user_id).where('curso_id', '==', curso_id).stream()
    insc_doc = next(insc_query, None)
    if insc_doc:
        concluidas = insc_doc.to_dict().get('aulas_concluidas', [])
        if aula_id not in concluidas:
            concluidas.append(aula_id)
            db.collection('inscricoes').document(insc_doc.id).update({"aulas_concluidas": concluidas, "progresso": 100 if concluidas else 0, "ultimo_acesso": datetime.now()})
