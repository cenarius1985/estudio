"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "./Nav";
import { getToken } from "@/lib/api";

/** Guard de sesión + layout con sidebar. */
export default function ConNav({ children, titulo }: { children: React.ReactNode; titulo: string }) {
  const router = useRouter();
  const [listo, setListo] = useState(false);

  useEffect(() => {
    if (!getToken()) router.push("/login");
    else setListo(true);
  }, [router]);

  if (!listo) return null;
  return (
    <div className="flex min-h-screen">
      <Nav />
      <main className="flex-1 p-8 max-w-6xl">
        <h1 className="text-2xl font-bold text-marca-700 mb-6">{titulo}</h1>
        {children}
      </main>
    </div>
  );
}
