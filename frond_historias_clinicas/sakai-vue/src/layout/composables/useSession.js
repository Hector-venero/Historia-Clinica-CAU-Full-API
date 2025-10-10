import { ref } from 'vue';

const user = ref(null);
const loading = ref(false);
const error = ref('');

export function useSession() {
  async function loadCurrentUser(force = false) {
    if (user.value && !force) return user.value;

    loading.value = true;
    error.value = '';
    try {
      const resp = await fetch('/api/user', { credentials: 'include' });
      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      const data = await resp.json();
      user.value = {
        nombre: data?.nombre || data?.name || data?.username || 'Usuario',
        username: data?.username || '',
        email: data?.email || '',
        rol: data?.rol || data?.role || ''
      };
      return user.value;
    } catch (e) {
      error.value = e?.message || 'No se pudo obtener el usuario';
      user.value = null;
    } finally {
      loading.value = false;
    }
  }

  function clearUser() {
    user.value = null;
  }

  return { user, loading, error, loadCurrentUser, clearUser };
}
