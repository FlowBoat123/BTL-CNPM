document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("appointmentForm").addEventListener("submit", async function (event) {
        event.preventDefault();

        let name = document.getElementById("name").value;
        let date = document.getElementById("date").value;
        let time = document.getElementById("time").value;

        if (!name || !date || !time) {
            alert("Vui lòng nhập đầy đủ thông tin!");
            return;
        }

        // Hiển thị thông tin trên giao diện
        let appointmentList = document.getElementById("appointmentList");
        let listItem = document.createElement("li");
        listItem.textContent = `${name} - ${date} lúc ${time}`;
        appointmentList.appendChild(listItem);

        // Xóa input sau khi thêm
        document.getElementById("appointmentForm").reset();

        // Kiểm tra nếu Firestore đã được khởi tạo
        if (!window.db) {
            console.error("Firebase chưa được khởi tạo!");
            alert("Lỗi hệ thống: Firebase chưa khởi tạo. Vui lòng thử lại.");
            return;
        }

        try {
            const { collection, addDoc } = window.firebaseFirestore;
            await addDoc(collection(window.db, "appointments"), {
                name: name,
                date: date,
                time: time
            });

            alert("Lịch hẹn đã được đặt thành công!");
        } catch (error) {
            console.error("Lỗi khi thêm lịch hẹn: ", error);
            alert("Lỗi hệ thống: Không thể lưu lịch hẹn.");
        }
    });
});
