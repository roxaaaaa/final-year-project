"use client";

/** OAuth return: read JWT from the URL, store it, then redirect into the app. */

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function AuthCallbackLoading() {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-white text-lg font-medium">Authenticating...</p>
      </div>
    </div>
  );
}

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const token = searchParams.get("token");
  const redirectTo = searchParams.get("redirect_to") || "/";

  useEffect(() => {
    if (!token) {
      router.push("/");
      return;
    }

    localStorage.setItem("token", token);

    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/user/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (!data.persona) {
          router.push("/persona");
        } else {
          router.push(redirectTo);
        }
      })
      .catch((err) => {
        console.error("Failed to load user info", err);
        router.push("/");
      });
  }, [router, token, redirectTo]);

  return <AuthCallbackLoading />;
}

export default function AuthCallback() {
  return (
    <Suspense fallback={<AuthCallbackLoading />}>
      <AuthCallbackContent />
    </Suspense>
  );
}
