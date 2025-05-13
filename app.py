import tkinter as tk
from tkinter import messagebox, simpledialog
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import sqlite3
import os
from datetime import datetime
import matplotlib.pyplot as plt

# Banco de dados
conn = sqlite3.connect("financas.db")
cursor = conn.cursor()

# Criação das tabelas (se não existirem)
cursor.execute("""
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY,
    tipo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    valor REAL NOT NULL,
    usuario_id INTEGER NOT NULL,
    categoria TEXT NOT NULL,
    data TEXT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
)
""")

# Tabela de usuários
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    senha TEXT NOT NULL
)
""")

# Inserir 2 usuários fixos (se não existirem)
usuarios_padrao = [("ranielli", "2408"), ("ana", "2408")]
for user, senha in usuarios_padrao:
    try:
        cursor.execute("INSERT INTO usuarios (username, senha) VALUES (?, ?)", (user, senha))
    except sqlite3.IntegrityError:
        continue  # Usuário já existe

conn.commit()

# Armazena dados do usuário logado
usuario_logado = {"id": None, "username": None}

# Funções principais
def atualizar_lista():
    lista_transacoes.delete(0, tk.END)
    cursor.execute("""
        SELECT t.tipo, t.descricao, t.valor, u.username, t.data, t.categoria
        FROM transacoes t
        JOIN usuarios u ON t.usuario_id = u.id
        ORDER BY t.id DESC
    """)
    for tipo, descricao, valor, usuario, data, categoria in cursor.fetchall():
        lista_transacoes.insert(tk.END, f"{tipo} - {descricao}: R$ {valor:.2f} (Categoria: {categoria}) - {usuario} - {data}")

def atualizar_saldo():
    cursor.execute("""
        SELECT SUM(CASE WHEN tipo = 'Entrada' THEN valor ELSE -valor END)
        FROM transacoes
        WHERE usuario_id = ?
    """, (usuario_logado["id"],))
    saldo = cursor.fetchone()[0]
    saldo = saldo if saldo is not None else 0.0
    saldo_var.set(f"Saldo do usuário: R$ {saldo:.2f}")

def salvar_transacao(tipo, descricao, valor, categoria, janela):
    if descricao == "":
        messagebox.showerror("Erro", "Descrição não pode ser vazia!", parent=janela)
        return
    try:
        valor = float(valor)
    except ValueError:
        messagebox.showerror("Erro", "Valor inválido!", parent=janela)
        return

    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO transacoes (tipo, descricao, valor, usuario_id, categoria, data)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (tipo, descricao, valor, usuario_logado["id"], categoria, data_atual))
    conn.commit()
    atualizar_lista()
    atualizar_saldo()
    janela.destroy()

def abrir_tela_transacao(tipo):
    janela = tk.Toplevel(tela_principal)
    janela.title(f"Nova {tipo}")

    tk.Label(janela, text="Descrição:").grid(row=0, column=0, padx=5, pady=5)
    desc_entry = tk.Entry(janela, width=30)
    desc_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(janela, text="Valor:").grid(row=1, column=0, padx=5, pady=5)
    valor_entry = tk.Entry(janela, width=30)
    valor_entry.grid(row=1, column=1, padx=5, pady=5)

    btn_color = "lightgreen" if tipo == "Entrada" else "tomato"
    tk.Button(janela, text="Salvar", bg=btn_color,
              command=lambda: salvar_transacao(tipo, desc_entry.get(), valor_entry.get(), categoria_entry.get(), janela)).grid(
        row=3, column=0, columnspan=2, pady=10)

def abrir_tela_reserva_emergencia():
    janela = tk.Toplevel(tela_principal)
    janela.title("Nova Reserva de Emergência")

    tk.Label(janela, text="Descrição:").grid(row=0, column=0, padx=5, pady=5)
    desc_entry = tk.Entry(janela, width=30)
    desc_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(janela, text="Valor:").grid(row=1, column=0, padx=5, pady=5)
    valor_entry = tk.Entry(janela, width=30)
    valor_entry.grid(row=1, column=1, padx=5, pady=5)

    # A categoria será automaticamente "Emergência"
    categoria_entry = tk.Entry(janela, width=30)
    categoria_entry.insert(0, "Emergência")
    categoria_entry.grid(row=2, column=1, padx=5, pady=5)

    tk.Button(janela, text="Salvar", bg="lightblue",
              command=lambda: salvar_transacao("Entrada", desc_entry.get(), valor_entry.get(), "Emergência", janela)).grid(
        row=3, column=0, columnspan=2, pady=10)

# Função para abrir relatório mensal
def abrir_relatorio_mensal():
    data_atual = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT tipo, SUM(valor), categoria
        FROM transacoes
        WHERE strftime('%Y-%m', data) = strftime('%Y-%m', ?)
        GROUP BY tipo, categoria
    """, (data_atual,))
    relatorio = cursor.fetchall()

    relatorio_str = f"Relatório Mensal - {data_atual}\n\n"
    for tipo, total, categoria in relatorio:
        relatorio_str += f"{tipo} ({categoria}): R$ {total:.2f}\n"

    messagebox.showinfo("Relatório Mensal", relatorio_str)

# Função para gerar gráfico de pizza
def gerar_grafico_pizza():
    cursor.execute("""
        SELECT tipo, SUM(valor)
        FROM transacoes
        GROUP BY tipo
    """)
    dados = cursor.fetchall()

    tipos = [item[0] for item in dados]
    valores = [item[1] for item in dados]

    plt.pie(valores, labels=tipos, autopct='%1.1f%%', startangle=90)
    plt.title("Distribuição de Entradas e Despesas")
    plt.show()

# Função de verificação de login
def verificar_login():
    username = usuario_entry.get()
    senha = senha_entry.get()

    cursor.execute("SELECT * FROM usuarios WHERE username = ? AND senha = ?", (username, senha))
    usuario = cursor.fetchone()

    if usuario:
        usuario_logado["id"] = usuario[0]
        usuario_logado["username"] = usuario[1]
        login_janela.destroy()
        abrir_tela_principal()
    else:
        messagebox.showerror("Erro", "Usuário ou senha inválidos!")

# Função para abrir tela principal
def abrir_tela_principal():
    global tela_principal
    tela_principal = tk.Tk()
    tela_principal.title("Aplicativo Financeiro")

    # Exibir o nome do usuário
    tk.Label(tela_principal, text=f"Bem-vindo, {usuario_logado['username']}!", font=("Arial", 16)).grid(row=0, column=0, columnspan=2, pady=10)

    # Botões principais
    tk.Button(tela_principal, text="Adicionar Entrada", width=20, command=lambda: abrir_tela_transacao("Entrada")).grid(row=1, column=0, padx=10, pady=10)
    tk.Button(tela_principal, text="Adicionar Saída", width=20, command=lambda: abrir_tela_transacao("Saída")).grid(row=1, column=1, padx=10, pady=10)
    tk.Button(tela_principal, text="Reserva de Emergência", width=20, command=abrir_tela_reserva_emergencia).grid(row=2, column=0, padx=10, pady=10)
    tk.Button(tela_principal, text="Relatório Mensal", width=20, command=abrir_relatorio_mensal).grid(row=2, column=1, padx=10, pady=10)
    tk.Button(tela_principal, text="Gerar Gráfico", width=20, command=gerar_grafico_pizza).grid(row=3, column=0, padx=10, pady=10)

    # Lista de transações
    lista_transacoes = tk.Listbox(tela_principal, width=50, height=15)
    lista_transacoes.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

    # Exibir saldo
    global saldo_var
    saldo_var = tk.StringVar()
    saldo_var.set("Saldo do usuário: R$ 0.00")
    tk.Label(tela_principal, textvariable=saldo_var, font=("Arial", 14)).grid(row=5, column=0, columnspan=2, pady=10)

    atualizar_lista()
    atualizar_saldo()

    tela_principal.mainloop()

# Tela de login
login_janela = tk.Tk()
login_janela.title("Login")

tk.Label(login_janela, text="Usuário:").grid(row=0, column=0, padx=5, pady=5)
usuario_entry = tk.Entry(login_janela)
usuario_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(login_janela, text="Senha:").grid(row=1, column=0, padx=5, pady=5)
senha_entry = tk.Entry(login_janela, show="*")
senha_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Button(login_janela, text="Entrar", command=verificar_login).grid(row=2, column=0, columnspan=2, pady=10)

login_janela.mainloop()
