import tkinter as tk
from tkinter import messagebox
import threading
from playwright.sync_api import sync_playwright
import json

class AutomationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Controle Playwright")
        self.root.geometry("450x650") # Aumentado para o log

        self.playwright = None
        self.browser = None
        self.page = None
        self.executando = False
        self.pausado = False

        self._cmd_queue = []
        self._cmd_event = threading.Event()
        self._lock = threading.Lock()

        self._pw_thread = threading.Thread(target=self._playwright_worker, daemon=True)
        self._pw_thread.start()

        self.label = tk.Label(root, text="Painel de Controle", font=("Arial", 12, "bold"))
        self.label.pack(pady=10)

        self.btn_abrir = tk.Button(root, text="1. Abrir Navegador e Site",
                                   command=self.thread_abrir_site, bg="#e1e1e1", width=25)
        self.btn_abrir.pack(pady=5)

        self.btn_rodar = tk.Button(root, text="2. Rodar Automação (Fila)",
                                   command=self.thread_rodar_script, state=tk.DISABLED, bg="#d1ffd1", width=25)
        self.btn_rodar.pack(pady=5)

        self.btn_pausar = tk.Button(root, text="Pausar Automação",
                                    command=self.alternar_pausa, state=tk.DISABLED, bg="#fff3cd", width=25)
        self.btn_pausar.pack(pady=5)

        self.btn_debug = tk.Button(root, text="Debugger (Breakpoint)",
                                   command=lambda: breakpoint(), bg="#ffebcc", width=25)
        self.btn_debug.pack(pady=5)

        self.btn_fechar = tk.Button(root, text="Fechar Navegador", command=self.thread_fechar, fg="red")
        self.btn_fechar.pack(pady=10)

        # Tela de Processos (Log)
        lb_log = tk.Label(root, text="Log de Processos:", font=("Arial", 10, "bold"))
        lb_log.pack(pady=(10, 0))

        self.log_text = tk.Text(root, height=12, width=50, state=tk.DISABLED, bg="#f8f9fa", font=("Consolas", 9))
        self.log_text.pack(padx=10, pady=5)

        # Scrollbar para o log
        self.scrollbar = tk.Scrollbar(root, command=self.log_text.yview)
        # self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y) # Pack as separate side might break layout
        self.log_text.config(yscrollcommand=self.scrollbar.set)

    def _playwright_worker(self):
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
                    msg_erro = str(e)
                    print(f"[ERRO] {msg_erro}")
                    self.root.after(0, lambda m=msg_erro: messagebox.showerror("Erro", m))

    def _enqueue(self, cmd):
        with self._lock:
            self._cmd_queue.append(cmd)
        self._cmd_event.set()

    def log(self, mensagem):
        """Adiciona uma mensagem à tela de log de forma thread-safe."""
        def _append():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"{mensagem}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        
        print(mensagem) # Mantém no terminal também
        self.root.after(0, _append)

    def alternar_pausa(self):
        self.pausado = not self.pausado
        texto = "Retomar Automação" if self.pausado else "Pausar Automação"
        cor = "#d1ffd1" if self.pausado else "#fff3cd"
        self.btn_pausar.config(text=texto, bg=cor)
        self.log(f"[STATUS] {'PAUSADO' if self.pausado else 'RETOMADO'}")

    def thread_abrir_site(self):
        self.btn_abrir.config(state=tk.DISABLED)
        self._enqueue(self._abrir_site)

    def thread_rodar_script(self):
        self.executando = True
        self.pausado = False
        self.btn_rodar.config(state=tk.DISABLED)
        self.btn_pausar.config(state=tk.NORMAL)
        self._enqueue(self._executar_tarefa_em_loop)

    def thread_fechar(self):
        self.executando = False
        self._enqueue(self._fechar_browser)

    def _abrir_site(self):
        self.log("\n[DEBUG] 1. Iniciando Navegador Playwright...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False, args=["--start-maximized"])
        
        self.log("[DEBUG] 2. Criando nova página...")
        self.page = self.browser.new_page(no_viewport=True)
        
        self.log("[DEBUG] 3. Navegando para app.powercrm.com.br...")
        self.page.goto("https://app.powercrm.com.br/")
        self.page.wait_for_selector("#emailField")
        
        self.log(f"[DEBUG] 4. Preenchendo login para: arx.patrik@gmail.com")
        self.page.locator("#emailField").fill("arx.patrik@gmail.com")
        self.page.locator("#j_password").fill("Arx2025")
        
        self.log("[DEBUG] 5. Clicando em Logar...")
        self.page.locator("input.btn_logar").click()
        
        self.log("[DEBUG] 6. Aguardando carregamento do painel...")
        self.page.wait_for_selector("#ppl_negotiation", timeout=30000)
        
        self.log("[DEBUG] 7. Login concluído com sucesso!")
        self.root.after(0, lambda: self.btn_rodar.config(state=tk.NORMAL))
        self.root.after(0, lambda: messagebox.showinfo("Info", "Login realizado!"))

    def _executar_tarefa_em_loop(self):
        if not self.page: return
        try:
            self.log("[PASSO] Abrindo arquivo lista.json...")
            with open('lista.json', 'r', encoding='utf-8') as f:
                dados_json = json.load(f)
            self.log(f"[INFO] {len(dados_json)} registros carregados do JSON.")
            
            seletor_cards = "#ppl_negotiation section.pwrcrm-card.card-simple" #
            
            while self.executando:
                while self.pausado:
                    self.page.wait_for_timeout(500)
                    if not self.executando: break
                
                if not self.executando: break

                self.log("\n--- [PASSO] ANALISANDO TOPO DA FILA ---")
                self.page.wait_for_selector(seletor_cards)
                card = self.page.locator(seletor_cards).nth(0) #
                
                if not card.is_visible():
                    self.log("[PASSO] Fila concluída ou card não visível.")
                    break
                
                self.log("[PASSO] Clicando no card...")
                card.scroll_into_view_if_needed()
                card.click()

                self.log("[PASSO] Aguardando histórico de mensagens (#wallmessages)...")
                self.page.wait_for_selector("#wallmessages", timeout=10000)
                self.page.wait_for_timeout(2000)

                self.log("[PASSO] Lendo mensagens do tipo 'Ação em massa'...")
                mensagens_locators = self.page.locator("#wallmessages div[data-type='2']") #
                item_correspondente = None
                
                self.log(f"[PASSO] Total de mensagens encontradas: {mensagens_locators.count()}")
                for j in range(mensagens_locators.count()):
                    texto_raw = mensagens_locators.nth(j).inner_text().lower()
                    texto_limpo = " ".join(texto_raw.split())
                    
                    for item in dados_json:
                        nome_trat = item['nome_tratamento'].lower().strip()
                        
                        # Construção da frase exata solicitada
                        frase_completa = f"carlos eduardo de souza alonso a negociação foi transferida de {nome_trat} para julliane thaíssa capuchinho andrade em uma ação em massa"
                        
                        if frase_completa in texto_limpo:
                            self.log(f"[MATCH] Usuário identificado: {nome_trat}") #
                            item_correspondente = item
                            break
                        
                    if item_correspondente: break

                if item_correspondente:
                    nome_comp = item_correspondente['nome_completo']
                    self.log(f"[PASSO] Iniciando transferência para: {nome_comp}")
                    
                    self.log("[PASSO] Abrindo modal de responsável...")
                    self.page.locator("#modal_negotiation_info_responsible").click() #
                    
                    # Isolar seção do usuário para evitar erro de múltiplos labels
                    self.log("[PASSO] Selecionando campo de usuário...")
                    secao_usuario = self.page.locator("aside:has-text('Para o usuário:')") #
                    secao_usuario.locator("div.fs-label").first.click() #

                    self.log(f"[PASSO] Pesquisando nome: {nome_comp}")
                    search_input = secao_usuario.locator("div.fs-search input") #
                    search_input.wait_for(state="visible")
                    search_input.fill(nome_comp) #
                    
                    self.log("[PASSO] Clicando no resultado da busca...")
                    secao_usuario.locator("div.fs-option").filter(has_text=nome_comp).first.click() #
                    
                    # Botão Transferir
                    self.log("[PASSO] Clicando no botão Transferir (#changeResponsibleQttn)...")
                    self.page.locator("#changeResponsibleQttn").click()

                    # Verificação de Alerta de Atenção (Caso alguém já esteja atendendo)
                    self.log("[PASSO] Verificando possível alerta de 'Atenção'...")
                    try:
                        alerta = self.page.locator("h3:has-text('Atenção')")
                        if alerta.is_visible(timeout=3000):
                            self.log("[ALERTA] Atenção detectada (já em atendimento). Fechando aviso.")
                            self.page.locator("button.closeModalAlert").first.click()
                            self.page.wait_for_timeout(1000)
                        else:
                            self.log("[INFO] Nenhum alerta de atenção detectado.")
                    except:
                        self.log("[INFO] Erro ao verificar ou fechar alerta.")
                        pass
                else:
                    self.log("[INFO] Nenhuma mensagem correspondente encontrada neste card.")

                # Fechamento do card (X no topo direito)
                self.log("[PASSO] Fechando card de negociação...")
                xpath_fechar = "xpath=/html/body/div[7]/div/div/div/div/div[1]/div/div[2]/div[2]/button"
                try:
                    btn_fechar = self.page.locator(xpath_fechar)
                    btn_fechar.wait_for(state="visible", timeout=3000)
                    btn_fechar.click()
                    self.log("[PASSO] Card fechado pelo botão X.")
                except:
                    self.log("[PASSO] Botão X não encontrado, usando tecla Escape...")
                    self.page.keyboard.press("Escape")
                
                self.log("[DEBUG] Aguardando 2 segundos para o próximo card...")
                self.page.wait_for_timeout(2000)

            self.root.after(0, lambda: messagebox.showinfo("Fim", "Processo concluído!"))

        except Exception as e:
            msg_erro = str(e)
            self.root.after(0, lambda m=msg_erro: messagebox.showerror("Erro", m))
        finally:
            self.executando = False
            self.root.after(0, lambda: self.btn_rodar.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_pausar.config(state=tk.DISABLED))

    def _fechar_browser(self):
        self.executando = False
        if self.browser:
            self.browser.close()
            self.playwright.stop()
            self.browser = self.playwright = self.page = None
            self.root.after(0, lambda: self.btn_abrir.config(state=tk.NORMAL))

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomationApp(root)
    root.mainloop()