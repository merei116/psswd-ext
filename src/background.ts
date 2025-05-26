// src/background.ts
import { openDB } from 'idb';

// On first install, open the extension’s popup or a welcome page
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    // Open the extension’s popup page (index.html) in a new tab
    chrome.tabs.create({ url: chrome.runtime.getURL('index.html') });
  }
});

// When patterns have been saved (chrome.storage flag is set), load them and send to all tabs
chrome.storage.onChanged.addListener(async (changes, area) => {
  if (area === 'local' && changes.hasPatterns && changes.hasPatterns.newValue === true) {
    // Load the patterns from IndexedDB
    const db = await openDB('pg-store', 1);
    const patterns = await db.get('patterns', 'profile') as any || {};
    // Broadcast to all tabs so content scripts can update their badges
    chrome.tabs.query({}, (tabs) => {
      for (const tab of tabs) {
        if (tab.id) {
          chrome.tabs.sendMessage(tab.id, { type: 'hotReloadPatterns', patterns });
        }
      }
    });
  }
});
