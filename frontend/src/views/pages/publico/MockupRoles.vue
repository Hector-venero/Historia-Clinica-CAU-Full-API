<script setup>
/**
 * Los roles y su acceso, dibujados como una matriz.
 *
 * La pagina de secretaria dice que el permiso se valida en el servidor; lo que
 * hay que ver de un vistazo es **que** ve cada uno. Una matriz de cuatro roles
 * por cuatro secciones lo dice sin un parrafo.
 */
const SECCIONES = ['Turnos', 'Pacientes', 'Historia', 'Usuarios'];

// true = accede. La fila de secretaria es el punto de la pagina: turnos y
// pacientes si, historia clinica no.
const ROLES = [
    { nombre: 'Dirección', acceso: [true, true, true, true] },
    { nombre: 'Profesional', acceso: [true, true, true, false] },
    { nombre: 'Secretaría', acceso: [true, true, false, false], destacado: true },
    { nombre: 'Referente de área', acceso: [true, true, false, false] }
];
</script>

<template>
    <div class="relative">
        <div class="absolute -inset-8 bg-gradient-to-tr from-indigo-400/15 via-primary-300/10 to-transparent blur-3xl rounded-full" aria-hidden="true"></div>

        <div class="relative rounded-2xl bg-white dark:bg-slate-900 shadow-2xl shadow-slate-900/10 dark:shadow-black/40 ring-1 ring-slate-900/5 dark:ring-white/10 overflow-hidden">
            <div class="px-5 py-4 border-b border-slate-200 dark:border-slate-700">
                <p class="text-sm font-bold text-slate-900 dark:text-white m-0">Permisos por rol</p>
                <p class="text-[11px] text-slate-500 dark:text-slate-400 m-0 mt-0.5">Se validan en el servidor</p>
            </div>

            <div class="p-4 overflow-x-auto">
                <table class="w-full border-collapse text-[11px] min-w-[20rem]">
                    <thead>
                        <tr>
                            <th class="text-left font-semibold text-slate-400 dark:text-slate-500 py-2 pr-3">Rol</th>
                            <th v-for="s in SECCIONES" :key="s" class="font-semibold text-slate-400 dark:text-slate-500 py-2 px-1.5 text-center">{{ s }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="r in ROLES" :key="r.nombre" class="border-t border-slate-100 dark:border-slate-800" :class="r.destacado ? 'bg-primary-500/5' : ''">
                            <td class="py-2.5 pr-3 font-medium text-slate-700 dark:text-slate-200 whitespace-nowrap">{{ r.nombre }}</td>
                            <td v-for="(ok, i) in r.acceso" :key="i" class="py-2.5 px-1.5 text-center">
                                <i v-if="ok" class="pi pi-check text-primary-500 text-[10px]"></i>
                                <i v-else class="pi pi-times text-slate-300 dark:text-slate-700 text-[10px]"></i>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</template>
