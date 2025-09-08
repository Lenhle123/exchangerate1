import { useState, useEffect, useRef, useCallback } from 'react';
import apiService from '../services/api';

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [liveRates, setLiveRates] = useState({});
  const [lastUpdate, setLastUpdate] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const maxReconnectAttempts = 5;
  const reconnectAttemptRef = useRef(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus('connecting');
    
    const ws = apiService.connectWebSocket(
      // onMessage
      (data) => {
        setLastUpdate(new Date());
        
        switch (data.type) {
          case 'initial_data':
            setLiveRates(data.data.rates);
            setIsConnected(true);
            setConnectionStatus('connected');
            reconnectAttemptRef.current = 0;
            break;
            
          case 'rate_update':
            setLiveRates(prevRates => ({
              ...prevRates,
              ...data.data
            }));
            break;
            
          case 'subscribed':
            console.log(`Subscribed to ${data.pair}`);
            break;
            
          default:
            console.log('Unknown message type:', data.type);
        }
      },
      
      // onError
      (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
        setConnectionStatus('error');
      },
      
      // onClose
      () => {
        setIsConnected(false);
        setConnectionStatus('disconnected');
        
        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptRef.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttemptRef.current) * 1000; // 1s, 2s, 4s, 8s, 16s
          reconnectAttemptRef.current += 1;
          
          setConnectionStatus('reconnecting');
          
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`Reconnecting... Attempt ${reconnectAttemptRef.current}`);
            connect();
          }, delay);
        } else {
          setConnectionStatus('failed');
          console.error('Max reconnection attempts reached');
        }
      }
    );

    wsRef.current = ws;
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setConnectionStatus('disconnected');
    reconnectAttemptRef.current = 0;
  }, []);

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  const subscribeToRate = useCallback((pair) => {
    return sendMessage({
      type: 'subscribe',
      pair: pair
    });
  }, [sendMessage]);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    isConnected,
    liveRates,
    lastUpdate,
    connectionStatus,
    connect,
    disconnect,
    sendMessage,
    subscribeToRate
  };
};
