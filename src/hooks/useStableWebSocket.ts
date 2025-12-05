import { useCallback, useEffect, useRef, useState } from 'react';

type WebSocketPayload = string | Record<string, unknown>;

interface StableWebSocketOptions {
  onMessage?: (event: MessageEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (event: Event) => void;
  heartbeatInterval?: number;
  initialReconnectDelay?: number;
  maxReconnectDelay?: number;
}

interface StableWebSocketResult {
  connected: boolean;
  readyState: number;
  send: (payload: WebSocketPayload) => boolean;
  reconnect: () => void;
}

export function useStableWebSocket(
  url: string,
  options: StableWebSocketOptions = {}
): StableWebSocketResult {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    heartbeatInterval = 15000,
    initialReconnectDelay = 1000,
    maxReconnectDelay = 10000,
  } = options;

  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectDelayRef = useRef(initialReconnectDelay);
  const isMountedRef = useRef(true);
  const connectRef = useRef<() => void>();

  const clearHeartbeat = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
  }, []);

  const cleanupSocket = useCallback(() => {
    clearHeartbeat();
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch (error) {
        // Ignore
      }
      wsRef.current = null;
    }
  }, [clearHeartbeat]);

  const scheduleReconnect = useCallback(() => {
    if (!isMountedRef.current) return;
    if (reconnectTimeoutRef.current) return;

    const delay = reconnectDelayRef.current;
    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectTimeoutRef.current = null;
      reconnectDelayRef.current = Math.min(delay * 2, maxReconnectDelay);
      connectRef.current?.();
    }, delay);
  }, [maxReconnectDelay]);

  const connect = useCallback(() => {
    cleanupSocket();

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) return;
        setConnected(true);
        reconnectDelayRef.current = initialReconnectDelay;
        clearHeartbeat();
        heartbeatRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            try {
              wsRef.current.send(JSON.stringify({ type: 'ping' }));
            } catch (error) {
              // Ignore heartbeat errors
            }
          }
        }, heartbeatInterval);
        onOpen?.();
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;
        onMessage?.(event);
      };

      ws.onerror = (event) => {
        if (!isMountedRef.current) return;
        setConnected(false);
        onError?.(event);
        scheduleReconnect();
      };

      ws.onclose = () => {
        if (!isMountedRef.current) return;
        setConnected(false);
        clearHeartbeat();
        onClose?.();
        scheduleReconnect();
      };
    } catch (error) {
      setConnected(false);
      scheduleReconnect();
    }
  }, [
    cleanupSocket,
    clearHeartbeat,
    url,
    initialReconnectDelay,
    heartbeatInterval,
    onOpen,
    onMessage,
    onError,
    onClose,
    scheduleReconnect,
  ]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const send = useCallback(
    (payload: WebSocketPayload) => {
      const message = typeof payload === 'string' ? payload : JSON.stringify(payload);
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(message);
          return true;
        } catch (error) {
          return false;
        }
      }
      return false;
    },
    []
  );

  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      cleanupSocket();
    };
  }, [connect, cleanupSocket]);

  const reconnect = useCallback(() => {
    reconnectDelayRef.current = initialReconnectDelay;
    connect();
  }, [connect, initialReconnectDelay]);

  return {
    connected,
    readyState: wsRef.current?.readyState ?? WebSocket.CLOSED,
    send,
    reconnect,
  };
}
