import yfinance as yf
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta
import pandas as pd
import logging
from typing import Dict, List, Optional
import json
import re

logger = logging.getLogger(__name__)

class FreeDataCollector:
    """Collect exchange rate and news data from free sources only"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=self.headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    # =====================================
    # EXCHANGE RATE DATA (FREE SOURCES)
    # =====================================
    
    def get_live_rates_yahoo(self, pairs: List[str]) -> Dict:
        """Get real-time exchange rates from Yahoo Finance (FREE - No API Key)"""
        rates = {}
        
        for pair in pairs:
            try:
                base, quote = pair.split('/')
                symbol = f"{base}{quote}=X"
                
                # Get recent data
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="5d", interval="1m")
                
                if not data.empty:
                    current_rate = float(data['Close'].iloc[-1])
                    
                    # Calculate 24h change
                    if len(data) >= 1440:  # 24 hours of minute data
                        prev_rate = float(data['Close'].iloc[-1440])
                    else:
                        prev_rate = float(data['Close'].iloc[0])
                    
                    change = current_rate - prev_rate
                    change_percent = (change / prev_rate) * 100
                    
                    # Get daily highs/lows
                    daily_data = ticker.history(period="2d", interval="1d")
                    high_24h = float(daily_data['High'].iloc[-1]) if not daily_data.empty else current_rate
                    low_24h = float(daily_data['Low'].iloc[-1]) if not daily_data.empty else current_rate
                    
                    rates[pair] = {
                        'rate': round(current_rate, 6),
                        'change': round(change, 6),
                        'change_percent': round(change_percent, 3),
                        'high': round(high_24h, 6),
                        'low': round(low_24h, 6),
                        'volume': int(data['Volume'].tail(60).sum()) if 'Volume' in data else 0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'source': 'yahoo_finance'
                    }
                    
                    logger.info(f"✅ {pair}: {current_rate:.4f} ({change:+.4f})")
                    
            except Exception as e:
                logger.error(f"Error fetching {pair} from Yahoo Finance: {e}")
                rates[pair] = self._get_fallback_rate(pair)
        
        return rates
    
    def get_historical_data(self, pair: str, period: str = "7d") -> List[Dict]:
        """Get historical OHLCV data from Yahoo Finance"""
        try:
            base, quote = pair.split('/')
            symbol = f"{base}{quote}=X"
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval="1h")
            
            if data.empty:
                logger.warning(f"No historical data for {pair}")
                return []
            
            historical = []
            for index, row in data.iterrows():
                historical.append({
                    'timestamp': index.isoformat(),
                    'open': round(float(row['Open']), 6),
                    'high': round(float(row['High']), 6),
                    'low': round(float(row['Low']), 6),
                    'close': round(float(row['Close']), 6),
                    'volume': int(row['Volume']) if row['Volume'] > 0 else 0,
                    'pair': pair
                })
            
            logger.info(f"📊 Retrieved {len(historical)} historical data points for {pair}")
            return historical
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {pair}: {e}")
            return []
    
    async def get_rates_fixer_free(self) -> Dict:
        """Get exchange rates from Fixer.io free tier (1000 requests/month)"""
        if not self.session:
            return {}
        
        try:
            # Note: Replace with your free Fixer.io API key
            api_key = "your_fixer_api_key"  # Get free at fixer.io
            if api_key == "your_fixer_api_key":
                return {}  # Skip if no API key set
            
            url = f"http://data.fixer.io/api/latest?access_key={api_key}"
            
            async with self.session.get(url) as response:
                data = await response.json()
                
                if data.get('success'):
                    rates = {}
                    base = data['base']  # Usually EUR for free tier
                    
                    for currency, rate in data['rates'].items():
                        if currency in ['USD', 'GBP', 'JPY', 'CAD', 'AUD']:
                            pair = f"{base}/{currency}"
                            rates[pair] = {
                                'rate': float(rate),
                                'timestamp': data['date'],
                                'source': 'fixer_io'
                            }
                    
                    return rates
                
        except Exception as e:
            logger.error(f"Fixer.io API error: {e}")
        
        return {}
    
    # =====================================
    # NEWS DATA (FREE WEB SCRAPING)
    # =====================================
    
    async def scrape_reuters_forex(self, max_articles: int = 10) -> List[Dict]:
        """Scrape Reuters forex news (FREE)"""
        articles = []
        
        if not self.session:
            return articles
        
        try:
            url = "https://www.reuters.com/markets/currencies/"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Reuters returned status {response.status}")
                    return articles
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for article elements (Reuters structure may change)
                selectors = [
                    'div[data-testid="BasicCard"]',
                    'article',
                    '.story-card',
                    '[data-module="ArticleCard"]'
                ]
                
                for selector in selectors:
                    elements = soup.select(selector)[:max_articles]
                    if elements:
                        break
                
                for element in elements:
                    try:
                        # Extract title
                        title_elem = element.select_one('h3 a, h2 a, a h3, a h2')
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        link = title_elem.get('href', '')
                        
                        if link
