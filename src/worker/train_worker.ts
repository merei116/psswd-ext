const STOP_WORDS = new Set([
  'next', 'page', 'and', 'or', 'the', 'a', 'an',
  'photos', 'videos', 'quot', 'facebook', 'youtube',
  'instagram', 'linkedin', 'profiles', 'profile',
  'login', 'register', 'search', 'home', 'view',
  'more', 'info', 'details', 'about', 'contact'
]);

export async function fetchKeywords(fullName: string, city: string): Promise<string[]> {
  const query = encodeURIComponent(`${fullName} ${city}`);
  const response = await fetch(`https://lite.duckduckgo.com/lite/?q=${query}`);
  const html = await response.text();

  // Вытаскиваем текст ссылок
  const linkMatches = [...html.matchAll(/<a .*?>(.*?)<\/a>/g)].map(m => m[1]);
  const text = linkMatches.join(' ').toLowerCase();

  // Вытаскиваем слова длиной от 3 символов, содержащие буквы
  const words = Array.from(new Set(
    text.match(/\b[a-zа-яё]{3,}\b/gi) || []
  )).filter(w =>
    !STOP_WORDS.has(w.toLowerCase())
  );

  return words.slice(0, 20);
}
