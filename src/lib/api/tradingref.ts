// ═══════════════════════════════════════════════════════════════════════════════
// VĀRTTĀ KŌŚA - TradingRef API Client
// Handles live data fetching and decryption
// ═══════════════════════════════════════════════════════════════════════════════

import { 
  TRADINGREF_API_BASE, 
  ALPHABET, 
  REVERSED_ALPHABET,
  LANGUAGE_DISPLAY_NAMES,
} from '@/lib/constants';
import { sanitizeName } from '@/lib/utils/sanitize';
import type { 
  DecryptedEntry, 
  NewspaperData, 
  DecodedNewspaperData,
  Language,
  Newspaper,
  Edition 
} from '@/types';

// Create translation map for decryption
const translationMap: Record<string, string> = {};
for (let i = 0; i < REVERSED_ALPHABET.length; i++) {
  translationMap[REVERSED_ALPHABET[i]] = ALPHABET[i];
}

export function decrypt(obfuscated: string): string {
  return obfuscated
    .split('')
    .map(char => translationMap[char] || char)
    .join('');
}

export function decryptEntry(obfuscated: string): DecryptedEntry {
  const decoded = decrypt(obfuscated);
  const parts = decoded.split('q!');
  
  if (parts.length < 3) {
    return { type: '', prefix: '', pages: [], pages_count: 0 };
  }
  
  const pages = parts[2].split('m%').filter(p => p.trim());
  
  return {
    type: parts[0] as DecryptedEntry['type'],
    prefix: parts[1],
    pages,
    pages_count: pages.length,
    raw_decoded: decoded,
  };
}

export function joinUrl(prefix: string, page: string): string {
  if (!page) return prefix;
  if (page.startsWith('http')) return page;
  return `${prefix.replace(/\/$/, '')}/${page}`;
}

export function normalizeLookupKey(value: string): string {
  return value
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

export function findMatchingKey(keys: string[], query: string): string | undefined {
  const direct = keys.find((key) => key === query);
  if (direct) return direct;

  const normalizedQuery = normalizeLookupKey(query);
  const sanitizedQuery = sanitizeName(query);

  return keys.find((key) => {
    const normalizedKey = normalizeLookupKey(key);
    return (
      normalizedKey === normalizedQuery ||
      normalizedKey === sanitizedQuery ||
      sanitizeName(key) === normalizedQuery ||
      sanitizeName(key) === sanitizedQuery
    );
  });
}

export async function fetchLiveData(dateStr: string): Promise<NewspaperData | null> {
  try {
    const url = `${TRADINGREF_API_BASE}/${dateStr}.json`;
    
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
      },
      cache: 'no-store',
    });
    
    if (!response.ok) {
      return null;
    }
    
    const data = await response.json();
    return data as NewspaperData;
  } catch (error) {
    console.error('Live fetch error:', error);
    return null;
  }
}

export function decryptNewspaperData(data: NewspaperData): DecodedNewspaperData {
  const decoded: DecodedNewspaperData = {};
  
  for (const [language, newspapers] of Object.entries(data)) {
    if (typeof newspapers !== 'object') continue;
    decoded[language] = {};
    
    for (const [newspaper, editions] of Object.entries(newspapers)) {
      if (typeof editions !== 'object') continue;
      decoded[language][newspaper] = {};
      
      for (const [edition, obfuscated] of Object.entries(editions)) {
        if (typeof obfuscated !== 'string') continue;
        decoded[language][newspaper][edition] = decryptEntry(obfuscated);
      }
    }
  }
  
  return decoded;
}

export function extractLanguages(data: NewspaperData): Language[] {
  return Object.keys(data)
    .filter(lang => typeof data[lang] === 'object')
    .map(lang => {
      const sanitized = sanitizeName(lang);
      const displayInfo = LANGUAGE_DISPLAY_NAMES[sanitized] || { name: lang, native: lang };
      return {
        id: sanitized,
        name: displayInfo.name,
        nativeName: displayInfo.native,
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}

export function extractNewspapers(data: NewspaperData, language: string): Newspaper[] {
  const newspapers = data[language];
  if (!newspapers || typeof newspapers !== 'object') return [];
  
  return Object.keys(newspapers)
    .filter(paper => typeof newspapers[paper] === 'object')
    .map(paper => ({
      id: sanitizeName(paper),
      name: paper,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

export function extractEditions(
  data: NewspaperData, 
  language: string, 
  newspaper: string
): Edition[] {
  const newspapers = data[language];
  if (!newspapers) return [];
  
  const editions = newspapers[newspaper];
  if (!editions || typeof editions !== 'object') return [];
  
  return Object.entries(editions)
    .filter(([, value]) => typeof value === 'string')
    .map(([edition, obfuscated]) => {
      const entry = decryptEntry(obfuscated as string);
      return {
        id: sanitizeName(edition),
        name: edition,
        pagesCount: entry.pages_count,
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}

export function getEditionData(
  data: NewspaperData,
  language: string,
  newspaper: string,
  edition: string
): DecryptedEntry | null {
  const newspapers = data[language];
  if (!newspapers) return null;
  
  const editions = newspapers[newspaper];
  if (!editions) return null;
  
  const obfuscated = editions[edition];
  if (typeof obfuscated !== 'string') return null;
  
  return decryptEntry(obfuscated);
}
