<template>
  <footer class="app-footer">
    <div class="footer-content">
      © 2025 <span class="brand">Historia Clínica CAU</span> — 
      Desarrollado por <span class="author">Héctor Venero</span> |
      Universidad Nacional de San Martín (UNSAM)
    </div>
  </footer>
</template>

<script setup>
// Footer simple, sin lógica adicional
</script>

<style scoped>
.app-footer {
  position: fixed; /* Mantiene el footer siempre visible al final */
  bottom: 0;
  left: 0;
  width: 100%;
  height: 40px;
  background-color: #f9fafb;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 13px;
  color: #6b7280;
  z-index: 100; /* Para que quede sobre el contenido, sin taparlo */
}

/* Espaciado interno del texto */
.footer-content {
  text-align: center;
  line-height: 1.5;
}

.brand {
  color: #003b70;
  font-weight: 600;
}

.author {
  color: #00936b;
  font-weight: 600;
}
</style>
