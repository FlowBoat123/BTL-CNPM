document.addEventListener("DOMContentLoaded", function () {
  // Lấy ngày thứ Hai của tuần hiện tại
  let currentWeekStart = getMonday(new Date());
  updateCalendar(currentWeekStart);

  // Sự kiện chuyển tuần: tuần trước
  document.getElementById("prev-week").addEventListener("click", function () {
    currentWeekStart = addDays(currentWeekStart, -7);
    updateCalendar(currentWeekStart);
  });

  // Sự kiện chuyển tuần: tuần sau
  document.getElementById("next-week").addEventListener("click", function () {
    currentWeekStart = addDays(currentWeekStart, 7);
    updateCalendar(currentWeekStart);
  });
});

// Hàm lấy ngày thứ Hai của tuần dựa trên ngày cho trước
function getMonday(d) {
  d = new Date(d);
  var day = d.getDay();
  var diff = d.getDate() - day + (day === 0 ? -6 : 1); // Nếu là Chủ nhật (0), chuyển về thứ Hai của tuần trước
  return new Date(d.setDate(diff));
}

// Hàm cộng số ngày vào một ngày nhất định
function addDays(date, days) {
  let result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

// Hàm cập nhật giao diện lịch với tuần bắt đầu từ 'monday'
function updateCalendar(monday) {
  // Cập nhật tiêu đề tuần: hiển thị khoảng từ thứ Hai đến Chủ nhật
  let weekTitle = document.getElementById("week-title");
  let sunday = addDays(monday, 6);
  weekTitle.textContent = formatDate(monday) + " - " + formatDate(sunday);

  // Cập nhật hàng tiêu đề của bảng lịch (bỏ qua ô đầu tiên "Giờ")
  let headerRow = document.querySelector(".calendar-table thead tr");
  // Mảng tên ngày tiếng Việt
  let dayNames = [
    "Thứ Hai",
    "Thứ Ba",
    "Thứ Tư",
    "Thứ Năm",
    "Thứ Sáu",
    "Thứ Bảy",
    "Chủ Nhật",
  ];

  // Lấy tất cả các ô header (th) trong hàng header
  let headerCells = headerRow.querySelectorAll("th");

  // Duyệt qua các ô từ index 1 (vì index 0 là cột "Giờ")
  for (let i = 1; i < headerCells.length; i++) {
    let dayDate = addDays(monday, i - 1);
    headerCells[i].textContent = dayNames[i - 1] + " " + formatDate(dayDate);

    // So sánh ngày hiện tại để làm nổi bật nếu trùng
    let today = new Date();
    if (
      today.getFullYear() === dayDate.getFullYear() &&
      today.getMonth() === dayDate.getMonth() &&
      today.getDate() === dayDate.getDate()
    ) {
      headerCells[i].classList.add("today");
    } else {
      headerCells[i].classList.remove("today");
    }
  }
}

// Hàm định dạng ngày theo dạng dd/mm/yyyy
function formatDate(date) {
  let d = new Date(date);
  let day = ("0" + d.getDate()).slice(-2);
  let month = ("0" + (d.getMonth() + 1)).slice(-2);
  let year = d.getFullYear();
  return day + "/" + month + "/" + year;
}
