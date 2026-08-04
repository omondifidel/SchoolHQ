import type { SessionUser } from "@/types/auth";

export const SESSION_COOKIE = "schoolhq_session";

/**
 * Decodes a JWT payload WITHOUT verifying its signature. This is
 * deliberate and safe here because:
 *   1. The cookie is httpOnly + set only by our own /api/auth/login
 *      route after a real FastAPI login succeeds -- a browser script
 *      can never read or forge it.
 *   2. Every actual data request goes through /api/backend/[...path],
 *      which forwards the raw token to FastAPI, and FastAPI
 *      independently verifies the signature there.
 * So this function is ONLY used for reading role/exp to make quick
 * redirect decisions (which page to land on, whether to bounce to
 * /login) -- never as the source of truth for authorization. If someone
 * tampered with the cookie, the worst case is a confusing redirect --
 * FastAPI will still reject the bad token on the next real request.
 */
export function decodeSessionPayload(token: string): SessionUser | null {
  try {
    const [, payloadB64] = token.split(".");
    const json = Buffer.from(payloadB64, "base64").toString("utf-8");
    return JSON.parse(json) as SessionUser;
  } catch {
    return null;
  }
}

export function isExpired(payload: SessionUser): boolean {
  return payload.exp * 1000 < Date.now();
}