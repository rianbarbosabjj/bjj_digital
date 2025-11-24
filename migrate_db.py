import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import os

# =========================================
# 1. CONEXÃO COM FIREBASE
# =========================================
def get_firestore_db():
    if not firebase_admin._apps:
        try:
            # Tenta pegar do secrets (Streamlit Cloud) ou local
            if "FIREBASE_KEY" in st.secrets:
                key_dict = dict(st.secrets["FIREBASE_KEY"])
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred)
            else:
                print("❌ Erro: Segredos do Firebase não encontrados.")
                return None
        except Exception as e:
            print(f"❌ Erro ao conectar Firebase: {e}")
            return None
    return firestore.client()

# =========================================
# 2. FUNÇÃO DE MIGRAÇÃO
# =========================================
def migrar_tabela(sql_conn, fs_db, nome_tabela, nome_colecao):
    print(f"🔄 Migrando tabela '{nome_tabela}' para coleção '{nome_colecao}'...")
    
    cursor = sql_conn.cursor()
    try:
        # Pega nomes das colunas
        cursor.execute(f"PRAGMA table_info({nome_tabela})")
        colunas = [col[1] for col in cursor.fetchall()]
        
        # Pega todos os dados
        cursor.execute(f"SELECT * FROM {nome_tabela}")
        linhas = cursor.fetchall()
        
        batch = fs_db.batch()
        contador = 0
        
        for linha in linhas:
            # Cria dicionário {coluna: valor}
            dados = dict(zip(colunas, linha))
            
            # ID original do SQL (importante para manter relações)
            doc_id = str(dados.pop('id')) 
            
            # Converte booleanos (SQLite usa 0/1)
            for k, v in dados.items():
                if k in ['perfil_completo', 'pode_aprovar', 'eh_responsavel', 'ativo', 'exame_habilitado']:
                    dados[k] = bool(v)
            
            # Prepara a escrita no Firestore usando o MESMO ID do SQL
            doc_ref = fs_db.collection(nome_colecao).document(doc_id)
            batch.set(doc_ref, dados)
            contador += 1
            
            # Firestore aceita batches de até 500
            if contador % 400 == 0:
                batch.commit()
                batch = fs_db.batch()
                print(f"   ... {contador} registros processados")
        
        # Comita o restante
        batch.commit()
        print(f"✅ Sucesso: {contador} documentos criados em '{nome_colecao}'.")
        
    except sqlite3.OperationalError:
        print(f"⚠️ Tabela '{nome_tabela}' não encontrada no SQLite. Pulando.")

# =========================================
# 3. EXECUÇÃO PRINCIPAL
# =========================================
if __name__ == "__main__":
    db_path = "bjj_digital.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Arquivo '{db_path}' não encontrado na pasta.")
        print("Baixe-o do GitHub e coloque na mesma pasta deste script.")
        exit()
        
    print("🚀 Iniciando migração...")
    
    # Conecta SQL
    conn = sqlite3.connect(db_path)
    
    # Conecta Firestore
    db = get_firestore_db()
    
    if db:
        # Lista de Tabelas para Migrar
        # Formato: (Nome Tabela SQL, Nome Coleção Firestore)
        tabelas = [
            ('usuarios', 'usuarios'),
            ('equipes', 'equipes'),
            ('professores', 'professores'),
            ('alunos', 'alunos'),
            ('resultados', 'resultados'),
            ('rola_resultados', 'rola_resultados')
        ]
        
        for tbl, col in tabelas:
            migrar_tabela(conn, db, tbl, col)
            
        print("\n🏁 Migração concluída! Agora seus dados estão na nuvem.")
    
    conn.close()
