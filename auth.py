import bcrypt
from database import get_db
from utils import formatar_e_validar_cpf
from firebase_admin import firestore

def autenticar_local(usuario_email_ou_cpf, senha):
    """
    Autentica o usuário verificando email ou CPF no Firestore.
    """
    db = get_db()
    cpf_formatado = formatar_e_validar_cpf(usuario_email_ou_cpf)
    
    users_ref = db.collection('usuarios')
    usuario_doc = None

    # 1. Busca por Email
    # Nota: Buscamos 'local' para garantir, mas o ideal é buscar pelo email independente do provider
    # para evitar duplicidade de login se o usuário mudou de método.
    query_email = users_ref.where('email', '==', usuario_email_ou_cpf).stream()
    for doc in query_email:
        d = doc.to_dict()
        if d.get('auth_provider') == 'local':
            usuario_doc = doc
            break
    
    # 2. Busca por CPF (se não achou por email)
    if not usuario_doc and cpf_formatado:
        query_cpf = users_ref.where('cpf', '==', cpf_formatado).stream()
        for doc in query_cpf:
            d = doc.to_dict()
            if d.get('auth_provider') == 'local':
                usuario_doc = doc
                break
            
    # 3. Busca por Nome (Fallback - opcional, mas útil)
    if not usuario_doc:
        query_nome = users_ref.where('nome', '==', usuario_email_ou_cpf.upper()).where('auth_provider', '==', 'local').stream()
        for doc in query_nome:
            usuario_doc = doc
            break

    if usuario_doc:
        dados = usuario_doc.to_dict()
        senha_hash = dados.get('senha')
        
        if senha_hash and bcrypt.checkpw(senha.encode(), senha_hash.encode()):
            # CORREÇÃO CRÍTICA AQUI:
            # O app.py espera a chave "tipo", mas no banco salvamos como "tipo_usuario".
            # Fazemos o mapeamento aqui para garantir que o login carregue o perfil certo.
            tipo_perfil = dados.get('tipo_usuario')
            
            # Fallback de segurança: se estiver vazio, assume aluno
            if not tipo_perfil:
                tipo_perfil = 'aluno'

            return {
                "id": usuario_doc.id,
                "nome": dados.get('nome'),
                "tipo": tipo_perfil,  # <--- Esta é a chave que o app.py lê
                "email": dados.get('email')
            }
   if not tipo_perfil:
                tipo_perfil = 'aluno'

            return {
                "id": usuario_doc.id,
                "nome": dados.get('nome'),
                "tipo": tipo_perfil,
                "email": dados.get('email'),
                # ADICIONE A LINHA ABAIXO:
                "precisa_trocar_senha": dados.get('precisa_trocar_senha', False) 
            }     
    return None

def buscar_usuario_por_email(email_ou_cpf):
    """Busca usuário para o fluxo do Google Auth."""
    db = get_db()
    users_ref = db.collection('usuarios')
    usuario_doc = None
    
    query = users_ref.where('email', '==', email_ou_cpf).stream()
    for doc in query:
        usuario_doc = doc
        break
        
    if usuario_doc:
        dados = usuario_doc.to_dict()
        
        # Mesma correção para o Login Google
        tipo_perfil = dados.get('tipo_usuario', 'aluno')
        
        return {
            "id": usuario_doc.id,
            "nome": dados.get('nome'),
            "tipo": tipo_perfil,  # <--- Mapeamento correto
            "perfil_completo": dados.get('perfil_completo', False),
            "email": dados.get('email')
        }
        
    return None

def criar_usuario_parcial_google(email, nome):
    """Cria o registro inicial vindo do Google."""
    db = get_db()
    
    novo_usuario = {
        "email": email,
        "nome": nome.upper(),
        "auth_provider": "google",
        "perfil_completo": False,
        "tipo_usuario": "aluno", # Default até completar cadastro
        "data_criacao": firestore.SERVER_TIMESTAMP
    }
    
    update_time, doc_ref = db.collection('usuarios').add(novo_usuario)
    
    return {
        "id": doc_ref.id, 
        "email": email, 
        "nome": nome
    }
