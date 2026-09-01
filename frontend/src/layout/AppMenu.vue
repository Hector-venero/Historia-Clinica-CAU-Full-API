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
    // Normalizamos el rol para evitar errores de mayúsculas/espacios.
    //
    // Se hace UNA vez y se usa en todas las comprobaciones: hasta ahora esta
    // línea normalizaba y las de más abajo comparaban `userStore.rol` crudo, así
    // que un rol con otra capitalización habría escondido medio menú sin que
    // nadie entendiera por qué.
    const rol = userStore.rol?.toLowerCase().trim();
    const esDirector = rol === 'director';

    /**
     * Una sección que depende de un módulo del plan.
     *
     * Antes, lo que no estaba contratado simplemente no aparecía, y el
     * consultorio nunca se enteraba de que existía: esconderlo le ahorra una
     * frustración a quien no paga y le cuesta la venta a quien sí pagaría.
     *
     * Ahora aparece con candado y lleva a la pantalla del plan. Solo para la
     * dirección: es quien decide qué se contrata, y al resto del equipo una
     * entrada que no puede usar ni desbloquear es ruido.
     *
     * Esto es presentación. Quien decide de verdad es @requiere_modulo, en el
     * servidor: la ruta sigue devolviendo 403.
     */
    function seccionDeModulo(modulo, seccion) {
        if (userStore.tieneModulo(modulo)) return seccion;
        if (!esDirector || !userStore.moduloBloqueado(modulo)) return { ...seccion, visible: false };
        return {
            ...seccion,
            items: [{ label: 'No incluido en tu plan', icon: 'pi pi-fw pi-lock', to: '/plan' }]
        };
    }

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
        seccionDeModulo('recetas', {
            label: 'Recetas y Prácticas',
            // Dos condiciones, porque son dos cosas distintas: el **módulo** dice
            // qué contrató el consultorio y el **rol**, quién puede emitir.
            //
            // Faltaba la segunda. La ruta exige director o profesional, así que
            // un administrativo con el módulo contratado veía la entrada y lo
            // rebotaba el guard. Es el mismo problema que ya se había arreglado
            // en la ruta y quedó pendiente en el menú.
            //
            // Ocultar la entrada es presentación: quien decide de verdad son
            // @requiere_modulo y @requiere_rol en el backend.
            visible: ['director', 'profesional'].includes(rol),
            items: [{ label: 'Generar Receta', icon: 'pi pi-file-edit', to: '/recetas' }]
        }),
        seccionDeModulo('comunicados', {
            label: 'Comunicados',
            items: [{ label: 'Ver Comunicados', icon: 'pi pi-fw pi-megaphone', to: '/comunicados' }]
        }),
        {
            label: 'Turnos',
            items: [
                { label: 'Agenda', icon: 'pi pi-fw pi-calendar', to: '/turnos' },
                { label: 'Nuevo Turno', icon: 'pi pi-fw pi-calendar-plus', to: '/turnos/nuevo' },
                // Una sola entrada. Antes eran cuatro pantallas sueltas
                // repartidas por el menú, y poner en marcha un consultorio era
                // ir a buscarlas de a una sin que nada dijera que existían.
                //
                // Cada pestaña de esa pantalla filtra por rol con la misma
                // lista que declara su ruta, así que acá alcanza con exigir el
                // rol que ve *alguna*: el `area` configura disponibilidad y
                // duración, el administrativo servicios y avisos.
                { label: 'Configuración', icon: 'pi pi-fw pi-cog', to: '/configuracion' }
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

        seccionDeModulo('grupos', {
            label: 'Agendas Grupales',
            items: [
                { label: 'Ver grupos', icon: 'pi pi-fw pi-users', to: '/grupos' },
                { label: 'Crear grupo', icon: 'pi pi-plus', to: '/grupos/crear', visible: esDirector }
            ]
        }),
        seccionDeModulo('blockchain', {
            label: 'Blockchain',
            items: [{ label: 'Verificar Hash', icon: 'pi pi-fw pi-search', to: '/blockchain/verificar' }]
        }),
        {
            label: 'Mi cuenta',
            // Solo con planes. En la instalación de un solo centro no hay nada
            // que mostrar: no se contrata, se instala.
            visible: esDirector && !!userStore.plan,
            items: [{ label: 'Plan y módulos', icon: 'pi pi-fw pi-verified', to: '/plan' }]
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
