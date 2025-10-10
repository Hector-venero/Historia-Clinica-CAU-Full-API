<script setup>
import { useLayout } from '@/layout/composables/layout';
import AppConfigurator from './AppConfigurator.vue';
import UserBadge from '@/components/UserBadge.vue';   // 👈 importamos el badge

const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout();
</script>

<template>
  <div class="layout-topbar">
    <!-- Logo + botón menú -->
    <div class="layout-topbar-logo-container">
      <button class="layout-menu-button layout-topbar-action" @click="toggleMenu">
        <i class="pi pi-bars"></i>
      </button>

      <router-link to="/" class="layout-topbar-logo flex items-center gap-2">
        <!-- ✅ Logo solo imagen -->
        <img
          src="@/assets/logo_unsam_sin_letras.png"
          alt="Logo UNSAM"
          class="h-8 md:h-10"
        />
        <!-- ✅ Texto al lado -->
        <div class="flex flex-col leading-tight">
          <div class="font-bold text-lg">
            CAU <span class="font-normal">UNSAM</span>
          </div>
          <div class="text-xs text-gray-500">Centro Asistencial Universitario</div>
        </div>
      </router-link>
    </div>

    <!-- Acciones topbar -->
    <div class="layout-topbar-actions flex items-center gap-4">
      <!-- 👤 Mostramos el usuario -->
      <UserBadge />

      <!-- Configuración y tema -->
      <div class="layout-config-menu">
        <button type="button" class="layout-topbar-action" @click="toggleDarkMode">
          <i :class="['pi', { 'pi-moon': isDarkTheme, 'pi-sun': !isDarkTheme }]"></i>
        </button>
        <div class="relative">
          <button
            v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'animate-scalein', leaveToClass: 'hidden', leaveActiveClass: 'animate-fadeout', hideOnOutsideClick: true }"
            type="button"
            class="layout-topbar-action layout-topbar-action-highlight"
          >
            <i class="pi pi-palette"></i>
          </button>
          <AppConfigurator />
        </div>
      </div>

      <!-- Menú extra -->
      <button
        class="layout-topbar-menu-button layout-topbar-action"
        v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'animate-scalein', leaveToClass: 'hidden', leaveActiveClass: 'animate-fadeout', hideOnOutsideClick: true }"
      >
        <i class="pi pi-ellipsis-v"></i>
      </button>

      <div class="layout-topbar-menu hidden lg:block">
        <div class="layout-topbar-menu-content">
          <button type="button" class="layout-topbar-action">
            <i class="pi pi-calendar"></i>
            <span>Calendar</span>
          </button>
          <button type="button" class="layout-topbar-action">
            <i class="pi pi-inbox"></i>
            <span>Messages</span>
          </button>
          <button type="button" class="layout-topbar-action">
            <i class="pi pi-user"></i>
            <span>Profile</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.layout-topbar-logo img {
  max-height: 40px;
}
</style>
