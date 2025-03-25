document.addEventListener("DOMContentLoaded", () => {
  // Lấy dữ liệu lịch khám từ localStorage (nếu có)
  let appointments = JSON.parse(localStorage.getItem("appointments")) || {};

  // Chọn tất cả các ô khung giờ trong bảng lịch
  const timeSlotCells = document.querySelectorAll(".time-slot");

  // Lấy các phần tử của modal và các container bên trong modal
  const modal = document.getElementById("appointment-modal");
  const formContainer = document.getElementById("form-container");
  const detailsContainer = document.getElementById("details-container");
  const detailsContent = document.getElementById("details-content");
  const closeDetailsBtn = document.getElementById("close-details");

  // Lấy các phần tử của form đặt lịch
  const appointmentForm = document.getElementById("appointment-form");
  const patientNameInput = document.getElementById("patient-name");
  const serviceSelect = document.getElementById("service");
  const appointmentDayInput = document.getElementById("appointment-day");
  const appointmentTimeSelect = document.getElementById("appointment-time");
  const appointmentNoteInput = document.getElementById("appointment-note");

  // Lấy tất cả các nút đóng modal (có class "close")
  const closeButtons = modal.querySelectorAll(".close");

  // Hàm hiển thị các lịch đã đặt trên bảng theo cặp "ngày-giờ"
  function renderAppointments() {
    timeSlotCells.forEach((cell) => {
      const day = cell.getAttribute("data-day");
      const time = cell.getAttribute("data-time");
      const key = `${day}-${time}`;
      cell.innerHTML = "";
      if (appointments[key]) {
        const appointmentData = appointments[key];
        cell.classList.add("appointment-marked");
        cell.innerHTML = `<strong>${appointmentData.patientName}</strong><br>${time}`;
      } else {
        cell.classList.remove("appointment-marked");
      }
    });
  }

  // Gán sự kiện click cho từng ô khung giờ
  timeSlotCells.forEach((cell) => {
    cell.addEventListener("click", () => {
      const day = cell.getAttribute("data-day");
      const time = cell.getAttribute("data-time");
      const key = `${day}-${time}`;
      if (appointments[key]) {
        // Nếu ô đã có lịch, hiển thị chi tiết lịch đặt
        const appData = appointments[key];
        detailsContent.innerHTML = `
          <p><strong>Họ tên:</strong> ${appData.patientName}</p>
          <p><strong>Dịch vụ:</strong> ${appData.service}</p>
          <p><strong>Ghi chú:</strong> ${appData.note || "Không có ghi chú"}</p>
          <p><strong>Thời gian:</strong> ${day} - ${time}</p>
        `;
        formContainer.style.display = "none";
        detailsContainer.style.display = "block";
        modal.style.display = "flex";
      } else {
        // Nếu ô chưa có lịch, hiển thị form đặt lịch
        formContainer.style.display = "block";
        detailsContainer.style.display = "none";
        appointmentDayInput.value = day;
        appointmentTimeSelect.value = time;
        patientNameInput.value = "";
        serviceSelect.value = "";
        appointmentNoteInput.value = "";
        modal.style.display = "flex";
      }
    });
  });

  // Sự kiện đóng modal từ tất cả các nút có class "close"
  closeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      modal.style.display = "none";
    });
  });

  // Sự kiện đóng modal khi click bên ngoài nội dung modal
  window.addEventListener("click", (event) => {
    if (event.target === modal) {
      modal.style.display = "none";
    }
  });

  // Xử lý submit form đặt lịch
  appointmentForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const day = appointmentDayInput.value;
    const time = appointmentTimeSelect.value;
    const patientName = patientNameInput.value.trim();
    const service = serviceSelect.value;
    const note = appointmentNoteInput.value.trim();

    if (!patientName || !service) {
      alert("Vui lòng điền đầy đủ thông tin cần thiết!");
      return;
    }

    const key = `${day}-${time}`;
    if (appointments[key]) {
      if (
        !confirm("Đã có lịch khám ở khung giờ này. Bạn có muốn cập nhật không?")
      ) {
        return;
      }
    }
    appointments[key] = { patientName, service, note };
    localStorage.setItem("appointments", JSON.stringify(appointments));
    renderAppointments();
    modal.style.display = "none";
  });

  // Xử lý nút "Đóng" trong chi tiết lịch đặt
  closeDetailsBtn.addEventListener("click", () => {
    modal.style.display = "none";
  });

  // Hiển thị lịch khám khi tải trang
  renderAppointments();
});
