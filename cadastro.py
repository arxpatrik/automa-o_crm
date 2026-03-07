import tkinter as tk
from tkinter import messagebox
import threading
from playwright.sync_api import sync_playwright
import json
import re

class AutomationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Controle Playwright")
        self.root.geometry("450x650")

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

        lb_log = tk.Label(root, text="Log de Processos:", font=("Arial", 10, "bold"))
        lb_log.pack(pady=(10, 0))

        self.log_text = tk.Text(root, height=12, width=50, state=tk.DISABLED, bg="#f8f9fa", font=("Consolas", 9))
        self.log_text.pack(padx=10, pady=5)

        self.scrollbar = tk.Scrollbar(root, command=self.log_text.yview)
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
        def _append():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"{mensagem}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        print(mensagem)
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
        
        self.log(f"[DEBUG] 4. Preenchendo login...")
        self.page.locator("#emailField").fill("arx.patrik@gmail.com")
        self.page.locator("#j_password").fill("Arx2025")
        
        self.log("[DEBUG] 5. Clicando em Logar...")
        self.page.locator("input.btn_logar").click()
        
        self.log("[DEBUG] 6. Aguardando carregamento do painel...")
        self.page.wait_for_selector("#ppl_received", timeout=30000)
        
        self.log("[DEBUG] 7. Login concluído!")
        self.root.after(0, lambda: self.btn_rodar.config(state=tk.NORMAL))
        self.root.after(0, lambda: messagebox.showinfo("Info", "Login realizado!"))

    def _fechar_card(self):
        """
        Fecha o modal da negociação usando o botão exato identificado via XPath.
        Estratégias em ordem de prioridade:
          1. button[data-dismiss='modal'][aria-label='Close']  dentro de .content-close-modal
          2. XPath absoluto fornecido
          3. Escape como último recurso
        Confirma fechamento aguardando #wallmessages ficar oculto.
        """
        self.log("[PASSO] Fechando modal da negociação...")

        fechou = False

        # ── Estratégia 1: seletor CSS confiável pelo atributo do botão ──────
        try:
            btn = self.page.locator(
                "div.content-close-modal button[data-dismiss='modal'][aria-label='Close']"
            ).first
            if btn.is_visible(timeout=2000):
                btn.click()
                self.log("[PASSO] Modal fechado via CSS (content-close-modal button).")
                fechou = True
        except:
            pass

        # ── Estratégia 2: XPath absoluto exato ──────────────────────────────
        if not fechou:
            try:
                btn_xpath = self.page.locator(
                    "xpath=/html/body/div[7]/div/div/div/div/div[1]/div/div[2]/div[2]/button"
                ).first
                if btn_xpath.is_visible(timeout=2000):
                    btn_xpath.click()
                    self.log("[PASSO] Modal fechado via XPath absoluto.")
                    fechou = True
            except:
                pass

        # ── Estratégia 3: XPath do pai (div[2]) — clicar no container ───────
        if not fechou:
            try:
                div_xpath = self.page.locator(
                    "xpath=/html/body/div[7]/div/div/div/div/div[1]/div/div[2]/div[2]"
                ).first
                if div_xpath.is_visible(timeout=2000):
                    # Clica no botão filho dentro do container
                    div_xpath.locator("button").first.click()
                    self.log("[PASSO] Modal fechado via XPath do container pai.")
                    fechou = True
            except:
                pass

        # ── Estratégia 4: Escape como fallback ──────────────────────────────
        if not fechou:
            self.log("[AVISO] Nenhum botão encontrado. Usando Escape...")
            self.page.keyboard.press("Escape")

        # ── Confirmação: aguarda #wallmessages sumir ─────────────────────────
        try:
            self.page.wait_for_selector("#wallmessages", state="hidden", timeout=5000)
            self.log("[PASSO] Modal confirmado como fechado.")
        except:
            self.log("[AVISO] wallmessages ainda visível. Tentando Escape adicional...")
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(1500)

        self.page.wait_for_timeout(800)

    def _normalizar_texto(self, texto):
        texto = texto.lower()
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    def _executar_tarefa_em_loop(self):
        if not self.page: return
        try:
            self.log("[PASSO] Abrindo arquivo lista.json...")
            with open('lista.json', 'r', encoding='utf-8') as f:
                dados_json = json.load(f)
            self.log(f"[INFO] {len(dados_json)} registros carregados.")
            
            seletor_cards = "#ppl_received section.pwrcrm-card.card-simple"
            indice_card = 0
        
            while self.executando:
                while self.pausado:
                    self.page.wait_for_timeout(500)
                    if not self.executando: break
                if not self.executando: break

                self.log(f"\n--- [PASSO] CARD ÍNDICE {indice_card} ---")
                try:
                    self.page.wait_for_selector(seletor_cards, timeout=5000)
                except:
                    self.log("[PASSO] Nenhum card visível.")
                    break

                cards = self.page.locator(seletor_cards)
                total_cards = cards.count()
                
                if indice_card >= total_cards:
                    self.log(f"[INFO] Todos os {total_cards} cards analisados.")
                    break

                card = cards.nth(indice_card)
                if not card.is_visible():
                    self.log(f"[PASSO] Card {indice_card} não visível.")
                    break
                
                self.log(f"[PASSO] Abrindo card {indice_card + 1}/{total_cards}...")
                card.scroll_into_view_if_needed()
                card.click()

                try:
                    self.page.wait_for_selector("#wallmessages", timeout=10000)
                    self.page.wait_for_timeout(2000)
                except:
                    self.log("[ERRO] Histórico não carregou. Fechando e pulando.")
                    self._fechar_card()
                    indice_card += 1
                    continue

                # ── Busca de match ───────────────────────────────────────────
                mensagens_locators = self.page.locator("#wallmessages div[data-type='2']")
                item_correspondente = None
                total_msg = mensagens_locators.count()
                self.log(f"[INFO] Mensagens tipo 2: {total_msg}")
                
                for j in range(total_msg):
                    texto_raw = mensagens_locators.nth(j).inner_text()
                    texto_limpo = self._normalizar_texto(texto_raw)
                    self.log(f"[DEBUG] msg {j}: {texto_limpo[:120]}...")

                    for item in dados_json:
                        nome_trat = item['nome_tratamento'].lower().strip()
                        padrao = (
                            r"a negociação foi transferida de\s+"
                            + re.escape(nome_trat)
                            + r"\s+para julliane\s+tha[ií]ssa\s+capuchinho\s+andrade\s+em uma ação em massa"
                        )
                        if re.search(padrao, texto_limpo):
                            self.log(f"[MATCH] {nome_trat}")
                            item_correspondente = item
                            break
                    if item_correspondente:
                        break

                # ── Ação ─────────────────────────────────────────────────────
                if item_correspondente:
                    nome_comp = item_correspondente['nome_completo']
                    FALLBACK_NOME = "Patrik Mateus da Silva Dias"
                    self.log(f"[PASSO] Transferindo para: {nome_comp}")
                    
                    self.page.locator("#modal_negotiation_responsible_name").click()
                    self.log("[PASSO] Botão de transferência clicado.")
                    
                    secao_usuario = self.page.locator("aside:has-text('Para o usuário:')")
                    secao_usuario.locator("div.fs-label").first.click()

                    search_input = secao_usuario.locator("div.fs-search input")
                    search_input.wait_for(state="visible")
                    search_input.fill(nome_comp)
                    self.page.wait_for_timeout(1000)  # aguarda resultados carregarem

                    opcao = secao_usuario.locator("div.fs-option").filter(has_text=nome_comp)
                    if opcao.count() > 0:
                        opcao.first.click()
                        self.log(f"[PASSO] Usuário '{nome_comp}' selecionado.")
                    else:
                        self.log(f"[AVISO] '{nome_comp}' não encontrado. Usando fallback: {FALLBACK_NOME}")
                        search_input.clear()
                        search_input.fill(FALLBACK_NOME)
                        self.page.wait_for_timeout(1000)
                        secao_usuario.locator("div.fs-option").filter(has_text=FALLBACK_NOME).first.click()
                        self.log(f"[PASSO] Fallback '{FALLBACK_NOME}' selecionado.")
                    
                    self.page.locator("#changeResponsibleQttn").click()
                    self.page.wait_for_timeout(1500)

                    alerta_impediu = False
                    try:
                        alerta = self.page.locator("h3:has-text('Atenção')")
                        if alerta.is_visible(timeout=3000):
                            self.log("[ALERTA] Transferência impedida (já em atendimento).")
                            # 1. Fecha o pop-up de alerta
                            self.page.locator("button.closeModalAlert").first.click()
                            self.page.wait_for_timeout(1000)
                            # 2. Fecha o modal de Trocar Responsável
                            fechou_modal = False
                            try:
                                btn_cancel = self.page.locator("#cancelChangePlan")
                                btn_cancel.wait_for(state="visible", timeout=3000)
                                btn_cancel.click()
                                self.log("[PASSO] Modal fechado via #cancelChangePlan.")
                                fechou_modal = True
                            except:
                                pass
                            if not fechou_modal:
                                # Clique fora do modal (no backdrop) para fechá-lo
                                try:
                                    backdrop = self.page.locator("div.modal-backdrop")
                                    if backdrop.is_visible(timeout=1500):
                                        backdrop.click()
                                        self.log("[PASSO] Modal fechado via clique no backdrop.")
                                        fechou_modal = True
                                except:
                                    pass
                            if not fechou_modal:
                                # Último recurso: clique nas coordenadas do canto superior esquerdo (fora do modal)
                                self.page.mouse.click(10, 300)
                                self.log("[PASSO] Modal fechado via clique fora (coordenadas).")
                            self.page.wait_for_timeout(800)
                            alerta_impediu = True  # sempre avança
                    except Exception as e:
                        self.log(f"[ERRO] Falha ao fechar alerta: {e}")

                    self._fechar_card()

                    if alerta_impediu:
                        indice_card += 1  # card não saiu da fila, avança
                    else:
                        self.log("[INFO] Transferência OK. Card saiu da fila, índice mantido.")
                        # índice NÃO avança — próximo card desce para mesma posição

                else:
                    self.log("[INFO] Sem match. Fechando e avançando.")
                    self._fechar_card()
                    indice_card += 1

                self.page.wait_for_timeout(1000)

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
