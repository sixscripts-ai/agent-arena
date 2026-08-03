import { Account, Client } from "appwrite";

const endpoint = process.env.NEXT_PUBLIC_APPWRITE_ENDPOINT || "";
const projectId = process.env.NEXT_PUBLIC_APPWRITE_PROJECT_ID || "";

export function createAppwriteClient() {
  const client = new Client().setEndpoint(endpoint).setProject(projectId);
  return client;
}

export function getAccount(client?: Client) {
  return new Account(client ?? createAppwriteClient());
}

export async function signup(email: string, password: string, name: string) {
  const account = getAccount();
  await account.create("unique()", email, password, name);
  return login(email, password);
}

export async function login(email: string, password: string) {
  const account = getAccount();
  await account.createEmailPasswordSession(email, password);
  return account.get();
}

export async function logout() {
  const account = getAccount();
  try {
    await account.deleteSession("current");
  } catch {
    /* already logged out */
  }
}

export async function getSessionUser() {
  const account = getAccount();
  try {
    return await account.get();
  } catch {
    return null;
  }
}

export async function createJwt(): Promise<string | null> {
  const account = getAccount();
  try {
    const jwt = await account.createJWT();
    return jwt.jwt;
  } catch {
    return null;
  }
}
