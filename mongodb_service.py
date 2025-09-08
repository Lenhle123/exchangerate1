import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class MongoDBService:
    """MongoDB service for storing exchange rate and news data"""
    
    def __init__(self):
        # MongoDB configuration
        self.connection_string = os.getenv(
            'MONGODB_URI', 
            'mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority'
        )
        self.database_name = os.getenv('MONGODB_DATABASE', 'exchange_rate_db')
        
        self.client = None
        self.db = None
        self.collections = {}
        
    async def connect(self):
        """Connect to MongoDB Atlas (Free Tier)"""
        try:
            self.client = AsyncIOMotorClient(self.connection_string)
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB Atlas successfully")
            
            self.db = self.client[self.database_name]
            await self._setup_collections()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            self.client = None
            self.db = None
            return False
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    async def _setup_collections(self):
        """Setup collections and indexes"""
        if not self.db:
            return
        
        # Exchange rates collection
        self.collections['rates'] = self.db.exchange_rates
        await self.collections['rates'].create_index([
            ("pair", 1),
            ("timestamp", -1)
        ])
        
        # News articles collection  
        self.collections['news'] = self.db.news_articles
        await self.collections['news'].create_index([
            ("url", 1)
        ], unique=True)
        await self.collections['news'].create_index([
            ("currency_pair", 1),
            ("published_at", -1)
        ])
        await self.collections['news'].create_index([
            ("sentiment.score", 1),
            ("relevance", -1)
        ])
        
        # Predictions collection
        self.collections['predictions'] = self.db.predictions
        await self.collections['predictions'].create_index([
            ("pair", 1),
            ("prediction_time", -1)
        ])
        
        # Sentiment aggregations collection
        self.collections['sentiment'] = self.db.sentiment_aggregations
        await self.collections['sentiment'].create_index([
            ("currency_pair", 1),
            ("date", -1)
        ])
        
        logger.info("📊 MongoDB collections and indexes setup complete")
    
    # EXCHANGE RATE DATA METHODS
    
    async def store_exchange_rate(self, pair: str, rate_data: Dict):
        """Store exchange rate data"""
        if not self.db:
            return None
        
        try:
            document = {
                'pair': pair,
                'rate': rate_data['rate'],
                'change': rate_data.get('change', 0),
                'change_percent': rate_data.get('change_percent', 0),
                'high': rate_data.get('high'),
                'low': rate_data.get('low'),
                'volume': rate_data.get('volume', 0),
                'timestamp': datetime.fromisoformat(rate_data['timestamp'].replace('Z', '+00:00')) if isinstance(rate_data['timestamp'], str) else rate_data['timestamp'],
                'source': rate_data.get('source', 'unknown'),
                'created_at': datetime.utcnow()
            }
            
            result = await self.collections['rates'].insert_one(document)
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Error storing exchange rate: {e}")
            return None
    
    async def get_latest_rates(self, pairs: List[str], limit: int = 1) -> Dict:
        """Get latest exchange rates for specified pairs"""
        if not self.db:
            return {}
        
        try:
            rates = {}
            for pair in pairs:
                cursor = self.collections['rates'].find(
                    {'pair': pair}
                ).sort('timestamp', -1).limit(limit)
                
                documents = await cursor.to_list(length=limit)
                if documents:
                    rates[pair] = documents[0]
            
            return rates
            
        except Exception as e:
            logger.error(f"Error fetching latest rates: {e}")
            return {}
    
    async def get_historical_rates(self, pair: str, hours: int = 24, limit: int = 100) -> List[Dict]:
        """Get historical exchange rates"""
        if not self.db:
            return []
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            cursor = self.collections['rates'].find({
                'pair': pair,
                'timestamp': {'$gte': cutoff_time}
            }).sort('timestamp', 1).limit(limit)
            
            return await cursor.to_list(length=limit)
            
        except Exception as e:
            logger.error(f"Error fetching historical rates: {e}")
            return []
    
    # NEWS DATA METHODS
    
    async def store_news_article(self, article_data: Dict, currency_pair: str):
        """Store news article with sentiment analysis"""
        if not self.db:
            return None
        
        try:
            document = {
                'title': article_data.get('title', ''),
                'description': article_data.get('description', ''),
                'content': article_data.get('content', ''),
                'url': article_data['url'],
                'source': article_data.get('source', ''),
                'currency_pair': currency_pair,
                'published_at': self._parse_datetime(article_data.get('published_at')),
                'scraped_at': datetime.utcnow(),
                'sentiment': article_data.get('sentiment', {}),
                'relevance': article_data.get('relevance', 0),
                'impact': article_data.get('impact', 'medium'),
                'processed': False
            }
            
            result = await self.collections['news'].insert_one(document)
            return result.inserted_id
            
        except DuplicateKeyError:
            # Article already exists
            return None
        except Exception as e:
            logger.error(f"Error storing news article: {e}")
            return None
    
    async def get_recent_news(self, currency_pair: str, hours: int = 24, limit: int = 20) -> List[Dict]:
        """Get recent news for currency pair"""
        if not self.db:
            return []
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            cursor = self.collections['news'].find({
                'currency_pair': currency_pair,
                'scraped_at': {'$gte': cutoff_time}
            }).sort('published_at', -1).limit(limit)
            
            return await cursor.to_list(length=limit)
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []
    
    async def get_sentiment_summary(self, currency_pair: str, hours: int = 24) -> Optional[Dict]:
        """Get sentiment summary for currency pair"""
        if not self.db:
            return None
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            pipeline = [
                {
                    '$match': {
                        'currency_pair': currency_pair,
                        'scraped_at': {'$gte': cutoff_time},
                        'sentiment.score': {'$exists': True}
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'avg_sentiment': {'$avg': '$sentiment.score'},
                        'positive_count': {
                            '$sum': {'$cond': [{'$gt': ['$sentiment.score', 0.1]}, 1, 0]}
                        },
                        'negative_count': {
                            '$sum': {'$cond': [{'$lt': ['$sentiment.score', -0.1]}, 1, 0]}
                        },
                        'neutral_count': {
                            '$sum': {'$cond': [
                                {'$and': [
                                    {'$gte': ['$sentiment.score', -0.1]},
                                    {'$lte': ['$sentiment.score', 0.1]}
                                ]}, 1, 0
                            ]}
                        },
                        'total_articles': {'$sum': 1},
                        'avg_relevance': {'$avg': '$relevance'},
                        'high_impact_count': {
                            '$sum': {'$cond': [{'$eq': ['$impact', 'high']}, 1, 0]}
                        }
                    }
                }
            ]
            
            cursor = self.collections['news'].aggregate(pipeline)
            results = await cursor.to_list(length=1)
            
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Error getting sentiment summary: {e}")
            return None
    
    # PREDICTION DATA METHODS
    
    async def store_predictions(self, pair: str, predictions: Dict):
        """Store ML predictions"""
        if not self.db:
            return None
        
        try:
            document = {
                'pair': pair,
                'predictions': predictions,
                'prediction_time': datetime.utcnow(),
                'model_version': '1.0',
                'confidence_scores': {
                    horizon: pred.get('confidence', 0.5)
                    for horizon, pred in predictions.items()
                }
            }
            
            result = await self.collections['predictions'].insert_one(document)
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Error storing predictions: {e}")
            return None
    
    async def get_latest_predictions(self, pair: str) -> Optional[Dict]:
        """Get latest predictions for currency pair"""
        if not self.db:
            return None
        
        try:
            document = await self.collections['predictions'].find_one(
                {'pair': pair},
                sort=[('prediction_time', -1)]
            )
            
            return document
            
        except Exception as e:
            logger.error(f"Error fetching predictions: {e}")
            return None
    
    # AGGREGATION METHODS
    
    async def aggregate_daily_sentiment(self, currency_pair: str, days: int = 30) -> List[Dict]:
        """Aggregate sentiment by day"""
        if not self.db:
            return []
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            pipeline = [
                {
                    '$match': {
                        'currency_pair': currency_pair,
                        'scraped_at': {'$gte': start_date}
                    }
                },
                {
                    '$group': {
                        '_id': {
                            'year': {'$year': '$scraped_at'},
                            'month': {'$month': '$scraped_at'},
                            'day': {'$dayOfMonth': '$scraped_at'}
                        },
                        'avg_sentiment': {'$avg': '$sentiment.score'},
                        'article_count': {'$sum': 1},
                        'positive_count': {
                            '$sum': {'$cond': [{'$gt': ['$sentiment.score', 0.1]}, 1, 0]}
                        },
                        'negative_count': {
                            '$sum': {'$cond': [{'$lt': ['$sentiment.score', -0.1]}, 1, 0]}
                        }
                    }
                },
                {
                    '$sort': {'_id': 1}
                }
            ]
            
            cursor = self.collections['news'].aggregate(pipeline)
            return await cursor.to_list(length=days)
            
        except Exception as e:
            logger.error(f"Error aggregating daily sentiment: {e}")
            return []
    
    async def get_database_stats(self) -> Dict:
        """Get database statistics"""
        if not self.db:
            return {}
        
        try:
            stats = {}
            
            # Count documents in each collection
            for name, collection in self.collections.items():
                count = await collection.count_documents({})
                stats[f"{name}_count"] = count
            
            # Get recent activity
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            stats['recent_rates'] = await self.collections['rates'].count_documents({
                'created_at': {'$gte': recent_cutoff}
            })
            stats['recent_news'] = await self.collections['news'].count_documents({
                'scraped_at': {'$gte': recent_cutoff}
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def _parse_datetime(self, date_string: str) -> datetime:
        """Parse datetime string to datetime object"""
        if isinstance(date_string, datetime):
            return date_string
        
        if not date_string:
            return datetime.utcnow()
        
        try:
            # Try different datetime formats
            formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%a, %d %b %Y %H:%M:%S %Z'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_string, fmt)
                except ValueError:
                    continue
            
            # If all else fails, return current time
            return datetime.utcnow()
            
        except Exception:
            return datetime.utcnow()
