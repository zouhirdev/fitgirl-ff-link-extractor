# FitGirl FuckingFast Link Extractor

A lightweight, threaded desktop GUI tool built in Python to retrieve, filter, and extract direct download links from FuckingFast hosters on FitGirl Repack pages and [paste.fitgirl-repacks.site](https://paste.fitgirl-repacks.site) PrivateBin pastes.

## Features
- **Paste support:** Decrypts FitGirl PrivateBin URLs (`?id#key`) and pulls every `fuckingfast.co` link.
- **HTML / raw links:** Accepts pasted `<a href="https://fuckingfast.co/...">` snippets or plain FF URLs.
- **Fast Parsing:** Instantly pulls files, setup binaries, and optional parts.
- **Selective Scrape:** Use checkboxes to exclude unwanted files (like bonus content, other languages, etc.) before running the slow browser extraction process.
- **Cloudflare Bypass:** Employs an undetected browser process to seamlessly pass Turnstile checks.
- **Copy-to-Clipboard:** One button copies all successfully resolved direct URLs for direct import into JDownloader 2, IDM, or Free Download Manager.

## Download (Pre-compiled Executable)
If you don't have Python installed, simply download the latest standalone `.exe` from our [Releases Page](https://github.com/zouhirdev/fitgirl-ff-link-extractor/releases).

## Running from Source
If you prefer to run the raw Python code:
1. Clone this repository:
   ```bash
   git clone https://github.com/zouhirdev/fitgirl-ff-link-extractor.git
   cd fitgirl-ff-link-extractor
   ```
2. Set up your environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the script:
   ```bash
   python ff_grabber.py
   ```
