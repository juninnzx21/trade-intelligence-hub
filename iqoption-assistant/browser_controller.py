from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
import socket
import subprocess
import time
from typing import Iterable

from playwright.sync_api import BrowserContext, Error, Page, Playwright, sync_playwright

from config import Settings


@dataclass
class BrowserSession:
    playwright: Playwright
    context: BrowserContext
    page: Page

    def close(self) -> None:
        self.context.close()
        self.playwright.stop()


class BrowserController:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger
        self._managed_process: subprocess.Popen[str] | None = None

    def is_chrome_running(self) -> bool:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
            capture_output=True,
            text=True,
            check=False,
        )
        return "chrome.exe" in result.stdout.lower()

    def connect(self) -> BrowserSession:
        playwright = sync_playwright().start()
        self.logger.info("Chrome running: %s", self.is_chrome_running())

        if self._port_open("127.0.0.1", self.settings.chrome_debug_port):
            self.logger.info("Conectando a uma instancia Chrome ja exposta na porta %s", self.settings.chrome_debug_port)
            browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{self.settings.chrome_debug_port}")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = self._ensure_page(context)
            return BrowserSession(playwright=playwright, context=context, page=page)

        if self.is_chrome_running():
            self.logger.warning("Chrome aberto sem porta de automacao. Abrindo uma instancia controlada separada.")
        else:
            self.logger.info("Chrome nao estava aberto. Abrindo uma instancia controlada.")

        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.settings.chrome_user_data_dir),
            channel="chrome",
            headless=False,
            args=[f"--remote-debugging-port={self.settings.chrome_debug_port}"],
            executable_path=self.settings.chrome_path,
        )
        page = self._ensure_page(context)
        return BrowserSession(playwright=playwright, context=context, page=page)

    def open_traderoom(self, page: Page) -> None:
        current_url = page.url
        if "iqoption.com/traderoom" in current_url:
            self.logger.info("Traderoom ja estava aberta.")
            return
        self.logger.info("Acessando %s", self.settings.iq_option_url)
        page.goto(self.settings.iq_option_url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(2_000)

    def ensure_page_ready(self, page: Page) -> bool:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15_000)
            _ = page.title()
            return True
        except Exception:
            self.logger.error("A pagina nao respondeu como esperado.")
            return False

    def wait_for_manual_login(self, page: Page) -> None:
        if not self._login_needed(page):
            self.logger.info("Nenhum bloqueio de login detectado.")
            return

        self.logger.warning("A pagina parece exigir login manual. A automacao vai pausar.")
        print("Login manual necessario na IQ Option. Faça o login no Chrome e pressione ENTER quando terminar.")
        input("> ")

        deadline = time.time() + self.settings.login_wait_timeout_seconds
        while time.time() < deadline:
            page.wait_for_timeout(2_000)
            if not self._login_needed(page):
                self.logger.info("Login manual concluido.")
                return
        raise TimeoutError("Tempo esgotado aguardando login manual.")

    def select_asset(self, page: Page, asset: str) -> bool:
        self.logger.info("Tentando preparar selecao do ativo %s", asset)
        candidates = [
            lambda: page.get_by_placeholder("Search"),
            lambda: page.get_by_placeholder("Pesquisar"),
            lambda: page.locator("input[type='search']").first,
            lambda: page.locator("input").nth(0),
        ]

        for build_locator in candidates:
            try:
                locator = build_locator()
                if hasattr(locator, "count") and locator.count() == 0:
                    continue
                locator.click(timeout=2_000)
                locator.fill(asset, timeout=2_000)
                locator.press("Enter")
                page.wait_for_timeout(1_500)
                self._show_overlay(page, f"Ativo solicitado: {asset}. Confira na tela antes de operar.", "#f59e0b")
                self.logger.info("Selecao do ativo tentada com sucesso.")
                return True
            except Exception:
                continue

        self.logger.warning("Nao foi possivel selecionar o ativo automaticamente. Selecione manualmente.")
        self._show_overlay(page, f"Selecione manualmente o ativo {asset}.", "#ef4444")
        return False

    def detect_current_asset(self, page: Page) -> str:
        candidates = [
            "text=/[A-Z]{3,10}\\/[A-Z]{3,10}/",
            "[data-test*=asset]",
            "[class*=asset]",
            "[class*=instrument]",
        ]
        for selector in candidates:
            try:
                locator = page.locator(selector).first
                if locator.count() == 0:
                    continue
                text = locator.inner_text(timeout=2_000).strip().upper().replace("-", "/")
                if "/" in text and len(text) <= 20:
                    self.logger.info("Ativo atual detectado: %s", text)
                    return text
            except Exception:
                continue
        return ""

    def asset_matches_signal(self, page: Page, asset: str) -> bool:
        current_asset = self.detect_current_asset(page)
        if not current_asset:
            self.logger.warning("Nao foi possivel confirmar o ativo atual na tela.")
            return False
        return current_asset == asset

    def detect_account_label(self, page: Page) -> str:
        probes: Iterable[str] = (
            "text=/demo|practice|treino|treinamento/i",
            "text=/real/i",
        )
        for selector in probes:
            try:
                locator = page.locator(selector).first
                if locator.count() > 0:
                    text = locator.inner_text(timeout=2_000).strip()
                    if text:
                        self.logger.info("Rotulo de conta detectado: %s", text)
                        return text
            except Exception:
                continue
        return ""

    def highlight_direction(self, page: Page, direction: str) -> bool:
        text_candidates = {
            "COMPRA": ["Comprar", "Buy", "Higher", "Call", "Up"],
            "VENDA": ["Vender", "Sell", "Lower", "Put", "Down"],
        }[direction]

        for text in text_candidates:
            try:
                locator = page.get_by_text(text, exact=False).first
                if locator.count() == 0:
                    continue
                locator.scroll_into_view_if_needed(timeout=2_000)
                locator.evaluate(
                    "(node) => { node.style.outline = '4px solid #22c55e'; node.style.boxShadow = '0 0 0 6px rgba(34,197,94,.25)'; }"
                )
                self._show_overlay(page, f"Clique manualmente em {direction} para o ativo preparado.", "#22c55e")
                self.logger.info("Botao de %s destacado na tela.", direction)
                return True
            except Exception:
                continue

        self.logger.warning("Nao foi possivel destacar o botao de %s automaticamente.", direction)
        self._show_overlay(page, f"Nao localizei o botao de {direction}. Confira manualmente antes de agir.", "#ef4444")
        return False

    def click_direction_demo_only(self, page: Page, direction: str) -> bool:
        text_candidates = {
            "COMPRA": ["Comprar", "Buy", "Higher", "Call", "Up"],
            "VENDA": ["Vender", "Sell", "Lower", "Put", "Down"],
        }[direction]

        for text in text_candidates:
            try:
                locator = page.get_by_text(text, exact=False).first
                if locator.count() == 0:
                    continue
                locator.click(timeout=2_000)
                self.logger.warning("Clique experimental executado em conta DEMO para %s.", direction)
                self._show_overlay(page, f"Clique DEMO experimental executado: {direction}.", "#22c55e")
                return True
            except Exception:
                continue
        return False

    def browser_alive(self, page: Page) -> bool:
        try:
            return not page.is_closed()
        except Exception:
            return False

    def _ensure_page(self, context: BrowserContext) -> Page:
        for page in context.pages:
            if "iqoption.com/traderoom" in page.url:
                return page
        if context.pages:
            return context.pages[0]
        return context.new_page()

    def _login_needed(self, page: Page) -> bool:
        url = page.url.lower()
        if "login" in url or "auth" in url:
            return True
        try:
            password_fields = page.locator("input[type='password']")
            if password_fields.count() > 0:
                return True
        except Error:
            pass
        try:
            sign_in = page.get_by_text("Sign in", exact=False)
            if sign_in.count() > 0:
                return True
        except Error:
            pass
        try:
            entrar = page.get_by_text("Entrar", exact=False)
            if entrar.count() > 0:
                return True
        except Error:
            pass
        return False

    def _show_overlay(self, page: Page, message: str, color: str) -> None:
        script = """
        ([message, color]) => {
          let node = document.getElementById('__iqassistant_overlay__');
          if (!node) {
            node = document.createElement('div');
            node.id = '__iqassistant_overlay__';
            document.body.appendChild(node);
          }
          node.textContent = message;
          Object.assign(node.style, {
            position: 'fixed',
            top: '16px',
            right: '16px',
            zIndex: '999999',
            padding: '14px 18px',
            borderRadius: '12px',
            fontFamily: 'Segoe UI, sans-serif',
            fontSize: '16px',
            fontWeight: '700',
            color: '#ffffff',
            background: color,
            boxShadow: '0 12px 30px rgba(0,0,0,.35)',
          });
        }
        """
        try:
            page.evaluate(script, [message, color])
        except Exception:
            self.logger.debug("Falha ao desenhar overlay na pagina.")

    @staticmethod
    def _port_open(host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.8)
            return sock.connect_ex((host, port)) == 0
