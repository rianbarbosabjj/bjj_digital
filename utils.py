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
import pandas as pd
import time  # <--- ADICIONADO: Essencial para upload de fotos/vídeos
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
# 2. FUNÇÕES DE UTILIDADE (CPF, CEP, LOGIN)
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

def buscar_usuario_por_cpf(cpf):
    if not cpf: return None
    cpf_limpo = re.sub(r'\D', '', str(cpf))
    db = get_db()
    try:
        docs = db.collection('usuarios').where('cpf', '==', cpf).stream()
        for doc in docs:
            d = doc.to_dict(); d['id'] = doc.id; return d
        docs_raw = db.collection('usuarios').stream()
        for doc in docs_raw:
            u_data = doc.to_dict()
            if re.sub(r'\D', '', str(u_data.get('cpf',''))) == cpf_limpo and cpf_limpo:
                u_data['id'] = doc.id; return u_data
        return None
    except: return None

def listar_todos_usuarios_para_selecao():
    db = get_db()
    try:
        users = db.collection('usuarios').stream()
        lista = []
        for u in users:
            dados = u.to_dict()
            lista.append({'id': u.id, 'nome': dados.get('nome', 'Sem Nome'), 'email': dados.get('email'), 'cpf': dados.get('cpf')})
        lista.sort(key=lambda x: x['nome'])
        return lista
    except: return []

def obter_nomes_usuarios(lista_ids):
    db = get_db()
    res = []
    if not lista_ids: return []
    for uid in lista_ids:
        try:
            doc = db.collection('usuarios').document(uid).get()
            if doc.exists:
                d = doc.to_dict()
                res.append({'id': uid, 'nome': d.get('nome','-'), 'cpf': d.get('cpf','-')})
        except: pass
    return res

# ==============================================================================
# 3. MÍDIA E UPLOAD (CORRIGIDO)
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
    """Função legada para upload genérico."""
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
        
        blob.make_public()
        return blob.public_url
    except Exception as e:
        st.error(f"Erro Upload: {e}")
        return None

def upload_arquivo_simples(arquivo, caminho_destino):
    """Função otimizada para aulas, aceitando caminho customizado."""
    if not arquivo: return None
    try:
        bucket = storage.bucket()
        blob = bucket.blob(caminho_destino)
        # Importante: seek(0) garante leitura do inicio
        arquivo.seek(0)
        blob.upload_from_file(arquivo, content_type=arquivo.type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"Erro upload simples: {e}")
        return None

# ==============================================================================
# 4. GERAÇÃO DE CERTIFICADOS E QR CODE (MANTIDO DO SEU CÓDIGO)
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
        try:
            import qrcode
            img = qrcode.make(url)
            img.save(caminho)
        except ImportError: pass
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

    y_base = 151
    pdf.set_xy(0, y_base + 4); pdf.set_font("Helvetica", "I", 20); pdf.set_text_color(218, 165, 32)
    pdf.cell(0, 14, limpa(professor), ln=True, align="C")
    
    x_start = (L/2) - 40
    pdf.set_draw_color(60, 60, 60)
    pdf.line(x_start, pdf.get_y() + 1, x_start + 80, pdf.get_y() + 1)
    
    pdf.ln(4); pdf.set_font("Helvetica", "", 9); pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "Professor(a) Responsavel", align="C")

    qr_path = gerar_qrcode(codigo)
    if qr_path and os.path.exists(qr_path):
        pdf.image(qr_path, x=L-56, y=y_base, w=32)
        pdf.set_xy(L-64, y_base + 32); pdf.set_font("Courier", "", 8)
        pdf.cell(45, 4, f"Ref: {codigo}", align="C")

    return pdf.output(dest="S").encode("latin-1"), f"Certificado_{nome.split()[0]}.pdf"

# ==============================================================================
# 5. MOTOR DE CURSOS E AULAS (AQUI ESTÃO AS CORREÇÕES CRÍTICAS)
# ==============================================================================

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
            excluir_modulo(mod.id)
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
        modulos_ref = db.collection('modulos').where('curso_id', '==', str(curso_id)).stream()
        estrutura = []

        for m in modulos_ref:
            mod_data = m.to_dict()
            mod_data['id'] = m.id

            # 🔁 NOVO: leitura unificada
            aulas = obter_aulas_unificadas_por_modulo(m.id)

            mod_data['aulas'] = aulas
            estrutura.append(mod_data)

        estrutura.sort(key=lambda x: int(x.get('ordem', 0) or 0))
        return estrutura
    except Exception as e:
        print(f"[LISTAR_MODULOS] erro: {e}")
        return []


def criar_modulo(curso_id, titulo, descricao, ordem):
    db = get_db()
    try:
        dados_modulo = {
            "curso_id": str(curso_id),
            "titulo": str(titulo),
            "descricao": str(descricao),
            "ordem": int(ordem),
            "criado_em": datetime.now(),
            "aulas": [] # Array inicializado para aulas mistas
        }
        _, doc_ref = db.collection('modulos').add(dados_modulo)
        return doc_ref.id
    except Exception as e:
        print(f"Erro ao criar módulo: {e}")
        raise e

def criar_aula(module_id, titulo, tipo, conteudo, duracao_min):
    """Cria aula simples (legado)."""
    db = get_db()
    conteudo_safe = conteudo.copy()
    
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

def criar_aula_mista(modulo_id, titulo, lista_blocos, duracao_min):
    """
    Cria uma aula FLEXÍVEL (Mista) salvando dentro do documento do módulo.
    CORRIGIDO: Usa time.time() e datetime.now() corretamente.
    """
    db = get_db()
    blocos_processados = []
    
    for i, bloco in enumerate(lista_blocos):
        novo_bloco = {"tipo": bloco['tipo']}
        
        if bloco['tipo'] == 'texto':
            novo_bloco['conteudo'] = bloco.get('conteudo', '')
            
        elif bloco['tipo'] in ['imagem', 'video']:
            arquivo = bloco.get('arquivo')
            if arquivo:
                ext = arquivo.name.split('.')[-1]
                # Nome único usando time.time() (agora importado!)
                nome_arq = f"aulas_mistas/{modulo_id}_{int(time.time())}_{i}.{ext}"
                url = upload_arquivo_simples(arquivo, nome_arq)
                novo_bloco['url'] = url
            else:
                novo_bloco['url'] = bloco.get('url_link', '')
                
        blocos_processados.append(novo_bloco)

    dados_aula = {
        "titulo": titulo,
        "tipo": "misto",
        "conteudo": { "blocos": blocos_processados },
        "duracao_min": duracao_min,
        "data_criacao": datetime.now() # Usa datetime.now() para evitar erro Sentinel
    }
    
    mod_ref = db.collection('modulos').document(modulo_id)
    mod_ref.update({
        "aulas": firestore.ArrayUnion([dados_aula])
    })
    return True

def excluir_modulo(modulo_id):
    db = get_db()
    try:
        aulas_ref = db.collection('aulas').where('modulo_id', '==', modulo_id).stream()
        for aula in aulas_ref: db.collection('aulas').document(aula.id).delete()
        db.collection('modulos').document(modulo_id).delete()
        return True
    except: return False

# ==============================================================================
# 6. GESTÃO DE ALUNOS (Cursos, Inscrições)
# ==============================================================================
def listar_cursos_inscritos(usuario_id):
    db = get_db()
    lista_final = []
    try:
        inscricoes = db.collection('inscricoes').where('usuario_id', '==', str(usuario_id)).stream()
        for insc in inscricoes:
            dados_insc = insc.to_dict()
            curso_id = dados_insc.get('curso_id')
            if curso_id:
                curso_doc = db.collection('cursos').document(curso_id).get()
                if curso_doc.exists:
                    dados_curso = curso_doc.to_dict(); dados_curso['id'] = curso_id
                    dados_curso['progresso'] = dados_insc.get('progresso', 0)
                    dados_curso['inscricao_id'] = insc.id
                    lista_final.append(dados_curso)
    except: pass
    return lista_final

def listar_cursos_disponiveis_para_aluno(usuario):
    db = get_db()
    cursos_disponiveis = []
    try:
        inscricoes = db.collection('inscricoes').where('usuario_id', '==', str(usuario['id'])).stream()
        ids_ja_inscritos = [i.to_dict().get('curso_id') for i in inscricoes]
        cursos_ref = db.collection('cursos').where('ativo', '==', True).stream()
        equipe_aluno = str(usuario.get('equipe', '')).strip().lower()
        
        for c in cursos_ref:
            dados = c.to_dict(); dados['id'] = c.id
            if dados['id'] in ids_ja_inscritos: continue
            
            publico = dados.get('publico', 'todos')
            if publico == 'equipe':
                equipe_curso = str(dados.get('equipe_destino', '')).strip().lower()
                if equipe_curso != equipe_aluno: continue
            
            cursos_disponiveis.append(dados)
    except: pass
    return cursos_disponiveis

def inscrever_usuario_em_curso(usuario_id, curso_id):
    db = get_db()
    try:
        db.collection('inscricoes').add({
            "usuario_id": str(usuario_id),
            "curso_id": str(curso_id),
            "data_inscricao": firestore.SERVER_TIMESTAMP,
            "progresso": 0,
            "status": "ativo",
            "aulas_concluidas": []
        })
        return True
    except: return False

def listar_alunos_inscritos(curso_id):
    db = get_db()
    try:
        inscricoes = db.collection('inscricoes').where('curso_id', '==', str(curso_id)).stream()
        lista = []
        for i in inscricoes:
            d = i.to_dict()
            uid = d.get('usuario_id')
            user = db.collection('usuarios').document(uid).get()
            if user.exists:
                ud = user.to_dict()
                lista.append({
                    "Nome": ud.get('nome','-').upper(),
                    "Email": ud.get('email','-'),
                    "Progresso": f"{d.get('progresso',0)}%"
                })
        return lista
    except: return []

# ==============================================================================
# 7. FUNÇÕES DE EXAME E AUDITORIA (MANTIDAS)
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

def carregar_todas_questoes(): return [] # Placeholder se necessário
# ==============================================================================
# 5B. AULAS V2 (BASE PROFISSIONAL - SEM QUEBRAR LEGADO)
# ------------------------------------------------------------------------------
# Objetivo: criar um padrão definitivo de aulas, em coleção separada (aulas_v2),
# sem mexer na UI atual. A unificação de leitura vem na Fase 2.
# ==============================================================================

AULAS_V2_COLLECTION = "aulas_v2"
AULA_SCHEMA_VERSION = 2

def _now_ts():
    # Timestamp consistente (pode trocar por firestore.SERVER_TIMESTAMP em updates)
    return datetime.now()

def _validar_tipo_aula(tipo: str) -> str:
    t = str(tipo or "").lower().strip()
    if t not in ["misto", "video", "imagem", "texto"]:
        return "texto"
    return t

def _normalizar_bloco_v2(bloco: dict, modulo_id: str, idx: int):
    """
    Converte blocos recebidos da UI (arquivos/link/texto) para o padrão V2.
    Aceita:
      - {"tipo":"texto","conteudo":"..."}
      - {"tipo":"imagem","arquivo": <UploadedFile>} ou {"tipo":"imagem","url_link":"..."}
      - {"tipo":"video","arquivo": <UploadedFile>} ou {"tipo":"video","url_link":"..."}
    Retorna bloco V2:
      - texto:  {"tipo":"texto","conteudo":"..."}
      - imagem: {"tipo":"imagem","url":"...","nome":"...","origem":"upload|link"}
      - video:  {"tipo":"video","url":"...","nome":"...","origem":"upload|link"}
    """
    if not isinstance(bloco, dict):
        return None

    tipo = str(bloco.get("tipo", "")).lower().strip()

    if tipo == "texto":
        return {
            "tipo": "texto",
            "conteudo": str(bloco.get("conteudo", "") or "")
        }

    if tipo in ["imagem", "video"]:
        arquivo = bloco.get("arquivo")
        url_link = bloco.get("url_link") or bloco.get("url")  # compat

        # Upload (preferência se veio arquivo)
        if arquivo:
            try:
                ext = arquivo.name.split(".")[-1]
            except Exception:
                ext = "bin"

            nome_arq = f"aulas_v2/{modulo_id}_{int(time.time())}_{idx}.{ext}"
            url = upload_arquivo_simples(arquivo, nome_arq)

            return {
                "tipo": tipo,
                "url": url,
                "nome": getattr(arquivo, "name", "") or "",
                "origem": "upload"
            }

        # Link
        if url_link:
            url_norm = str(url_link).strip()
            if tipo == "video":
                url_norm = normalizar_link_video(url_norm)

            return {
                "tipo": tipo,
                "url": url_norm,
                "nome": "",
                "origem": "link"
            }

        # Se não veio nada útil, ignora
        return None

    # Tipo desconhecido -> ignora
    return None


def obter_proxima_ordem_aula_v2(modulo_id: str) -> int:
    """
    Retorna a próxima ordem sugerida para aula no módulo.
    Seguro (não depende de agregações).
    """
    db = get_db()
    try:
        q = (db.collection(AULAS_V2_COLLECTION)
               .where("modulo_id", "==", str(modulo_id))
               .where("ativo", "==", True)
               .stream())
        ordens = []
        for d in q:
            data = d.to_dict() or {}
            ordens.append(int(data.get("ordem", 0) or 0))
        return (max(ordens) + 1) if ordens else 1
    except:
        return 1


def criar_aula_v2(
    curso_id: str,
    modulo_id: str,
    titulo: str,
    tipo: str,
    blocos: list,
    duracao_min: int,
    ordem: int = None,
    autor_id: str = None,
    autor_nome: str = None
) -> str:
    """
    Cria aula no padrão profissional (V2), em coleção separada: aulas_v2.

    - Não mexe no legado.
    - Já suporta uploads e links nos blocos.
    - Retorna o ID do documento criado.
    """
    db = get_db()

    tipo_ok = _validar_tipo_aula(tipo)
    titulo_ok = str(titulo or "").strip()
    if not titulo_ok:
        raise ValueError("Título da aula é obrigatório.")

    dur = int(duracao_min or 0)
    if dur < 1:
        dur = 1

    if ordem is None:
        ordem = obter_proxima_ordem_aula_v2(modulo_id)

    blocos_processados = []
    for idx, b in enumerate(blocos or []):
        nb = _normalizar_bloco_v2(b, str(modulo_id), idx)
        if nb:
            # Evita bloco texto vazio demais
            if nb["tipo"] == "texto" and not str(nb.get("conteudo", "")).strip():
                continue
            blocos_processados.append(nb)

    # Se tipo não for misto, ainda assim guardamos em "blocos"
    # Ex: texto vira 1 bloco texto, video vira 1 bloco video etc.
    # Isso padroniza o player depois.
    if tipo_ok != "misto" and not blocos_processados:
        if tipo_ok == "texto":
            blocos_processados = [{"tipo": "texto", "conteudo": ""}]
        elif tipo_ok in ["imagem", "video"]:
            blocos_processados = [{"tipo": tipo_ok, "url": "", "nome": "", "origem": "link"}]

    doc = {
        "schema_version": AULA_SCHEMA_VERSION,
        "curso_id": str(curso_id),
        "modulo_id": str(modulo_id),
        "titulo": titulo_ok,
        "tipo": tipo_ok,
        "blocos": blocos_processados,
        "duracao_min": dur,
        "ordem": int(ordem),
        "ativo": True,
        "autor_id": str(autor_id) if autor_id else "",
        "autor_nome": str(autor_nome) if autor_nome else "",
        "criado_em": firestore.SERVER_TIMESTAMP,
        "atualizado_em": firestore.SERVER_TIMESTAMP,
    }

    _, ref = db.collection(AULAS_V2_COLLECTION).add(doc)
    return ref.id


def listar_aulas_v2_por_modulo(modulo_id: str, incluir_inativas: bool = False) -> list:
    """
    Lista aulas V2 do módulo, ordenadas por 'ordem'.
    Não impacta legado.
    """
    db = get_db()
    try:
        q = db.collection(AULAS_V2_COLLECTION).where("modulo_id", "==", str(modulo_id))
        if not incluir_inativas:
            q = q.where("ativo", "==", True)

        docs = list(q.stream())
        aulas = []
        for d in docs:
            data = d.to_dict() or {}
            data["id"] = d.id
            aulas.append(data)

        aulas.sort(key=lambda x: int(x.get("ordem", 0) or 0))
        return aulas
    except:
        return []


def editar_aula_v2(aula_id: str, dados_atualizados: dict) -> bool:
    """
    Edita uma aula V2 (campos permitidos).
    Segurança: atualiza 'atualizado_em' automaticamente.
    """
    db = get_db()
    if not aula_id:
        return False

    allowed = {"titulo", "tipo", "blocos", "duracao_min", "ordem", "ativo"}
    payload = {}

    for k, v in (dados_atualizados or {}).items():
        if k in allowed:
            payload[k] = v

    if not payload:
        return False

    # Normalizações seguras
    if "tipo" in payload:
        payload["tipo"] = _validar_tipo_aula(payload["tipo"])

    if "titulo" in payload:
        payload["titulo"] = str(payload["titulo"] or "").strip()

    if "duracao_min" in payload:
        try:
            payload["duracao_min"] = int(payload["duracao_min"] or 1)
        except:
            payload["duracao_min"] = 1

    if "ordem" in payload:
        try:
            payload["ordem"] = int(payload["ordem"] or 1)
        except:
            payload["ordem"] = 1

    payload["atualizado_em"] = firestore.SERVER_TIMESTAMP

    try:
        db.collection(AULAS_V2_COLLECTION).document(str(aula_id)).update(payload)
        return True
    except:
        return False


def desativar_aula_v2(aula_id: str) -> bool:
    """
    Soft delete (profissional): não apaga, só desativa.
    """
    return editar_aula_v2(aula_id, {"ativo": False})

# ==============================================================================
# 5C. LEITURA UNIFICADA DE AULAS (V2 -> LEGADO)
# ==============================================================================

def obter_aulas_unificadas_por_modulo(modulo_id: str) -> list:
    """
    Retorna aulas do módulo priorizando AULAS_V2.
    Se não houver nenhuma V2, cai para o legado.
    Sempre retorna no formato esperado pela UI atual.
    """
    # 1. Tenta V2
    aulas_v2 = listar_aulas_v2_por_modulo(modulo_id)

    if aulas_v2:
        aulas_norm = []
        for a in aulas_v2:
            aulas_norm.append({
                "id": a.get("id"),
                "titulo": a.get("titulo"),
                "tipo": a.get("tipo"),
                "duracao_min": a.get("duracao_min", 0),
                # UI atual espera 'conteudo'
                "conteudo": {
                    "blocos": a.get("blocos", [])
                }
            })
        return aulas_norm

    # 2. Fallback — legado (coleção aulas)
    db = get_db()
    try:
        aulas_legacy = db.collection("aulas").where("modulo_id", "==", modulo_id).stream()
        return [{"id": d.id, **d.to_dict()} for d in aulas_legacy]
    except:
        return []

