import setuptools  # Register distutils fallback
import os
import traceback
import datetime

# --- TEMP DIAGNOSTICS (remove after debugging) ---
DIAG_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagnostics.log")

def diag(msg, exc=False):
    line = f"[{datetime.datetime.now():%H:%M:%S}] {msg}"
    if exc:
        line += "\n" + traceback.format_exc()
    print(line, flush=True)
    try:
        with open(DIAG_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
# --------------------------------------------------
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import re
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

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
            diag(f"FETCH ERROR: {e}", exc=True)
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

    def run_extraction(self, links):
        driver = None
        total = len(links)
        
        selected_browser = self.browser_var.get()
        browser_executable = self.get_browser_path(selected_browser)
        
        if not browser_executable:
            self.root.after(0, self.update_ui, f"Error: Could not find {selected_browser} on your system.")
            self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
            self.root.after(0, lambda: self.extract_btn.config(state="normal"))
            return

        browser_name = os.path.basename(browser_executable).replace('.exe', '')
        diag(f"EXTRACTION START: {total} links, browser={selected_browser} -> {browser_executable}")
        self.root.after(0, self.update_ui, f"Initializing using {browser_name} to bypass Cloudflare...", 0, total)
        
        def create_driver(version=None):
            if browser_name.lower() == 'firefox':
                from selenium import webdriver
                from selenium.webdriver.firefox.options import Options
                opts = Options()
                opts.binary_location = browser_executable
                # geckodriver exposes navigator.webdriver regardless of these
                # preferences, so Cloudflare can still detect the session
                opts.set_preference("dom.webdriver.enabled", False)
                return webdriver.Firefox(options=opts)
            elif browser_name.lower() == 'msedge':
                from selenium import webdriver
                from selenium.webdriver.edge.options import Options
                opts = Options()
                opts.binary_location = browser_executable
                opts.add_experimental_option("excludeSwitches", ["enable-automation"])
                opts.add_experimental_option('useAutomationExtension', False)
                opts.add_argument("--disable-blink-features=AutomationControlled")
                return webdriver.Edge(options=opts)
            else:
                opts = uc.ChromeOptions()
                return uc.Chrome(
                    options=opts, 
                    use_subprocess=True, 
                    browser_executable_path=browser_executable, 
                    version_main=version
                )
        
        def ensure_window(drv):
            # Reattach to a surviving window and keep a spare blank tab open,
            # so a site closing its own window can't take the whole browser down
            handles = drv.window_handles
            if not handles:
                raise RuntimeError("all browser windows closed")
            try:
                drv.current_window_handle
            except Exception:
                drv.switch_to.window(handles[-1])
            if len(drv.window_handles) < 2:
                try:
                    drv.execute_script("window.open('about:blank','_blank');")
                except Exception:
                    pass

        def session_is_dead(err):
            msg = str(err)
            return any(s in msg for s in (
                "invalid session id",
                "browser has closed",
                "not connected to DevTools",
                "no such window",
                "web view not found",
                "chrome not reachable",
                "unable to connect to renderer",
                "Tried to run command without establishing a connection",
                "Browsing context has been discarded",
                "Failed to decode response from marionette",
            ))

        working_version = None
        try:
            try:
                driver = create_driver()
            except Exception as e:
                diag(f"DRIVER CREATE ERROR ({browser_name}): {e}", exc=True)
                error_msg = str(e)
                if browser_name.lower() not in ['firefox', 'msedge'] and "Current browser version is" in error_msg:
                    match = re.search(r"Current browser version is (\d+)", error_msg)
                    if match:
                        correct_version = int(match.group(1))
                        working_version = correct_version
                        self.root.after(0, self.update_ui, f"Auto-fixing ChromeDriver version to v{correct_version}...")
                        driver = create_driver(version=correct_version)
                    else:
                        raise e
                else:
                    raise e

            # --- Block downloads globally so Chrome doesn't actually download the 5GB files ---
            if browser_name.lower() != 'firefox':
                try:
                    # (Removed the local 'import os' that was causing the crash!)
                    driver.execute_cdp_cmd(
                        "Browser.setDownloadBehavior", {
                            "behavior": "deny",
                            "downloadPath": os.path.abspath(os.sep)
                        }
                    )
                except:
                    pass
            # ---------------------------------------------------------------------------------

            # --- Javascript Interceptors ---
            js_inject = """
            // 1. Kill popup ads instantly
            window.open = function() { return null; };
            
            // 2. Intercept the network request to catch the direct URL before HTMX processes it
            if (!window.xhrIntercepted) {
                window.xhrIntercepted = true;
                var originalXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function() {
                    var xhr = new originalXHR();
                    xhr.addEventListener('readystatechange', function() {
                        if (xhr.readyState === 4) {
                            var redirect = xhr.getResponseHeader('hx-redirect') || xhr.getResponseHeader('location');
                            if (redirect && redirect.includes('dl.fuckingfast.co')) {
                                document.body.setAttribute('data-direct-url', redirect);
                            }
                        }
                    });
                    return xhr;
                };
            }
            """
            
            js_click = """
            let btn = document.querySelector('a[hx-post]');
            if (btn && btn.style.opacity !== '0.5') {
                btn.click(); // Natively click the button!
            }
            return document.body.getAttribute('data-direct-url');
            """
            # -------------------------------

            for i, link in enumerate(links, 1):
                filename = link.split('#')[-1] if '#' in link else link.split('/')[-1]
                self.root.after(0, self.update_ui, f"Processing [{i}/{total}]: {filename}")
                
                try:
                    driver.get(link)
                    driver.execute_script(js_inject)
                    
                    direct_url = None
                    for _ in range(30):
                        time.sleep(1)
                        
                        # Click the button and check if our interceptor caught the URL
                        result = driver.execute_script(js_click)
                        if result and "dl.fuckingfast.co" in result:
                            direct_url = result
                            break
                            
                        # Fallback: check if the browser natively navigated to the link
                        if "dl.fuckingfast.co" in driver.current_url:
                            direct_url = driver.current_url
                            break
                            
                        # Fallback: Old window.open method
                        match_old = re.search(r'window\.open\("([^"]+)"\)', driver.page_source)
                        if match_old:
                            direct_url = match_old.group(1)
                            break
                            
                    if direct_url:
                        self.root.after(0, self.update_ui, None, i, None, direct_url)
                    else:
                        self.root.after(0, self.update_ui, None, i, None, f"# FAILED: {filename} ({link})")
                        
                except Exception as e:
                    self.root.after(0, self.update_ui, None, i, None, f"# ERROR: {str(e)} -> {filename}")

            else:
                self.root.after(0, self.update_ui, f"Extraction complete! Processed {total} links.")
            
        except Exception as e:
            diag(f"CRITICAL ERROR: {e}", exc=True)
            self.root.after(0, self.update_ui, f"Critical Error: {str(e)}")
            
        finally:
            self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
            self.root.after(0, lambda: self.extract_btn.config(state="normal"))
            if driver:
                try:
                    driver.quit()
                except:
                    pass

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
        
    app = FitgirlExtractorApp(root)
    root.mainloop()
