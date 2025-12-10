// src/utils/fotoUrl.js

export const buildFotoURL = (filename, timestamp = null) => {
  if (!filename) return null;
  if (filename.startsWith('http')) return filename;

  // 👇 AQUÍ ESTÁ EL TRUCO:
  // En lugar de usar '/api' (que pasa por el proxy y a veces falla con imágenes),
  // apuntamos DIRECTO al servidor Flask que sabemos que funciona (puerto 5000).
  
  // Si estás en producción, usa tu dominio real. En local, usa localhost:5000.
  const isDev = import.meta.env.DEV; 
  const baseUrl = isDev ? 'http://localhost:5000/api' : '/api';

  let url = `${baseUrl}/static/fotos_usuarios/${filename}`;
  
  // Mantenemos el timestamp para romper el caché cuando actualizas
  if (timestamp) {
    url += `?t=${timestamp}`;
  }
  
  return url;
};