# FitGirl FuckingFast Link Extractor

A lightweight, threaded desktop GUI tool built in Python to retrieve, filter, and extract direct download links from FuckingFast hosters on FitGirl Repack pages.

## Features
- **Fast Parsing:** Instantly pulls files, setup binaries, and optional parts.
- **Selective Scrape:** Use checkboxes to exclude unwanted files (like bonus content, other languages, etc.) before running the slow browser extraction process.
- **Headless SeleniumBase CDP:** Uses SeleniumBase UC + CDP mode with headless mode for the browser extraction step.
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
   python -m pip install -r requirements.txt
   ```
3. Run the script:
   ```bash
   python ff_grabber.py
   ```
