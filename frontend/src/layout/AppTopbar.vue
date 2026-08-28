<script setup>
import { useLayout } from '@/layout/composables/layout';
import AppConfigurator from './AppConfigurator.vue';
import UserMenu from '@/components/dashboard/UserMenu.vue'; // ← nuevo menú de usuario
import ComunicadosCampana from '@/components/ComunicadosCampana.vue';
import { useRouter } from 'vue-router';
import { onMounted } from 'vue';
import { useMarcaStore } from '@/stores/marca';
import logoPorDefecto from '@/assets/logo_unsam_sin_letras.png';

const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout();
const router = useRouter();
const marca = useMarcaStore();

onMounted(() => marca.cargar());

// 👉 Ir a Agenda
function irAgenda() {
    router.push('/turnos');
}
</script>

<template>
    <div class="layout-topbar">
        <!-- ◀️ Logo + menú -->
        <div class="layout-topbar-logo-container">
            <button class="layout-menu-button layout-topbar-action" @click="toggleMenu">
                <i class="pi pi-bars"></i>
            </button>

            <!-- Nombre y logo salen del backend, que los resuelve segun el
                 subdominio del consultorio. Estaban escritos aca. -->
            <router-link to="/" class="layout-topbar-logo flex items-center gap-2">
                <img :src="marca.logo || logoPorDefecto" :alt="`Logo ${marca.nombreCorto}`" class="h-8 md:h-10" />
                <div class="flex flex-col leading-tight">
                    <div class="font-bold text-lg">{{ marca.nombreCorto }}</div>
                    <div class="text-xs text-gray-500">{{ marca.nombre }}</div>
                </div>
            </router-link>
        </div>

        <!-- ▶️ Acciones -->
        <div class="layout-topbar-actions flex items-center gap-4">
            <!-- 🧭 Agenda directo -->
            <button type="button" class="layout-topbar-action" @click="irAgenda">
                <i class="pi pi-calendar"></i>
            </button>

            <!-- 🔔 Comunicados -->
            <ComunicadosCampana />

            <!-- 🎨 Tema -->
            <button type="button" class="layout-topbar-action" @click="toggleDarkMode">
                <i :class="['pi', { 'pi-moon': isDarkTheme, 'pi-sun': !isDarkTheme }]"></i>
            </button>

            <!-- 🎛 Configurador -->
            <div class="relative">
                <button
                    v-styleclass="{
                        selector: '@next',
                        enterFromClass: 'hidden',
                        enterActiveClass: 'animate-scalein',
                        leaveToClass: 'hidden',
                        leaveActiveClass: 'animate-fadeout',
                        hideOnOutsideClick: true
                    }"
                    type="button"
                    class="layout-topbar-action layout-topbar-action-highlight"
                >
                    <i class="pi pi-palette"></i>
                </button>
                <AppConfigurator />
            </div>

            <!-- 👤 Nuevo menú de usuario (foto + perfil + logout) -->
            <UserMenu />
        </div>
    </div>
</template>

<style scoped>
.layout-topbar-logo img {
    max-height: 40px;
}
</style>
