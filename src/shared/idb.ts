// src/content/password-checker.ts
import { openDB } from 'idb';
import { get as _get, set as _set } from 'idb-keyval';
export const idb = { get: _get, set: _set, clear: () => _set.clear() };
