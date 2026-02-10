/**
 * WebSocket client for streaming story generation.
 */

export class StorySocket {
  constructor() {
    this.ws = null;
    this.onToken = null;   // (text) => void
    this.onComplete = null; // (node) => void
    this.onError = null;    // (message) => void
    this.onOpen = null;     // () => void
    this.onClose = null;    // () => void
    this._reconnectTimer = null;
    this._intentionalClose = false;
    this._connectPromise = null;
  }

  connect() {
    if (this.ws) {
      if (this.ws.readyState === WebSocket.CONNECTING) return this._connectPromise;
      if (this.ws.readyState === WebSocket.OPEN) return Promise.resolve();
      // Clean up old socket in CLOSING/CLOSED state so its handlers don't fire
      this.ws.onclose = null;
      this.ws.onerror = null;
    }

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/generate`;

    this._intentionalClose = false;
    this.ws = new WebSocket(url);

    let resolveConnect;
    this._connectPromise = new Promise(resolve => { resolveConnect = resolve; });

    this.ws.onopen = () => {
      if (this._reconnectTimer) {
        clearTimeout(this._reconnectTimer);
        this._reconnectTimer = null;
      }
      this.onOpen?.();
      resolveConnect();
    };

    this.ws.onmessage = (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }

      if (msg.type === 'token') {
        this.onToken?.(msg.content);
      } else if (msg.type === 'complete') {
        this.onComplete?.(msg.node);
      } else if (msg.type === 'error') {
        this.onError?.(msg.message, msg.error_type, msg.service);
      }
    };

    this.ws.onclose = () => {
      this.onClose?.();
      if (!this._intentionalClose) {
        this._scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      // onclose will fire after onerror
    };

    return this._connectPromise;
  }

  disconnect() {
    this._intentionalClose = true;
    this._connectPromise = null;
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(msg) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
      return true;
    }
    return false;
  }

  generate(storyId, prompt, parentNodeId = null) {
    const msg = { action: 'generate', story_id: storyId, prompt };
    if (parentNodeId) msg.parent_node_id = parentNodeId;
    return this.send(msg);
  }

  branch(storyId, nodeId, prompt) {
    return this.send({ action: 'branch', story_id: storyId, node_id: nodeId, prompt });
  }

  get connected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  _scheduleReconnect() {
    if (this._reconnectTimer) return;
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this.connect();
    }, 3000);
  }
}
