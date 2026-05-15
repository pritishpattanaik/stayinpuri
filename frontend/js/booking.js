const BookingForm = {
  form: null,

  init() {
    this.form = document.getElementById("booking-form");
    if (!this.form) return;

    this.populateServiceTypes();
    this.bindEvents();
    this.setMinDates();
  },

  populateServiceTypes() {
    const select = this.form.querySelector("#service-type");
    if (!select) return;

    CONFIG.BOOKING.SERVICE_TYPES.forEach((type) => {
      const option = document.createElement("option");
      option.value = type.value;
      option.textContent = type.label;
      select.appendChild(option);
    });
  },

  bindEvents() {
    this.form.addEventListener("submit", (e) => this.handleSubmit(e));

    const serviceSelect = this.form.querySelector("#service-type");
    if (serviceSelect) {
      serviceSelect.addEventListener("change", () =>
        this.toggleDateFields()
      );
    }
  },

  setMinDates() {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + CONFIG.BOOKING.ADVANCE_BOOKING_DAYS);
    const minDate = tomorrow.toISOString().split("T")[0];

    const checkin = this.form.querySelector("#checkin-date");
    const checkout = this.form.querySelector("#checkout-date");
    if (checkin) checkin.min = minDate;
    if (checkout) checkout.min = minDate;
  },

  toggleDateFields() {
    const serviceType = this.form.querySelector("#service-type")?.value;
    const dateGroup = this.form.querySelector("#date-fields");
    const propertyGroup = this.form.querySelector("#property-fields");

    if (!dateGroup) return;

    if (serviceType === "homestay") {
      dateGroup.style.display = "block";
      if (propertyGroup) propertyGroup.style.display = "block";
    } else {
      dateGroup.style.display = "none";
      if (propertyGroup) propertyGroup.style.display = "none";
    }
  },

  getFormData() {
    const data = {
      service_type: this.form.querySelector("#service-type")?.value,
      guest_name: this.form.querySelector("#guest-name")?.value,
      guest_email: this.form.querySelector("#guest-email")?.value,
      guest_phone: this.form.querySelector("#guest-phone")?.value,
      num_guests: parseInt(this.form.querySelector("#num-guests")?.value) || 1,
      special_requests: this.form.querySelector("#special-requests")?.value,
    };

    if (data.service_type === "homestay") {
      data.checkin_date = this.form.querySelector("#checkin-date")?.value;
      data.checkout_date = this.form.querySelector("#checkout-date")?.value;
      data.property_slug = this.form.querySelector("#property-select")?.value;
    }

    return data;
  },

  validate(data) {
    const errors = [];

    if (!data.guest_name || data.guest_name.length < 2) {
      errors.push("Name is required (min 2 characters)");
    }
    if (!data.guest_phone || data.guest_phone.length < 8) {
      errors.push("Phone number is required (min 8 digits)");
    }
    if (!data.service_type) {
      errors.push("Please select a service type");
    }
    if (
      data.service_type === "homestay" &&
      (!data.checkin_date || !data.checkout_date)
    ) {
      errors.push("Check-in and check-out dates are required for homestays");
    }
    if (data.checkin_date && data.checkout_date) {
      if (new Date(data.checkout_date) <= new Date(data.checkin_date)) {
        errors.push("Check-out date must be after check-in date");
      }
    }

    return errors;
  },

  async handleSubmit(e) {
    e.preventDefault();

    const data = this.getFormData();
    const errors = this.validate(data);

    if (errors.length > 0) {
      this.showMessage(errors.join(". "), "error");
      return;
    }

    const submitBtn = this.form.querySelector('button[type="submit"]');
    const originalText = submitBtn?.textContent;

    try {
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Booking...";
      }

      const result = await API.createBooking(data);
      this.showMessage(
        `${CONFIG.BOOKING.CONFIRMATION_MESSAGE} Reference: ${result.booking_ref}`,
        "success"
      );
      this.form.reset();
      this.toggleDateFields();
    } catch (err) {
      this.showMessage(
        err.message || "Booking failed. Please try again.",
        "error"
      );
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
      }
    }
  },

  showMessage(text, type) {
    const msgEl =
      document.getElementById("booking-message") ||
      this.createMessageElement();
    msgEl.textContent = text;
    msgEl.className = `booking-message ${type}`;
    msgEl.style.display = "block";

    if (type === "success") {
      setTimeout(() => {
        msgEl.style.display = "none";
      }, 10000);
    }
  },

  createMessageElement() {
    const el = document.createElement("div");
    el.id = "booking-message";
    this.form.prepend(el);
    return el;
  },
};

document.addEventListener("DOMContentLoaded", () => {
  BookingForm.init();
});
