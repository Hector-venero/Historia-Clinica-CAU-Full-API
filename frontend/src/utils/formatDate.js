export function parseFecha(fecha) {
  if (!fecha || typeof fecha !== "string") return null;

  // Normalizamos "YYYY-MM-DD HH:MM:SS" → "YYYY-MM-DDTHH:MM:SS"
  const normalizada = fecha.replace(" ", "T");

  const date = new Date(normalizada);

  // Si es inválida → retorna null
  return isNaN(date.getTime()) ? null : date;
}

export function fechaBonita(fecha) {
  const d = parseFecha(fecha);
  return d ? d.toLocaleString("es-AR") : "-";
}
