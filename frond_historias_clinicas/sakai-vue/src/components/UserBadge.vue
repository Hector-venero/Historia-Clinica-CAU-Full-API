
<template>
  <div class="flex items-center gap-3">
    <div v-if="loading" class="flex items-center gap-2">
      <div class="animate-pulse w-8 h-8 rounded-full bg-gray-300/60"></div>
      <div class="animate-pulse h-4 w-28 rounded bg-gray-300/60"></div>
      <div class="animate-pulse h-5 w-16 rounded bg-gray-300/60"></div>
    </div>

    <template v-else-if="user">
      <div class="text-right leading-tight hidden sm:block">
        <div class="font-medium text-sm">{{ user.nombre }}</div>
        <div class="text-xs text-gray-500">{{ user.username }}</div>
      </div>

      <!-- Avatar con iniciales -->
      <div
        class="w-8 h-8 rounded-full flex items-center justify-center bg-sky-600 text-white font-semibold"
        :title="user.email || user.username"
      >
        {{ initials }}
      </div>

      <!-- Rol -->
      <span
        class="px-2 py-1 text-xs rounded-full border"
        :class="roleClass"
        :title="`Rol: ${user.rol}`"
      >
        {{ user.rol || '—' }}
      </span>
    </template>

    <template v-else>
      <span class="text-sm text-gray-500">No autenticado</span>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useSession } from '@/layout/composables/useSession';

const { user, loading, loadCurrentUser } = useSession();

onMounted(() => {
  loadCurrentUser();
});

const initials = computed(() => {
  const n = user.value?.nombre?.trim() || user.value?.username || '';
  if (!n) return '?';
  const parts = n.split(/\s+/).slice(0, 2);
  return parts.map(p => p[0]?.toUpperCase()).join('');
});

const roleClass = computed(() => {
  const r = (user.value?.rol || '').toLowerCase();
  if (r === 'director') return 'bg-emerald-50 border-emerald-200 text-emerald-700';
  if (r === 'administrativo') return 'bg-indigo-50 border-indigo-200 text-indigo-700';
  if (r === 'profesional') return 'bg-amber-50 border-amber-200 text-amber-700';
  return 'bg-gray-50 border-gray-200 text-gray-700';
});
</script>

<style scoped>
</style>
