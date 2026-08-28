import axios from 'axios';

// Antes: window.location.origin.replace('https://', 'http://') + '/api'
// Eso degradaba la conexion de HTTPS a HTTP en produccion, mandando la cookie
// de sesion en claro. Una ruta relativa deja que el navegador resuelva host y
// esquema, que es lo correcto detras del proxy de nginx.
const baseURL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
    baseURL,
    withCredentials: true
});

const PUBLIC_PATHS = ['/auth/login', '/recuperar', '/logout'];

const isPublicPath = (path) => PUBLIC_PATHS.some((p) => path.startsWith(p)) || path.startsWith('/reset/');

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Import diferido: si se importa el router arriba se arma un ciclo
            // (axios -> router -> stores/user -> usuarioService -> axios).
            const { default: router } = await import('@/router');
            const currentPath = router.currentRoute?.value?.path || '';

            if (!isPublicPath(currentPath)) {
                router.push('/auth/login');
            }
        }

        // 402: la cuenta del consultorio está suspendida. No es un problema de
        // permisos del usuario sino del estado de la suscripción, así que en vez
        // de un error suelto se lleva a la pantalla que explica qué pasó y deja
        // descargar los datos.
        if (error.response?.status === 402) {
            const { default: router } = await import('@/router');
            if (router.currentRoute?.value?.path !== '/cuenta/suspendida') {
                router.push('/cuenta/suspendida');
            }
        }

        return Promise.reject(error);
    }
);

export default api;
