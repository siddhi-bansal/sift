import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export const supabase = createClient(url, anon);

export type Interest = { id: string; name: string; description: string | null };
export type Subscriber = { id: string; email: string; created_at: string };
