import { fileURLToPath, URL } from 'node:url';

import { PrimeVueResolver } from '@primevue/auto-import-resolver';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { defineConfig } from 'vite';

// https://vitejs.dev/config/
export default defineConfig({
    optimizeDeps: {
        noDiscovery: true
    },
    plugins: [
        vue(),
        Components({
            resolvers: [PrimeVueResolver()]
        })
    ],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    server: {
        host: '0.0.0.0', // 🔹 Necesario para exponer el servidor dentro del contenedor
        port: 5173,
        proxy: {
            // El destino depende de desde dónde corra el dev server, así que sale
            // del entorno en vez de estar fijo (antes había que editar el archivo
            // y comentar/descomentar la línea de al lado):
            //   - en la máquina, contra el backend publicado -> localhost:5000
            //   - dentro de la red de Docker (perfil `dev`)  -> http://web:5000
            '/api': {
                target: process.env.VITE_PROXY_TARGET || 'http://localhost:5000',
                // `changeOrigin: false` a proposito: con `true`, el proxy
                // reescribe el encabezado Host al del destino (`web:5000`), y
                // ese encabezado es **lo unico** con lo que el backend sabe a
                // que consultorio pertenece el pedido. Con `true`,
                // drlopez.localhost:5173 respondia 404 "No se indico ningun
                // consultorio" y no habia forma de probar un consultorio con
                // recarga en caliente. El portal y el sitio publico funcionaban
                // igual, porque son justamente los que no necesitan inquilino.
                changeOrigin: false,
                secure: false
            }
        }
    }
});
