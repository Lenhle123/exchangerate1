from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
import os
import random
import time
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Exchange Rate Forecasting API",
    description="Real-time exchange rate prediction with news sentiment analysis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections - GLOBAL DECLARATION
websocket_connections = set()

# Mock exchange rates data
current_rates = {
    'USD/EUR': {
        'rate': 1.0847,
        'change': 0.0023,
        'change_percent': 0.21,
        'high': 1.0870,
        'low': 1.0820,
        'volume': 1500000,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'source': 'mock'
    },
    'USD/GBP': {
        'rate': 0.7834,
        'change': -0.0012,
        'change_percent': -0.15,
        'high': 0.7850,
        'low': 0.7820,
        'volume': 1200000,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'source': 'mock'
    },
    'USD/JPY': {
        'rate': 149.85,
        'change': 0.45,
        'change_percent': 0.30,
        'high': 150.20,
        'low': 149.40,
        'volume': 2000000,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'source': 'mock'
    },
    'EUR/GBP': {
        'rate': 0.8612,
        'change': 0.0034,
        'change_percent': 0.40,
        'high': 0.8640,
        'low': 0.8580,
        'volume': 800000,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'source': 'mock'
    }
}

# Mock news data
mock_news = [
    {
        'id': 1,
        'title': 'Federal Reserve Maintains Current Policy Stance',
        'description': 'The Federal Reserve decided to keep interest rates unchanged in their latest meeting.',
        'url': 'https://example.com/fed-policy',
        'source': 'Federal Reserve',
        'published_at': datetime.now(timezone.utc).isoformat(),
        'sentiment': {'score': 0.1, 'label': 'neutral'},
        'relevance': 0.8,
        'impact': 'medium'
    },
    {
        'id': 2,
        'title': 'Economic Data Shows Continued Growth',
        'description': 'Recent economic indicators suggest sustained economic expansion.',
        'url': 'https://example.com/economic-growth',
        'source': 'Economic Report',
        'published_at': (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        'sentiment': {'score': 0.4, 'label': 'positive'},
        'relevance': 0.7,
        'impact': 'medium'
    },
    {
        'id': 3,
        'title': 'Currency Markets Show Increased Volatility',
        'description': 'Trading volumes have increased as markets react to recent policy announcements.',
        'url': 'https://example.com/market-volatility',
        'source': 'Market Analysis',
        'published_at': (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat(),
        'sentiment': {'score': -0.2, 'label': 'negative'},
        'relevance': 0.9,
        'impact': 'high'
    }
]

def update_mock_rates():
    """Update mock rates with small random changes"""
    for pair, data in current_rates.items():
        # Small random change
        change = random.uniform(-0.002, 0.002)
        new_rate = data['rate'] + change
        
        # Update data
        data['rate'] = round(new_rate, 6)
        data['change'] = round(change, 6)
        data['change_percent'] = round((change / data['rate']) * 100, 3)
        data['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Update high/low occasionally
        if random.random() < 0.1:  # 10% chance
            if new_rate > data['high']:
                data['high'] = new_rate
            elif new_rate < data['low']:
                data['low'] = new_rate

async def rate_update_task():
    """Background task to update rates every 5 seconds"""
    global websocket_connections  # Declare as global
    
    while True:
        try:
            update_mock_rates()
            
            # Broadcast to WebSocket clients
            message = {
                'type': 'rate_update',
                'data': current_rates,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Send to all connected clients
            disconnected = set()
            for websocket in websocket_connections.copy():  # Use copy to avoid modification during iteration
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.add(websocket)
            
            # Remove disconnected clients
            websocket_connections -= disconnected
            
            logger.info(f"Updated rates and broadcast to {len(websocket_connections)} clients")
            
        except Exception as e:
            logger.error(f"Error in rate update task: {e}")
        
        await asyncio.sleep(5)  # Update every 5 seconds

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    logger.info("Starting Exchange Rate Forecasting API...")
    
    # Start rate update task
    asyncio.create_task(rate_update_task())
    
    logger.info("All services initialized successfully")

# API Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "exchange-rate-api",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Exchange Rate Forecasting API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "status": "running",
        "available_endpoints": [
            "GET /health",
            "GET /api/v1/rates/live",
            "GET /api/v1/rates/{pair}/history",
            "GET /api/v1/predictions/{pair}",
            "GET /api/v1/predictions/performance",
            "GET /api/v1/news/{pair}",
            "GET /api/v1/news/{pair}/sentiment",
            "WS /ws"
        ]
    }

@app.get("/api/v1/rates/live")
async def get_live_rates():
    """Get current exchange rates"""
    return {
        "rates": current_rates,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "mock_data"
    }

@app.get("/api/v1/rates/{pair}/history")
async def get_historical_rates(pair: str):
    """Get historical rates for a currency pair"""
    if pair not in current_rates:
        return {"error": "Currency pair not found", "available_pairs": list(current_rates.keys())}
    
    # Generate mock historical data
    base_rate = current_rates[pair]['rate']
    history = []
    
    for i in range(24):  # 24 hours of data
        time_point = datetime.now(timezone.utc) - timedelta(hours=23-i)
        variation = random.uniform(-0.01, 0.01)
        rate = base_rate + variation
        
        history.append({
            'timestamp': time_point.isoformat(),
            'rate': round(rate, 6),
            'volume': random.randint(500000, 2000000),
            'high': round(rate + abs(variation) * 0.5, 6),
            'low': round(rate - abs(variation) * 0.5, 6)
        })
    
    return {
        "pair": pair,
        "data": history,
        "period": "24h",
        "count": len(history)
    }

@app.get("/api/v1/predictions/{pair}")
async def get_predictions(pair: str):
    """Get AI predictions for currency pair"""
    if pair not in current_rates:
        return {"error": "Currency pair not found", "available_pairs": list(current_rates.keys())}
    
    current_rate = current_rates[pair]['rate']
    
    predictions = {
        '1h': {
            'rate': round(current_rate + random.uniform(-0.001, 0.001), 6),
            'confidence': round(random.uniform(0.80, 0.95), 2),
            'direction': 'up' if random.random() > 0.5 else 'down'
        },
        '24h': {
            'rate': round(current_rate + random.uniform(-0.01, 0.01), 6),
            'confidence': round(random.uniform(0.70, 0.85), 2),
            'direction': 'up' if random.random() > 0.5 else 'down'
        },
        '168h': {
            'rate': round(current_rate + random.uniform(-0.03, 0.03), 6),
            'confidence': round(random.uniform(0.60, 0.75), 2),
            'direction': 'up' if random.random() > 0.5 else 'down'
        }
    }
    
    return {
        "pair": pair,
        "predictions": predictions,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "ensemble_mock"
    }

@app.get("/api/v1/predictions/performance")
async def get_model_performance():
    """Get model performance metrics"""
    return {
        "accuracy": round(random.uniform(0.82, 0.87), 3),
        "mse": round(random.uniform(0.0001, 0.0003), 6),
        "mae": round(random.uniform(0.005, 0.015), 4),
        "directional_accuracy": round(random.uniform(0.70, 0.78), 3),
        "total_predictions": random.randint(5000, 10000),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "model_version": "1.0.0"
    }

@app.get("/api/v1/news/{pair}")
async def get_news(pair: str):
    """Get news articles for currency pair"""
    return {
        "pair": pair,
        "articles": mock_news,
        "total_count": len(mock_news),
        "sentiment_summary": {
            "overall_sentiment": round(sum(article['sentiment']['score'] for article in mock_news) / len(mock_news), 3),
            "positive_count": sum(1 for a in mock_news if a['sentiment']['score'] > 0.1),
            "neutral_count": sum(1 for a in mock_news if -0.1 <= a['sentiment']['score'] <= 0.1),
            "negative_count": sum(1 for a in mock_news if a['sentiment']['score'] < -0.1)
        },
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/news/{pair}/sentiment")
async def get_sentiment_analysis(pair: str):
    """Get sentiment analysis for currency pair"""
    return {
        "pair": pair,
        "period": "24h",
        "overall_sentiment": round(random.uniform(0.15, 0.45), 2),
        "sentiment_trend": random.choice(['improving', 'declining', 'stable']),
        "distribution": {
            "positive": round(random.uniform(0.35, 0.50), 2),
            "neutral": round(random.uniform(0.25, 0.40), 2),
            "negative": round(random.uniform(0.10, 0.35), 2)
        },
        "confidence": round(random.uniform(0.75, 0.90), 2),
        "article_count": random.randint(15, 35),
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    global websocket_connections
    
    await websocket.accept()
    websocket_connections.add(websocket)
    
    try:
        # Send initial data
        await websocket.send_json({
            "type": "initial_data",
            "data": {
                "rates": current_rates,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await websocket.receive_json()
                
                if data.get("type") == "subscribe":
                    pair = data.get("pair")
                    if pair in current_rates:
                        await websocket.send_json({
                            "type": "subscribed",
                            "pair": pair,
                            "data": current_rates[pair]
                        })
                
                elif data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    
    finally:
        websocket_connections.discard(websocket)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
