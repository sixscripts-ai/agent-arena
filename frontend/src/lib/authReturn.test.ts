import assert from "node:assert/strict";
import { authRoute, currentInternalReturn, sanitizeInternalReturn } from "./authReturn.ts";

assert.equal(sanitizeInternalReturn("/battles/new?format=duel#setup"), "/battles/new?format=duel#setup");
assert.equal(sanitizeInternalReturn("https://example.com"), "/");
assert.equal(sanitizeInternalReturn("//example.com"), "/");
assert.equal(sanitizeInternalReturn("battles/new"), "/");
assert.equal(authRoute("login", "/providers"), "/login?next=%2Fproviders");
assert.equal(authRoute("signup", "/"), "/signup");
assert.equal(currentInternalReturn({ pathname: "/battles/a1", search: "?tab=artifact", hash: "#latest" }), "/battles/a1?tab=artifact#latest");
