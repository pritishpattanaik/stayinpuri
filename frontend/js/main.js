const App = {
  init() {
    this.initNavbar();
    this.initSmoothScroll();
    this.loadDynamicContent();
  },

  initNavbar() {
    const hamburger = document.querySelector(".navbar-hamburger");
    const navLinks = document.querySelector(".navbar-links");

    if (hamburger && navLinks) {
      hamburger.addEventListener("click", () => {
        navLinks.classList.toggle("active");
        hamburger.classList.toggle("active");
      });

      navLinks.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => {
          navLinks.classList.remove("active");
          hamburger.classList.remove("active");
        });
      });
    }

    this.setActiveNavLink();
  },

  setActiveNavLink() {
    const currentPage = window.location.pathname.split("/").pop() || "index.html";
    document.querySelectorAll(".navbar-links a").forEach((link) => {
      const href = link.getAttribute("href");
      if (href === currentPage || (currentPage === "" && href === "index.html")) {
        link.classList.add("active");
      }
    });
  },

  initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener("click", function (e) {
        const targetId = this.getAttribute("href");
        if (targetId === "#") return;
        e.preventDefault();
        const target = document.querySelector(targetId);
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    });
  },

  applyPlaceholders(root) {
    const scope = root || document;
    scope.querySelectorAll(".card-image-wrapper").forEach((wrapper) => {
      const img = wrapper.querySelector("img");
      if (!img) return;

      const src = img.getAttribute("src");
      if (src && src !== "" && !src.includes("placeholder")) return;

      const label = img.getAttribute("data-placeholder") || img.alt || "Image";
      const emoji = img.getAttribute("data-emoji") || "📷";
      const tag = wrapper.querySelector(".card-tag");
      const tagHTML = tag ? tag.outerHTML : "";

      wrapper.innerHTML = `
        <div style="background:#F5EDD8; display:flex; flex-direction:column;
          align-items:center; justify-content:center; height:100%; width:100%;
          border-radius:4px 4px 0 0;">
          <span style="font-size:2.5rem">${emoji}</span>
          <span style="color:#6B4C3B; font-size:0.8rem; margin-top:8px;
            text-align:center; padding:0 10px">${label}</span>
          <span style="color:#C9973A; font-size:0.7rem; margin-top:4px">
            📷 Photo coming soon</span>
        </div>${tagHTML}`;
    });
  },

  async loadDynamicContent() {
    try {
      const health = await API.healthCheck();
      console.log(`Connected to ${health.app} API`);
    } catch {
      console.log("API not available — using frontend config only");
    }
  },

  renderCards(containerId, items, cardRenderer) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = "";
    items.forEach((item) => {
      const card = cardRenderer(item);
      container.appendChild(card);
    });

    this.applyPlaceholders(container);
  },

  createTempleCard(temple) {
    const card = document.createElement("div");
    card.className = "card temple-card";
    card.innerHTML = `
      <div class="card-image-wrapper">
        <img alt="${temple.name}" data-placeholder="${temple.name}" data-emoji="${temple.emoji}" />
        <span class="card-tag" style="background-color: ${temple.tagColor}">${temple.tag}</span>
      </div>
      <div class="card-body">
        <h3 class="card-title">${temple.emoji} ${temple.name}</h3>
        <p class="card-description">${temple.description}</p>
        ${
          temple.darshan_timings
            ? `<p class="card-detail"><i class="fas fa-clock"></i> ${temple.darshan_timings}`
            : ""
        }
        ${
          temple.timings
            ? `<p class="card-detail"><i class="fas fa-clock"></i> ${temple.timings}</p>`
            : ""
        }
        ${
          temple.entry_fee
            ? `<p class="card-detail"><i class="fas fa-ticket"></i> ${temple.entry_fee}</p>`
            : ""
        }
        ${
          temple.distance_from_beach
            ? `<p class="card-detail"><i class="fas fa-walking"></i> ${temple.distance_from_beach} from beach</p>`
            : ""
        }
        ${
          temple.distance_from_puri
            ? `<p class="card-detail"><i class="fas fa-map-marker-alt"></i> ${temple.distance_from_puri} from Puri</p>`
            : ""
        }
        ${
          temple.tips
            ? `<p class="card-tip"><i class="fas fa-lightbulb"></i> ${temple.tips}</p>`
            : ""
        }
        ${
          temple.best_time
            ? `<p class="card-detail"><i class="fas fa-calendar"></i> Best: ${temple.best_time}</p>`
            : ""
        }
      </div>
    `;
    return card;
  },

  createServiceCard(service) {
    const card = document.createElement("div");
    card.className = "card service-card";
    card.innerHTML = `
      <div class="card-image-wrapper">
        <img alt="${service.name}" data-placeholder="${service.name}" data-emoji="${service.emoji}" />
      </div>
      <div class="card-body">
        <h3 class="card-title"><i class="fas ${service.icon}"></i> ${service.name}</h3>
        <p class="card-description">${service.description}</p>
        <div class="card-price">
          <span class="price-amount">₹${service.price.toLocaleString()}</span>
          <span class="price-unit">${service.price_unit}</span>
        </div>
        <a href="services.html#booking" class="btn btn-primary btn-sm">Book Now</a>
      </div>
    `;
    return card;
  },

  createFoodCard(food) {
    const card = document.createElement("div");
    card.className = "card food-card";
    card.innerHTML = `
      <div class="card-image-wrapper">
        <img alt="${food.name}" data-placeholder="${food.name}" data-emoji="${food.emoji}" />
      </div>
      <div class="card-body">
        <h3 class="card-title">${food.emoji} ${food.name}</h3>
        <p class="card-description">${food.description}</p>
        <p class="card-detail"><i class="fas fa-utensils"></i> Where: ${food.where_to_eat}</p>
      </div>
    `;
    return card;
  },

  createPropertyCard(prop) {
    const card = document.createElement("div");
    card.className = "card property-card";
    card.innerHTML = `
      <div class="card-image-wrapper">
        <img alt="${prop.name}" data-placeholder="${prop.name}" data-emoji="🏠" />
      </div>
      <div class="card-body">
        <h3 class="card-title">🏠 ${prop.name}</h3>
        <p class="card-description">${prop.description || "A comfortable homestay in Puri with modern amenities and traditional Odia hospitality."}</p>
        <div class="homestay-features">
          <span class="homestay-feature"><i class="fas fa-users"></i> ${prop.capacity} Guests</span>
          <span class="homestay-feature"><i class="fas fa-bed"></i> ${prop.bedrooms} Bedrooms</span>
          <span class="homestay-feature"><i class="fas fa-wifi"></i> WiFi</span>
          <span class="homestay-feature"><i class="fas fa-snowflake"></i> AC</span>
        </div>
        <div class="card-price">
          <span class="price-amount">₹${prop.price.toLocaleString()}</span>
          <span class="price-unit">per night</span>
        </div>
        <a href="#booking" class="btn btn-primary btn-sm">Book This Property</a>
      </div>
    `;
    return card;
  },

  async loadProperties(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let properties = [];
    try {
      properties = await API.getProperties();
    } catch {
      console.log("API unavailable — loading properties from CONFIG");
      properties = [
        {
          name: CONFIG.PROPERTY_1_NAME || "Asiyana",
          slug: CONFIG.PROPERTY_1_SLUG || "asiyana",
          capacity: 4,
          bedrooms: 2,
          price: 2500,
          description: "A beautiful and cozy homestay located near Puri beach. Perfect for families seeking a peaceful retreat.",
        },
        {
          name: CONFIG.PROPERTY_2_NAME || "Tulsi Vihar",
          slug: CONFIG.PROPERTY_2_SLUG || "tulsi-vihar",
          capacity: 3,
          bedrooms: 2,
          price: 2000,
          description: "A charming homestay close to the Jagannath Temple. Ideal for devotees and travelers.",
        },
      ];
    }

    this.renderCards(containerId, properties, (prop) => this.createPropertyCard(prop));

    const propertySelect = document.getElementById("property-select");
    if (propertySelect) {
      propertySelect.innerHTML = '<option value="">Select property...</option>';
      properties.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.slug;
        opt.textContent = `${p.name} — ₹${(p.price_per_night || p.price).toLocaleString()}/night`;
        propertySelect.appendChild(opt);
      });
    }
  },
};

document.addEventListener("DOMContentLoaded", () => {
  App.init();
  App.applyPlaceholders();
});
