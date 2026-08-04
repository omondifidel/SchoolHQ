import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE, decodeSessionPayload, isExpired } from "@/lib/auth";
import { ROLE_HOME, ROLE_MODULES, type Role } from "@/types/auth";

const PUBLIC_PATHS = ["/login"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  const payload = token ? decodeSessionPayload(token) : null;
  const isLoggedIn = !!payload && !isExpired(payload);

  const isPublicPath = PUBLIC_PATHS.includes(pathname);

  // Not logged in, hitting a protected page -> bounce to login.
  if (!isLoggedIn && !isPublicPath) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Already logged in, hitting /login -> send them to their module home
  // instead of showing the login form again.
  if (isLoggedIn && isPublicPath) {
    return NextResponse.redirect(new URL(ROLE_HOME[payload!.role], request.url));
  }

  if (isLoggedIn) {
    const role = payload!.role as Role;

    // Root of the app: each role lands directly on their own module,
    // per the product decision -- no shared landing page to route
    // through first.
    if (pathname === "/") {
      return NextResponse.redirect(new URL(ROLE_HOME[role], request.url));
    }

    // Role gate: block a teacher from typing /finance into the URL bar
    // directly, etc. This is a UX guard, not the real security boundary
    // -- FastAPI's require_roles + Postgres RLS are what actually
    // enforce this; this just avoids showing someone a page full of
    // 403 errors instead of a clean redirect.
    const allowedModules = ROLE_MODULES[role];
    const isAllowed = allowedModules.some((m) => pathname.startsWith(m));
    if (!isAllowed) {
      return NextResponse.redirect(new URL(ROLE_HOME[role], request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match everything except:
     * - api routes (they handle their own auth)
     * - static files, images, favicon
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
