import * as SecureStore from "expo-secure-store";

// SecureStore values are limited to about 2 KB, and a Supabase session can be larger,
// so values are split into chunks under `<key>.<n>` with the chunk count at `<key>.count`.
const CHUNK_SIZE = 1800;

async function removeChunks(key: string): Promise<void> {
  const count = Number(await SecureStore.getItemAsync(`${key}.count`)) || 0;
  await Promise.all(
    Array.from({ length: count }, (_, i) => SecureStore.deleteItemAsync(`${key}.${i}`)),
  );
  await SecureStore.deleteItemAsync(`${key}.count`);
}

/** Supabase auth storage backed by the device keychain / keystore (TDD §4.1). */
export const secureStorage = {
  async getItem(key: string): Promise<string | null> {
    const count = Number(await SecureStore.getItemAsync(`${key}.count`)) || 0;
    if (count === 0) return null;
    const chunks = await Promise.all(
      Array.from({ length: count }, (_, i) => SecureStore.getItemAsync(`${key}.${i}`)),
    );
    return chunks.some((c) => c === null) ? null : chunks.join("");
  },

  async setItem(key: string, value: string): Promise<void> {
    await removeChunks(key);
    const chunks = value.match(new RegExp(`[\\s\\S]{1,${CHUNK_SIZE}}`, "g")) ?? [];
    await Promise.all(chunks.map((chunk, i) => SecureStore.setItemAsync(`${key}.${i}`, chunk)));
    await SecureStore.setItemAsync(`${key}.count`, String(chunks.length));
  },

  removeItem: removeChunks,
};
