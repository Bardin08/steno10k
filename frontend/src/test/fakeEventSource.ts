type Listener = (ev: MessageEvent) => void;

export class FakeEventSource {
  static instances: FakeEventSource[] = [];
  url: string;
  listeners: Record<string, Listener[]> = {};
  closed = false;
  onerror: ((ev: unknown) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }
  addEventListener(type: string, fn: Listener) {
    (this.listeners[type] ??= []).push(fn);
  }
  close() {
    this.closed = true;
  }

  /** Test helper: dispatch a named SSE event with a JSON payload. */
  emit(type: string, payload: unknown) {
    const ev = { data: JSON.stringify(payload) } as MessageEvent;
    (this.listeners[type] ?? []).forEach((fn) => fn(ev));
  }
  /** Test helper: dispatch a native, data-less transport error event. */
  emitNativeError() {
    (this.listeners["error"] ?? []).forEach((fn) => fn({} as MessageEvent));
  }
  static reset() {
    FakeEventSource.instances = [];
  }
}

export function installFakeEventSource() {
  FakeEventSource.reset();
  (globalThis as unknown as { EventSource: unknown }).EventSource =
    FakeEventSource;
  return FakeEventSource;
}
