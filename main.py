from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import logging
from datetime import datetime, timedelta
import os
from typing import Dict, List
import uvicorn

# Import your services
from app.services.data_collector import FreeDataCollector
from app.services.mongodb_service import MongoDBService
from app.services.sentiment_analyzer import SentimentAnalyzer
from app.services.ml_predictor import MLPredictor
from app.services.websocket_manager import WebSocketManager
from app.api.routes import rates, predictions, news
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Exchange Rate Forecasting API",
    description="Real-time exchange rate prediction with news sentiment analysis",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-vercel-app.vercel.app",  # Replace with your Vercel domain
        "https://*.vercel.app",
        "http://localhost:3000",  # For development
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize services
data_collector = FreeDataCollector()
mongodb_service = MongoDBService()
sentiment_analyzer = SentimentAnalyzer()
ml_predictor = MLPredictor()
websocket_manager = WebSocketManager()

# Include API routes
app.include_router(rates.router, prefix="/api/v1/rates", tags=["rates"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["predictions"])
app.include_router(news.router, prefix="/api/v1/news", tags=["news"])

# Global state for current rates
current_rates = {
    'USD/EUR': {'rate': 1.0847, 'change': 0.0023, 'timestamp': datetime.utcnow().isoformat()},
    'USD/GBP': {'rate': 0.7834, 'change': -0.0012, 'timestamp': datetime.utcnow().isoformat()},
    'USD/JPY': {'rate': 149.85, 'change': 0.45, 'timestamp': datetime.utcnow().isoformat()},
    'EUR/GBP': {'rate': 0.8612, 'change': 0.0034, 'timestamp': datetime.utcnow().isoformat()},
}

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting Exchange Rate Forecasting API...")
    
    # Initialize MongoDB connection
    await mongodb_service.connect()
    
    # Start background tasks
    asyncio.create_task(collect_data_periodically())
    asyncio.create_task(update_predictions_periodically())
    asyncio.create_task(broadcast_live_rates())
    
    logger.info("✅ All services initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🔄 Shutting down services...")
    await data_collector.close()
    await mongodb_service.close()
    logger.info("✅ Shutdown complete")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check for Render deployment"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "exchange-rate-api",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Exchange Rate Forecasting API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health"
    }

# WebSocket endpoint for real-time data
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time rate updates"""
    await websocket.accept()
    client_id = await websocket_manager.connect(websocket)
    
    try:
        # Send initial data
        await websocket.send_json({
            "type": "initial_data",
            "data": {
                "rates": current_rates,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for client messages (optional)
                data = await websocket.receive_json()
                
                # Handle client requests
                if data.get("type") == "subscribe":
                    pair = data.get("pair")
                    await websocket.send_json({
                        "type": "subscribed",
                        "pair": pair,
                        "data": current_rates.get(pair, {})
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    
    finally:
        await websocket_manager.disconnect(client_id)

# Background task: Collect data every 30 seconds
async def collect_data_periodically():
    """Collect exchange rate and news data periodically"""
    while True:
        try:
            logger.info("📊 Collecting exchange rate data...")
            
            # Get live rates
            pairs = ['USD/EUR', 'USD/GBP', 'USD/JPY', 'EUR/GBP']
            new_rates = data_collector.get_live_rates_yahoo(pairs)
            
            # Update global rates
            for pair, rate_data in new_rates.items():
                current_rates[pair] = rate_data
                
                # Store in MongoDB
                await mongodb_service.store_exchange_rate(pair, rate_data)
            
            # Collect news every 5 minutes (less frequent)
            current_minute = datetime.utcnow().minute
            if current_minute % 5 == 0:
                logger.info("📰 Collecting news data...")
                await collect_news_data()
            
            logger.info(f"✅ Data collection complete. Next update in 30 seconds.")
            
        except Exception as e:
            logger.error(f"❌ Data collection error: {e}")
        
        await asyncio.sleep(30)  # Update every 30 seconds

async def collect_news_data():
    """Collect news data from free sources"""
    try:
        # Scrape news from multiple sources
        reuters_articles = await data_collector.scrape_reuters_forex()
        bloomberg_articles = await data_collector.scrape_bloomberg_forex()
        fed_articles = data_collector.get_fed_news_rss()
        
        all_articles = reuters_articles + bloomberg_articles + fed_articles
        
        # Process and store articles
        for article in all_articles:
            # Analyze sentiment
            text = f"{article.get('title', '')} {article.get('description', '')}"
            sentiment = sentiment_analyzer.analyze_sentiment(text)
            article['sentiment'] = sentiment
            
            # Determine relevance for each currency pair
            pairs = ['USD/EUR', 'USD/GBP', 'USD/JPY', 'EUR/GBP']
            for pair in pairs:
                relevance = calculate_relevance(text, pair)
                if relevance > 0.3:  # Only store relevant articles
                    await mongodb_service.store_news_article(article, pair)
        
        logger.info(f"📰 Processed {len(all_articles)} news articles")
        
    except Exception as e:
        logger.error(f"News collection error: {e}")

def calculate_relevance(text: str, pair: str) -> float:
    """Calculate relevance score for currency pair"""
    text_lower = text.lower()
    score = 0.0
    
    # Direct pair mention
    if pair.lower().replace('/', '') in text_lower or pair.lower() in text_lower:
        score += 1.0
    
    # Individual currencies
    currencies = pair.split('/')
    for currency in currencies:
        if currency.lower() in text_lower:
            score += 0.3
    
    # Central bank keywords
    cb_keywords = {
        'USD': ['federal reserve', 'fed', 'fomc', 'jerome powell'],
        'EUR': ['ecb', 'european central bank', 'christine lagarde'],
        'GBP': ['bank of england', 'boe', 'andrew bailey'],
        'JPY': ['bank of japan', 'boj', 'kazuo ueda']
    }
    
    for currency in currencies:
        for keyword in cb_keywords.get(currency, []):
            if keyword in text_lower:
                score += 0.5
    
    # Economic keywords
    econ_keywords = ['interest rate', 'inflation', 'gdp', 'monetary policy', 'economic growth']
    for keyword in econ_keywords:
        if keyword in text_lower:
            score += 0.2
    
    return min(score, 1.0)  # Cap at 1.0

# Background task: Update predictions every 5 minutes
async def update_predictions_periodically():
    """Update ML predictions periodically"""
    while True:
        try:
            current_minute = datetime.utcnow().minute
            if current_minute % 5 == 0:  # Every 5 minutes
                logger.info("🧠 Updating ML predictions...")
                
                pairs = ['USD/EUR', 'USD/GBP', 'USD/JPY', 'EUR/GBP']
                for pair in pairs:
                    # Get historical data for features
                    historical_data = data_collector.get_historical_data(pair, period="7d")
                    
                    # Get recent news sentiment
                    sentiment_data = await mongodb_service.get_sentiment_summary(pair, hours=24)
                    
                    # Generate predictions
                    predictions = ml_predictor.predict(
                        pair=pair,
                        historical_data=historical_data,
                        sentiment_data=sentiment_data,
                        horizon_hours=[1, 24, 168]  # 1 hour, 1 day, 1 week
                    )
                    
                    # Store predictions
                    await mongodb_service.store_predictions(pair, predictions)
                
                logger.info("✅ Predictions updated")
        
        except Exception as e:
            logger.error(f"Prediction update error: {e}")
        
        await asyncio.sleep(60)  # Check every minute

# Background task: Broadcast live rates via WebSocket
async def broadcast_live_rates():
    """Broadcast live rates to connected WebSocket clients"""
    while True:
        try:
            # Broadcast current rates to all connected clients
            message = {
                "type": "rate_update",
                "data": current_rates,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.broadcast(message)
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
        
        await asyncio.sleep(5)  # Broadcast every 5 seconds

if __name__ == "__main__":
    # For local development
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )
