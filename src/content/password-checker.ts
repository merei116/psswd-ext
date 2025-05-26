// src/content/password-checker.ts
import { get } from '../shared/storage';
import { openDB } from 'idb';
let seq = 0;  

interface Patterns {
  masks?: Record<string, number>;
  words?: Record<string, number>;
  numbers?: Record<string, number>;
  password_counts?: Record<string, number>;  // новое поле!
}

type RatedResult = {
  score: 'WEAK' | 'MED' | 'STRONG';
  matches: string[];
};

function getMask(pwd: string): string {
  return pwd.split('').map(c =>
    /[A-Za-z]/.test(c) ? 'X' :
    /\d/.test(c) ? 'D' :
    /[!@#$%^&*()\-_=+]/.test(c) ? 'S' : '_'
  ).join('');
}

function rate(pwd: string, pat: Patterns, keywords: string[]): RatedResult {
  if (!pwd) return { score: 'WEAK', matches: [] };

  const lower = pwd.toLowerCase();
  const keywordMatches = keywords.filter(k => lower.includes(k)).slice(0, 5);
  const patternMatches = Object.keys(pat.words || {}).filter(w => lower.includes(w)).slice(0, 5);
  const mask = getMask(pwd);
  const maskFreq = pat.masks?.[mask] || 0;

  let score = 0;
  if (pwd.length >= 12) score += 30;
  else if (pwd.length >= 8) score += 15;
  else score += 5;

  if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) score += 15;
  if (/\d/.test(pwd)) score += 15;
  if (/[!@#$%^&*()\-_=+]/.test(pwd)) score += 15;

  if (maskFreq >= 50) score -= 30;
  else if (maskFreq >= 10) score -= 20;
  else if (maskFreq >= 3) score -= 10;

  if (keywordMatches.length > 0) score -= 20;
  if (patternMatches.length > 0) score -= 30;


  let result: 'WEAK' | 'MED' | 'STRONG' = 'WEAK';
  if (score >= 70) result = 'STRONG';
  else if (score >= 40) result = 'MED';

  return {
    score: result,
    matches: [...keywordMatches, ...patternMatches],
  };
}

async function checkPwnedPassword(password: string): Promise<number> {
  const sha1 = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(password));
  const hashArray = Array.from(new Uint8Array(sha1));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('').toUpperCase();
  const prefix = hashHex.slice(0, 5);
  const suffix = hashHex.slice(5);

  const response = await fetch(`https://api.pwnedpasswords.com/range/${prefix}`);
  if (!response.ok) {
    console.error("HIBP API error:", response.status);
    return 0;
  }

  const text = await response.text();
  const lines = text.split('\n');

  for (const line of lines) {
    const [hashSuffix, count] = line.trim().split(':');
    if (hashSuffix === suffix) {
      return parseInt(count, 10);
    }
  }

  return 0;
}

// Загрузка patterns из assets
async function loadStaticPatterns(): Promise<Patterns> {
  try {
    const res = await fetch(chrome.runtime.getURL("src/assets/patterns.json"));
    return await res.json();
  } catch (error) {
    console.error('Ошибка при загрузке patterns.json:', error);
    return {};
  }
}

// Загрузка patterns из IndexedDB (если есть)
async function loadDynamicPatterns(): Promise<Patterns> {
  const hasPatterns = await get<boolean>('hasPatterns');
  if (!hasPatterns) return {};
  try {
    const db = await openDB('pg-store', 1);
    return await db.get('patterns', 'profile') as Patterns || {};
  } catch (error) {
    console.error('Ошибка при загрузке динамических паттернов:', error);
    return {};
  }
}

(async () => {
  const staticPatterns = await loadStaticPatterns();
  const dynamicPatterns = await loadDynamicPatterns(); // пока не используется
  const keywords: string[] = await get('keywords') || [];
  const keywordList = keywords.map(k => k.toLowerCase());

  function scanAndAttach() {
    document.querySelectorAll<HTMLInputElement>('input[type="password"]:not([data-pg])')
      .forEach(input => {
        input.dataset.pg = '1';

        const span = document.createElement('span');
        span.className = 'pg-badge WEAK';
        span.textContent = '…';

        const info = document.createElement('div');
        info.className = 'pg-keywords';
        info.style.fontSize = '0.75rem';
        info.style.color = '#999';
        info.style.marginLeft = '8px';

        input.after(span, info);

        input.addEventListener('input', () => {
          
          
          const val = input.value;
          const result = rate(val, staticPatterns, keywordList);
          const id    = ++seq;            // текущий номер запроса
          info.innerHTML = '';            // мгновенно очищаем вывод
          span.textContent = '…'; 
          span.className   = 'pg-badge WEAK';
          const extraNotes: string[] = [];
          const mask = getMask(val);
          const maskFreq = staticPatterns.masks?.[mask] || 0;
          const matched = result.matches;
          const topKeywords = keywordList.slice(0, 5);

          const passwordCounts = staticPatterns.password_counts || {};
          const repeats = passwordCounts[val] || 0;

          checkPwnedPassword(val).then(pwnCount => {
            if (!val) { span.textContent = '…'; info.innerHTML=''; return; }

            if (id !== seq) return;
            if (pwnCount > 0) {
              extraNotes.push(`❌ This password was found ${pwnCount} times in data breaches!`);
            }
            if (matched.length > 0) {
              extraNotes.push(`⚠️ Matches found: ${matched.join(', ')}`);
            }
            if (maskFreq > 0) {
              extraNotes.push(`⚠️ The mask "${mask}" has been encountered ${maskFreq} times`);
            }
            if (repeats > 1) {
              extraNotes.push(`❗ The password has been found ${repeats} times in the history`);
            }
          const finalScore: 'WEAK' | 'MED' | 'STRONG' =
          pwnCount > 0 ? 'WEAK' : result.score;        // если утечка — всегда WEAK
          span.textContent = finalScore;                 // обновляем текст бейджа
          span.className   = 'pg-badge ' + finalScore;

          
            info.innerHTML = `
              <div><strong>Keywords:</strong> ${topKeywords.join(', ')}</div>
              ${extraNotes.map(m => `<div>${m}</div>`).join('')}
            `;
          });
        });
      });
  }

  scanAndAttach();
  new MutationObserver(scanAndAttach)
    .observe(document.documentElement, { childList: true, subtree: true });

  chrome.runtime.onMessage.addListener(msg => {
    if (msg.type === 'hotReloadPatterns') {
      Object.assign(staticPatterns, msg.patterns);
    }
  });
})();
