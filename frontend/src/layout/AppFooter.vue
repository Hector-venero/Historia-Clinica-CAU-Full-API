<script setup>
import { computed, onMounted } from 'vue';
import { useMarcaStore } from '@/stores/marca';

const marca = useMarcaStore();
const anio = computed(() => new Date().getFullYear());

onMounted(() => marca.cargar());
</script>

<template>
    <!-- El nombre sale de la marca del consultorio. La autoría del sistema se
         mantiene: el software es el mismo, lo que cambia es quién lo usa. -->
    <footer class="app-footer">
        <div class="footer-content">
            © {{ anio }} <span class="brand">{{ marca.nombreCorto }}</span> — con <span class="author">Ficha Salud</span>
        </div>
    </footer>
</template>

<style scoped>
/* Fluye al final del contenido, no `position: fixed`.
 *
 * Fijo al fondo con `z-index: 100` se superponía a las tarjetas: el contenedor
 * deja 2rem de margen inferior y el pie mide 40px, así que la última franja de
 * cada pantalla quedaba debajo. Mantener esas dos medidas sincronizadas desde
 * archivos distintos es justamente lo que ya falló. */
.app-footer {
    width: 100%;
    min-height: 40px;
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 13px;
    border-top: 1px solid var(--footer-border);
    background-color: var(--footer-bg);
    color: var(--footer-text);
    transition:
        background-color 0.3s ease,
        color 0.3s ease;
}

.footer-content {
    text-align: center;
    line-height: 1.5;
}

/* Colores institucionales */
.brand {
    color: var(--footer-brand);
    font-weight: 600;
}

.author {
    color: var(--footer-author);
    font-weight: 600;
}

/* ====== 🎨 Tema claro ====== */
:root {
    --footer-bg: #f9fafb;
    --footer-border: #e5e7eb;
    --footer-text: #6b7280;
    --footer-brand: #003b70;
    --footer-author: #00936b;
}

/* ====== 🌙 Tema oscuro ====== */
.app-dark .app-footer,
html.dark .app-footer {
    --footer-bg: #1a1a1a;
    --footer-border: #2e2e2e;
    --footer-text: #e0e0e0;
    --footer-brand: #3db5e6; /* celeste institucional */
    --footer-author: #00bfa5; /* verde turquesa */
}
</style>
