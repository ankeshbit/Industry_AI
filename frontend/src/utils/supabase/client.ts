import { createBrowserClient } from "@supabase/ssr";

const supabaseUrl =
  (import.meta.env.VITE_SUPABASE_URL as string | undefined) ||
  (import.meta.env.NEXT_PUBLIC_SUPABASE_URL as string | undefined) ||
  ((globalThis as any)?.process?.env?.NEXT_PUBLIC_SUPABASE_URL as string | undefined) ||
  "https://haewyxqgkobaoydyvhjd.supabase.co";

const supabaseKey =
  (import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined) ||
  (import.meta.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY as string | undefined) ||
  ((globalThis as any)?.process?.env?.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY as string | undefined) ||
  "sb_publishable_CvUU5NNRoBW-sRPcn5wFXw_AW9mfX6f";

export const createClient = () =>
  createBrowserClient(
    supabaseUrl,
    supabaseKey,
  );
