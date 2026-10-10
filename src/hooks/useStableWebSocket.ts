import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

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

type ConnectionListener = StableWebSocketOptions & {
  setConnected?: (value: boolean) => void;
  setReadyState?: (state: number) => void;
};

interface SharedConnection {
  ws: WebSocket | null;
  refCount: number;
  listeners: Set<ConnectionListener>;
  reconnectTimeout: ReturnType<typeof setTimeout> | null;
  heartbeatIntervalId: ReturnType<typeof setInterval> | null;
  reconnectDelay: number;
  initialReconnectDelay: number;
  heartbeatInterval: number;
  maxReconnectDelay: number;
  connect: () => void;
  cleanup: () => void;
}

const connectionPool = new Map<string, SharedConnection>();

function createSharedConnection(url: string, options: Required<Pick<StableWebSocketOptions, 'heartbeatInterval' | 'initialReconnectDelay' | 'maxReconnectDelay'>>): SharedConnection {
  const connection: SharedConnection = {
    ws: null,
    refCount: 0,
    listeners: new Set(),
    reconnectTimeout: null,
    heartbeatIntervalId: null,
    reconnectDelay: options.initialReconnectDelay,
    initialReconnectDelay: options.initialReconnectDelay,
    heartbeatInterval: options.heartbeatInterval,
    maxReconnectDelay: options.maxReconnectDelay,
    connect: () => {},
    cleanup: () => {},
  };

  const clearHeartbeat = () => {
    if (connection.heartbeatIntervalId) {
      clearInterval(connection.heartbeatIntervalId);
      connection.heartbeatIntervalId = null;
    }
  };

  const notify = (event: keyof ConnectionListener, payload?: Event | MessageEvent) => {
    connection.listeners.forEach((listener) => {
      if (event === 'onMessage' && listener.onMessage && payload instanceof MessageEvent) {
        listener.onMessage(payload);
      }
      if (event === 'onOpen' && listener.onOpen) listener.onOpen();
      if (event === 'onClose' && listener.onClose) listener.onClose();
      if (event === 'onError' && listener.onError && payload) listener.onError(payload);
      if (event === 'setConnected' && typeof listener.setConnected === 'function' && typeof payload === 'boolean') {
        listener.setConnected(payload);
      }
      if (event === 'setReadyState' && typeof listener.setReadyState === 'function' && typeof payload === 'number') {
        listener.setReadyState(payload);
      }
    });
  };

  const scheduleReconnect = () => {
    if (connection.reconnectTimeout) return;

    const delay = connection.reconnectDelay;
    connection.reconnectTimeout = setTimeout(() => {
      connection.reconnectTimeout = null;
      connection.reconnectDelay = Math.min(delay * 2, connection.maxReconnectDelay);
      connection.connect();
    }, delay);
  };

  const handleCloseOrError = (event?: Event) => {
    notify('setConnected', false);
    notify('setReadyState', connection.ws?.readyState ?? WebSocket.CLOSED);
    if (event) notify('onError', event);
    notify('onClose');
    clearHeartbeat();
    scheduleReconnect();
  };

  connection.cleanup = () => {
    clearHeartbeat();
    if (connection.reconnectTimeout) {
      clearTimeout(connection.reconnectTimeout);
      connection.reconnectTimeout = null;
    }
    if (connection.ws) {
      try {
        connection.ws.close();
      } catch (error) {
        // ignore
      }
      connection.ws = null;
    }
  };

  connection.connect = () => {
    // avoid creating multiple sockets if one is already connecting/open
    if (connection.ws && (connection.ws.readyState === WebSocket.OPEN || connection.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    connection.cleanup();

    try {
      const ws = new WebSocket(url);
      connection.ws = ws;
      notify('setReadyState', WebSocket.CONNECTING);

      ws.onopen = () => {
        notify('setConnected', true);
        notify('setReadyState', WebSocket.OPEN);
        connection.reconnectDelay = connection.initialReconnectDelay;
        clearHeartbeat();
        connection.heartbeatIntervalId = setInterval(() => {
          if (connection.ws?.readyState === WebSocket.OPEN) {
            try {
              connection.ws.send(JSON.stringify({ type: 'ping' }));
            } catch (error) {
              handleCloseOrError();
            }
          }
        }, connection.heartbeatInterval);
        notify('onOpen');
      };

      ws.onmessage = (event) => {
        notify('onMessage', event);
      };

      ws.onerror = (event) => {
        handleCloseOrError(event);
      };

      ws.onclose = () => {
        handleCloseOrError();
      };
    } catch (error) {
      handleCloseOrError();
    }
  };

  return connection;
}

function getSharedConnection(url: string, options: Required<Pick<StableWebSocketOptions, 'heartbeatInterval' | 'initialReconnectDelay' | 'maxReconnectDelay'>>): SharedConnection {
  if (!connectionPool.has(url)) {
    connectionPool.set(url, createSharedConnection(url, options));
  }
  return connectionPool.get(url)!;
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
  const [readyState, setReadyState] = useState<number>(WebSocket.CLOSED);

  const connection = useMemo(
    () => getSharedConnection(url, { heartbeatInterval, initialReconnectDelay, maxReconnectDelay }),
    [url, heartbeatInterval, initialReconnectDelay, maxReconnectDelay]
  );

  const listenerRef = useRef<ConnectionListener>({});
  listenerRef.current = {
    onMessage,
    onOpen,
    onClose,
    onError,
    setConnected,
    setReadyState,
  };

  useEffect(() => {
    connection.refCount += 1;
    connection.listeners.add(listenerRef.current);
    // Start connection only once and let the pool handle reconnects
    connection.connect();

    return () => {
      connection.listeners.delete(listenerRef.current);
      connection.refCount -= 1;

      if (connection.refCount <= 0) {
        connection.cleanup();
        connectionPool.delete(url);
      }
    };
  }, [connection, url]);

  const send = useCallback(
    (payload: WebSocketPayload) => {
      const message = typeof payload === 'string' ? payload : JSON.stringify(payload);
      if (connection.ws?.readyState === WebSocket.OPEN) {
        try {
          connection.ws.send(message);
          return true;
        } catch (error) {
          return false;
        }
      }
      return false;
    },
    [connection]
  );

  const reconnect = useCallback(() => {
    connection.reconnectDelay = connection.initialReconnectDelay;
    connection.connect();
  }, [connection]);

  return {
    connected,
    readyState,
    send,
    reconnect,
  };
}
