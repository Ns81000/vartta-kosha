"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                     VĀRTTĀ KŌŚA - BATCH UPLOAD ARCHIVER v4.0                                         ║
║                                    For Google Colab                                                  ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════╣
║  ⚡ FAST: Concurrent downloads, BATCH folder uploads (1 commit per date!)                            ║
║  💾 EFFICIENT: Deletes temp files after each date, low memory footprint                              ║
║  🔄 ROBUST: Crash-safe resume, atomic progress saves, duplicate prevention                           ║
║  📑 INDEX: Generates manifest files for archive navigation                                           ║
║  🚫 NO RATE LIMITS: Batch uploads avoid HuggingFace 128 commits/hour limit                          ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════╝

QUICK START:
═══════════════════════════════════════════════════════════════════════════════════════════════════════
Cell 1: !pip install -q huggingface_hub pikepdf img2pdf Pillow tqdm
Cell 2: import os; os.environ["HF_TOKEN"] = "hf_YOUR_TOKEN"
Cell 3: [Paste this script]
Cell 4: run_archiver()
═══════════════════════════════════════════════════════════════════════════════════════════════════════

NEW IN v4.0:
═══════════════════════════════════════════════════════════════════════════════════════════════════════
- BATCH FOLDER UPLOADS: All PDFs for a date uploaded in ONE commit
- Avoids HuggingFace 128 commits/hour rate limit
- ~2900 editions = 1 commit instead of 2900 commits
- Temp folder cleaned after each date to save Colab storage
═══════════════════════════════════════════════════════════════════════════════════════════════════════
"""

import os
import io
import re
import gc
import sys
import json
import time
import atexit
import signal
import shutil
import tempfile
import threading
import urllib.request
import urllib.error
import urllib.parse
import concurrent.futures
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict

# Suppress verbose logging
import logging
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

# Third-party imports
try:
    from huggingface_hub import HfApi, login
    from tqdm.auto import tqdm
    import img2pdf
    from PIL import Image
    import pikepdf
except ImportError as e:
    print(f"❌ Missing: {e}\nRun: !pip install -q huggingface_hub pikepdf img2pdf Pillow tqdm")
    raise

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class Config:
    HF_REPO_ID: str = "forkitover/vartta-kosha-archive"
    HF_REPO_TYPE: str = "dataset"
    START_DATE: str = "20250729"
    END_DATE: str = ""
    API_BASE_URL: str = "https://data.tradingref.com/{date}.json"
    
    # Performance tuning
    DOWNLOAD_WORKERS: int = 16  # Concurrent page downloads
    REQUEST_TIMEOUT: int = 45
    RETRY_ATTEMPTS: int = 3
    
    # Paths - will be updated by setup_google_drive()
    PROGRESS_FILE: str = "/content/archive_progress.json"
    PROGRESS_BACKUP: str = "/content/archive_progress.backup.json"
    TEMP_DIR: str = "/content/temp_archive"  # Temp folder for batch uploads
    
    # Headers
    HEADERS: Dict[str, str] = field(default_factory=lambda: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })

CONFIG = Config()

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# GOOGLE DRIVE PERSISTENCE (Crash-Proof)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

def setup_google_drive():
    """Mount Google Drive and set progress file path for crash-proof persistence."""
    try:
        from google.colab import drive
        
        # Check if already mounted
        if not os.path.exists("/content/drive/MyDrive"):
            print("📁 Mounting Google Drive...")
            drive.mount("/content/drive")
        
        # Create archive folder in Drive
        drive_folder = "/content/drive/MyDrive/VarttaKosha"
        os.makedirs(drive_folder, exist_ok=True)
        
        # Update config paths to use Drive for progress (NOT temp files - those stay local)
        CONFIG.PROGRESS_FILE = f"{drive_folder}/archive_progress.json"
        CONFIG.PROGRESS_BACKUP = f"{drive_folder}/archive_progress.backup.json"
        
        # Temp dir stays in /content for speed (will be deleted after each date)
        CONFIG.TEMP_DIR = "/content/temp_archive"
        
        print(f"✅ Progress saved to: {CONFIG.PROGRESS_FILE}")
        print(f"   (Persists across Colab sessions!)")
        print(f"📂 Temp folder: {CONFIG.TEMP_DIR} (cleaned after each date)\n")
        return True
        
    except ImportError:
        print("⚠️ Not in Colab - using local paths")
        return False
    except Exception as e:
        print(f"⚠️ Drive mount failed: {e}")
        print("   Using /content/ (will be lost if session ends)")
        return False

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DECRYPTION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/"
TRANSLATION_TABLE = str.maketrans(ALPHABET[::-1], ALPHABET)

def decrypt_entry(obfuscated: str) -> Dict[str, Any]:
    decoded = obfuscated.translate(TRANSLATION_TABLE)
    parts = decoded.split("q!", 2)
    if len(parts) < 3:
        return {"type": "", "prefix": "", "pages": [], "pages_count": 0}
    pages = [p for p in parts[2].split("m%") if p.strip()]
    return {"type": parts[0], "prefix": parts[1], "pages": pages, "pages_count": len(pages)}

def join_url(prefix: str, page: str) -> str:
    if not page: return prefix
    if page.startswith("http"): return page
    return f"{prefix.rstrip('/')}/{page}"

def sanitize(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '-', name).strip('-').lower()
    return name[:80] if name else "unknown"

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# ROBUST PROGRESS TRACKER (Crash-Safe)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class ProgressTracker:
    """Atomic, crash-safe progress tracking with duplicate prevention."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.backup_path = filepath.replace('.json', '.backup.json')
        self.lock = threading.Lock()
        self.data = self._load()
        self._dirty = False
        
        # Auto-save on exit
        atexit.register(self.save)
        signal.signal(signal.SIGTERM, lambda s, f: self.save())
    
    def _load(self) -> Dict:
        for path in [self.filepath, self.backup_path]:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        # Convert lists back to sets
                        if "completed_dates" in data:
                            data["completed_dates"] = set(data["completed_dates"])
                        if "completed_editions" in data:
                            data["completed_editions"] = set(data["completed_editions"])
                        return data
                except: pass
        
        return {
            "completed_dates": set(),
            "completed_editions": set(),
            "failed_editions": {},
            "stats": {"pdfs": 0, "bytes": 0, "started": datetime.now().isoformat()}
        }
    
    def save(self):
        with self.lock:
            if not self._dirty:
                return
            
            save_data = {
                "completed_dates": list(self.data.get("completed_dates", set())),
                "completed_editions": list(self.data.get("completed_editions", set())),
                "failed_editions": self.data.get("failed_editions", {}),
                "stats": self.data.get("stats", {})
            }
            
            temp_path = self.filepath + ".tmp"
            try:
                with open(temp_path, 'w') as f:
                    json.dump(save_data, f)
                
                if os.path.exists(self.filepath):
                    os.replace(self.filepath, self.backup_path)
                
                os.replace(temp_path, self.filepath)
                self._dirty = False
            except Exception as e:
                print(f"⚠️ Progress save error: {e}")
    
    def is_date_done(self, date: str) -> bool:
        with self.lock:
            return date in self.data.get("completed_dates", set())
    
    def mark_date_done(self, date: str, pdf_count: int, byte_count: int):
        with self.lock:
            self.data["completed_dates"].add(date)
            self.data["stats"]["pdfs"] = self.data["stats"].get("pdfs", 0) + pdf_count
            self.data["stats"]["bytes"] = self.data["stats"].get("bytes", 0) + byte_count
            self._dirty = True
        self.save()
    
    def mark_failed(self, date: str, lang: str, paper: str, edition: str, error: str):
        key = f"{date}/{lang}/{paper}/{edition}"
        with self.lock:
            self.data["failed_editions"][key] = error[:100]
            self._dirty = True
    
    @property
    def stats(self) -> Dict:
        return self.data.get("stats", {})

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# FAST DOWNLOADER
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

def download_url(url: str, timeout: int = None) -> Optional[bytes]:
    timeout = timeout or CONFIG.REQUEST_TIMEOUT
    
    for attempt in range(CONFIG.RETRY_ATTEMPTS):
        try:
            req = urllib.request.Request(url, headers=CONFIG.HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except:
            if attempt < CONFIG.RETRY_ATTEMPTS - 1:
                time.sleep(0.5 * (attempt + 1))
    return None

def download_with_proxy(url: str) -> Optional[bytes]:
    data = download_url(url)
    if data:
        return data
    
    if not url.startswith("https://images.weserv.nl"):
        proxy_url = f"https://images.weserv.nl/?url={urllib.parse.quote(url, safe='')}&output=jpg"
        return download_url(proxy_url)
    return None

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PDF GENERATION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

def images_to_pdf(images: List[bytes]) -> Optional[bytes]:
    valid = [img for img in images if img]
    if not valid:
        return None
    
    try:
        return img2pdf.convert(valid)
    except:
        try:
            converted = []
            for img_data in valid:
                img = Image.open(io.BytesIO(img_data))
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=100)
                converted.append(buf.getvalue())
            return img2pdf.convert(converted) if converted else None
        except:
            return None

def merge_pdfs(pdfs: List[bytes]) -> Optional[bytes]:
    valid = [p for p in pdfs if p]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0]
    
    try:
        merger = pikepdf.Pdf.new()
        for pdf_data in valid:
            src = pikepdf.Pdf.open(io.BytesIO(pdf_data))
            merger.pages.extend(src.pages)
        output = io.BytesIO()
        merger.save(output)
        return output.getvalue()
    except:
        return valid[0]

def unlock_pdf(pdf_data: bytes, password: str) -> bytes:
    try:
        pdf = pikepdf.Pdf.open(io.BytesIO(pdf_data), password=password)
        output = io.BytesIO()
        pdf.save(output)
        return output.getvalue()
    except:
        return pdf_data

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# BATCH UPLOADER (Folder Upload = 1 Commit!)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class BatchUploader:
    """
    Uploads entire folders in a single commit to avoid rate limits.
    HuggingFace limit: 128 commits/hour
    With batch: 1 commit per date instead of ~2900 commits per date!
    """
    
    def __init__(self, repo_id: str, token: str):
        self.repo_id = repo_id
        self.api = HfApi()
        if token:
            login(token=token, add_to_git_credential=False)
    
    def upload_folder(self, local_folder: str, path_in_repo: str, commit_message: str) -> bool:
        """
        Upload entire folder as a single commit.
        
        Args:
            local_folder: Path to local folder (e.g., /content/temp_archive/data/2025/07/29)
            path_in_repo: Path in repo (e.g., data/2025/07/29)
            commit_message: Commit message
        
        Returns:
            True if successful
        """
        try:
            self.api.upload_folder(
                folder_path=local_folder,
                path_in_repo=path_in_repo,
                repo_id=self.repo_id,
                repo_type=CONFIG.HF_REPO_TYPE,
                commit_message=commit_message,
                ignore_patterns=["*.tmp", "*.temp"]
            )
            return True
        except Exception as e:
            print(f"⚠️ Folder upload failed: {e}")
            return False
    
    def upload_file(self, file_path: str, path_in_repo: str, commit_message: str) -> bool:
        """Upload a single file (for index.json updates)."""
        try:
            self.api.upload_file(
                path_or_fileobj=file_path,
                path_in_repo=path_in_repo,
                repo_id=self.repo_id,
                repo_type=CONFIG.HF_REPO_TYPE,
                commit_message=commit_message
            )
            return True
        except Exception as e:
            print(f"⚠️ File upload failed: {e}")
            return False

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# INDEX MANIFEST MANAGER
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class IndexManager:
    """Manages archive index files for website navigation."""
    
    def __init__(self, uploader: BatchUploader):
        self.uploader = uploader
        self.master_index = {"lastUpdated": "", "dates": []}
        self.lock = threading.Lock()
        self._load_master_index()
    
    def _load_master_index(self):
        try:
            url = f"https://huggingface.co/datasets/{CONFIG.HF_REPO_ID}/resolve/main/index.json"
            req = urllib.request.Request(url, headers={"User-Agent": CONFIG.HEADERS["User-Agent"]})
            with urllib.request.urlopen(req, timeout=30) as resp:
                self.master_index = json.loads(resp.read().decode('utf-8'))
                print(f"📑 Loaded existing master index: {len(self.master_index.get('dates', []))} dates")
        except:
            self.master_index = {"lastUpdated": "", "dates": []}
    
    def create_date_index(self, date: str, data: Dict) -> Dict:
        """Create index structure for a specific date."""
        index = {
            "date": date,
            "lastUpdated": datetime.now().isoformat(),
            "languages": {}
        }
        
        for lang, papers in data.items():
            if not isinstance(papers, dict):
                continue
            
            sanitized_lang = sanitize(lang)
            index["languages"][sanitized_lang] = {}
            
            for paper, editions in papers.items():
                if not isinstance(editions, dict):
                    continue
                
                sanitized_paper = sanitize(paper)
                edition_list = [sanitize(edition) for edition in editions.keys()]
                
                if edition_list:
                    index["languages"][sanitized_lang][sanitized_paper] = sorted(edition_list)
        
        return index
    
    def save_date_index_locally(self, date: str, date_index: Dict, temp_dir: str):
        """Save per-date index to local temp folder (will be uploaded with batch)."""
        y, m, d = date[:4], date[4:6], date[6:8]
        index_path = os.path.join(temp_dir, "data", y, m, d, "index.json")
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(date_index, f, indent=2, ensure_ascii=False)
    
    def add_date_to_master(self, date: str):
        with self.lock:
            if date not in self.master_index["dates"]:
                self.master_index["dates"].append(date)
                self.master_index["dates"].sort()
    
    def upload_master_index(self) -> bool:
        """Upload the master index to HuggingFace."""
        with self.lock:
            self.master_index["lastUpdated"] = datetime.now().isoformat()
            self.master_index["totalDates"] = len(self.master_index["dates"])
            
            # Write to temp file
            temp_path = os.path.join(CONFIG.TEMP_DIR, "index.json")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.master_index, f, indent=2, ensure_ascii=False)
            
            return self.uploader.upload_file(
                temp_path,
                "index.json",
                f"Update master index ({len(self.master_index['dates'])} dates)"
            )

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# EDITION PROCESSOR (Saves to Local Folder)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

def process_edition_to_file(
    entry_data: str,
    date: str,
    lang: str,
    paper: str,
    edition: str,
    temp_dir: str,
    progress: ProgressTracker
) -> Tuple[bool, int, int]:
    """
    Process single edition: download → PDF → save to local folder.
    Returns (success, pages_count, file_size)
    """
    
    # Decrypt entry
    entry = decrypt_entry(entry_data)
    if not entry["pages"]:
        return False, 0, 0
    
    content_type = entry["type"]
    urls = [join_url(entry["prefix"], p) for p in entry["pages"]]
    
    # Parallel download all pages
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG.DOWNLOAD_WORKERS) as executor:
        futures = {executor.submit(download_with_proxy, url): i for i, url in enumerate(urls)}
        results = [None] * len(urls)
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except:
                pass
        downloaded = results
    
    # Handle password-protected PDFs
    if content_type in ("pdfl", "dfl"):
        unlocked = []
        for i, data in enumerate(downloaded):
            if data and entry["pages"][i].endswith(".pdf"):
                pwd = entry["pages"][i][:10] if len(entry["pages"][i]) >= 10 else None
                if pwd:
                    data = unlock_pdf(data, pwd)
            unlocked.append(data)
        downloaded = unlocked
    
    # Create PDF
    valid_data = [d for d in downloaded if d]
    if not valid_data:
        progress.mark_failed(date, lang, paper, edition, "No pages downloaded")
        return False, 0, 0
    
    if content_type in ("image", ""):
        pdf_data = images_to_pdf(valid_data)
    else:
        pdf_data = merge_pdfs(valid_data)
    
    if not pdf_data:
        progress.mark_failed(date, lang, paper, edition, "PDF creation failed")
        return False, 0, 0
    
    # Save to local temp folder
    y, m, d = date[:4], date[4:6], date[6:8]
    local_path = os.path.join(
        temp_dir, "data", y, m, d,
        sanitize(lang), sanitize(paper), f"{sanitize(edition)}.pdf"
    )
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    with open(local_path, 'wb') as f:
        f.write(pdf_data)
    
    file_size = len(pdf_data)
    
    # Free memory
    del pdf_data
    del downloaded
    gc.collect()
    
    return True, len(valid_data), file_size

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DATE PROCESSOR (Batch Upload)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

def fetch_date_data(date: str) -> Optional[Dict]:
    url = CONFIG.API_BASE_URL.format(date=date)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": CONFIG.HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except:
        return None

def process_date_batch(
    date: str,
    uploader: BatchUploader,
    progress: ProgressTracker,
    index_manager: IndexManager,
    pbar: tqdm
) -> Tuple[int, int, int]:
    """
    Process all editions for a date:
    1. Download all PDFs to local temp folder
    2. Upload entire folder as single commit
    3. Clean up temp folder
    
    Returns (success, failed, total_bytes)
    """
    
    # Skip if already done
    if progress.is_date_done(date):
        return 0, 0, 0
    
    # Fetch data
    data = fetch_date_data(date)
    if not data:
        return 0, 0, 0
    
    # Create temp directory for this date
    temp_dir = CONFIG.TEMP_DIR
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    # Collect editions
    editions_list = []
    for lang, papers in data.items():
        if not isinstance(papers, dict):
            continue
        for paper, editions in papers.items():
            if not isinstance(editions, dict):
                continue
            for edition, entry_data in editions.items():
                editions_list.append((lang, paper, edition, entry_data))
    
    total = len(editions_list)
    success = failed = 0
    total_bytes = 0
    
    # Process all editions (save to local folder)
    for i, (lang, paper, edition, entry_data) in enumerate(editions_list):
        pbar.set_postfix_str(f"{date}: {i+1}/{total} ✓{success} ✗{failed}", refresh=True)
        
        try:
            ok, _, size = process_edition_to_file(
                entry_data, date, lang, paper, edition, temp_dir, progress
            )
            if ok:
                success += 1
                total_bytes += size
            else:
                failed += 1
        except Exception as e:
            failed += 1
            progress.mark_failed(date, lang, paper, edition, str(e)[:50])
    
    # Create and save date index to temp folder
    date_index = index_manager.create_date_index(date, data)
    index_manager.save_date_index_locally(date, date_index, temp_dir)
    
    # Upload entire date folder as single commit!
    if success > 0:
        y, m, d = date[:4], date[4:6], date[6:8]
        date_folder = os.path.join(temp_dir, "data", y, m, d)
        
        pbar.set_postfix_str(f"{date}: Uploading {success} PDFs...", refresh=True)
        
        if uploader.upload_folder(
            date_folder,
            f"data/{y}/{m}/{d}",
            f"Archive {date}: {success} newspapers"
        ):
            # Success! Mark date complete and update master index
            progress.mark_date_done(date, success, total_bytes)
            index_manager.add_date_to_master(date)
        else:
            # Upload failed - don't mark as done, will retry next run
            print(f"\n⚠️ Upload failed for {date} - will retry on next run")
            failed = total  # Mark all as failed
            success = 0
    
    # Clean up temp folder to save Colab storage
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    gc.collect()
    
    return success, failed, total_bytes

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# MAIN ARCHIVER
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

def run_archiver(start_date: str = None, end_date: str = None):
    """
    Main entry point - Batch Upload Archiver.
    
    Key improvement: Uploads entire date folders in single commits.
    This avoids HuggingFace's 128 commits/hour rate limit!
    
    Usage:
        run_archiver()                                    # All dates
        run_archiver("20260301", "20260331")             # Specific range
        run_archiver(start_date="20260331")              # Single date
    """
    
    # Banner
    print("\n" + "═" * 70)
    print("   📰 VĀRTTĀ KŌŚA - BATCH UPLOAD ARCHIVER v4.0")
    print("   🚫 No rate limits: 1 commit per date!")
    print("═" * 70)
    
    # Setup Google Drive for crash-proof persistence
    setup_google_drive()
    
    # Config
    start = start_date or CONFIG.START_DATE
    end = end_date or CONFIG.END_DATE or datetime.now().strftime("%Y%m%d")
    
    # Check token
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("❌ Set HF_TOKEN: os.environ['HF_TOKEN'] = 'hf_...'")
        return
    
    print(f"   Repo: {CONFIG.HF_REPO_ID}")
    print(f"   Range: {start} → {end}")
    
    # Initialize
    uploader = BatchUploader(CONFIG.HF_REPO_ID, token)
    progress = ProgressTracker(CONFIG.PROGRESS_FILE)
    index_manager = IndexManager(uploader)
    
    if progress.stats.get("pdfs", 0) > 0:
        print(f"   Resuming: {progress.stats['pdfs']} PDFs already archived")
    
    # Generate dates
    start_dt = datetime.strptime(start, "%Y%m%d")
    end_dt = datetime.strptime(end, "%Y%m%d")
    all_dates = []
    current = start_dt
    while current <= end_dt:
        all_dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    
    # Filter completed
    dates = [d for d in all_dates if not progress.is_date_done(d)]
    
    print(f"   Dates: {len(dates)} remaining / {len(all_dates)} total")
    print("═" * 70 + "\n")
    
    if not dates:
        print("✅ All dates already archived!")
        print("📑 Updating master index...")
        index_manager.upload_master_index()
        return
    
    # Process with clean progress bar
    total_success = total_failed = 0
    total_bytes = 0
    
    with tqdm(dates, desc="Archiving", unit="day", dynamic_ncols=True, leave=True) as pbar:
        for date in pbar:
            pbar.set_description(f"📅 {date}")
            try:
                s, f, b = process_date_batch(date, uploader, progress, index_manager, pbar)
                total_success += s
                total_failed += f
                total_bytes += b
            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted - progress saved!")
                progress.save()
                break
            except Exception as e:
                print(f"\n⚠️ Error on {date}: {e}")
    
    # Final save
    progress.save()
    
    # Upload final master index
    print("\n📑 Uploading master index...")
    if index_manager.upload_master_index():
        print("✅ Master index updated successfully")
    
    # Cleanup temp folder
    if os.path.exists(CONFIG.TEMP_DIR):
        shutil.rmtree(CONFIG.TEMP_DIR)
    
    # Summary
    print("\n" + "═" * 70)
    print("   📊 COMPLETE")
    print("═" * 70)
    print(f"   ✅ Uploaded: {total_success} PDFs")
    print(f"   ❌ Failed: {total_failed}")
    print(f"   📁 Total archived: {progress.stats.get('pdfs', 0)} PDFs")
    print(f"   📑 Master index: {len(index_manager.master_index.get('dates', []))} dates")
    gb = progress.stats.get('bytes', 0) / (1024**3)
    print(f"   💾 Total size: {gb:.2f} GB")
    print("═" * 70 + "\n")


# ══════════════════════════════════════════════════════════��════════════════════════════════════════════
# UTILITY: REGENERATE INDEXES
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

def regenerate_indexes(start_date: str = None, end_date: str = None):
    """
    Regenerate index files for dates already in the archive.
    Use this if you ran v2/v3 and want to add/update index files.
    """
    
    print("\n" + "═" * 70)
    print("   📑 VĀRTTĀ KŌŚA - INDEX REGENERATOR")
    print("═" * 70)
    
    setup_google_drive()
    
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("❌ Set HF_TOKEN: os.environ['HF_TOKEN'] = 'hf_...'")
        return
    
    uploader = BatchUploader(CONFIG.HF_REPO_ID, token)
    progress = ProgressTracker(CONFIG.PROGRESS_FILE)
    index_manager = IndexManager(uploader)
    
    completed_dates = progress.data.get("completed_dates", set())
    dates = sorted(completed_dates)
    
    if start_date:
        dates = [d for d in dates if d >= start_date]
    if end_date:
        dates = [d for d in dates if d <= end_date]
    
    print(f"   Processing {len(dates)} dates for index generation...")
    print("═" * 70 + "\n")
    
    # Create temp dir
    temp_dir = CONFIG.TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)
    
    success_count = 0
    
    with tqdm(dates, desc="Indexing", unit="day", dynamic_ncols=True) as pbar:
        for date in pbar:
            pbar.set_description(f"📑 {date}")
            
            data = fetch_date_data(date)
            if not data:
                continue
            
            # Create index
            date_index = index_manager.create_date_index(date, data)
            
            # Save locally
            y, m, d = date[:4], date[4:6], date[6:8]
            index_path = os.path.join(temp_dir, f"index_{date}.json")
            
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(date_index, f, indent=2, ensure_ascii=False)
            
            # Upload
            if uploader.upload_file(index_path, f"data/{y}/{m}/{d}/index.json", f"Add index for {date}"):
                index_manager.add_date_to_master(date)
                success_count += 1
            
            # Clean up
            os.remove(index_path)
    
    # Upload master index
    print("\n📑 Uploading master index...")
    index_manager.upload_master_index()
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    print("\n" + "═" * 70)
    print(f"   ✅ Generated indexes for {success_count} dates")
    print(f"   📑 Master index: {len(index_manager.master_index.get('dates', []))} dates")
    print("═" * 70 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run_archiver()
