import setuptools  # Register distutils fallback
import os
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import re
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

class FitgirlExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FitGirl FF Link Extractor (Pro)")
        self.root.geometry("700x750")
        self.root.minsize(550, 600)
        
        # Configure layout weighting
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1) # Checklist area
        self.root.rowconfigure(5, weight=1) # Output area

        self.checkbox_vars = {}  # Store {url: BooleanVar}
        
        # --- Add this style configuration ---
        self.style = ttk.Style()
        self.style.theme_use("clam")  # Ensures color customization works
        self.style.configure(
            "Custom.Horizontal.TProgressbar",
            background="#24890d",   # Green color matching FitGirl's style
            troughcolor="#e0e0e0",  # Light grey empty background track
            bordercolor="#24890d",  # Matching border
            lightcolor="#24890d",
            darkcolor="#24890d"
        )
        # ------------------------------------

        self.setup_ui()

        # Bind MouseWheel globally
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Button-4>", self._on_mousewheel) 
        self.root.bind_all("<Button-5>", self._on_mousewheel)

    def setup_ui(self):
        # 1. Input Frame
        input_frame = ttk.Frame(self.root, padding="10 10 10 5")
        input_frame.grid(row=0, column=0, sticky="ew")
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="FitGirl Game URL:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        
        self.url_var = tk.StringVar()
        self.url_var.set("https://fitgirl-repacks.site/grand-theft-auto-v/")
        self.url_entry = ttk.Entry(input_frame, textvariable=self.url_var, font=("Arial", 10))
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        
        self.fetch_btn = ttk.Button(input_frame, text="1. Fetch Links", command=self.start_fetch_thread)
        self.fetch_btn.grid(row=2, column=0, columnspan=2, pady=5)

        # 2. Status Label
        self.status_var = tk.StringVar()
        self.status_var.set("Waiting for input...")
        status_label = ttk.Label(self.root, textvariable=self.status_var, font=("Arial", 9, "italic"), foreground="#555")
        status_label.grid(row=1, column=0, sticky="w", padx=10)

        # 3. Checklist Area (Scrollable)
        checklist_container = ttk.LabelFrame(self.root, text="Found Parts (Uncheck unwanted)", padding="5 5 5 5")
        checklist_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        checklist_container.rowconfigure(0, weight=1)
        checklist_container.columnconfigure(0, weight=1)

        # Canvas & Scrollbar for Checklist
        self.canvas = tk.Canvas(checklist_container, highlightthickness=0)
        self.scrollbar_list = ttk.Scrollbar(checklist_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar_list.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar_list.grid(row=0, column=1, sticky="ns")

        # Checklist Controls
        controls_frame = ttk.Frame(checklist_container)
        controls_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        ttk.Button(controls_frame, text="Select All", command=self.select_all).pack(side="left", padx=2)
        ttk.Button(controls_frame, text="Deselect All", command=self.deselect_all).pack(side="left", padx=2)
        
        self.extract_btn = ttk.Button(controls_frame, text="2. Extract Selected", command=self.start_extraction_thread, state="disabled")
        self.extract_btn.pack(side="right", padx=2)
        self.browser_var = tk.StringVar(value="Auto-Detect Browser")
        self.browser_combo = ttk.Combobox(controls_frame, textvariable=self.browser_var, state="readonly", width=18)
        self.browser_combo['values'] = (
                    "Auto-Detect Browser", 
                    "Google Chrome", 
                    "Microsoft Edge", 
                    "Brave", 
                    "Mozilla Firefox"
                )
        self.browser_combo.pack(side="right", padx=(5, 10))
        self.verbose_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls_frame, text="Verbose", variable=self.verbose_var).pack(side="right", padx=(5, 0))

        # 4. Progress Bar
        self.progress = ttk.Progressbar(
            self.root, 
            orient="horizontal", 
            mode="determinate",
            style="Custom.Horizontal.TProgressbar"  # Apply our custom style here
        )
        self.progress.grid(row=4, column=0, sticky="ew", padx=10, pady=5)

        # 5. Output Links Frame
        output_frame = ttk.LabelFrame(self.root, text="Extracted Direct Links", padding="5 5 5 5")
        output_frame.grid(row=5, column=0, sticky="nsew", padx=10, pady=5)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.text_area = tk.Text(output_frame, wrap="none", font=("Consolas", 9), height=10)
        self.text_area.grid(row=0, column=0, sticky="nsew")
        
        scrollbar_y = ttk.Scrollbar(output_frame, orient="vertical", command=self.text_area.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.text_area.configure(yscrollcommand=scrollbar_y.set)

        scrollbar_x = ttk.Scrollbar(output_frame, orient="horizontal", command=self.text_area.xview)
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.text_area.configure(xscrollcommand=scrollbar_x.set)

        # 6. Bottom Buttons Frame
        btn_frame = ttk.Frame(self.root, padding="10 5 10 10")
        btn_frame.grid(row=6, column=0, sticky="ew")
        
        self.copy_btn = ttk.Button(btn_frame, text="📋 Copy All Links", command=self.copy_to_clipboard)
        self.copy_btn.pack(side="right")
        
        self.clear_btn = ttk.Button(btn_frame, text="Clear Output", command=self.clear_output)
        self.clear_btn.pack(side="right", padx=10)


    # --- Mousewheel Logic ---

    def _on_mousewheel(self, event):
        try:
            # Find exactly what widget the mouse is currently hovering over
            widget = self.root.winfo_containing(event.x_root, event.y_root)
            
            # If hovering over the canvas or any checkbox inside the scrollable frame
            if widget == self.canvas or (widget and str(widget).startswith(str(self.scrollable_frame))):
                if hasattr(event, 'delta') and event.delta != 0:
                    # Windows / macOS
                    direction = -1 if event.delta > 0 else 1
                    self.canvas.yview_scroll(direction, "units")
                elif hasattr(event, 'num'):
                    # Linux
                    if event.num == 4:
                        self.canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        self.canvas.yview_scroll(1, "units")
        except Exception:
            pass


    # --- UI Logic ---

    def select_all(self):
        for var in self.checkbox_vars.values():
            var.set(True)

    def deselect_all(self):
        for var in self.checkbox_vars.values():
            var.set(False)

    def copy_to_clipboard(self):
        links = self.text_area.get(1.0, tk.END).strip()
        if links:
            self.root.clipboard_clear()
            self.root.clipboard_append(links)
            messagebox.showinfo("Success", "All links copied to clipboard!")
        else:
            messagebox.showwarning("Empty", "No links to copy!")

    def clear_output(self):
        self.text_area.delete(1.0, tk.END)
        self.progress.config(value=0)

    def update_ui(self, status=None, progress_val=None, max_val=None, text_append=None):
        if status is not None:
            self.status_var.set(status)
        if max_val is not None:
            self.progress.config(maximum=max_val)
        if progress_val is not None:
            self.progress.config(value=progress_val)
        if text_append is not None:
            self.text_area.insert(tk.END, text_append + "\n")
            self.text_area.see(tk.END)

    def log_verbose(self, message):
        """Append a diagnostic line to the output area when Verbose is enabled."""
        if self.verbose_var.get():
            self.root.after(0, self.update_ui, None, None, None, f"# {message}")
            print(f"[verbose] {message}", flush=True)


    # --- Step 1: Fetching Links ---

    def start_fetch_thread(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid FitGirl URL.")
            return

        self.fetch_btn.config(state="disabled")
        self.extract_btn.config(state="disabled")
        self.status_var.set("Fetching page...")
        
        # Clear existing checkboxes
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.checkbox_vars.clear()

        thread = threading.Thread(target=self.run_fetch, args=(url,), daemon=True)
        thread.start()

    def run_fetch(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            res = requests.get(url, headers=headers, timeout=10) # Restored Timeout
            res.raise_for_status() 
            soup = BeautifulSoup(res.text, 'html.parser')
            
            ff_links = []
            for a in soup.find_all('a', href=True):
                if 'fuckingfast.co' in a['href'] and a['href'] not in ff_links:
                    ff_links.append(a['href'])
            
            self.root.after(0, self.populate_checkboxes, ff_links)
            
        except requests.exceptions.ConnectionError:
            # Restored Network Block warning!
            self.root.after(0, self.update_ui, "Network Error: Cannot reach FitGirl. Is your ISP blocking it? Try a VPN/Custom DNS.")
            self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
        except Exception as e:
            self.root.after(0, self.update_ui, f"Error fetching links: {str(e)}")
            self.root.after(0, lambda: self.fetch_btn.config(state="normal"))

    def populate_checkboxes(self, links):
        if not links:
            self.status_var.set("No FuckingFast links found on this page!")
            self.fetch_btn.config(state="normal")
            return

        for link in links:
            var = tk.BooleanVar(value=True)
            self.checkbox_vars[link] = var
            
            # Extract readable name
            filename = link.split('#')[-1] if '#' in link else link.split('/')[-1]
            
            chk = ttk.Checkbutton(self.scrollable_frame, text=filename, variable=var)
            chk.pack(anchor="w", padx=5, pady=2)

        self.status_var.set(f"Found {len(links)} parts. Select what you need and click Extract.")
        self.fetch_btn.config(state="normal")
        self.extract_btn.config(state="normal")


    # --- Step 2: Extraction ---
    def get_browser_path(self, selected_browser="Auto-Detect Browser"):
        import sys
        
        # Check if running on Linux / Steam Deck
        is_linux = sys.platform.startswith('linux')
        
        browser_paths = {
            "Google Chrome": [
                r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
                r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
                r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/var/lib/flatpak/exports/bin/com.google.Chrome" # Common Steam Deck Flatpak path
            ],
            "Microsoft Edge": [
                r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
                r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
                r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe",
                "/usr/bin/microsoft-edge-stable",
                "/usr/bin/microsoft-edge"
            ],
            "Brave": [
                r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe",
                "/usr/bin/brave-browser",
                "/usr/bin/brave",
                "/var/lib/flatpak/exports/bin/com.brave.Browser" # Common Steam Deck Flatpak path
            ],
            "Mozilla Firefox": [
                r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
                r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",
                r"%LocalAppData%\Mozilla Firefox\firefox.exe",
                "/usr/bin/firefox",
                "/var/lib/flatpak/exports/bin/org.mozilla.firefox"
            ]
        }
        
        if selected_browser != "Auto-Detect Browser":
            paths_to_check = browser_paths.get(selected_browser, [])
        else:
            paths_to_check = []
            for paths in browser_paths.values():
                paths_to_check.extend(paths)

        for path in paths_to_check:
            # os.path.expandvars handles the Windows % variables, safely ignores Linux ones
            expanded_path = os.path.expandvars(path)
            if os.path.exists(expanded_path):
                return expanded_path
        return None
    

    def start_extraction_thread(self):
        selected_links = [url for url, var in self.checkbox_vars.items() if var.get()]
        
        if not selected_links:
            messagebox.showwarning("Warning", "No links selected to extract!")
            return

        self.fetch_btn.config(state="disabled")
        self.extract_btn.config(state="disabled")
        self.clear_output()

        thread = threading.Thread(target=self.run_extraction, args=(selected_links,), daemon=True)
        thread.start()

    def extract_direct_with_curl_cffi(self, page_url):
        """Fast path: resolve via curl_cffi Chrome impersonation (often blocked by CF JS)."""
        from urllib.parse import urljoin
        from curl_cffi import requests as cffi_requests

        base = page_url.split("#", 1)[0]
        session = cffi_requests.Session(impersonate="chrome")
        response = session.get(page_url, timeout=20)
        if response.status_code != 200:
            return None, f"page GET HTTP {response.status_code}"

        html = response.text
        if "Just a moment" in html or "cf-challenge" in html.lower():
            return None, "Cloudflare JS challenge page (curl_cffi cannot solve it)"

        match_old = re.search(r'window\.open\("(https://dl\.fuckingfast\.co/dl/[^"]+)"\)', html)
        if match_old:
            return match_old.group(1), None

        htmx_match = re.search(r'hx-(?:post|get)="([^"]+)"', html)
        if not htmx_match:
            return None, "no hx-post/get in page HTML"

        endpoint_path = htmx_match.group(1)
        is_get = htmx_match.group(0).lower().startswith("hx-get")
        endpoint_url = urljoin(page_url, endpoint_path)
        headers = {
            "HX-Request": "true",
            "HX-Current-URL": base,
            "Referer": base,
            "Origin": "https://fuckingfast.co",
        }
        if is_get:
            api_resp = session.get(endpoint_url, headers=headers, timeout=20, allow_redirects=False)
        else:
            api_resp = session.post(endpoint_url, headers=headers, timeout=20, allow_redirects=False)

        direct_link = (
            api_resp.headers.get("hx-redirect")
            or api_resp.headers.get("HX-Redirect")
            or api_resp.headers.get("location")
            or api_resp.headers.get("Location")
        )
        if not direct_link and api_resp.text:
            dl_match = re.search(r'(https://dl\.fuckingfast\.co/dl/[^"\s\'<>]+)', api_resp.text)
            if dl_match:
                direct_link = dl_match.group(1)

        if direct_link:
            return direct_link, None
        return None, f"/go returned HTTP {api_resp.status_code}; body={api_resp.text[:80]!r}"

    def _install_ff_hooks(self, driver):
        """Capture /go HX-Redirect and suppress ad popups (FitFast-style)."""
        driver.execute_script(
            """
            window.open = function(){ return null; };
            window.__ff = {url: null, status: null, body: null, clicks: 0};
            if (!window.__ffHookInstalled) {
                window.__ffHookInstalled = true;
                const capture = (xhr) => {
                    try {
                        const redir = xhr.getResponseHeader('HX-Redirect')
                            || xhr.getResponseHeader('hx-redirect')
                            || xhr.getResponseHeader('Location');
                        window.__ff.status = xhr.status;
                        window.__ff.body = (xhr.responseText || '').slice(0, 300);
                        if (redir) window.__ff.url = redir;
                    } catch (e) {}
                };
                const origOpen = XMLHttpRequest.prototype.open;
                XMLHttpRequest.prototype.open = function(method, url) {
                    this.__ffUrl = url;
                    this.addEventListener('load', function() {
                        if (String(this.__ffUrl || '').includes('/go')) capture(this);
                    });
                    return origOpen.apply(this, arguments);
                };
                document.addEventListener('htmx:afterRequest', function(evt) {
                    try { if (evt.detail && evt.detail.xhr) capture(evt.detail.xhr); } catch (e) {}
                });
                document.addEventListener('htmx:beforeOnLoad', function(evt) {
                    try {
                        const redir = evt.detail.xhr.getResponseHeader('HX-Redirect')
                            || evt.detail.xhr.getResponseHeader('hx-redirect');
                        if (redir) {
                            window.__ff.url = redir;
                            window.__ff.status = evt.detail.xhr.status;
                            evt.detail.shouldSwap = false;
                        }
                    } catch (e) {}
                });
            }
            """
        )

    def _capture_from_performance_logs(self, driver):
        """Fallback: scrape Chrome performance logs for hx-redirect on /go."""
        try:
            import json
            for entry in driver.get_log("performance"):
                try:
                    msg = json.loads(entry["message"])["message"]
                except Exception:
                    continue
                if msg.get("method") != "Network.responseReceived":
                    continue
                params = msg.get("params") or {}
                resp = params.get("response") or {}
                url = resp.get("url") or ""
                if "/go" not in url or "/f/" not in url:
                    continue
                headers = {str(k).lower(): v for k, v in (resp.get("headers") or {}).items()}
                redir = headers.get("hx-redirect") or headers.get("location")
                if redir:
                    return redir
        except Exception:
            pass
        return None

    def extract_direct_with_browser(self, driver, link, index, total):
        """FitFast flow: load page, click download twice, capture hx-redirect."""
        self.log_verbose(f"[{index}/{total}] Opening in browser: {link}")
        driver.get(link)

        try:
            driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {"behavior": "deny", "downloadPath": "/tmp"},
            )
        except Exception:
            pass

        # Give Cloudflare passive JS challenge time to finish.
        time.sleep(2.5)

        button_ready = False
        for attempt in range(30):
            page_html = driver.page_source
            match_old = re.search(r'window\.open\("(https://dl\.fuckingfast\.co/dl/[^"]+)"\)', page_html)
            if match_old:
                self.log_verbose(f"[{index}/{total}] Found window.open URL")
                return match_old.group(1), None

            has_btn = driver.execute_script(
                "return !!document.querySelector('a.link-button, [hx-post*=\"/go\"], [hx-get*=\"/go\"]');"
            )
            if has_btn:
                button_ready = True
                break

            if attempt % 5 == 0:
                try:
                    title = driver.title
                except Exception:
                    title = None
                cf_hint = "just a moment" in page_html.lower() or "turnstile" in page_html.lower()
                self.log_verbose(
                    f"[{index}/{total}] Waiting for download button (attempt {attempt + 1}/30)"
                    f"{f', title={title!r}' if title else ''}"
                    f"{' [possible CF]' if cf_hint else ''}"
                )
            time.sleep(1)

        if not button_ready:
            return None, "download button never appeared (Cloudflare or page change?)"

        self._install_ff_hooks(driver)
        self.log_verbose(f"[{index}/{total}] Clicking a.link-button twice (FitFast flow)")

        # First click often fires an ad/popup; second click triggers /go.
        for click_num in (1, 2):
            clicked = driver.execute_script(
                """
                const el = document.querySelector('a.link-button')
                    || document.querySelector('[hx-post*="/go"], [hx-get*="/go"], [hx-post], [hx-get]');
                if (!el) return false;
                el.click();
                window.__ff.clicks = (window.__ff.clicks || 0) + 1;
                return true;
                """
            )
            if not clicked:
                return None, f"click {click_num}: download button not found"
            self.log_verbose(f"[{index}/{total}] Click {click_num} OK")
            if click_num == 1:
                time.sleep(1.2)

        deadline = time.time() + 20
        last_status = None
        last_body = None
        while time.time() < deadline:
            try:
                current = driver.current_url or ""
            except Exception:
                current = ""
            if "dl.fuckingfast.co" in current:
                self.log_verbose(f"[{index}/{total}] Captured via navigation")
                return current.split("#", 1)[0], None

            info = driver.execute_script("return window.__ff || null;")
            if isinstance(info, dict):
                if info.get("url"):
                    self.log_verbose(
                        f"[{index}/{total}] Captured via XHR/HTMX (status={info.get('status')})"
                    )
                    return info["url"], None
                if info.get("status") not in (None, 0):
                    last_status = info.get("status")
                    last_body = info.get("body")

            perf_url = self._capture_from_performance_logs(driver)
            if perf_url:
                self.log_verbose(f"[{index}/{total}] Captured via performance log")
                return perf_url, None

            time.sleep(0.25)

        if last_status is not None:
            return None, f"after double-click /go -> HTTP {last_status}; body={last_body!r}"
        return None, "double-clicked download but no hx-redirect within 20s"

    def _create_browser_driver(self, browser_executable, browser_name, version=None):
        if browser_name.lower() == "firefox":
            from selenium import webdriver
            from selenium.webdriver.firefox.options import Options
            opts = Options()
            opts.binary_location = browser_executable
            opts.set_preference("dom.webdriver.enabled", False)
            opts.set_preference("useAutomationExtension", False)
            return webdriver.Firefox(options=opts)

        if browser_name.lower() == "msedge":
            from selenium import webdriver
            from selenium.webdriver.edge.options import Options
            opts = Options()
            opts.binary_location = browser_executable
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.set_capability("ms:loggingPrefs", {"performance": "ALL"})
            return webdriver.Edge(options=opts)

        opts = uc.ChromeOptions()
        opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        return uc.Chrome(
            options=opts,
            use_subprocess=True,
            browser_executable_path=browser_executable,
            version_main=version,
        )

    def run_extraction(self, links):
        driver = None
        total = len(links)
        verbose = self.verbose_var.get()

        try:
            # curl_cffi is a fast path only. Current CF often requires a real
            # browser double-click (FitFast flow); fall back immediately on failure.
            cffi_ok = False
            try:
                import curl_cffi  # noqa: F401
                cffi_ok = True
            except ImportError:
                cffi_ok = False

            remaining = list(enumerate(links, 1))
            if cffi_ok:
                self.root.after(
                    0, self.update_ui, "Trying curl_cffi fast path (1 probe)...", 0, total
                )
                probe_link = links[0]
                self.log_verbose(f"Probing curl_cffi with: {probe_link}")
                try:
                    probe_url, probe_err = self.extract_direct_with_curl_cffi(probe_link)
                except Exception as e:
                    probe_url, probe_err = None, f"{type(e).__name__}: {e}"

                if probe_url:
                    # Fast path works — resolve everything with curl_cffi.
                    self.log_verbose("curl_cffi probe OK — using it for all links")
                    self.root.after(0, self.update_ui, None, 1, None, probe_url)
                    remaining = []
                    for i, link in enumerate(links[1:], 2):
                        filename = link.split("#")[-1] if "#" in link else link.split("/")[-1]
                        self.root.after(0, self.update_ui, f"Processing [{i}/{total}]: {filename}")
                        self.log_verbose(f"[{i}/{total}] curl_cffi: {link}")
                        try:
                            direct_url, err = self.extract_direct_with_curl_cffi(link)
                        except Exception as e:
                            direct_url, err = None, f"{type(e).__name__}: {e}"
                        if direct_url:
                            self.root.after(0, self.update_ui, None, i, None, direct_url)
                        else:
                            self.log_verbose(f"[{i}/{total}] curl_cffi miss: {err}")
                            remaining.append((i, link))
                        time.sleep(0.5)
                    if not remaining:
                        self.root.after(
                            0, self.update_ui, f"Extraction complete! Processed {total} links."
                        )
                        return
                    self.log_verbose(
                        f"Falling back to browser for {len(remaining)} remaining link(s)"
                    )
                else:
                    self.log_verbose(
                        f"curl_cffi probe failed ({probe_err}); "
                        "using browser double-click for all links"
                    )
                    remaining = list(enumerate(links, 1))

            selected_browser = self.browser_var.get()
            browser_executable = self.get_browser_path(selected_browser)
            if not browser_executable:
                self.root.after(
                    0,
                    self.update_ui,
                    f"Error: Could not find {selected_browser} on your system.",
                )
                for i, link in remaining:
                    filename = link.split("#")[-1] if "#" in link else link.split("/")[-1]
                    self.root.after(
                        0, self.update_ui, None, i, None, f"# FAILED: {filename} ({link})"
                    )
                return

            browser_name = os.path.basename(browser_executable).replace(".exe", "")
            self.root.after(
                0,
                self.update_ui,
                f"Browser resolve via {browser_name} (double-click download)...",
                0,
                total,
            )
            self.log_verbose(f"Using browser FitFast-style flow with {browser_name}")

            try:
                driver = self._create_browser_driver(browser_executable, browser_name)
            except Exception as e:
                error_msg = str(e)
                if (
                    browser_name.lower() not in ["firefox", "msedge"]
                    and "Current browser version is" in error_msg
                ):
                    match = re.search(r"Current browser version is (\d+)", error_msg)
                    if match:
                        correct_version = int(match.group(1))
                        self.root.after(
                            0,
                            self.update_ui,
                            f"Auto-fixing ChromeDriver version to v{correct_version}...",
                        )
                        driver = self._create_browser_driver(
                            browser_executable, browser_name, version=correct_version
                        )
                    else:
                        raise
                else:
                    raise

            for i, link in remaining:
                filename = link.split("#")[-1] if "#" in link else link.split("/")[-1]
                self.root.after(0, self.update_ui, f"Processing [{i}/{total}]: {filename}")
                try:
                    direct_url, err = self.extract_direct_with_browser(driver, link, i, total)
                    if direct_url:
                        self.root.after(0, self.update_ui, None, i, None, direct_url)
                    else:
                        self.root.after(
                            0,
                            self.update_ui,
                            None,
                            i,
                            None,
                            f"# FAILED: {filename} ({link})",
                        )
                        if verbose:
                            self.log_verbose(f"[{i}/{total}] FAIL detail: {err}")
                except Exception as e:
                    self.root.after(
                        0,
                        self.update_ui,
                        None,
                        i,
                        None,
                        f"# ERROR: {str(e)} -> {filename}",
                    )
                    self.log_verbose(f"[{i}/{total}] Exception: {type(e).__name__}: {e}")

            self.root.after(0, self.update_ui, f"Extraction complete! Processed {total} links.")

        except Exception as e:
            self.root.after(0, self.update_ui, f"Critical Error: {str(e)}")

        finally:
            self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
            self.root.after(0, lambda: self.extract_btn.config(state="normal"))
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
        
    app = FitgirlExtractorApp(root)
    root.mainloop()
