document.addEventListener("DOMContentLoaded", function () {
    const appointmentModal = document.getElementById("appointmentModal");
    const closeModal = document.querySelector(".close");
    const appointmentForm = document.getElementById("appointmentForm");
    const timeSelect = document.getElementById("time");
    const appointmentList = document.getElementById("appointmentList");
    let selectedDate = "";

    // Lấy ngày hôm nay (YYYY-MM-DD)
    const today = new Date().toISOString().split("T")[0];

    // Khởi tạo FullCalendar
    let calendar = new FullCalendar.Calendar(document.getElementById("calendar"), {
        initialView: "dayGridMonth",
        selectable: true,
        validRange: {
            start: today // Chỉ cho chọn từ hôm nay trở đi
        },
        dateClick: function (info) {
            selectedDate = info.dateStr;
            updateAvailableTimes(selectedDate);
            appointmentModal.style.display = "block";
        }
    });
    calendar.render();

    // Cập nhật danh sách giờ hợp lệ
    function updateAvailableTimes(date) {
        timeSelect.innerHTML = ""; // Xóa danh sách giờ cũ

        const now = new Date();
        const currentHour = now.getHours();
        const isToday = date === today; // Kiểm tra có phải hôm nay không

        const availableTimes = ["08:00", "09:00", "10:00", "14:00", "15:00", "16:00"];

        availableTimes.forEach(time => {
            const hour = parseInt(time.split(":")[0]);

            if (!isToday || hour > currentHour) { // Chỉ hiển thị giờ còn hợp lệ
                const option = document.createElement("option");
                option.value = time;
                option.textContent = time;
                timeSelect.appendChild(option);
            }
        });
    }

    // Đóng popup khi bấm nút X
    closeModal.onclick = function () {
        appointmentModal.style.display = "none";
    };

    // Xử lý đặt lịch
    appointmentForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const name = document.getElementById("name").value;
        const time = timeSelect.value;

        if (!selectedDate || !name || !time) {
            alert("Vui lòng nhập đầy đủ thông tin!");
            return;
        }

        const appointmentItem = document.createElement("li");
        appointmentItem.textContent = `📅 ${selectedDate} - 🕒 ${time} - 👤 ${name}`;
        appointmentList.appendChild(appointmentItem);

        // Reset form
        document.getElementById("name").value = "";
        appointmentModal.style.display = "none";
    });

    // Đóng popup nếu click bên ngoài
    window.onclick = function (event) {
        if (event.target === appointmentModal) {
            appointmentModal.style.display = "none";
        }
    };
});
