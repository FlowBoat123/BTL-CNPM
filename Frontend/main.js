import { db } from "../Backend/config.js";
import { collection, getDocs, addDoc, doc, updateDoc } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

document.addEventListener("DOMContentLoaded", async () => {

// render lịch theo thời điểm hiện tại ( thứ ) 
    const weekTitle = document.getElementById("week-title");
    const calendarBody = document.getElementById("calendar-body");
    const days = ["Chủ nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"];

    function getCurrentWeekDays() {
        const today = new Date();
        const todayIndex = today.getDay();

        const sortedDays = [...days.slice(todayIndex), ...days.slice(0, todayIndex)];
        const sortedDates = [];

        for (let i = 0; i < 7; i++) {
            let date = new Date();
            date.setDate(today.getDate() + i);
            let formattedDate = date.toLocaleDateString("vi-VN").split("/").reverse().join("-");
            sortedDates.push(formattedDate);
        }

        return { sortedDays, sortedDates };
    }

    function generateSchedule() {
        const { sortedDays, sortedDates } = getCurrentWeekDays();
        
        weekTitle.textContent = `Lịch trong một tuần tới`;

        const headerRow = document.querySelector(".calendar-table thead tr");
        headerRow.innerHTML = "<th>Giờ</th>" + sortedDays.map((day, index) => `<th data-date="${sortedDates[index]}">${day}</th>`).join("");

        calendarBody.innerHTML = "";

        const times = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"];
        times.forEach(time => {
            const row = document.createElement("tr");
            row.innerHTML = `<td>${time}</td>` + sortedDays.map((day, index) => 
                `<td class="time-slot" data-day="${day}" data-date="${sortedDates[index]}" data-time="${time}"></td>`
            ).join("");
            calendarBody.appendChild(row);
        });
    }

    generateSchedule();

// logic 

    const timeSlotCells = document.querySelectorAll(".time-slot");

    const modal = document.getElementById("appointment-modal");
    const formContainer = document.getElementById("form-container");
    const detailsContainer = document.getElementById("details-container");
    const detailsContent = document.getElementById("details-content");
    const closeDetailsBtn = document.getElementById("close-details");

    const appointmentForm = document.getElementById("appointment-form");
    const patientNameInput = document.getElementById("patient-name");
    const serviceSelect = document.getElementById("service");
    const appointmentDayInput = document.getElementById("appointment-day");
    const appointmentTimeSelect = document.getElementById("appointment-time");
    const appointmentNoteInput = document.getElementById("appointment-note");

    const closeButtons = modal.querySelectorAll(".close");

    async function fetchAppointments() {
        try {
            const querySnapshot = await getDocs(collection(db, "appointments"));
            let appointments = {};

            querySnapshot.forEach((doc) => {
                const data = doc.data();
                const key = `${data.day}-${data.time}`;
                appointments[key] = { ...data, id: doc.id };
            });

            return appointments;
        } catch (error) {
            console.error("Lỗi khi lấy dữ liệu từ Firestore:", error);
            return {};
        }
    }

    async function renderAppointments() {
        const appointments = await fetchAppointments();
    
        timeSlotCells.forEach((cell) => {
            const day = cell.getAttribute("data-day");
            const time = cell.getAttribute("data-time");
            const key = `${day}-${time}`;
            cell.innerHTML = "";
    
            if (appointments[key]) {
                const appointmentData = appointments[key];
                cell.classList.add("appointment-marked");
                cell.innerHTML = `
                    <strong>${appointmentData.patientName}</strong><br>
                    <small>${appointmentData.date}</small><br>
                    ${time}
                `;
            } else {
                cell.classList.remove("appointment-marked");
            }
        });
    }

    timeSlotCells.forEach((cell) => {
        cell.addEventListener("click", async () => {
            const day = cell.getAttribute("data-day");
            const date = cell.getAttribute("data-date"); // Lấy ngày chính xác
            const time = cell.getAttribute("data-time");
            const key = `${day}-${time}`;
            const appointments = await fetchAppointments();

            if (appointments[key]) {
                const appData = appointments[key];
                detailsContent.innerHTML = `
                    <p><strong>Họ tên:</strong> ${appData.patientName}</p>
                    <p><strong>Dịch vụ:</strong> ${appData.service}</p>
                    <p><strong>Ghi chú:</strong> ${appData.note || "Không có ghi chú"}</p>
                    <p><strong>Thời gian:</strong> ${day} (${date}) - ${time}</p>
                `;
                formContainer.style.display = "none";
                detailsContainer.style.display = "block";
                modal.style.display = "flex";
            } else {
                formContainer.style.display = "block";
                detailsContainer.style.display = "none";
                appointmentDayInput.value = day;
                appointmentTimeSelect.value = time;
                patientNameInput.value = "";
                serviceSelect.value = "";
                appointmentNoteInput.value = "";
                modal.style.display = "flex";

                appointmentForm.dataset.selectedDate = date; // Lưu ngày để gửi lên Firebase
            }
        });
    });

    closeButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            modal.style.display = "none";
        });
    });

    window.addEventListener("click", (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    });

    appointmentForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const day = appointmentDayInput.value;
        const date = appointmentForm.dataset.selectedDate; // Lấy ngày đã lưu trước đó
        const time = appointmentTimeSelect.value;
        const patientName = patientNameInput.value.trim();
        const service = serviceSelect.value;
        const note = appointmentNoteInput.value.trim();

        if (!patientName || !service) {
            alert("Vui lòng điền đầy đủ thông tin cần thiết!");
            return;
        }

        try {
            const appointments = await fetchAppointments();
            const key = `${day}-${time}`;

            if (appointments[key]) {
                if (!confirm("Đã có lịch khám ở khung giờ này. Bạn có muốn cập nhật không?")) {
                    return;
                }
                const appointmentRef = doc(db, "appointments", appointments[key].id);
                await updateDoc(appointmentRef, { patientName, service, note, date });
            } else {
                await addDoc(collection(db, "appointments"), { day, date, time, patientName, service, note });
            }

            renderAppointments();
            modal.style.display = "none";
        } catch (error) {
            console.error("❌ Lỗi khi thêm dữ liệu vào Firestore:", error);
        }
    });

    closeDetailsBtn.addEventListener("click", () => {
        modal.style.display = "none";
    });

    await renderAppointments();
});
