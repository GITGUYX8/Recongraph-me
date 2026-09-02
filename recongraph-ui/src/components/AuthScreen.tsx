"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { login, signup } from "@/lib/api";

interface AuthScreenProps {
  onAuthenticated: () => void;
}

export default function AuthScreen({ onAuthenticated }: AuthScreenProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSignup, setIsSignup] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      if (isSignup) {
        if (password !== confirmPassword) {
          throw new Error("Passwords do not match");
        }
        await signup(username, password);
        setIsSignup(false);
        setPassword("");
        setConfirmPassword("");
        setError("Account created. Sign in with your new account.");
      } else {
        await login(username, password);
        onAuthenticated();
      }
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "The API is not reachable. Start the backend on http://localhost:8000 and try again."
          : err instanceof Error
            ? err.message
            : "Unable to sign in",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 md:px-6 max-w-7xl mx-auto flex items-center justify-center">
      <Card className="w-full max-w-md border-border/70 bg-background/95 shadow-lg">
        <CardContent className="p-6 md:p-8">
          <div className="mb-8">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">
              Secure workspace
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight text-foreground">
              Sign in to ReconGraph
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Use your configured auditor or administrator account to access reconciliation data.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              Username
              <input
                autoComplete="username"
                className="h-11 rounded-md border border-border bg-background px-3 font-normal outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </label>

            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              Password
              <input
                type="password"
                autoComplete="current-password"
                className="h-11 rounded-md border border-border bg-background px-3 font-normal outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>

            {isSignup && (
              <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
                Confirm password
                <input
                  type="password"
                  autoComplete="new-password"
                  className="h-11 rounded-md border border-border bg-background px-3 font-normal outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  required
                />
              </label>
            )}

            {error && (
              <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </p>
            )}

            <Button type="submit" size="lg" className="mt-1 w-full" disabled={isLoading}>
              {isLoading ? (isSignup ? "Creating account..." : "Signing in...") : (isSignup ? "Create account" : "Sign in")}
            </Button>

            <button
              type="button"
              className="text-sm text-primary underline-offset-4 hover:underline"
              onClick={() => {
                setIsSignup((value) => !value);
                setError(null);
              }}
            >
              {isSignup ? "Already have an account? Sign in" : "Need an account? Sign up"}
            </button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
