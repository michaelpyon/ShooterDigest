import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

/**
 * POST /api/subscribe
 * Subscribe to the weekly digest.
 * Body: { email: string }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const email = body.email?.trim()?.toLowerCase();

    if (!email || !email.includes("@")) {
      return NextResponse.json(
        { error: "Valid email required." },
        { status: 400 }
      );
    }

    // Check for existing subscriber
    const existing = await prisma.subscriber.findUnique({
      where: { email },
    });

    if (existing) {
      if (existing.status === "active") {
        return NextResponse.json(
          { error: "Already subscribed." },
          { status: 409 }
        );
      }

      // Reactivate unsubscribed user
      await prisma.subscriber.update({
        where: { email },
        data: { status: "active" },
      });

      return NextResponse.json({ ok: true, reactivated: true });
    }

    // Create new subscriber
    await prisma.subscriber.create({
      data: { email },
    });

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("Subscribe error:", err);
    return NextResponse.json(
      { error: "Internal server error." },
      { status: 500 }
    );
  }
}

/**
 * GET /api/subscribe?action=unsubscribe&email=...
 * Unsubscribe from the weekly digest.
 */
export async function GET(request: NextRequest) {
  const action = request.nextUrl.searchParams.get("action");
  const email = request.nextUrl.searchParams.get("email");

  if (action === "unsubscribe" && email) {
    try {
      await prisma.subscriber.update({
        where: { email: email.toLowerCase() },
        data: { status: "unsubscribed" },
      });

      return new NextResponse(
        `<html><body style="background:#0a0a0a;color:#e2e8f0;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
          <div style="text-align:center;">
            <h1 style="font-size:20px;margin-bottom:8px;">Unsubscribed</h1>
            <p style="color:#64748b;font-size:14px;">You won't receive any more digests.</p>
            <a href="/" style="color:#3b82f6;font-size:14px;margin-top:16px;display:inline-block;">Back to dashboard</a>
          </div>
        </body></html>`,
        {
          headers: { "Content-Type": "text/html" },
        }
      );
    } catch {
      return new NextResponse("Email not found.", { status: 404 });
    }
  }

  return NextResponse.json({ error: "Invalid request." }, { status: 400 });
}
