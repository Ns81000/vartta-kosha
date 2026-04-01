"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    TRADINGREF DATE DISCOVERY SCRIPT                           ║
║                         For Google Colab                                      ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  Purpose: Find the earliest date with valid JSON data from TradingRef API     ║
║  Method:  Start from 2025-07-01 and scan backwards until first valid response ║
║  Output:  Earliest available date for newspaper archive                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝

INSTRUCTIONS FOR GOOGLE COLAB:
1. Create a new Colab notebook
2. Copy this entire script into a code cell
3. Run the cell
4. Wait for results (may take several minutes)
5. Note down the "EARLIEST VALID DATE" from the output

"""

import urllib.request
import urllib.error
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

API_BASE_URL = "https://data.tradingref.com/{date}.json"
START_DATE = datetime.now().strftime("%Y%m%d")  # Start from today
MIN_DATE = "20220101"    # Don't go earlier than January 1, 2022

# Browser-mimicking headers to avoid being blocked
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}

REQUEST_TIMEOUT = 30  # seconds
DELAY_BETWEEN_REQUESTS = 0.5  # seconds (be respectful to the server)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def date_str_to_obj(date_str: str) -> datetime:
    """Convert YYYYMMDD string to datetime object."""
    return datetime.strptime(date_str, "%Y%m%d")

def date_obj_to_str(date_obj: datetime) -> str:
    """Convert datetime object to YYYYMMDD string."""
    return date_obj.strftime("%Y%m%d")

def check_date(date_str: str) -> Tuple[bool, Optional[dict], Optional[str]]:
    """
    Check if a given date has valid JSON data.
    
    Returns:
        Tuple of (success: bool, data: dict or None, error: str or None)
    """
    url = API_BASE_URL.format(date=date_str)
    
    try:
        request = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            if response.status == 200:
                content = response.read()
                data = json.loads(content.decode('utf-8'))
                
                # Validate that data is not empty
                if data and isinstance(data, dict) and len(data) > 0:
                    return True, data, None
                else:
                    return False, None, "Empty or invalid JSON structure"
                    
    except urllib.error.HTTPError as e:
        return False, None, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, None, f"URL Error: {e.reason}"
    except json.JSONDecodeError as e:
        return False, None, f"JSON Decode Error: {e}"
    except Exception as e:
        return False, None, f"Unexpected Error: {e}"
    
    return False, None, "Unknown error"

def count_entries(data: dict) -> dict:
    """Count languages, newspapers, and editions in the data."""
    stats = {
        "languages": 0,
        "newspapers": 0,
        "editions": 0
    }
    
    for language, newspapers in data.items():
        stats["languages"] += 1
        if isinstance(newspapers, dict):
            for newspaper, editions in newspapers.items():
                stats["newspapers"] += 1
                if isinstance(editions, dict):
                    stats["editions"] += len(editions)
                    
    return stats

def print_banner():
    """Print a nice banner."""
    print("\n" + "═" * 70)
    print("   📰 TRADINGREF DATE DISCOVERY SCRIPT")
    print("   Finding the earliest available newspaper data...")
    print("═" * 70 + "\n")

def print_progress(current_date: str, status: str, detail: str = ""):
    """Print progress update."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if detail:
        print(f"[{timestamp}] {current_date}: {status} - {detail}")
    else:
        print(f"[{timestamp}] {current_date}: {status}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DISCOVERY LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

def discover_earliest_date() -> Optional[str]:
    """
    Scan backwards from START_DATE to find the earliest valid date.
    
    Strategy:
    1. First, verify START_DATE works (it should, as it's recent)
    2. Use binary search to efficiently find the boundary
    3. Linear scan near the boundary for precision
    
    Returns:
        The earliest date with valid JSON, or None if none found
    """
    print_banner()
    
    start_dt = date_str_to_obj(START_DATE)
    min_dt = date_str_to_obj(MIN_DATE)
    
    print(f"📅 Search Range: {MIN_DATE} to {START_DATE}")
    print(f"📊 Total days to potentially scan: {(start_dt - min_dt).days + 1}")
    print("-" * 70)
    
    # Step 1: Verify start date works
    print("\n🔍 Phase 1: Verifying start date has data...")
    success, data, error = check_date(START_DATE)
    
    if not success:
        print(f"❌ ERROR: Start date {START_DATE} has no valid data!")
        print(f"   Reason: {error}")
        print("\n⚠️  Please update START_DATE to a more recent date and try again.")
        return None
    
    stats = count_entries(data)
    print(f"✅ Start date {START_DATE} is valid!")
    print(f"   Languages: {stats['languages']}, Newspapers: {stats['newspapers']}, Editions: {stats['editions']}")
    
    # Step 2: Binary search to find approximate boundary
    print("\n🔍 Phase 2: Binary search for approximate boundary...")
    
    left = min_dt
    right = start_dt
    last_valid = start_dt
    
    iterations = 0
    max_iterations = 50  # Safety limit
    
    while left <= right and iterations < max_iterations:
        iterations += 1
        mid = left + (right - left) // 2
        mid_str = date_obj_to_str(mid)
        
        time.sleep(DELAY_BETWEEN_REQUESTS)
        success, data, error = check_date(mid_str)
        
        if success:
            print_progress(mid_str, "✅ VALID", f"Found data")
            last_valid = mid
            right = mid - timedelta(days=1)
        else:
            print_progress(mid_str, "❌ NO DATA", error[:50] if error else "")
            left = mid + timedelta(days=1)
    
    print(f"\n   Binary search complete after {iterations} iterations")
    print(f"   Approximate earliest: {date_obj_to_str(last_valid)}")
    
    # Step 3: Linear scan for precision (check a few days before last_valid)
    print("\n🔍 Phase 3: Linear scan for precision...")
    
    # Check up to 7 days before the last valid date found
    scan_start = last_valid - timedelta(days=7)
    if scan_start < min_dt:
        scan_start = min_dt
    
    earliest_valid = last_valid
    current = scan_start
    
    while current <= last_valid:
        current_str = date_obj_to_str(current)
        
        time.sleep(DELAY_BETWEEN_REQUESTS)
        success, data, error = check_date(current_str)
        
        if success:
            print_progress(current_str, "✅ VALID")
            if current < earliest_valid:
                earliest_valid = current
            # Once we find a valid date, check the day before
            check_before = current - timedelta(days=1)
            if check_before >= min_dt:
                time.sleep(DELAY_BETWEEN_REQUESTS)
                before_success, _, before_error = check_date(date_obj_to_str(check_before))
                if before_success:
                    current = check_before
                    earliest_valid = check_before
                    print_progress(date_obj_to_str(check_before), "✅ VALID (earlier found!)")
                    continue
                else:
                    print_progress(date_obj_to_str(check_before), "❌ NO DATA", "This is the boundary!")
                    break
        else:
            print_progress(current_str, "❌ NO DATA", error[:40] if error else "")
        
        current += timedelta(days=1)
    
    return date_obj_to_str(earliest_valid)

def main():
    """Main entry point."""
    try:
        earliest_date = discover_earliest_date()
        
        if earliest_date:
            print("\n" + "═" * 70)
            print("   🎉 DISCOVERY COMPLETE!")
            print("═" * 70)
            print(f"\n   📅 EARLIEST VALID DATE: {earliest_date}")
            print(f"   📅 Human readable: {date_str_to_obj(earliest_date).strftime('%B %d, %Y')}")
            print("\n   This is the starting point for your archive.")
            print("   All dates from this date to today have newspaper data available.")
            print("\n" + "═" * 70)
            
            # Fetch and display stats for the earliest date
            print("\n📊 Statistics for earliest date:")
            success, data, _ = check_date(earliest_date)
            if success:
                stats = count_entries(data)
                print(f"   • Languages available: {stats['languages']}")
                print(f"   • Newspapers available: {stats['newspapers']}")
                print(f"   • Edition entries: {stats['editions']}")
                
                print("\n📋 Languages found:")
                for i, lang in enumerate(data.keys(), 1):
                    print(f"   {i:2}. {lang}")
            
            print("\n" + "═" * 70)
            print("   ✅ YOU CAN NOW PROCEED TO PHASE 2: ARCHIVING")
            print("   Use this date as your starting point for the mass archive script.")
            print("═" * 70 + "\n")
            
            return earliest_date
        else:
            print("\n❌ Could not find any valid dates in the search range.")
            print("   Please check your internet connection and try again.")
            return None
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Script interrupted by user.")
        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# RUN THE SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    result = main()
    
    # For Colab: store result in a variable
    EARLIEST_DATE = result
    print(f"\n💾 Result stored in variable: EARLIEST_DATE = '{EARLIEST_DATE}'")
