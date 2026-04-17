export type SupportedLanguageCode = 'en' | 'ta';

export interface LanguageOption {
  code: SupportedLanguageCode;
  label: string;
}

const LANGUAGE_ALIASES: Record<string, SupportedLanguageCode> = {
  en: 'en',
  english: 'en',
  'en-us': 'en',
  'en-in': 'en',
  hi: 'en',
  hindi: 'en',
  ta: 'ta',
  tamil: 'ta',
  te: 'en',
  telugu: 'en',
  bn: 'en',
  bengali: 'en',
  mr: 'en',
  marathi: 'en',
};

export const LANGUAGE_OPTIONS: LanguageOption[] = [
  { code: 'en', label: 'English' },
  { code: 'ta', label: 'Tamil' },
];

export const DEFAULT_LANGUAGE: SupportedLanguageCode = 'en';

export function normalizeLanguage(value: string | null | undefined): SupportedLanguageCode {
  if (!value) {
    return DEFAULT_LANGUAGE;
  }

  const normalized = value.trim().toLowerCase().replace('_', '-');
  if (LANGUAGE_ALIASES[normalized]) {
    return LANGUAGE_ALIASES[normalized];
  }

  const base = normalized.split('-')[0];
  if (LANGUAGE_ALIASES[base]) {
    return LANGUAGE_ALIASES[base];
  }

  return DEFAULT_LANGUAGE;
}

export function languageName(code: string | null | undefined): string {
  const normalized = normalizeLanguage(code);
  const item = LANGUAGE_OPTIONS.find((option) => option.code === normalized);
  return item?.label ?? 'English';
}

export function readLanguageFromPersistedProfile(): SupportedLanguageCode {
  try {
    const raw = localStorage.getItem('APXMIND-profile');
    if (!raw) {
      return DEFAULT_LANGUAGE;
    }

    const parsed = JSON.parse(raw) as {
      state?: { profile?: { preferredLanguage?: string | null } };
    };
    return normalizeLanguage(parsed?.state?.profile?.preferredLanguage);
  } catch {
    return DEFAULT_LANGUAGE;
  }
}

export function writeLanguageToPersistedProfile(language: string | null | undefined): void {
  try {
    const nextLanguage = normalizeLanguage(language);
    const raw = localStorage.getItem('APXMIND-profile');

    if (!raw) {
      return;
    }

    const parsed = JSON.parse(raw) as {
      state?: {
        profile?: Record<string, unknown>;
      };
    };

    if (!parsed.state) {
      parsed.state = {};
    }

    parsed.state.profile = {
      ...(parsed.state.profile ?? {}),
      preferredLanguage: nextLanguage,
    };

    localStorage.setItem('APXMIND-profile', JSON.stringify(parsed));
  } catch {
    // Best effort only; in-memory Zustand state still updates.
  }
}
