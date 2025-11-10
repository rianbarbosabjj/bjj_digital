import streamlit as st
from fpdf import FPDF
from PIL import Image
import sqlite3
import json
import random
import os
import qrcode
import unicodedata
import pandas as pd
import plotly.express as px
from datetime import datetime

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(page_title="BJJ Digital", page_icon="🥋", layout="wide")

COR_FUNDO = "#0e2d26"
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD700"
COR_BOTAO = "#078B6C"
COR_HOVER = "#FFD700"

st.markdown(f"""
    <style>
    body {{
        background-color: {COR_FUNDO};
        color: {COR_TEXTO};
        font-family: 'Poppins', sans-serif;
    }}
    .stButton>button {{
        background: linear-gradient(90deg, {COR_BOTAO}, #056853);
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.6em 1.2em;
        border-radius: 10px;
        transition: 0.3s;
    }}
    .stButton>button:hover {{
        background: {COR_HOVER};
        color: {COR_FUNDO};
    }}
    h1, h2, h3 {{
        color: {COR_DESTAQUE};
        text-align: center;
        font-weight: 700;
    }}
    </style>
""", unsafe_allow_html=True)

# =========================================
# BANCO DE DADOS
# =========================================
DB_PATH = os.path.join("database", "bjj_digital.db")

def criar_banco():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        modo TEXT,
        tema TEXT,
        faixa TEXT,
        pontuacao INTEGER,
        tempo TEXT,
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        codigo_verificacao TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS config_exame (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faixa TEXT,
        questoes_json TEXT,
        professor TEXT,
        data_config DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

try:
    criar_banco()
except Exception as e:
    st.error(f"Erro ao criar o banco de dados: {e}")

# =========================================
# FUNÇÕES AUXILIARES
# =========================================
def carregar_questoes(tema):
    path = f"questions/{tema}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def gerar_codigo_unico():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM resultados")
    total = cursor.fetchone()[0] + 1
    conn.close()
    ano = datetime.now().year
    return f"BJJDIGITAL-{ano}-{total:05d}"

def salvar_resultado(usuario, modo, tema, faixa, pontuacao, tempo, codigo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO resultados (usuario, modo, tema, faixa, pontuacao, tempo, codigo_verificacao)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (usuario, modo, tema, faixa, pontuacao, tempo, codigo))
    conn.commit()
    conn.close()

def exportar_certificados_json():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT usuario, faixa, pontuacao, modo, tema, data, codigo_verificacao
        FROM resultados
    """)
    registros = cursor.fetchall()
    conn.close()

    certificados = [
        {
            "codigo": codigo,
            "usuario": usuario,
            "faixa": faixa,
            "pontuacao": pontuacao,
            "modo": modo,
            "tema": tema,
            "data": data
        }
        for usuario, faixa, pontuacao, modo, tema, data, codigo in registros
    ]
    os.makedirs("certificados", exist_ok=True)
    with open("certificados/certificados.json", "w", encoding="utf-8") as f:
        json.dump(certificados, f, ensure_ascii=False, indent=2)

def gerar_qrcode(codigo):
    os.makedirs("certificados/qrcodes", exist_ok=True)
    caminho_qr = os.path.abspath(f"certificados/qrcodes/{codigo}.png")
    url_verificacao = f"https://bjjdigital.netlify.app/verificar?codigo={codigo}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(url_verificacao)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img.save(caminho_qr)
    return caminho_qr

def normalizar_nome(nome):
    nfkd = unicodedata.normalize("NFKD", nome)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "_")

# =========================================
# GERAÇÃO DE PDF (FINAL COM QUEBRA DE LINHA)
# =========================================
def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    """
    Gera o certificado exatamente como no modelo CERTIFICADO.jpg.
    """
    pdf = FPDF("L", "mm", "A4") # Paisagem (Landscape), milímetros, A4
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_font("Helvetica") # Definir uma fonte padrão

    # Modelo base (fundo visual - bordas)
    modelo_path = "assets/CERTIFICADO.pdf"
    if not os.path.exists(modelo_path):
        raise FileNotFoundError("O modelo 'assets/CERTIFICADO.pdf' não foi encontrado.")
    
    # Adiciona a imagem de fundo (provavelmente apenas as bordas)
    pdf.image(modelo_path, x=0, y=0, w=297, h=210)

    # ========================
    # CORES E CONFIGURAÇÕES
    # ========================
    # AJUSTE: Cor dourada/amarela do modelo
    dourado = (218, 165, 32) 
    preto = (40, 40, 40)
    percentual = int((pontuacao / total) * 100)
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ========================
    # TÍTULO
    # ========================
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*dourado) # AJUSTE: Título é dourado no modelo
    pdf.set_y(40) # AJUSTE: Posição Y
    pdf.cell(0, 10, "CERTIFICADO DE EXAME TEÓRICO DE FAIXA", align="C")

    # ========================
    # LOGO BJJ DIGITAL (TOP)
    # ========================
    # NOVO: Este logo aparece na imagem mas não estava no código.
    # Você precisa ter este arquivo de imagem.
    logo_top_path = "assets/logo_bjjdigital_top.png" 
    if os.path.exists(logo_top_path):
        # Centraliza o logo (assumindo 30mm de largura)
        pdf.image(logo_top_path, x=(297-30)/2, y=58, w=30) 

    # ========================
    # TEXTO: "Certificamos que o(a) aluno(a)"
    # ========================
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*preto)
    pdf.set_y(85) # AJUSTE: Posição Y (abaixo do logo)
    pdf.cell(0, 8, "Certificamos que o(a) aluno(a)", align="C")

    # ========================
    # NOME DO ALUNO
    # ========================
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*dourado)
    pdf.set_y(97) # AJUSTE: Posição Y
    pdf.cell(0, 12, usuario.upper(), align="C")

    # ========================
    # TEXTO: "concluiu o exame teórico..."
    # ========================
    # LÓGICA CORRIGIDA: Esta é a parte mais complexa.
    # O modelo tem 3 partes na mesma linha (texto1, faixa, texto2)
    # e uma segunda linha separada para a data.
    
    cores_faixa = {
        "Cinza": (169, 169, 169),
        "Amarela": (255, 215, 0),
        "Laranja": (255, 140, 0),
        "Verde": (0, 128, 0),
        "Azul": (30, 144, 255),
        "Roxa": (128, 0, 128),
        "Marrom": (139, 69, 19),
        "Preta": (0, 0, 0)
    }
    cor_faixa = cores_faixa.get(faixa, (0, 0, 0))

    # --- LINHA 1 (Texto + Faixa + Texto) ---
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*preto)

    # Definir os 3 pedaços de texto
    texto_inicial = "concluiu o exame teórico para a faixa "
    texto_faixa = faixa.upper()
    texto_final = f" obtendo {percentual}% de aproveitamento,"

    # Calcular a largura de cada pedaço
    pdf.set_font("Helvetica", "", 14)
    largura_inicial = pdf.get_string_width(texto_inicial)
    pdf.set_font("Helvetica", "B", 14) # Faixa é Bold
    largura_faixa = pdf.get_string_width(texto_faixa)
    pdf.set_font("Helvetica", "", 14)
    largura_final = pdf.get_string_width(texto_final)
    
    largura_total_linha1 = largura_inicial + largura_faixa + largura_final
    
    # Calcular o X inicial para centralizar o bloco todo
    x_inicial_linha1 = (297 - largura_total_linha1) / 2
    
    # Posicionar e escrever a Linha 1
    pdf.set_y(115) # AJUSTE: Posição Y
    pdf.set_x(x_inicial_linha1)
    
    # Parte 1 (Preto, Normal)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*preto)
    pdf.cell(largura_inicial, 8, texto_inicial)
    
    # Parte 2 (Cor, Bold)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*cor_faixa)
    pdf.cell(largura_faixa, 8, texto_faixa)
    
    # Parte 3 (Preto, Normal)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*preto)
    pdf.cell(largura_final, 8, texto_final)

    # --- LINHA 2 (Data) ---
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*preto)
    pdf.set_y(122) # AJUSTE: Nova linha, um pouco abaixo
    pdf.cell(0, 8, f"realizado em {data_hora}.", align="C")

    # ========================
    # RESULTADO
    # ========================
    resultado = "APROVADO" if pontuacao >= (total * 0.6) else "REPROVADO"
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*dourado)
    pdf.set_y(135) # AJUSTE: Posição Y
    pdf.cell(0, 10, resultado, align="C")

    
    # ========================
    # SEÇÃO INFERIOR (Layout de 3 colunas)
    # ========================
    # AJUSTE: A seção inferior inteira foi reescrita.
    # O modelo tem Selo (Esquerda), Assinatura (Centro), QR (Direita)
    # Todos alinhados em uma altura base.
    
    y_base_inferior = 160 # Linha de alinhamento principal
    
    # --- Coluna Esquerda: SELO ---
    # NOVO: Este selo dourado não estava no código.
    seal_path = "assets/logo_seal.png" # Você precisa ter este arquivo
    if os.path.exists(seal_path):
        pdf.image(seal_path, x=25, y=y_base_inferior - 5, w=30, h=30)

    # --- Coluna Central: ASSINATURA ---
    if professor:
        nome_normalizado = "".join(
            c for c in professor.lower() if c.isalnum() or c in "_-"
        ).replace(" ", "_")
        assinatura_path = f"assets/assinaturas/{nome_normalizado}.png"
        
        if os.path.exists(assinatura_path):
            # AJUSTE: Centraliza a assinatura acima da linha
            pdf.image(assinatura_path, x=(297-60)/2, y=y_base_inferior - 15, w=60)

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*preto)
    pdf.set_y(y_base_inferior) # AJUSTE: Posição Y da linha
    pdf.cell(0, 8, "Assinatura do Professor Responsável", align="C")
    
    # AJUSTE: O texto "Projeto Resgate" é parte da assinatura, não do rodapé
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*dourado)
    pdf.set_y(y_base_inferior + 6) # Logo abaixo da linha
    pdf.cell(0, 6, "Projeto Resgate GFTeam IAPC de Irajá - BJJ Digital", align="C")

    # --- Coluna Direita: QR CODE ---
    caminho_qr = f"certificados/qrcodes/{codigo}.png"
    os.makedirs("certificados/qrcodes", exist_ok=True)
    url_verificacao = f"https://bjjdigital.netlify.app/verificar?codigo={codigo}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(url_verificacao)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img.save(caminho_qr)

    # AJUSTE: Posição (Direita) e Tamanho
    qr_w = 30 # Tamanho do QR
    x_qr = 297 - 25 - qr_w # Margem direita de 25mm
    y_qr = y_base_inferior - 5 # Alinhado com o selo
    
    pdf.image(caminho_qr, x=x_qr, y=y_qr, w=qr_w)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*preto)
    # AJUSTE: Centraliza o código *abaixo* do QR
    pdf.set_xy(x_qr, y_qr + qr_w + 1)
    pdf.cell(qr_w, 5, f"Código: {codigo}", align="C")


    # ========================
    # SALVAR PDF FINAL
    # ========================
    os.makedirs("relatorios", exist_ok=True)
    caminho_pdf = os.path.abspath(f"relatorios/Certificado_{usuario}_{faixa}.pdf")
    pdf.output(caminho_pdf)
    return caminho_pdf
# =========================================
# MODO EXAME DE FAIXA (DOWNLOAD PERSISTENTE)
# =========================================
def modo_exame():
    st.markdown("<h1 style='color:#FFD700;'>🏁 Exame de Faixa</h1>", unsafe_allow_html=True)
    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa = st.selectbox("Selecione a faixa:", faixas)
    usuario = st.text_input("Nome do aluno:")
    professor = st.text_input("Nome do professor responsável:")
    tema = "regras"

    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado = False
        st.session_state.respostas = {}
        st.session_state.certificado_path = None

    if not st.session_state.exame_iniciado:
        if st.button("Iniciar Exame"):
            questoes = carregar_questoes(tema)
            if not questoes:
                st.error("Nenhuma questão encontrada para o tema selecionado.")
                return
            random.shuffle(questoes)
            st.session_state.questoes = questoes[:5]
            st.session_state.exame_iniciado = True
            st.rerun()

    if st.session_state.exame_iniciado:
        questoes = st.session_state.questoes
        total = len(questoes)
        for i, q in enumerate(questoes, 1):
            st.markdown(f"### {i}. {q['pergunta']}")
            resp = st.radio("Escolha:", q["opcoes"], key=f"resp_{i}", index=None)
            st.session_state.respostas[f"resp_{i}"] = resp

        if st.button("Finalizar Exame"):
            pontuacao = sum(
                1 for i, q in enumerate(questoes, 1)
                if st.session_state.respostas.get(f"resp_{i}", "").startswith(q["resposta"])
            )
            codigo = gerar_codigo_unico()
            salvar_resultado(usuario, "Exame", tema, faixa, pontuacao, "00:05:00", codigo)
            exportar_certificados_json()
            caminho_pdf = gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor)
            st.session_state.certificado_path = caminho_pdf
            st.rerun()

    if st.session_state.get("certificado_path"):
        caminho_pdf = st.session_state.certificado_path
        st.success(f"🎉 Certificado de {usuario.upper() if usuario else 'ALUNO'} ({faixa}) gerado com sucesso!")
        try:
            with open(caminho_pdf, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label="📄 Baixar Certificado",
                data=pdf_bytes,
                file_name=os.path.basename(caminho_pdf),
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"⚠️ Erro ao preparar o download: {e}")

# =========================================
# HISTÓRICO DE CERTIFICADOS
# =========================================
def painel_certificados():
    st.markdown("<h1 style='color:#FFD700;'>📜 Histórico de Certificados</h1>", unsafe_allow_html=True)
    nome = st.text_input("Digite seu nome completo:")
    if st.button("🔍 Buscar"):
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM resultados ORDER BY data DESC", conn)
        conn.close()
        df = df[df["usuario"].str.contains(nome, case=False, na=False)]
        if df.empty:
            st.info("Nenhum certificado encontrado.")
        else:
            st.success(f"Foram encontrados {len(df)} registro(s).")
            st.dataframe(df[["usuario","faixa","pontuacao","data","codigo_verificacao"]])

# =========================================
# DASHBOARD DO PROFESSOR
# =========================================
def dashboard_professor():
    st.markdown("<h1 style='color:#FFD700;'>📈 Dashboard do Professor</h1>", unsafe_allow_html=True)
    abas = st.tabs(["📊 Indicadores", "📋 Histórico"])

    with abas[0]:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM resultados", conn)
        conn.close()

        if df.empty:
            st.info("Nenhum exame registrado ainda.")
            return

        total, media = len(df), df["pontuacao"].mean()
        taxa = (df[df["pontuacao"] >= 3].shape[0] / total) * 100
        aprovados = df[df["pontuacao"] >= 3].shape[0]
        reprovados = total - aprovados

        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Exames", total)
        col2.metric("Média de Pontuação", f"{media:.2f}")
        col3.metric("Taxa de Aprovação", f"{taxa:.1f}%")

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(df, x="faixa", color="faixa",
                          title="Distribuição de Exames por Faixa",
                          color_discrete_sequence=px.colors.sequential.YlGn)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.pie(names=["Aprovados", "Reprovados"], values=[aprovados, reprovados],
                          title="Taxa de Aprovação", color_discrete_sequence=["#FFD700", "#0e2d26"])
            st.plotly_chart(fig2, use_container_width=True)

    with abas[1]:
        st.markdown("### 📋 Histórico de Exames")
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT usuario, faixa, pontuacao, data, codigo_verificacao FROM resultados", conn)
        conn.close()
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📤 Exportar CSV", csv, "relatorio_exames.csv", "text/csv")

# =========================================
# MENU PRINCIPAL
# =========================================
def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown("<h3 style='color:#FFD700;'>Plataforma BJJ Digital</h3>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegar:", [
        "🏁 Exame de Faixa",
        "📜 Histórico de Certificados",
        "📈 Dashboard do Professor"
    ])
    if menu == "🏁 Exame de Faixa":
        modo_exame()
    elif menu == "📜 Histórico de Certificados":
        painel_certificados()
    elif menu == "📈 Dashboard do Professor":
        dashboard_professor()

if __name__ == "__main__":
    main()
