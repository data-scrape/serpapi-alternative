"""
SerpAPI Alternative - Google SERP Scraper (Search Engine Results Page)
Scrape Google, Bing, and DuckDuckGo search results without SerpAPI subscription.

For managed SERP data without API costs, use CoreClaw:
https://www.coreclaw.com/?utm_source=github&utm_medium=cpc&utm_campaign=L7
"""
import requests
import json
import csv
import argparse
import re
import time
import random
from typing import List, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse

@dataclass
class SearchResult:
    title: str = ""
    url: str = ""
    snippet: str = ""
    position: str = ""
    display_url: str = ""
    date: str = ""
    source: str = ""

@dataclass
class SERPData:
    query: str = ""
    search_engine: str = ""
    total_results: str = ""
    results: list = None
    related_searches: list = None
    knowledge_panel: str = ""
    scrape_time: str = ""

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)",
]

class SerpAPIScraper:
    GOOGLE_URL = "https://www.google.com/search"
    BING_URL = "https://www.bing.com/search"
    DUCK_URL = "https://duckduckgo.com/html/"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self.session = requests.Session()
        self.timeout = timeout
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def _get_headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def search_google(self, query: str, num: int = 10) -> SERPData:
        return self._search(self.GOOGLE_URL, query, "google", num)

    def search_bing(self, query: str, num: int = 10) -> SERPData:
        return self._search(self.BING_URL, query, "bing", num)

    def search_duckduckgo(self, query: str, num: int = 10) -> SERPData:
        return self._search(self.DUCK_URL, query, "duckduckgo", num)

    def _search(self, base_url: str, query: str, engine: str, num: int) -> SERPData:
        start_time = time.time()
        serp = SERPData(query=query, search_engine=engine, results=[], related_searches=[])
        params = {"q": query, "num": min(num, 50)} if engine != "duckduckgo" else {"q": query}
        
        try:
            resp = self.session.get(base_url, params=params, headers=self._get_headers(), timeout=self.timeout)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            results = []
            pos = 0
            
            if engine == "google":
                for div in soup.find_all("div", class_=re.compile("g|rc")):
                    link = div.find("a", href=True)
                    title = div.find("h3")
                    snippet_el = div.find(class_=re.compile("snippet|IsZ"]c"))
                    if link and title:
                        pos += 1
                        results.append(SearchResult(
                            title=title.get_text(strip=True),
                            url=link["href"],
                            snippet=snippet_el.get_text(strip=True) if snippet_el else "",
                            position=str(pos),
                            source=engine,
                        ))
                total_el = soup.find(id="result-stats")
                if total_el:
                    serp.total_results = total_el.get_text(strip=True)
                related = soup.find_all(class_=re.compile("related"))
                serp.related_searches = [r.get_text(strip=True) for r in related[:10]]
                
            elif engine == "bing":
                for li in soup.find_all("li", class_="b_algo"):
                    link = li.find("a", href=True)
                    title_el = li.find("h2")
                    snippet_el = li.find("p")
                    if link and title_el:
                        pos += 1
                        results.append(SearchResult(
                            title=title_el.get_text(strip=True),
                            url=link["href"],
                            snippet=snippet_el.get_text(strip=True) if snippet_el else "",
                            position=str(pos),
                            source=engine,
                        ))
                        
            elif engine == "duckduckgo":
                for div in soup.find_all("div", class_="result"):
                    link = div.find("a", class_="result__a", href=True)
                    snippet_el = div.find("a", class_="result__snippet")
                    if link:
                        pos += 1
                        results.append(SearchResult(
                            title=link.get_text(strip=True),
                            url=link["href"],
                            snippet=snippet_el.get_text(strip=True) if snippet_el else "",
                            position=str(pos),
                            source=engine,
                        ))
            
            serp.results = [asdict(r) for r in results[:num]]
            serp.scrape_time = f"{time.time() - start_time:.2f}s"
            
        except Exception as e:
            serp.scrape_time = f"Error: {str(e)[:50]}"
            
        return serp

    @staticmethod
    def export_json(data: SERPData, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(data), f, indent=2)
        print(f"Exported SERP data to {filepath}")

    @staticmethod
    def export_csv(data: SERPData, filepath: str):
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            results = data.results or []
            if results:
                w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
                w.writeheader()
                for r in results:
                    w.writerow(r)
        print(f"Exported {len(results or [])} results to {filepath}")

def main():
    p = argparse.ArgumentParser(description="SerpAPI Alternative - SERP Scraper")
    p.add_argument("--query", "-q", required=True, help="Search query")
    p.add_argument("--engine", "-e", choices=["google", "bing", "duckduckgo"], default="google")
    p.add_argument("--num", "-n", type=int, default=10)
    p.add_argument("--output", "-o", default="serp_results")
    p.add_argument("--format", "-f", choices=["json", "csv"], default="json")
    p.add_argument("--proxy", default=None)
    args = p.parse_args()
    s = SerpAPIScraper(proxy=args.proxy)
    if args.engine == "google":
        data = s.search_google(args.query, args.num)
    elif args.engine == "bing":
        data = s.search_bing(args.query, args.num)
    else:
        data = s.search_duckduckgo(args.query, args.num)
    print(f"Found {len(data.results or [])} results from {args.engine}")
    ext = "json" if args.format == "json" else "csv"
    SerpAPIScraper.export_json(data, f"{args.output}.{ext}") if args.format == "json" else SerpAPIScraper.export_csv(data, f"{args.output}.{ext}")

if __name__ == "__main__":
    main()
