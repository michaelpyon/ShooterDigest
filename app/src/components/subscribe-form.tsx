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
    <div className="border-t border-border mt-12 pt-8">
      <div className="max-w-md mx-auto text-center">
        <h3 className="text-text font-semibold text-sm mb-1">
          Weekly Digest
        </h3>
        <p className="text-text-subtle text-xs mb-4">
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
            className="flex-1 bg-surface border border-border px-3 py-2 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent transition-colors"
          />
          <button
            type="submit"
            disabled={status === "loading"}
            className="bg-accent hover:bg-accent-hover text-bg text-sm font-medium px-4 py-2 transition-colors disabled:opacity-50"
          >
            {status === "loading" ? "..." : "Subscribe"}
          </button>
        </form>

        {status !== "idle" && status !== "loading" && (
          <p
            className={`text-xs mt-2 ${
              status === "success"
                ? "text-secondary"
                : status === "exists"
                  ? "text-warning"
                  : "text-tertiary"
            }`}
          >
            {message}
          </p>
        )}
      </div>
    </div>
  );
}
