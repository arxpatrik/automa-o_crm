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
            seletor_coluna = "#ppl_received"
            indice_card = 0
            ciclo = 1
        
            while self.executando:
                while self.pausado:
                    self.page.wait_for_timeout(500)
                    if not self.executando: break
                if not self.executando: break

                self.log(f"\n--- [PASSO] CARD ÍNDICE {indice_card} (ciclo {ciclo}) ---")
                try:
                    self.page.wait_for_selector(seletor_cards, timeout=5000)
                except:
                    self.log("[PASSO] Nenhum card visível.")
                    break

                cards = self.page.locator(seletor_cards)
                total_cards = cards.count()
                
                if indice_card >= total_cards:
                    # Tentar rolar a coluna para baixo para carregar mais cards
                    self.log(f"[INFO] Índice {indice_card} atingiu limite ({total_cards} visíveis). Rolando para carregar mais...")
                    coluna = self.page.locator(seletor_coluna)
                    try:
                        coluna.evaluate("el => el.scrollTop += 1500")
                    except:
                        self.page.evaluate("window.scrollBy(0, 1500)")
                    self.page.wait_for_timeout(2000)

                    novo_total = self.page.locator(seletor_cards).count()
                    if novo_total > total_cards:
                        self.log(f"[INFO] Novos cards carregados: {novo_total} (eram {total_cards}). Continuando...")
                        continue  # volta ao topo do loop com o mesmo indice_card
                    else:
                        # Sem novos cards — reinicia do início
                        self.log(f"\n{'='*50}")
                        self.log(f"[INFO] Fim do ciclo {ciclo}. Reiniciando do topo da fila...")
                        self.log(f"{'='*50}\n")
                        # Rolar de volta ao topo da coluna
                        try:
                            coluna.evaluate("el => el.scrollTop = 0")
                        except:
                            pass
                        self.page.wait_for_timeout(3000)
                        indice_card = 0
                        ciclo += 1
                        continue

                card = cards.nth(indice_card)
                if not card.is_visible():
                    self.log(f"[PASSO] Card {indice_card} não visível. Rolando para visualizar...")
                    try:
                        card.scroll_into_view_if_needed()
                        self.page.wait_for_timeout(500)
                    except:
                        indice_card += 1
                        continue
                
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
                
                # Padrão com \s* para tolerar 'alonsoa' (sem espaço no texto do CRM)
                # Captura o nome variável (grupo 1) entre 'transferida de' e 'para julliane'
                padrao_extracao = re.compile(
                    r"carlos eduardo de souza alonso\s*"
                    r"a negociação foi transferida de\s+(.+?)\s+"
                    r"para julliane\s+tha[ií]ssa\s+capuchinho\s+andrade",
                    re.IGNORECASE
                )

                for j in range(total_msg):
                    texto_raw = mensagens_locators.nth(j).inner_text()
                    texto_limpo = self._normalizar_texto(texto_raw)
                    self.log(f"[DEBUG] msg {j}: {texto_limpo[:120]}...")

                    m = padrao_extracao.search(texto_limpo)
                    if m:
                        nome_extraido = m.group(1).strip().lower()
                        self.log(f"[MATCH] Nome extraído da mensagem: '{nome_extraido}'")
                        # Busca o item no JSON pelo nome_tratamento
                        for item in dados_json:
                            if item['nome_tratamento'].lower().strip() == nome_extraido:
                                item_correspondente = item
                                self.log(f"[MATCH] Item JSON encontrado: {item['nome_completo']}")
                                break
                        if not item_correspondente:
                            self.log(f"[AVISO] '{nome_extraido}' não encontrado no JSON. Será usado fallback na transferência.")
                            # Cria um item genérico para acionar o fluxo de transferência (o fallback cuidará do nome_completo)
                            item_correspondente = {"nome_tratamento": nome_extraido, "nome_completo": "__FALLBACK__"}
                        break

                # ── Ação ─────────────────────────────────────────────────────
                tentativa = 1
                while tentativa <= 2:
                    if not item_correspondente:
                        self.log("[INFO] Sem match. Fechando e avançando.")
                        self._fechar_card()
                        indice_card += 1
                        break

                    nome_comp = item_correspondente['nome_completo']
                    FALLBACK_NOME = "Patrik Mateus da Silva Dias"
                    self.log(f"[PASSO] Transferindo para: {nome_comp} (Tentativa {tentativa})")
                    
                    self.page.locator("#modal_negotiation_responsible_name").click()
                    self.log("[PASSO] Botão de transferência clicado.")
                    
                    secao_usuario = self.page.locator("aside:has-text('Para o usuário:')")
                    secao_usuario.locator("div.fs-label").first.click()

                    search_input = secao_usuario.locator("div.fs-search input")
                    search_input.wait_for(state="visible")
                    search_input.fill(nome_comp)
                    self.page.wait_for_timeout(1000)

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
                                try:
                                    backdrop = self.page.locator("div.modal-backdrop")
                                    if backdrop.is_visible(timeout=1500):
                                        backdrop.click()
                                        self.log("[PASSO] Modal fechado via clique no backdrop.")
                                        fechou_modal = True
                                except:
                                    pass
                            if not fechou_modal:
                                self.page.mouse.click(10, 300)
                                self.log("[PASSO] Modal fechado via clique fora (coordenadas).")
                            self.page.wait_for_timeout(800)
                            alerta_impediu = True
                    except Exception as e:
                        self.log(f"[ERRO] Falha ao tratar alerta: {e}")

                    if alerta_impediu and tentativa == 1:
                        self.log("[FALLBACK] Indo para tabQuotation e alterando dados para re-tentativa...")
                        try:
                            # Clica na aba de Cotação
                            self.page.locator("#tabQuotation").click()
                            self.page.wait_for_timeout(1000)
                            
                            # Modifica Placa
                            placa_input = self.page.locator("#vhclPlates")
                            placa_val = placa_input.input_value()
                            if placa_val:
                                novo_val = placa_val[:-1]
                                placa_input.fill(novo_val)
                                self.log(f"[PASSO] Placa alterada: {placa_val} -> {novo_val}")
                                
                            # Modifica Chassi
                            chassi_input = self.page.locator("#vhclChassi")
                            chassi_val = chassi_input.input_value()
                            if chassi_val:
                                novo_val = chassi_val[:-1]
                                chassi_input.fill(novo_val)
                                self.log(f"[PASSO] Chassi alterado: {chassi_val} -> {novo_val}")
                            
                            self.page.wait_for_timeout(500)
                            
                            # Clica em Salvar
                            self.log("[PASSO] Clicando em Salvar alterações...")
                            self.page.locator("#vhclEditSave").click()
                            self.page.wait_for_timeout(2000)
                            
                            tentativa += 1
                            continue # Volta para o início do while para tentar transferir de novo
                        except Exception as e:
                            self.log(f"[ERRO] Falha ao alterar dados: {e}")
                            self._fechar_card()
                            indice_card += 1
                            break
                    
                    # Se chegou aqui, ou deu certo ou falhou a segunda tentativa
                    self._fechar_card()
                    if alerta_impediu:
                        self.log("[AVISO] Transferência falhou em ambas as tentativas.")
                        indice_card += 1
                    else:
                        self.log("[INFO] Transferência OK. Card saiu da fila, índice mantido.")
                    break

                self.page.wait_for_timeout(1000)

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
