<script setup>
import { useUserStore } from '@/stores/user';
import { useRouter } from 'vue-router';
import { ref, computed } from 'vue';
import { buildFotoURL } from '@/utils/fotoUrl.js';

const userStore = useUserStore();
const router = useRouter();

const abierto = ref(false);

// URL completa de la foto con helper reutilizable
const fotoURL = computed(() => buildFotoURL(userStore.foto));

// 👉 Ir a la pantalla de perfil
const irPerfil = () => {
  router.push('/mi-perfil');
  abierto.value = false;
};

// 👉 Ir a cambiar contraseña
const irPassword = () => {
  router.push('/cambiar-password');
  abierto.value = false;
};

// 👉 Logout: usamos la ruta /logout que ya tienes definida
const logout = () => {
  abierto.value = false;     // cerramos el menú para evitar el error de outside click
  router.push('/logout');    // aquí tu vista Logout se encarga de hacer /api/logout y redirigir
};
</script>

<template>
  <div class="relative">

    <!-- Botón con foto o inicial -->
    <button
      class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center overflow-hidden shadow cursor-pointer hover:ring-2 hover:ring-blue-400"
      @click="abierto = !abierto"
    >
      <img
        v-if="fotoURL"
        :src="fotoURL"
        class="w-full h-full object-cover"
      />
      <span v-else class="font-bold text-gray-700">
        {{ userStore.nombre?.charAt(0)?.toUpperCase() }}
      </span>
    </button>

    <!-- Menú flotante -->
    <div
      v-if="abierto"
      class="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border p-3 z-50"
    >
      <div class="pb-3 mb-3 border-b">
        <div class="font-semibold">{{ userStore.nombre }}</div>
        <div class="text-xs text-gray-500">{{ userStore.email }}</div>
        <span class="text-xs font-medium bg-blue-100 text-blue-700 px-2 py-1 rounded mt-1 inline-block">
          {{ userStore.rol }}
        </span>
      </div>

      <button class="w-full text-left px-2 py-2 rounded hover:bg-gray-100" @click="irPerfil">
        👤 Mi Perfil
      </button>

      <button class="w-full text-left px-2 py-2 rounded hover:bg-gray-100" @click="irPassword">
        🔐 Cambiar contraseña
      </button>

      <button class="w-full text-left px-2 py-2 rounded hover:bg-red-100 text-red-600" @click="logout">
        🚪 Cerrar sesión
      </button>
    </div>
  </div>
</template>
