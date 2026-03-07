import tkinter as tk
from tkinter import messagebox
import threading
from playwright.sync_api import sync_playwright
import json

class AutomationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Controle Playwright")
        self.root.geometry("400x250")

        self.playwright = None
        self.browser = None
        self.page = None

        # Fila de comandos para a thread do Playwright
        self._cmd_queue = []
        self._cmd_event = threading.Event()
        self._lock = threading.Lock()

        # Thread única e persistente do Playwright
        self._pw_thread = threading.Thread(target=self._playwright_worker, daemon=True)
        self._pw_thread.start()

        self.label = tk.Label(root, text="Painel de Controle", font=("Arial", 12, "bold"))
        self.label.pack(pady=10)

        self.btn_abrir = tk.Button(root, text="1. Abrir Navegador e Site",
                                   command=self.thread_abrir_site, bg="#e1e1e1", width=25)
        self.btn_abrir.pack(pady=5)

        self.btn_rodar = tk.Button(root, text="2. Rodar Automação",
                                   command=self.thread_rodar_script, state=tk.DISABLED, bg="#d1ffd1", width=25)
        self.btn_rodar.pack(pady=5)

        self.btn_fechar = tk.Button(root, text="Fechar Navegador", command=self.thread_fechar, fg="red")
        self.btn_fechar.pack(pady=20)

    def _playwright_worker(self):
        """Thread única que roda todos os comandos do Playwright."""
        while True:
            self._cmd_event.wait()
            self._cmd_event.clear()
            with self._lock:
                cmds = self._cmd_queue[:]
                self._cmd_queue.clear()
            for cmd in cmds:
                try:
                    cmd()
                except Exception as e:
                    erro = str(e)
                    self.root.after(0, lambda err=erro: messagebox.showerror("Erro", err))

    def _enqueue(self, cmd):
        """Envia um comando para a thread do Playwright."""
        with self._lock:
            self._cmd_queue.append(cmd)
        self._cmd_event.set()

    # --- Botões chamam _enqueue ---
    def thread_abrir_site(self):
        self.btn_abrir.config(state=tk.DISABLED)
        self._enqueue(self._abrir_site)

    def thread_rodar_script(self):
        self.btn_rodar.config(state=tk.DISABLED)
        self._enqueue(self._executar_tarefa)

    def thread_fechar(self):
        self._enqueue(self._fechar_browser)

    # --- Lógica Playwright (roda sempre na mesma thread) ---
    def _abrir_site(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
        self.page = self.browser.new_page(no_viewport=True)
        self.page.goto("https://app.powercrm.com.br/")

        self.page.wait_for_selector("#emailField")
        self.page.locator("#emailField").fill("arx.patrik@gmail.com")
        self.page.locator("#j_password").fill("Arx2025")
        self.page.locator("input.btn_logar").click()
        self.page.wait_for_selector("#ppl_negotiation", timeout=30000)

        self.root.after(0, lambda: self.btn_rodar.config(state=tk.NORMAL))
        self.root.after(0, lambda: messagebox.showinfo("Info", "Login realizado! Navegador pronto."))


    def _executar_tarefa(self):
        if not self.page:
            return

        try:
            # 1. Carregar a lista de nomes do JSON
            with open('lista.json', 'r', encoding='utf-8') as f:
                dados_json = json.load(f)
            
            # 2. Clicar no primeiro card
            self.page.wait_for_selector("#ppl_negotiation section.pwrcrm-card.card-simple")
            primeiro_card = self.page.locator("#ppl_negotiation section.pwrcrm-card.card-simple").nth(0)
            primeiro_card.scroll_into_view_if_needed()
            primeiro_card.click()

            # 3. Aguardar as mensagens carregarem
            self.page.wait_for_selector("#wallmessages", timeout=10000)
            
            mensagens_locators = self.page.locator("#wallmessages div[data-type='2']")
            count = mensagens_locators.count()
            
            item_encontrado = None # Aqui vamos guardar o dicionário completo do JSON
            
            # 4. Iterar pelas mensagens e verificar o texto
            for i in range(count):
                texto_mensagem = mensagens_locators.nth(i).inner_text().lower()
                
                # Procuramos qual item da lista está contido na mensagem
                for item in dados_json:
                    if item['nome_tratamento'].lower() in texto_mensagem:
                        print(f"Correspondência encontrada: {item['nome_tratamento']}")
                        item_encontrado = item
                        break
                
                if item_encontrado:
                    break

            # 5. Se encontrar, executa as ações e preenche o input
            if item_encontrado:
                # Clica em alterar responsável
                self.page.locator("#modal_negotiation_info_responsible").click()
                print("Click em alterar")
                
                # Clica no campo/dropdown de seleção
                selector_click = "xpath=/html/body/div[19]/div/div/div/div/div[2]/div/aside[3]/div/div[1]/div"
                self.page.locator(selector_click).click()
                print("Click em selecionar")

                # Preenche o input com o NOME_COMPLETO
                input_xpath = "xpath=/html/body/div[19]/div/div/div/div/div[2]/div/aside[3]/div/div[2]/div[1]/input"
                # Usamos fill para limpar e escrever o nome completo
                self.page.locator(input_xpath).fill(item_encontrado['nome_completo'])
                
                # Dica: Geralmente após o fill em sistemas CRM, 
                # pode ser necessário apertar "Enter" para confirmar a busca
                self.page.keyboard.press("Enter")
                
                print(f"Input preenchido com: {item_encontrado['nome_completo']}")
                self.root.after(0, lambda: messagebox.showinfo("Sucesso", f"Encontrado: {item_encontrado['nome_tratamento']}\nPreenchido: {item_encontrado['nome_completo']}"))
            else:
                self.root.after(0, lambda: messagebox.showwarning("Aviso", "Nenhum nome da lista foi encontrado nas mensagens."))

        except Exception as e:
            erro = f"Erro na automação: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Erro", erro))
        
        finally:
            self.root.after(0, lambda: self.btn_rodar.config(state=tk.NORMAL))

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomationApp(root)
    root.mainloop()