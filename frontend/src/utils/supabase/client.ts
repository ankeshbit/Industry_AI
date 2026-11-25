import { createBrowserClient } from '@supabase/ssr';
import type { SupabaseClient } from '@supabase/supabase-js';

function isValidHttpUrl(str?: string): boolean {
  if (!str) return false;
  try {
    const url = new URL(str);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

function isValidKey(key?: string): boolean {
  if (!key) return false;
  const trimmed = key.trim();
  if (
    trimmed === '' ||
    trimmed === 'your-supabase-anon-public-key' ||
    trimmed === 'your-supabase-anon-key' ||
    trimmed.startsWith('your-')
  ) {
    return false;
  }
  return true;
}

const envUrl = (
  (import.meta.env.VITE_SUPABASE_URL as string | undefined) ||
  (import.meta.env.NEXT_PUBLIC_SUPABASE_URL as string | undefined) ||
  ((globalThis as any)?.process?.env?.NEXT_PUBLIC_SUPABASE_URL as string | undefined) ||
  ''
).trim();

const envKey = (
  (import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined) ||
  (import.meta.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY as string | undefined) ||
  (import.meta.env.NEXT_PUBLIC_SUPABASE_ANON_KEY as string | undefined) ||
  ((globalThis as any)?.process?.env?.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY as string | undefined) ||
  ''
).trim();

let activeUrl: string = isValidHttpUrl(envUrl) ? envUrl : '';
let activeKey: string = isValidKey(envKey) ? envKey : '';

let browserClient: SupabaseClient | null =
  activeUrl && activeKey
    ? createBrowserClient(activeUrl, activeKey, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
        },
      })
    : null;

/**
 * Returns true if both Supabase URL and Publishable/Anon Key are valid and configured.
 */
export const isSupabaseConfigured = (): boolean => {
  return Boolean(activeUrl && activeKey && isValidHttpUrl(activeUrl) && isValidKey(activeKey));
};

/**
 * Initializes or updates the browser Supabase client with runtime credentials (e.g. from backend /auth/config).
 */
export const initSupabaseClient = (url?: string | null, key?: string | null): SupabaseClient | null => {
  if (url && key && isValidHttpUrl(url) && isValidKey(key)) {
    activeUrl = url.trim();
    activeKey = key.trim();
    browserClient = createBrowserClient(activeUrl, activeKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });
    supabase = browserClient;
    return browserClient;
  }
  return browserClient;
};

/**
 * Canonical singleton Supabase browser client instance.
 * null if Supabase credentials are not configured.
 */
export let supabase: SupabaseClient | null = browserClient;

/**
 * Getter for current Supabase client instance.
 */
export const getSupabaseClient = (): SupabaseClient | null => {
  return browserClient;
};

/**
 * Returns the singleton browser client or throws if configuration is missing.
 */
export const createClient = (): SupabaseClient => {
  if (!browserClient) {
    if (activeUrl && activeKey) {
      browserClient = createBrowserClient(activeUrl, activeKey, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
        },
      });
      supabase = browserClient;
    } else {
      throw new Error(
        'Supabase client cannot be created: VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are missing or invalid.'
      );
    }
  }
  return browserClient;
};
