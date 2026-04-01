"use client";

import { useState, type FormEvent } from "react";

export function SubscribeForm() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "error" | "exists"
  >("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email) return;

    setStatus("loading");

    try {
      const res = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const data = await res.json();

      if (res.ok) {
        setStatus("success");
        setMessage("Subscribed. You'll get the next weekly digest.");
        setEmail("");
      } else if (res.status === 409) {
        setStatus("exists");
        setMessage("Already subscribed.");
      } else {
        setStatus("error");
        setMessage(data.error ?? "Something went wrong.");
      }
    } catch {
      setStatus("error");
      setMessage("Network error. Try again.");
    }
  }

  return (
    <div className="border-t border-[#1f2937] mt-12 pt-8">
      <div className="max-w-md mx-auto text-center">
        <h3 className="text-[#e2e8f0] font-semibold text-sm mb-1">
          Weekly Digest
        </h3>
        <p className="text-[#6b7280] text-xs mb-4">
          Get the competitive FPS market report every Monday at 8 AM ET.
        </p>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (status !== "idle" && status !== "loading") setStatus("idle");
            }}
            placeholder="you@example.com"
            required
            className="flex-1 bg-[#111111] border border-[#1f2937] rounded-md px-3 py-2 text-sm text-[#e2e8f0] placeholder-[#6b7280] focus:outline-none focus:border-[#3b82f6] transition-colors"
          />
          <button
            type="submit"
            disabled={status === "loading"}
            className="bg-[#3b82f6] hover:bg-[#2563eb] text-white text-sm font-medium px-4 py-2 rounded-md transition-colors disabled:opacity-50"
          >
            {status === "loading" ? "..." : "Subscribe"}
          </button>
        </form>

        {status !== "idle" && status !== "loading" && (
          <p
            className={`text-xs mt-2 ${
              status === "success"
                ? "text-[#22c55e]"
                : status === "exists"
                  ? "text-[#f59e0b]"
                  : "text-[#ef4444]"
            }`}
          >
            {message}
          </p>
        )}
      </div>
    </div>
  );
}
