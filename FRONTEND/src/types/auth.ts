export type Role = "super_admin" | "director" | "bursar" | "teacher" | "admin_staff";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

/** Decoded JWT shape -- mirrors app/core/security.py TokenPayload on the backend. */
export interface SessionUser {
  sub: string; // user_id
  school_id: string | null;
  role: Role;
  exp: number;
}

/** Which module a role lands on by default -- kept here, single source of
 * truth, used by both middleware.ts (server redirect) and the sidebar
 * (client-side nav filtering) so they can never disagree. */
export const ROLE_HOME: Record<Role, string> = {
  director: "/finance", // directors care most about the money story first
  bursar: "/finance",
  teacher: "/academics",
  admin_staff: "/comms",
  super_admin: "/finance",
};

export const ROLE_MODULES: Record<Role, string[]> = {
  director: ["/finance", "/academics", "/comms"],
  bursar: ["/finance"],
  teacher: ["/academics"],
  admin_staff: ["/comms"],
  super_admin: ["/finance", "/academics", "/comms"],
};