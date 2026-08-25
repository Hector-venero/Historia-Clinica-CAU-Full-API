/**
 * Descarga de archivos que llegan por la API.
 *
 * Los PDF salen de rutas autenticadas, así que no se pueden abrir con un
 * `window.open` a una URL armada a mano: hay que pedirlos con la instancia
 * `api` (que manda la cookie de sesión) y entregar el blob resultante.
 *
 * Centralizado acá porque cada vista lo resolvía por su cuenta y ninguna
 * liberaba el object URL ni sacaba el <a> del DOM.
 */

/**
 * Dispara la descarga de un blob con el nombre indicado.
 *
 * @param {Blob} blob      contenido del archivo
 * @param {string} nombre  nombre con el que se guarda
 */
export function descargarBlob(blob, nombre) {
    const url = window.URL.createObjectURL(blob);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = nombre;
    document.body.appendChild(enlace);
    enlace.click();

    // Sin esto el <a> se acumula en el DOM y el blob queda retenido en memoria
    // hasta que se recarga la página.
    enlace.remove();
    window.URL.revokeObjectURL(url);
}

/**
 * Pide un PDF a la API y lo descarga.
 *
 * @param {Promise} peticion  promesa de axios con responseType 'blob'
 * @param {string} nombre     nombre del archivo resultante
 */
export async function descargarPdfDesde(peticion, nombre) {
    const { data } = await peticion;
    descargarBlob(new Blob([data], { type: 'application/pdf' }), nombre);
}
