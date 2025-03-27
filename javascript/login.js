// Đảm bảo mã chạy sau khi DOM được tải đầy đủ
document.addEventListener("DOMContentLoaded", function () {
  const loginForm = document.getElementById("loginForm");

  if (loginForm) {
    loginForm.addEventListener("submit", function (e) {
      e.preventDefault(); // Ngăn form gửi dữ liệu theo mặc định
      // Chuyển hướng sang trang index.html
      window.location.href = "index.html";
    });
  }
});
