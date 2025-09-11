import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Progress } from '@/components/ui/progress.jsx'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { TrendingUp, TrendingDown, Activity, DollarSign, BarChart3, Globe, Clock, Zap } from 'lucide-react'
import './App.css'

function App() {
  const [selectedPair, setSelectedPair] = useState('USD/EUR')
  const [selectedTimeframe, setSelectedTimeframe] = useState('24H')
  const [currentTime, setCurrentTime] = useState(new Date())
  const [isLive, setIsLive] = useState(true)

  // Mock data for demonstration
  const exchangeRates = {
    'USD/EUR': { current: 1.0545, change: 0.0023, changePercent: 0.218, forecast: 1.0578 },
    'USD/GBP': { current: 0.7845, change: -0.0012, changePercent: -0.153, forecast: 0.7832 },
    'USD/JPY': { current: 149.85, change: 0.45, changePercent: 0.301, forecast: 150.12 },
    'EUR/GBP': { current: 0.8456, change: 0.0008, changePercent: 0.095, forecast: 0.8463 },
    'EUR/JPY': { current: 158.92, change: 0.78, changePercent: 0.492, forecast: 159.24 },
    'GBP/JPY': { current: 191.05, change: -0.32, changePercent: -0.167, forecast: 190.89 }
  }

  const chartData = [
    { time: '09:00', rate: 1.0520, forecast: null },
    { time: '10:00', rate: 1.0525, forecast: null },
    { time: '11:00', rate: 1.0518, forecast: null },
    { time: '12:00', rate: 1.0532, forecast: null },
    { time: '13:00', rate: 1.0528, forecast: null },
    { time: '14:00', rate: 1.0545, forecast: null },
    { time: '15:00', rate: null, forecast: 1.0552 },
    { time: '16:00', rate: null, forecast: 1.0558 },
    { time: '17:00', rate: null, forecast: 1.0565 },
    { time: '18:00', rate: null, forecast: 1.0572 },
    { time: '19:00', rate: null, forecast: 1.0578 }
  ]

  const newsData = [
    {
      title: "Fed Signals Potential Rate Cut in Q2",
      source: "Reuters",
      time: "2 hours ago",
      sentiment: "positive",
      impact: "high",
      summary: "Federal Reserve hints at dovish policy stance amid economic uncertainty..."
    },
    {
      title: "ECB Meeting Results Released",
      source: "Bloomberg",
      time: "4 hours ago", 
      sentiment: "neutral",
      impact: "medium",
      summary: "European Central Bank maintains current rates, signals cautious approach..."
    },
    {
      title: "USD Strengthens Against Major Currencies",
      source: "Financial Times",
      time: "6 hours ago",
      sentiment: "positive", 
      impact: "high",
      summary: "Dollar gains momentum following positive economic indicators..."
    }
  ]

  const predictions = [
    { timeframe: "Next 6 Hours", change: "+0.15%", confidence: 75, direction: "up" },
    { timeframe: "Next 24 Hours", change: "+0.31%", confidence: 84, direction: "up" },
    { timeframe: "Next 7 Days", change: "-0.12%", confidence: 68, direction: "down" }
  ]

  const modelPerformance = [
    { model: "Ensemble", accuracy: 84.7, status: "active" },
    { model: "LSTM", accuracy: 82.3, status: "active" },
    { model: "XGBoost", accuracy: 81.9, status: "active" },
    { model: "Random Forest", accuracy: 79.5, status: "active" }
  ]

  // Update time every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const currentRate = exchangeRates[selectedPair]
  const isPositive = currentRate.change > 0

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-blue-900 via-blue-800 to-indigo-900 text-white shadow-2xl">
        <div className="container mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <BarChart3 className="h-8 w-8 text-blue-300" />
                <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
                  FX FORECAST PRO
                </h1>
              </div>
              <Badge variant="destructive" className="animate-pulse bg-red-500 hover:bg-red-600">
                <Activity className="h-3 w-3 mr-1" />
                LIVE
              </Badge>
            </div>
            <div className="flex items-center space-x-6 text-sm">
              <div className="flex items-center space-x-2">
                <Globe className="h-4 w-4 text-green-400" />
                <span>API Status: Connected</span>
              </div>
              <div className="flex items-center space-x-2">
                <Clock className="h-4 w-4 text-blue-300" />
                <span>{currentTime.toLocaleTimeString()}</span>
              </div>
              <div className="flex items-center space-x-2">
                <Zap className="h-4 w-4 text-yellow-400" />
                <span>Last Update: 2s ago</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        {/* Currency Pair Navigation */}
        <div className="flex flex-wrap gap-2 mb-8">
          {Object.keys(exchangeRates).map((pair) => (
            <Button
              key={pair}
              variant={selectedPair === pair ? "default" : "outline"}
              onClick={() => setSelectedPair(pair)}
              className={`${selectedPair === pair 
                ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                : 'hover:bg-blue-50 border-blue-200'
              }`}
            >
              {pair}
            </Button>
          ))}
        </div>

        {/* Main Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Current Rate Card */}
          <Card className="border-l-4 border-l-blue-500 shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">CURRENT RATE</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-3xl font-bold text-gray-900">{currentRate.current}</p>
                  <p className="text-sm text-gray-600">{selectedPair}</p>
                </div>
                <Badge variant="secondary" className="bg-green-100 text-green-800 hover:bg-green-200">
                  <Activity className="h-3 w-3 mr-1" />
                  LIVE
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* 24H Change Card */}
          <Card className={`border-l-4 ${isPositive ? 'border-l-green-500' : 'border-l-red-500'} shadow-lg hover:shadow-xl transition-shadow`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">24H CHANGE</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-start">
                <div>
                  <p className={`text-3xl font-bold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                    {isPositive ? '+' : ''}{currentRate.change.toFixed(4)}
                  </p>
                  <p className={`text-sm ${isPositive ? 'text-green-600' : 'text-red-600'} flex items-center`}>
                    {isPositive ? <TrendingUp className="h-4 w-4 mr-1" /> : <TrendingDown className="h-4 w-4 mr-1" />}
                    {isPositive ? '+' : ''}{currentRate.changePercent.toFixed(3)}%
                  </p>
                </div>
                <Badge variant={isPositive ? "default" : "destructive"} className={isPositive ? "bg-green-100 text-green-800 hover:bg-green-200" : ""}>
                  {isPositive ? 'BULLISH' : 'BEARISH'}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Forecast Card */}
          <Card className="border-l-4 border-l-purple-500 shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">24H FORECAST</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-3xl font-bold text-purple-600">{currentRate.forecast}</p>
                  <p className="text-sm text-purple-600">
                    +{((currentRate.forecast - currentRate.current) / currentRate.current * 100).toFixed(2)}% Target
                  </p>
                </div>
                <Badge variant="secondary" className="bg-purple-100 text-purple-800 hover:bg-purple-200">
                  🔮 AI
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Confidence Card */}
          <Card className="border-l-4 border-l-orange-500 shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">CONFIDENCE</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-3xl font-bold text-orange-600">84.7%</p>
                  <p className="text-sm text-orange-600">High Accuracy</p>
                </div>
                <Badge variant="secondary" className="bg-orange-100 text-orange-800 hover:bg-orange-200">
                  ⭐ STRONG
                </Badge>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Currency Selector and Timeframe */}
        <Card className="mb-8 shadow-lg">
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center space-x-4">
                <label className="text-gray-700 font-medium">Currency Pair:</label>
                <Select value={selectedPair} onValueChange={setSelectedPair}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD/EUR">🇺🇸 USD/EUR 🇪🇺</SelectItem>
                    <SelectItem value="USD/GBP">🇺🇸 USD/GBP 🇬🇧</SelectItem>
                    <SelectItem value="USD/JPY">🇺🇸 USD/JPY 🇯🇵</SelectItem>
                    <SelectItem value="EUR/GBP">🇪🇺 EUR/GBP 🇬🇧</SelectItem>
                    <SelectItem value="EUR/JPY">🇪🇺 EUR/JPY 🇯🇵</SelectItem>
                    <SelectItem value="GBP/JPY">🇬🇧 GBP/JPY 🇯🇵</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center space-x-2">
                {['1H', '6H', '24H', '7D', '30D'].map((timeframe) => (
                  <Button
                    key={timeframe}
                    variant={selectedTimeframe === timeframe ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedTimeframe(timeframe)}
                    className={selectedTimeframe === timeframe ? "bg-blue-600 hover:bg-blue-700" : "hover:bg-blue-50"}
                  >
                    {timeframe}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Interactive Chart */}
        <Card className="mb-8 shadow-lg">
          <CardHeader>
            <div className="flex justify-between items-center">
              <div>
                <CardTitle className="text-xl font-bold text-gray-900 flex items-center">
                  <BarChart3 className="h-5 w-5 mr-2 text-blue-600" />
                  Exchange Rate Chart - {selectedPair}
                </CardTitle>
                <CardDescription>Real-time rates with AI-powered forecasting</CardDescription>
              </div>
              <div className="flex items-center space-x-4 text-sm">
                <span className="flex items-center text-red-600">
                  <div className="w-2 h-2 bg-red-500 rounded-full mr-2 animate-pulse"></div>
                  Real-time
                </span>
                <span className="text-gray-600">Last: {currentRate.current}</span>
                <span className={`${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                  {isPositive ? '+' : ''}{currentRate.change.toFixed(4)} ({isPositive ? '+' : ''}{currentRate.changePercent.toFixed(2)}%)
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis 
                    dataKey="time" 
                    stroke="#64748b"
                    fontSize={12}
                  />
                  <YAxis 
                    domain={['dataMin - 0.001', 'dataMax + 0.001']}
                    stroke="#64748b"
                    fontSize={12}
                    tickFormatter={(value) => value.toFixed(4)}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: 'none',
                      borderRadius: '8px',
                      color: 'white'
                    }}
                    formatter={(value, name) => [
                      value ? value.toFixed(4) : 'N/A',
                      name === 'rate' ? 'Current Rate' : 'Forecast'
                    ]}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="rate" 
                    stroke="#2563eb" 
                    strokeWidth={3}
                    dot={{ fill: '#2563eb', strokeWidth: 2, r: 4 }}
                    name="Historical Rate"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="forecast" 
                    stroke="#7c3aed" 
                    strokeWidth={3}
                    strokeDasharray="8 8"
                    dot={{ fill: '#7c3aed', strokeWidth: 2, r: 4 }}
                    name="AI Forecast"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* News & Predictions Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* News & Sentiment Section */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="text-xl font-bold text-gray-900 flex items-center">
                📰 Market News & Sentiment
              </CardTitle>
              <CardDescription>Latest financial news affecting currency markets</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {newsData.map((news, index) => (
                  <div key={index} className={`border-l-4 pl-4 py-3 rounded-r-lg ${
                    news.sentiment === 'positive' ? 'border-l-green-500 bg-green-50' :
                    news.sentiment === 'negative' ? 'border-l-red-500 bg-red-50' :
                    'border-l-yellow-500 bg-yellow-50'
                  }`}>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900 text-sm">{news.title}</h4>
                        <p className="text-xs text-gray-600">{news.source} • {news.time}</p>
                      </div>
                      <div className="flex flex-col items-end space-y-1">
                        <Badge 
                          variant="secondary" 
                          className={`text-xs ${
                            news.sentiment === 'positive' ? 'bg-green-100 text-green-800' :
                            news.sentiment === 'negative' ? 'bg-red-100 text-red-800' :
                            'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {news.sentiment === 'positive' ? '🟢 POSITIVE' :
                           news.sentiment === 'negative' ? '🔴 NEGATIVE' : '🟡 NEUTRAL'}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {news.impact.toUpperCase()} IMPACT
                        </Badge>
                      </div>
                    </div>
                    <p className="text-sm text-gray-700">{news.summary}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* AI Predictions Section */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="text-xl font-bold text-gray-900 flex items-center">
                🤖 AI Predictions & Model Performance
              </CardTitle>
              <CardDescription>Machine learning insights and forecasts</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Predictions */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3">Forecast Timeline</h4>
                  <div className="space-y-3">
                    {predictions.map((pred, index) => (
                      <div key={index} className={`rounded-lg p-4 ${
                        pred.direction === 'up' ? 'bg-green-50' : 'bg-red-50'
                      }`}>
                        <div className="flex justify-between items-center mb-2">
                          <span className="font-medium text-gray-900 text-sm">{pred.timeframe}</span>
                          <span className={`font-bold text-sm ${
                            pred.direction === 'up' ? 'text-green-600' : 'text-red-600'
                          } flex items-center`}>
                            {pred.direction === 'up' ? 
                              <TrendingUp className="h-4 w-4 mr-1" /> : 
                              <TrendingDown className="h-4 w-4 mr-1" />
                            }
                            {pred.change}
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                          <div 
                            className={`h-2 rounded-full ${
                              pred.direction === 'up' ? 'bg-green-500' : 'bg-red-500'
                            }`}
                            style={{width: `${pred.confidence}%`}}
                          ></div>
                        </div>
                        <span className="text-xs text-gray-600">Confidence: {pred.confidence}%</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Model Performance */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3">Model Performance</h4>
                  <div className="space-y-2">
                    {modelPerformance.map((model, index) => (
                      <div key={index} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-sm">{model.model}</span>
                          <Badge variant="secondary" className="bg-blue-100 text-blue-800 text-xs">
                            {model.status.toUpperCase()}
                          </Badge>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-bold text-gray-900">{model.accuracy}%</span>
                          <div className="w-16 bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-blue-500 h-2 rounded-full"
                              style={{width: `${model.accuracy}%`}}
                            ></div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default App
