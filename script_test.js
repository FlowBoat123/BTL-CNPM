document.addEventListener("DOMContentLoaded", () => {
  // Xử lý điều hướng trang (nếu các phần tử với id này tồn tại)
  const navHome = document.getElementById("home");
  const navSchedule = document.getElementById("schedule");
  const navSettings = document.getElementById("settings");
  const navLogout = document.getElementById("logout");

  if (navHome) {
    navHome.addEventListener("click", () => {
      window.location.href = "index.html";
    });
  }
  if (navSchedule) {
    navSchedule.addEventListener("click", () => {
      window.location.href = "schedule.html";
    });
  }
  if (navSettings) {
    navSettings.addEventListener("click", () => {
      window.location.href = "settings.html";
    });
  }
  if (navLogout) {
    navLogout.addEventListener("click", () => {
      window.location.href = "logout.html";
    });
  }

  // Lấy dữ liệu lịch khám từ localStorage (nếu có)
  let appointments = JSON.parse(localStorage.getItem("appointments")) || {};

  // Chọn tất cả các ô khung giờ trong bảng lịch
  const timeSlotCells = document.querySelectorAll(".time-slot");

  // Lấy các phần tử của modal và form nhập thông tin lịch khám
  const modal = document.getElementById("appointment-modal");
  const closeModal = document.querySelector(".close");
  const appointmentForm = document.getElementById("appointment-form");

  const patientNameInput = document.getElementById("patient-name");
  const serviceSelect = document.getElementById("service");
  const appointmentDayInput = document.getElementById("appointment-day");
  const appointmentTimeSelect = document.getElementById("appointment-time");
  const appointmentNoteInput = document.getElementById("appointment-note");

  let currentCell = null;

  // Hàm hiển thị lịch khám trên bảng theo cặp "ngày-giờ"
  function renderAppointments() {
    timeSlotCells.forEach((cell) => {
      const day = cell.getAttribute("data-day");
      const time = cell.getAttribute("data-time");
      const key = `${day}-${time}`;
      // Reset nội dung ô
      cell.innerHTML = "";
      // Nếu có lịch khám lưu trong localStorage cho ô này thì hiển thị
      if (appointments[key]) {
        const appointmentData = appointments[key];
        cell.classList.add("appointment-marked");
        cell.innerHTML = `<strong>${appointmentData.patientName}</strong><br>${time}`;
      } else {
        cell.classList.remove("appointment-marked");
      }
    });
  }

  // Gán sự kiện click cho từng ô khung giờ để mở modal nhập lịch khám
  timeSlotCells.forEach((cell) => {
    cell.addEventListener("click", () => {
      currentCell = cell;
      const day = cell.getAttribute("data-day");
      const time = cell.getAttribute("data-time");
      // Gán giá trị cho field ngày khám (đọc được từ ô được click)
      appointmentDayInput.value = day;
      // Đặt mặc định dropdown giờ khám là giờ của ô đó
      appointmentTimeSelect.value = time;
      // Reset form modal
      patientNameInput.value = "";
      serviceSelect.value = "";
      appointmentNoteInput.value = "";
      modal.style.display = "flex";
    });
  });

  // Đóng modal khi click vào dấu X
  closeModal.addEventListener("click", () => {
    modal.style.display = "none";
  });

  // Đóng modal khi click ra ngoài modal-content
  window.addEventListener("click", (event) => {
    if (event.target === modal) {
      modal.style.display = "none";
    }
  });

  // Xử lý khi form modal được submit
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

    // Tạo key cho lịch khám
    const key = `${day}-${time}`;

    // Nếu đã có lịch ở khung giờ này, hỏi xác nhận cập nhật
    if (appointments[key]) {
      if (
        !confirm("Đã có lịch khám ở khung giờ này. Bạn có muốn cập nhật không?")
      ) {
        return;
      }
    }

    // Lưu lịch khám vào object và localStorage
    appointments[key] = { patientName, service, note };
    localStorage.setItem("appointments", JSON.stringify(appointments));

    // Hiển thị lại lịch khám trên bảng
    renderAppointments();
    modal.style.display = "none";
  });

  // Hiển thị lịch khám khi tải trang
  renderAppointments();
});
