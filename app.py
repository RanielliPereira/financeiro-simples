import shutil
import datetime
import os
import tkinter as tk
from tkinter import messagebox
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
import subprocess
import platform

# --- Função de backup automático ---
def fazer_backup():
    if not os.path.exists("backups"):
        os.makedirs("backups")
    agora = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nome_backup = f"backups/financeiro_backup_{agora}.db"
    shutil.copyfile("financeiro.db", nome_backup)

# --- Conexão com o banco de dados ---
conn = sqlite3.connect('financas.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    categoria TEXT,
    valor REAL,
    data TEXT
)
''')
conn.commit()

# Usuários fixos
usuarios = {
    "ranielli": "2408",
    "ana": "2408"
}

# --- Tela de login ---
def verificar_login():
    usuario = usuario_entry.get()
    senha = senha_entry.get()
    if usuarios.get(usuario) == senha:
        login_janela.destroy()
        abrir_tela_principal()
    else:
        messagebox.showerror("Erro", "Usuário ou senha inválidos.")

# --- Abrir tela principal ---
def abrir_tela_principal():
    global tela_principal
    global lista_transacoes
    global saldo_var

    tela_principal = tk.Toplevel()
    tela_principal.title("Controle Financeiro")

    saldo_var = tk.StringVar()
    saldo_var.set("Saldo: R$ 0.00")
    tk.Label(tela_principal, textvariable=saldo_var, font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2)

    tk.Button(tela_principal, text="Entradas", width=20, command=abrir_tela_entrada).grid(row=1, column=0, padx=10, pady=5)
    tk.Button(tela_principal, text="Saídas", width=20, command=abrir_tela_saida).grid(row=1, column=1, padx=10, pady=5)
    tk.Button(tela_principal, text="Reserva Emergência", width=20, command=abrir_tela_reserva).grid(row=2, column=0, padx=10, pady=5)
    tk.Button(tela_principal, text="Relatório Mensal", width=20, command=abrir_relatorio_mensal).grid(row=2, column=1, padx=10, pady=5)
    tk.Button(tela_principal, text="Exportar PDF", width=20, command=exportar_pdf).grid(row=3, column=0, columnspan=2, pady=5)
    tk.Button(tela_principal, text="Gráfico Pizza", width=20, command=mostrar_grafico).grid(row=4, column=0, columnspan=2, pady=5)
    tk.Button(tela_principal, text="Visualizar PDF", width=20, command=visualizar_pdf).grid(row=6, column=0, pady=5)
    tk.Button(tela_principal, text="Compartilhar PDF", width=20, command=compartilhar_pdf).grid(row=6, column=1, pady=5)
    tk.Button(tela_principal, text="Editar Selecionado", width=20, command=editar_transacao).grid(row=7, column=0, pady=5)


    lista_transacoes = tk.Listbox(tela_principal, width=50, height=15)
    lista_transacoes.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

    tk.Button(tela_principal, text="Editar Selecionado", width=20, command=editar_transacao).grid(row=7, column=0, pady=5)
    tk.Button(tela_principal, text="Excluir Selecionado", width=20, command=excluir_transacao).grid(row=7, column=1, pady=5)

    def excluir_transacao():
        selecionado = lista_transacoes.curselection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma transação para excluir.")
        return

    texto = lista_transacoes.get(selecionado)
    tipo = texto.split(']')[0].strip('[').lower()
    categoria = texto.split(']')[1].split('-')[0].strip()
    valor = float(texto.split('R$')[1].split('em')[0].strip())
    data = texto.split('em')[1].strip()

    cursor.execute("DELETE FROM transacoes WHERE tipo = ? AND categoria = ? AND valor = ? AND data = ?", (tipo, categoria, valor, data))
    conn.commit()
    atualizar_lista()
    messagebox.showinfo("Sucesso", "Transação excluída com sucesso.")
# --- Função para editar uma transação selecionada ---
def editar_transacao():
    try:
        # Obtém o índice da transação selecionada
        selected_index = lista_transacoes.curselection()[0]
        # Obtém os dados da transação selecionada
        cursor.execute("SELECT id, tipo, categoria, valor FROM transacoes ORDER BY data DESC")
        transacao = cursor.fetchall()[selected_index]
        transacao_id, tipo, categoria, valor = transacao

        # Cria a janela para edição
        janela_edicao = tk.Toplevel()
        janela_edicao.title(f"Editar {tipo.capitalize()}")

        tk.Label(janela_edicao, text="Categoria:").grid(row=0, column=0, padx=10, pady=5)
        categoria_entry = tk.Entry(janela_edicao)
        categoria_entry.insert(0, categoria)  # Preenche com a categoria atual
        categoria_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(janela_edicao, text="Valor (R$):").grid(row=1, column=0, padx=10, pady=5)
        valor_entry = tk.Entry(janela_edicao)
        valor_entry.insert(0, valor)  # Preenche com o valor atual
        valor_entry.grid(row=1, column=1, padx=10, pady=5)

        def salvar_edicao():
            try:
                novo_valor = float(valor_entry.get())
                nova_categoria = categoria_entry.get()
                cursor.execute("UPDATE transacoes SET categoria = ?, valor = ? WHERE id = ?",
                               (nova_categoria, novo_valor, transacao_id))
                conn.commit()
                atualizar_lista()  # Atualiza a lista de transações após a edição
                janela_edicao.destroy()  # Fecha a janela de edição
            except ValueError:
                messagebox.showerror("Erro", "Digite um valor válido.")

        tk.Button(janela_edicao, text="Salvar", command=salvar_edicao).grid(row=2, column=0, columnspan=2, pady=10)

    except IndexError:
        messagebox.showerror("Erro", "Selecione uma transação para editar.")



# --- Função de inserção de transações ---
def inserir_transacao(tipo, categoria, valor):
    data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO transacoes (tipo, categoria, valor, data) VALUES (?, ?, ?, ?)",
                   (tipo, categoria, valor, data))
    conn.commit()
    atualizar_lista()

# --- Atualizar lista de transações com cores ---
def atualizar_lista():
    lista_transacoes.delete(0, tk.END)
    cursor.execute("SELECT tipo, categoria, valor, data FROM transacoes ORDER BY data DESC")
    transacoes = cursor.fetchall()
    total = 0
    for t in transacoes:
        tipo, cat, val, dt = t
        if tipo == "entrada":
            lista_transacoes.insert(tk.END, f"[{tipo.upper()}] {cat} - R$ {val:.2f} em {dt}")
            lista_transacoes.itemconfig(tk.END, {'fg': 'green'})  # Entradas em verde
            total += val
        elif tipo == "saida":
            lista_transacoes.insert(tk.END, f"[{tipo.upper()}] {cat} - R$ {val:.2f} em {dt}")
            lista_transacoes.itemconfig(tk.END, {'fg': 'red'})  # Saídas em vermelho
            total -= val
        elif tipo == "reserva":
            lista_transacoes.insert(tk.END, f"[{tipo.upper()}] {cat} - R$ {val:.2f} em {dt}")
            lista_transacoes.itemconfig(tk.END, {'fg': 'blue'})  # Reserva em azul
            total -= val
    saldo_var.set(f"Saldo: R$ {total:.2f}")

# --- Telas de entrada, saída e reserva ---
def abrir_tela_entrada():
    abrir_tela_transacao("entrada")

def abrir_tela_saida():
    abrir_tela_transacao("saida")

def abrir_tela_reserva():
    abrir_tela_transacao("reserva")

def abrir_tela_transacao(tipo):
    janela = tk.Toplevel()
    janela.title(f"Lançar {tipo.capitalize()}")

    tk.Label(janela, text="Categoria:").grid(row=0, column=0, padx=10, pady=5)
    categoria_entry = tk.Entry(janela)
    categoria_entry.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(janela, text="Valor (R$):").grid(row=1, column=0, padx=10, pady=5)
    valor_entry = tk.Entry(janela)
    valor_entry.grid(row=1, column=1, padx=10, pady=5)

    def salvar():
        try:
            valor = float(valor_entry.get())
            categoria = categoria_entry.get()
            inserir_transacao(tipo, categoria, valor)
            janela.destroy()
        except ValueError:
            messagebox.showerror("Erro", "Digite um valor válido.")

    tk.Button(janela, text="Salvar", command=salvar).grid(row=2, column=0, columnspan=2, pady=10)

# --- Relatório mensal com filtros de mês e ano ---
def abrir_relatorio_mensal():
    # Tela para selecionar mês e ano
    relatorio = tk.Toplevel()
    relatorio.title("Relatório Mensal")

    tk.Label(relatorio, text="Mês (1-12):").grid(row=0, column=0, padx=10, pady=5)
    mes_entry = tk.Entry(relatorio)
    mes_entry.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(relatorio, text="Ano:").grid(row=1, column=0, padx=10, pady=5)
    ano_entry = tk.Entry(relatorio)
    ano_entry.grid(row=1, column=1, padx=10, pady=5)

    def gerar_relatorio():
        mes = mes_entry.get()
        ano = ano_entry.get()

        # Verifica se as entradas são válidas
        try:
            mes = int(mes)
            ano = int(ano)
            if mes < 1 or mes > 12:
                messagebox.showerror("Erro", "Mês deve estar entre 1 e 12.")
                return
        except ValueError:
            messagebox.showerror("Erro", "Digite um mês e ano válidos.")
            return

        relatorio_texto = tk.Text(relatorio, width=60, height=20)
        relatorio_texto.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        cursor.execute('''
            SELECT tipo, categoria, valor, data FROM transacoes
            WHERE strftime('%m', data) = ? AND strftime('%Y', data) = ?
        ''', (f'{mes:02}', str(ano)))
        dados = cursor.fetchall()

        entradas, saidas, reserva = 0, 0, 0

        for tipo, cat, val, data in dados:
            if tipo == "entrada":
                entradas += val
                relatorio_texto.insert(tk.END, f"[ENTRADA] {cat} - R$ {val:.2f} em {data}\n")
            elif tipo == "saida":
                saidas += val
                relatorio_texto.insert(tk.END, f"[SAÍDA] {cat} - R$ {val:.2f} em {data}\n")
            elif tipo == "reserva":
                reserva += val
                relatorio_texto.insert(tk.END, f"[RESERVA] {cat} - R$ {val:.2f} em {data}\n")

        total = entradas - saidas - reserva
        relatorio_texto.insert(tk.END, f"\nEntradas: R$ {entradas:.2f}\nSaídas: R$ {saidas:.2f}\nReserva: R$ {reserva:.2f}\nSaldo final: R$ {total:.2f}")

    # Botão para gerar o relatório
    tk.Button(relatorio, text="Gerar Relatório", command=gerar_relatorio).grid(row=2, column=0, columnspan=2, pady=10)

# --- Exportar relatório para PDF ---
def exportar_pdf():
    c = canvas.Canvas("relatorio_financeiro.pdf", pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(30, 750, "Relatório Financeiro")

    y = 720
    cursor.execute("SELECT tipo, categoria, valor, data FROM transacoes")
    dados = cursor.fetchall()

    entradas, saidas, reserva = 0, 0, 0
    for tipo, cat, val, data in dados:
        if tipo == "entrada":
            entradas += val
            c.setFillColorRGB(0, 1, 0)  # Cor verde para entradas
            c.drawString(30, y, f"Entrada: {cat} - R$ {val:.2f} em {data}")
        elif tipo == "saida":
            saidas += val
            c.setFillColorRGB(1, 0, 0)  # Cor vermelha para saídas
            c.drawString(30, y, f"Saída: {cat} - R$ {val:.2f} em {data}")
        elif tipo == "reserva":
            reserva += val
            c.setFillColorRGB(0, 0, 1)  # Cor azul para reserva
            c.drawString(30, y, f"Reserva: {cat} - R$ {val:.2f} em {data}")
        
        y -= 15
        if y < 40:
            c.showPage()
            y = 750

    c.setFillColorRGB(0, 0, 0)  # Cor preta para o texto final
    c.drawString(30, y, f"\nTotal de Entradas: R$ {entradas:.2f}")
    c.drawString(30, y-15, f"Total de Saídas: R$ {saidas:.2f}")
    c.drawString(30, y-30, f"Reserva Emergência: R$ {reserva:.2f}")
    saldo_final = entradas - saidas - reserva
    c.drawString(30, y-45, f"Saldo Final: R$ {saldo_final:.2f}")

    c.save()
    messagebox.showinfo("PDF", "Relatório salvo como relatorio_financeiro.pdf")


def visualizar_pdf():
    caminho = os.path.abspath("relatorio_financeiro.pdf")
    try:
        if platform.system() == "Windows":
            os.startfile(caminho)
        elif platform.system() == "Darwin":  # macOS
            subprocess.call(["open", caminho])
        else:  # Linux
            subprocess.call(["xdg-open", caminho])
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível abrir o PDF.\n{e}")

def compartilhar_pdf():
    pasta = os.path.abspath(os.path.dirname("relatorio_financeiro.pdf"))
    try:
        if platform.system() == "Windows":
            os.startfile(pasta)
        elif platform.system() == "Darwin":
            subprocess.call(["open", pasta])
        else:
            subprocess.call(["xdg-open", pasta])
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível abrir a pasta.\n{e}")


# --- Mostrar gráfico de pizza ---
def mostrar_grafico():
    cursor.execute("SELECT tipo, valor FROM transacoes")
    dados = cursor.fetchall()

    entradas = sum(val for tipo, val in dados if tipo == 'entrada')
    saidas = sum(val for tipo, val in dados if tipo == 'saida')
    reserva = sum(val for tipo, val in dados if tipo == 'reserva')

    labels = ['Entradas', 'Saídas', 'Reserva']
    sizes = [entradas, saidas, reserva]
    colors = ['green', 'red', 'blue']

    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')
    plt.title("Distribuição de Entradas, Saídas e Reserva")
    plt.show()

# --- Função principal ---
if __name__ == "__main__":
    # Tela de Login
    login_janela = tk.Tk()
    login_janela.title("Login")

    tk.Label(login_janela, text="Usuário:").grid(row=0, column=0, padx=10, pady=10)
    usuario_entry = tk.Entry(login_janela)
    usuario_entry.grid(row=0, column=1, padx=10, pady=10)

    tk.Label(login_janela, text="Senha:").grid(row=1, column=0, padx=10, pady=10)
    senha_entry = tk.Entry(login_janela, show="*")
    senha_entry.grid(row=1, column=1, padx=10, pady=10)

    tk.Button(login_janela, text="Entrar", command=verificar_login).grid(row=2, column=0, columnspan=2, pady=10)

    login_janela.mainloop()
