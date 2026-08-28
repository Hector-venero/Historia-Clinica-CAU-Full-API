<script setup>
import { computed } from 'vue';
import AppMenuItem from './AppMenuItem.vue';
import authService from '@/service/authService';
import { useRouter } from 'vue-router';
import { useSession } from './composables/useSession';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const { clearUser } = useSession();
const userStore = useUserStore(); // 3. Instanciar el store

async function handleLogout() {
    // Marcar la salida antes del pedido: sin esto el guard ve que el store
    // todavía tiene usuario y rebota de vuelta al dashboard.
    userStore.startLogout();
    try {
        await authService.logout();
    } catch (e) {
        console.error('Error cerrando sesión:', e);
    } finally {
        clearUser();
        router.replace('/auth/login?logged_out=1');
    }
}

// 4. Cambiamos 'ref' por 'computed' para poder usar lógica dinámica
const model = computed(() => {
    // Normalizamos el rol para evitar errores de mayúsculas/espacios
    const esDirector = userStore.rol?.toLowerCase().trim() === 'director';

    return [
        {
            label: 'Inicio',
            items: [{ label: 'Dashboard', icon: 'pi pi-fw pi-home', to: '/' }]
        },
        {
            label: 'Pacientes',
            items: [
                { label: 'Listado', icon: 'pi pi-fw pi-users', to: '/pacientes' },
                { label: 'Registrar', icon: 'pi pi-fw pi-user-plus', to: '/pacientes/registrar' }
            ]
        },
        {
            label: 'Historias Clínicas',
            items: [{ label: 'Ver Historias', icon: 'pi pi-fw pi-book', to: '/historias' }]
        },
        {
            label: 'Recetas y Prácticas',
            // Los módulos los define el plan del consultorio. Ocultar la entrada
            // es presentación: quien decide es @requiere_modulo en el backend.
            visible: userStore.tieneModulo('recetas'),
            items: [{ label: 'Generar Receta', icon: 'pi pi-file-edit', to: '/recetas' }]
        },
        {
            label: 'Comunicados',
            visible: userStore.tieneModulo('comunicados'),
            items: [{ label: 'Ver Comunicados', icon: 'pi pi-fw pi-megaphone', to: '/comunicados' }]
        },
        {
            label: 'Turnos',
            items: [
                { label: 'Agenda', icon: 'pi pi-fw pi-calendar', to: '/turnos' },
                { label: 'Nuevo Turno', icon: 'pi pi-fw pi-calendar-plus', to: '/turnos/nuevo' },
                // Las dos pantallas de ajustes van agrupadas: son lo que se
                // toca al configurar la agenda (que dias se atiende y de cuanto
                // es cada turno), no algo del uso diario. Sueltas al mismo nivel
                // que Agenda y Nuevo Turno, competian en peso con lo que se usa
                // todos los dias.
                {
                    label: 'Configuración',
                    icon: 'pi pi-fw pi-cog',
                    items: [
                        { label: 'Disponibilidad', icon: 'pi pi-fw pi-clock', to: '/disponibilidad' },
                        {
                            label: 'Duración de turnos',
                            icon: 'pi pi-fw pi-sliders-h',
                            to: '/turnos/configuracion',
                            visible: ['profesional', 'director', 'area'].includes(userStore.rol)
                        }
                    ]
                }
            ]
        },

        // 🔒 SECCIÓN USUARIOS PROTEGIDA
        {
            label: 'Usuarios',
            visible: esDirector, // <--- ESTA ES LA CLAVE: Solo se muestra si es true
            items: [
                { label: 'Listado', icon: 'pi pi-fw pi-id-card', to: '/usuarios' },
                { label: 'Crear Usuario', icon: 'pi pi-fw pi-user-edit', to: '/usuarios/crear' },
                { label: 'Inactivos', icon: 'pi pi-fw pi-user-minus', to: '/usuarios/inactivos' }
            ]
        },

        {
            label: 'Agendas Grupales',
            visible: userStore.tieneModulo('grupos'),
            items: [
                { label: 'Ver grupos', icon: 'pi pi-fw pi-users', to: '/grupos' },
                { label: 'Crear grupo', icon: 'pi pi-plus', to: '/grupos/crear', visible: esDirector }
            ]
        },
        {
            label: 'Blockchain',
            visible: userStore.tieneModulo('blockchain'),
            items: [{ label: 'Verificar Hash', icon: 'pi pi-fw pi-search', to: '/blockchain/verificar' }]
        },
        {
            label: 'Salir',
            items: [{ label: 'Cerrar sesión', icon: 'pi pi-fw pi-sign-out', command: handleLogout }]
        }
    ];
});
</script>

<template>
    <ul class="layout-menu">
        <template v-for="(item, i) in model" :key="i">
            <app-menu-item v-if="!item.separator && item.visible !== false" :item="item" :index="i" />
            <li v-if="item.separator" class="menu-separator"></li>
        </template>
    </ul>
</template>
