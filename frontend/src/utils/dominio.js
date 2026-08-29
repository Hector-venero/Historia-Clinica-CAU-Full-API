/**
 * Por dónde entró el visitante.
 *
 * La misma aplicación se sirve en tres lugares distintos y `/` significa una
 * cosa en cada uno:
 *
 *   fichasalud.com.ar           → el sitio público
 *   drlopez.fichasalud.com.ar   → el sistema del consultorio
 *   mi.fichasalud.com.ar        → el portal del paciente
 *
 * Estaba resuelto con un `split('.')[0]` suelto en el guard del router. Acá
 * queda en un solo lugar, porque van a hacer falta las tres respuestas y una
 * lógica repetida en varios archivos es una que se va a desincronizar.
 */

// Subdominios del producto: no son consultorios.
const RESERVADOS = ['www', 'api', 'app', 'mi'];

/** La primera etiqueta del host, o null si no hay ninguna. */
function primeraEtiqueta() {
    const host = window.location.host.split(':')[0].toLowerCase();
    const partes = host.split('.');

    // `localhost` a secas no tiene subdominio; `drlopez.localhost` sí.
    if (partes.length < 2) return null;
    return partes[0];
}

/** El portal del paciente vive en `mi.<dominio>`. */
export function esPortalPaciente() {
    return primeraEtiqueta() === 'mi';
}

/**
 * El sitio público: el dominio raíz o `www`.
 *
 * En desarrollo `localhost:5173` cuenta como raíz, que es lo que permite ver el
 * sitio sin montar subdominios en la máquina.
 */
export function esSitioPublico() {
    const etiqueta = primeraEtiqueta();
    return etiqueta === null || etiqueta === 'www';
}

/** El slug del consultorio, o null si no se entró por el de ninguno. */
export function slugConsultorio() {
    const etiqueta = primeraEtiqueta();
    if (etiqueta === null || RESERVADOS.includes(etiqueta)) return null;
    return etiqueta;
}
