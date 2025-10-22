import axios from 'axios';

export default {
  login(data) {
    return axios.post('/api/login', data, { withCredentials: true });
  },
  logout() {
    return axios.post('/api/logout', {}, { withCredentials: true });
  },
  getUserInfo() {
    return axios.get('/api/user', { withCredentials: true });
  }
};
