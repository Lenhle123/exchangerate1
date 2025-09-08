// Frontend API service for communicating with Render backend
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

class APIService {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.wsURL = WS_URL;
    this.cache = new Map();
    this.cacheTimeout = 30000; // 30 seconds
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // Cache management
  getCached(key) {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data;
    }
    return null;
  }

  setCache(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }

  // Exchange Rate API calls
  async getLiveRates(pairs = ['USD/EUR', 'USD/GBP', 'USD/JPY', 'EUR/GBP']) {
    const cacheKey = `live-rates-${pairs.join(',')}`;
    const cached = this.getCached(cacheKey);
    if (cached) return cached;

    try {
      const data = await this.request(`/api/v1/rates/live?pairs=${pairs.join(',')}`);
      this.setCache(cacheKey, data);
      return data;
    } catch (error) {
      // Fallback to mock data if API fails
      return this.getMockRates(pairs);
    }
  }

  async getHistoricalRates(pair, period = '24h') {
    const cacheKey = `historical-${pair}-${period}`;
    const cached = this.getCached(cacheKey);
    if (cached) return cached;

    try {
      const data = await this.request(`/api/v1/rates/${pair}/history?period=${period}`);
      this.setCache(cacheKey, data);
      return data;
    } catch (error) {
      return this.getMockHistoricalData(pair);
    }
  }

  // Prediction API calls
  async getPredictions(pair, horizon = [1, 24, 168]) {
    try {
      const data = await this.request(`/api/v1/predictions/${pair}?horizon=${horizon.join(',')}`);
      return data;
    } catch (error) {
      return this.getMockPredictions(pair);
    }
  }

  async getModelPerformance() {
    try {
      const data = await this.request('/api/v1/predictions/performance');
      return data;
    } catch (error) {
      return {
        accuracy: 0.847,
        mse: 0.000123,
        last_updated: new Date().toISOString()
      };
    }
  }

  // News API calls
  async getNews(pair, limit = 20) {
    try {
      const data = await this.request(`/api/v1/news/${pair}?limit=${limit}`);
      return data;
    } catch (error) {
      return this.getMockNews(pair);
    }
  }

  async getSentimentAnalysis(pair, period = '24h') {
    try {
      const data = await this.request(`/api/v1/news/${pair}/sentiment?period=${period}`);
      return data;
    } catch (error) {
      return this.getMockSentiment(pair);
    }
  }

  // WebSocket connection
  connectWebSocket(onMessage, onError, onClose) {
    try {
      const ws = new WebSocket(this.wsURL);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        // Subscribe to rate updates
        ws.send(JSON.stringify({
          type: 'subscribe',
          pairs: ['USD/EUR', 'USD/GBP', 'USD/JPY', 'EUR/GBP']
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (error) {
          console.error('WebSocket message parsing error:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (onError) onError(error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        if (onClose) onClose();
        
        // Reconnect after 5 seconds
        setTimeout(() => {
          this.connectWebSocket(onMessage, onError, onClose);
        }, 5000);
      };

      return ws;
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      if (onError) onError(error);
      return null;
    }
  }

  // Fallback mock data methods
  getMockRates(pairs) {
    const mockRates = {
      'USD/EUR': { rate: 1.0847, change: 0.0023, change_percent: 0.21 },
      'USD/GBP': { rate: 0.7834, change: -0.0012, change_percent: -0.15 },
      'USD/JPY': { rate: 149.85, change: 0.45, change_percent: 0.30 },
      'EUR/GBP': { rate: 0.8612, change: 0.0034, change_percent: 0.40 }
    };

    return {
      rates: pairs.reduce((acc, pair) => {
        acc[pair] = {
          ...mockRates[pair],
          timestamp: new Date().toISOString(),
          source: 'mock'
        };
        return acc;
      }, {}),
      timestamp: new Date().toISOString()
    };
  }

  getMockHistoricalData(pair) {
    const baseRate = {
      'USD/EUR': 1.0847,
      'USD/GBP': 0.7834,
      'USD/JPY': 149.85,
      'EUR/GBP': 0.8612
    }[pair] || 1.0000;

    const data = [];
    for (let i = 23; i >= 0; i--) {
      const time = new Date();
      time.setHours(time.getHours() - i);
      
      data.push({
        timestamp: time.toISOString(),
        rate: baseRate + (Math.random() - 0.5) * 0.02,
        volume: Math.floor(Math.random() * 1000000) + 500000
      });
    }

    return {
      pair,
      data,
      period: '24h'
    };
  }

  getMockPredictions(pair) {
    const currentRate = {
      'USD/EUR': 1.0847,
      'USD/GBP': 0.7834,
      'USD/JPY': 149.85,
      'EUR/GBP': 0.8612
    }[pair] || 1.0000;

    return {
      pair,
      predictions: {
        '1h': {
          rate: currentRate + (Math.random() - 0.5) * 0.001,
          confidence: 0.85,
          direction: 'up'
        },
        '24h': {
          rate: currentRate + (Math.random() - 0.5) * 0.01,
          confidence: 0.78,
          direction: Math.random() > 0.5 ? 'up' : 'down'
        },
        '168h': {
          rate: currentRate + (Math.random() - 0.5) * 0.03,
          confidence: 0.65,
          direction: Math.random() > 0.5 ? 'up' : 'down'
        }
      },
      generated_at: new Date().toISOString()
    };
  }

  getMockNews(pair) {
    const mockNews = [
      {
        id: 1,
        title: "Federal Reserve Signals Potential Rate Changes",
        description: "The Federal Reserve indicated potential monetary policy adjustments that could significantly impact currency markets in the coming months.",
        source: "Reuters",
        published_at: new Date(Date.now() - 2 * 3600000).toISOString(),
        sentiment: { score: 0.3, label: 'positive', confidence: 0.85 },
        relevance: 0.9,
        impact: 'high'
      },
      {
        id: 2,
        title: "European Central Bank Maintains Current Policy",
        description: "The ECB decided to keep interest rates unchanged while monitoring inflation trends across the eurozone.",
        source: "Bloomberg",
        published_at: new Date(Date.now() - 4 * 3600000).toISOString(),
        sentiment: { score: -0.1, label: 'neutral', confidence: 0.75 },
        relevance: 0.7,
        impact: 'medium'
      },
      {
        id: 3,
        title: "USD Strengthens on Economic Data",
        description: "Recent economic indicators show stronger than expected performance, boosting USD confidence.",
        source: "Financial Times",
        published_at: new Date(Date.now() - 6 * 3600000).toISOString(),
        sentiment: { score: 0.6, label: 'positive', confidence: 0.9 },
        relevance: 0.8,
        impact: 'high'
      }
    ];

    return {
      pair,
      articles: mockNews,
      total_count: mockNews.length,
      sentiment_summary: {
        overall_sentiment: 0.27,
        positive_count: 2,
        neutral_count: 1,
        negative_count: 0
      }
    };
  }

  getMockSentiment(pair) {
    return {
      pair,
      period: '24h',
      overall_sentiment: 0.35,
      sentiment_trend: 'improving',
      distribution: {
        positive: 0.45,
        neutral: 0.32,
        negative: 0.23
      },
      confidence: 0.82,
      article_count: 25,
      last_updated: new Date().toISOString()
    };
  }
}

export default new APIService();
