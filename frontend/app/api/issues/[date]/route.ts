import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { parseIssueFromMarkdown } from "@/lib/email/parseIssueFromMarkdown";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ date: string }> }
) {
  const { date } = await params;
  if (!date || date.length !== 10 || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return NextResponse.json(
      { error: "Use a date like YYYY-MM-DD" },
      { status: 400 }
    );
  }

  const supabase = createClient(url, anon);
  const { data, error } = await supabase
    .from("daily_reports")
    .select("markdown_content")
    .eq("date", date)
    .maybeSingle();

  if (error) {
    return NextResponse.json(
      { error: error.message || "Failed to load report" },
      { status: 500 }
    );
  }
  const markdown = data?.markdown_content ?? null;
  if (!markdown) {
    return NextResponse.json(
      { error: "No report for this date" },
      { status: 404 }
    );
  }

  const issue = parseIssueFromMarkdown(markdown);
  if (!issue) {
    return NextResponse.json(
      { error: "Could not parse report" },
      { status: 422 }
    );
  }
  return NextResponse.json(issue);
}
