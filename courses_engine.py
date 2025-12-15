"""
courses_engine.py
Motor de lógica para gerenciamento de cursos, módulos e aulas do BJJ Digital.
"""

import streamlit as st
import os
from datetime import datetime
from database import get_db
import uuid

# ==============================================================================
# FUNÇÕES DE CURSO (CRUD)
# ==============================================================================

def criar_curso(professor_id, nome_professor, titulo, descricao, modalidade, publico, equipe_destino, pago, preco, split_custom, certificado_automatico):
    """Cria um novo curso no banco de dados."""
    db = get_db()
    
    novo_curso = {
        "professor_id": professor_id,
        "professor_nome": nome_professor,
        "titulo": titulo,
        "descricao": descricao,
        "modalidade": modalidade,
        "publico": publico,
        "equipe_destino": equipe_destino,
        "pago": pago,
        "preco": float(preco),
        "split_custom": split_custom,
        "certificado_automatico": certificado_automatico,
        "ativo": True,
        "criado_em": datetime.now(),
        "duracao_estimada": "A definir",
        "nivel": "Todos os Níveis"
    }
    
    _, doc_ref = db.collection('cursos').add(novo_curso)
    return doc_ref.id

def editar_curso(curso_id, dados_atualizados):
    """Atualiza os dados de um curso existente."""
    db = get_db()
    try:
        db.collection('cursos').document(curso_id).update(dados_atualizados)
        return True
    except Exception as e:
        print(f"Erro ao editar curso: {e}")
        return False

def excluir_curso(curso_id: str) -> bool:
    """
    Exclui um curso e todos os seus dados associados (módulos, aulas, inscrições).
    """
    db = get_db()
    if not db:
        print("Erro: Sem conexão com banco de dados.")
        return False

    try:
        print(f"--- Iniciando exclusão do curso ID: {curso_id} ---")

        # 1. Excluir Aulas e Módulos
        modulos_ref = db.collection('modulos').where('curso_id', '==', curso_id).stream()
        
        for mod in modulos_ref:
            mod_id = mod.id
            
            # Deletar aulas associadas ao módulo
            aulas_ref = db.collection('aulas').where('modulo_id', '==', mod_id).stream()
            for aula in aulas_ref:
                db.collection('aulas').document(aula.id).delete()
            
            # Deleta o módulo
            db.collection('modulos').document(mod_id).delete()

        # 2. Excluir Inscrições
        inscricoes_ref = db.collection('inscricoes').where('curso_id', '==', curso_id).stream()
        for insc in inscricoes_ref:
            db.collection('inscricoes').document(insc.id).delete()

        # 3. Excluir o curso
        db.collection('cursos').document(curso_id).delete()
        
        return True

    except Exception as e:
        print(f"❌ ERRO CRÍTICO ao excluir curso: {e}")
        return False

def listar_cursos_do_professor(professor_id):
    """Lista todos os cursos criados por um professor específico."""
    db = get_db()
    cursos_ref = db.collection('cursos').where('professor_id', '==', professor_id).stream()
    
    lista_cursos = []
    for doc in cursos_ref:
        curso = doc.to_dict()
        curso['id'] = doc.id
        lista_cursos.append(curso)
        
    return lista_cursos

def listar_cursos_disponiveis_para_usuario(usuario):
    """
    Lista cursos disponíveis para o aluno (filtra por equipe se necessário).
    """
    db = get_db()
    cursos_ref = db.collection('cursos').where('ativo', '==', True).stream()
    
    lista_cursos = []
    equipe_usuario = usuario.get('equipe', '').lower().strip()
    
    for doc in cursos_ref:
        curso = doc.to_dict()
        curso['id'] = doc.id
        
        # Filtro de visibilidade
        if curso.get('publico') == 'equipe':
            equipe_curso = str(curso.get('equipe_destino', '')).lower().strip()
            if equipe_curso != equipe_usuario and usuario.get('tipo') != 'admin':
                continue # Pula este curso se não for da equipe do aluno
                
        lista_cursos.append(curso)
        
    return lista_cursos

# ==============================================================================
# FUNÇÕES DE MÓDULOS E AULAS
# ==============================================================================

def listar_modulos_do_curso(curso_id):
    """Retorna apenas a lista de módulos (sem as aulas detalhadas)."""
    db = get_db()
    try:
        modulos = db.collection('modulos')\
            .where('curso_id', '==', curso_id)\
            .order_by('ordem')\
            .stream()
        
        return [{"id": m.id, **m.to_dict()} for m in modulos]
    except Exception as e:
        print(f"Erro ao listar módulos: {e}")
        return []

def listar_modulos_e_aulas(curso_id):
    """
    Retorna estrutura completa: Módulos com suas respectivas Aulas aninhadas.
    """
    db = get_db()
    
    # 1. Buscar Módulos
    modulos = listar_modulos_do_curso(curso_id)
    
    # 2. Buscar Aulas para cada módulo
    estrutura_completa = []
    for mod in modulos:
        aulas_ref = db.collection('aulas')\
            .where('modulo_id', '==', mod['id'])\
            .order_by('titulo')\
            .stream() # Idealmente teria um campo 'ordem' nas aulas também
            
        aulas = [{"id": a.id, **a.to_dict()} for a in aulas_ref]
        
        mod['aulas'] = aulas
        estrutura_completa.append(mod)
        
    return estrutura_completa

def criar_modulo(curso_id, titulo, descricao, ordem):
    """Cria um novo módulo dentro de um curso."""
    db = get_db()
    db.collection('modulos').add({
        "curso_id": curso_id,
        "titulo": titulo,
        "descricao": descricao,
        "ordem": ordem,
        "criado_em": datetime.now()
    })

def criar_aula(module_id, titulo, tipo, conteudo, duracao_min):
    """
    Cria uma nova aula. Lida com salvamento de arquivos (Uploads).
    """
    db = get_db()
    
    # === LÓGICA DE UPLOAD DE ARQUIVOS ===
    # Se houver arquivos reais (UploadedFile do Streamlit), precisamos salvar.
    # Aqui estamos salvando em disco local por simplicidade.
    # Para produção, substitua por upload para Firebase Storage ou S3.
    
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    # 1. Processar Vídeo Upload
    if tipo == 'video' and conteudo.get('tipo_video') == 'upload':
        arquivo = conteudo.get('arquivo_video')
        if arquivo:
            # Gera nome único para não sobrescrever
            ext = arquivo.name.split('.')[-1]
            nome_final = f"vid_{uuid.uuid4()}.{ext}"
            caminho_salvo = os.path.join(upload_dir, nome_final)
            
            with open(caminho_salvo, "wb") as f:
                f.write(arquivo.getbuffer())
            
            # Atualiza o dicionário para salvar apenas o caminho/URL no banco
            conteudo['arquivo_video'] = caminho_salvo # ou URL pública
            # Remove o objeto binário pesado antes de salvar no banco
            if 'arquivo_video' in conteudo and not isinstance(conteudo['arquivo_video'], str):
                 del conteudo['arquivo_video'] 
            conteudo['arquivo_video'] = caminho_salvo # Recoloca como string

    # 2. Processar PDF Upload
    if 'material_apoio' in conteudo:
        arquivo_pdf = conteudo.get('material_apoio')
        if arquivo_pdf:
            ext = arquivo_pdf.name.split('.')[-1]
            nome_final = f"pdf_{uuid.uuid4()}.{ext}"
            caminho_salvo = os.path.join(upload_dir, nome_final)
            
            with open(caminho_salvo, "wb") as f:
                f.write(arquivo_pdf.getbuffer())
            
            # Atualiza dicionário
            conteudo['material_apoio'] = caminho_salvo # ou URL pública
            
    # === SALVAR NO BANCO ===
    db.collection('aulas').add({
        "modulo_id": module_id,
        "titulo": titulo,
        "tipo": tipo,
        "conteudo": conteudo, # Agora contém caminhos/strings, não bytes
        "duracao_min": duracao_min,
        "criado_em": datetime.now()
    })

# ==============================================================================
# FUNÇÕES DE INSCRIÇÃO E PROGRESSO
# ==============================================================================

def obter_inscricao(user_id, curso_id):
    """Verifica se existe inscrição e retorna os dados."""
    db = get_db()
    docs = db.collection('inscricoes')\
        .where('usuario_id', '==', user_id)\
        .where('curso_id', '==', curso_id)\
        .stream()
        
    for doc in docs:
        return doc.to_dict()
    return None

def inscrever_usuario_em_curso(user_id, curso_id):
    """Cria o registro de inscrição inicial."""
    db = get_db()
    
    # Verifica se já existe para não duplicar
    if obter_inscricao(user_id, curso_id):
        return
        
    db.collection('inscricoes').add({
        "usuario_id": user_id,
        "curso_id": curso_id,
        "progresso": 0,
        "aulas_concluidas": [],
        "criado_em": datetime.now(),
        "status": "ativo"
    })

def verificar_aula_concluida(user_id, aula_id):
    """Checa se o ID da aula está na lista de concluídas do usuário."""
    # Como a estrutura de inscrição pode variar, vamos buscar pelo documento de inscrição
    # que contenha essa aula na lista, ou buscar pelo documento de progresso separado.
    # Assumindo estrutura simples dentro de 'inscricoes':
    
    db = get_db()
    # Busca todas inscrições do usuário (pode otimizar se tiver curso_id)
    inscricoes = db.collection('inscricoes').where('usuario_id', '==', user_id).stream()
    
    for insc in inscricoes:
        dados = insc.to_dict()
        concluidas = dados.get('aulas_concluidas', [])
        if aula_id in concluidas:
            return True
    return False

def marcar_aula_concluida(user_id, aula_id):
    """Adiciona aula à lista de concluídas e recalcula progresso."""
    db = get_db()
    
    # 1. Encontrar a aula para saber qual o curso dela
    aula_ref = db.collection('aulas').document(aula_id).get()
    if not aula_ref.exists:
        return
    
    modulo_id = aula_ref.to_dict().get('modulo_id')
    mod_ref = db.collection('modulos').document(modulo_id).get()
    curso_id = mod_ref.to_dict().get('curso_id')
    
    # 2. Encontrar a inscrição
    inscricao_query = db.collection('inscricoes')\
        .where('usuario_id', '==', user_id)\
        .where('curso_id', '==', curso_id)\
        .stream()
    
    insc_doc = None
    for d in inscricao_query:
        insc_doc = d
        break
        
    if not insc_doc:
        return # Usuário não inscrito
        
    # 3. Atualizar
    dados_insc = insc_doc.to_dict()
    concluidas = dados_insc.get('aulas_concluidas', [])
    
    if aula_id not in concluidas:
        concluidas.append(aula_id)
        
        # Calcular novo progresso %
        # Precisamos do total de aulas do curso
        total_aulas = 0
        mods = listar_modulos_e_aulas(curso_id)
        for m in mods:
            total_aulas += len(m['aulas'])
            
        progresso_pct = (len(concluidas) / total_aulas) * 100 if total_aulas > 0 else 0
        if progresso_pct > 100: progresso_pct = 100
        
        db.collection('inscricoes').document(insc_doc.id).update({
            "aulas_concluidas": concluidas,

# --- ADICIONE ESTA FUNÇÃO NOVA NO INÍCIO OU FIM DO ARQUIVO ---
def listar_todos_usuarios_para_selecao():
    """Retorna uma lista simples de usuários para serem escolhidos como editores."""
    db = get_db()
    users = db.collection('usuarios').stream()
    lista = []
    for u in users:
        dados = u.to_dict()
        # Filtra apenas quem é professor ou admin para ser editor
        if dados.get('tipo') in ['professor', 'admin']:
            lista.append({'id': u.id, 'nome': dados.get('nome', 'Sem Nome'), 'email': dados.get('email')})
    return lista

# --- ATUALIZE A FUNÇÃO CRIAR_CURSO (Adicionando o parametro editores_ids) ---
def criar_curso(professor_id, nome_professor, titulo, descricao, modalidade, publico, equipe_destino, pago, preco, split_custom, certificado_automatico, editores_ids=[]):
    """Cria um novo curso no banco de dados com lista de editores."""
    db = get_db()
    
    novo_curso = {
        "professor_id": professor_id,
        "professor_nome": nome_professor,
        "editores_ids": editores_ids,  # <--- NOVA LINHA: Lista de IDs que podem editar
        "titulo": titulo,
        "descricao": descricao,
        "modalidade": modalidade,
        "publico": publico,
        "equipe_destino": equipe_destino,
        "pago": pago,
        "preco": float(preco),
        "split_custom": split_custom,
        "certificado_automatico": certificado_automatico,
        "ativo": True,
        "criado_em": datetime.now(),
        "duracao_estimada": "A definir",
        "nivel": "Todos os Níveis"
    }
    
    _, doc_ref = db.collection('cursos').add(novo_curso)
    return doc_ref.id

# --- ATUALIZE A FUNÇÃO LISTAR_CURSOS_DO_PROFESSOR ---
def listar_cursos_do_professor(usuario_id):
    """Lista cursos onde o usuário é DONO ou EDITOR."""
    db = get_db()
    lista_cursos = []
    
    # 1. Cursos onde ele é o dono
    cursos_dono = db.collection('cursos').where('professor_id', '==', usuario_id).stream()
    for doc in cursos_dono:
        c = doc.to_dict()
        c['id'] = doc.id
        c['papel'] = 'Dono'
        lista_cursos.append(c)
        
    # 2. Cursos onde ele é editor (array-contains)
    # Nota: Firestore permite buscar se um valor existe dentro de um array
    cursos_editor = db.collection('cursos').where('editores_ids', 'array_contains', usuario_id).stream()
    
    # Evitar duplicatas caso a query traga o mesmo (difícil, mas preventivo)
    ids_existentes = [c['id'] for c in lista_cursos]
    
    for doc in cursos_editor:
        if doc.id not in ids_existentes:
            c = doc.to_dict()
            c['id'] = doc.id
            c['papel'] = 'Editor' # Marcamos visualmente que ele é editor
            lista_cursos.append(c)
            
    return lista_cursos
            "progresso": progresso_pct,
            "ultimo_acesso": datetime.now()
        })
