"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken, clearTokens } from "@/lib/api";

export function useAuth() {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  useEffect(() => {
    setAuthed(!!getToken());
    setReady(true);
  }, []);
  return { ready, authed };
}

/** Redirect to /login if there is no token. Returns whether we're checking. */
export function useRequireAuth() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setChecking(false);
  }, [router]);
  return checking;
}

export function logout() {
  clearTokens();
}
