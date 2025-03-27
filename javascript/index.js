document.addEventListener("DOMContentLoaded", function () {
  // Lấy tất cả các liên kết trong sidebar
  const navLinks = document.querySelectorAll(".sidebar ul li a");

  // Duyệt qua từng liên kết và gán sự kiện click
  navLinks.forEach(function (link) {
    link.addEventListener("click", function (event) {
      event.preventDefault(); // Ngăn hành động mặc định của anchor tag

      // Lấy đường dẫn trang từ thuộc tính href của liên kết
      const targetPage = this.getAttribute("href");

      // Thực hiện chuyển hướng sang trang tương ứng
      window.location.href = targetPage;
    });
  });
});
