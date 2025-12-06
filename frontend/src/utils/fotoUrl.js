// utils/fotoUrl.js

export function buildFotoURL(filename) {
  if (!filename) return null;

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

  return `${API_URL}/static/fotos_usuarios/${filename}?v=${Date.now()}`;
}
