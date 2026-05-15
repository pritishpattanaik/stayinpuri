const API = {
  async request(endpoint, options = {}) {
    const url = `${CONFIG.API_BASE_URL}${endpoint}`;
    const config = {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Request failed: ${response.status}`);
      }
      return await response.json();
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err.message);
      throw err;
    }
  },

  get(endpoint) {
    return this.request(endpoint, { method: "GET" });
  },

  post(endpoint, data) {
    return this.request(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  getProperties() {
    return this.get(CONFIG.API_ENDPOINTS.PROPERTIES);
  },

  getProperty(slug) {
    return this.get(CONFIG.API_ENDPOINTS.PROPERTY(slug));
  },

  getServices() {
    return this.get(CONFIG.API_ENDPOINTS.SERVICES);
  },

  getService(slug) {
    return this.get(CONFIG.API_ENDPOINTS.SERVICE(slug));
  },

  createBooking(bookingData) {
    return this.post(CONFIG.API_ENDPOINTS.BOOKINGS, bookingData);
  },

  getBooking(ref) {
    return this.get(CONFIG.API_ENDPOINTS.BOOKING(ref));
  },

  getBookings(status) {
    const query = status ? `?status=${status}` : "";
    return this.get(`${CONFIG.API_ENDPOINTS.BOOKINGS}${query}`);
  },

  getSiteConfig() {
    return this.get(CONFIG.API_ENDPOINTS.SITE_CONFIG);
  },

  healthCheck() {
    return this.get(CONFIG.API_ENDPOINTS.HEALTH);
  },
};
