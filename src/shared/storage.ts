// src/shared/storage.ts

export const get = <T = any>(key: string): Promise<T> =>
  new Promise((resolve) => {
    chrome.storage.local.get(key, data => resolve(data[key]));
  });

export const set = (obj: Record<string, any>): Promise<void> =>
  new Promise((resolve) => chrome.storage.local.set(obj, () => resolve()));

export const clear = (): Promise<void> =>
  new Promise((resolve) => chrome.storage.local.clear(resolve));
