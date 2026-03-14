import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re
from datetime import datetime

class BaseScraper:
    def __init__(self, name, base_url):
        self.name = name
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.thai_months = {
            "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
            "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
            "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
            "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12
        }

    def normalize_thai_date(self, date_str):
        """Converts various Thai date formats to YYYY-MM-DD (CE)"""
        if not date_str:
            return "0000-00-00"
        
        # Clean up string
        date_str = date_str.strip()

        # Format 1: DD/MM/YYYY (BE)
        match1 = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
        if match1:
            day = int(match1.group(1))
            month = int(match1.group(2))
            year = int(match1.group(3)) - 543
            return f"{year:04d}-{month:02d}-{day:02d}"

        # Format 2: DD Month YYYY (BE) - handles spaces or no spaces
        # Match: Day, Month (letters/dots), Year (4 digits)
        match2 = re.search(r'(\d{1,2})\s*([^\s\d]+)\s*(\d{4})', date_str)
        if match2:
            day = int(match2.group(1))
            month_name = match2.group(2).strip()
            year = int(match2.group(3)) - 543
            
            # Remove trial dot if exists (e.g. "ก.พ." -> "ก.พ.")
            month = self.thai_months.get(month_name, 1)
            # If not found, try without trailing dot
            if month_name not in self.thai_months and month_name.endswith('.'):
                 month = self.thai_months.get(month_name[:-1], 1)
            elif month_name not in self.thai_months:
                 # Try adding dot
                 month = self.thai_months.get(month_name + '.', 1)

            return f"{year:04d}-{month:02d}-{day:02d}"
            
        return "0000-00-00"

    def fetch(self, url, params=None):
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30, verify=False)
            response.raise_for_status()
            
            # If encoding is not specified or is ISO-8859-1, try apparent_encoding
            if response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding
                
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse(self, html):
        raise NotImplementedError("Subclasses must implement parse()")

    def scrape(self):
        raise NotImplementedError("Subclasses must implement scrape()")

    def save_raw_data(self, data, filename):
        os.makedirs('data', exist_ok=True)
        filepath = os.path.join('data', filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath
