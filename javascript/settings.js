document.addEventListener("DOMContentLoaded", function () {
  // Avatar update: khi click vào khung ảnh đại diện
  const avatarContainer = document.getElementById("avatarContainer");
  const avatarInput = document.getElementById("avatarInput");
  const avatarPreview = document.getElementById("avatarPreview");

  if (avatarContainer && avatarInput && avatarPreview) {
    // Khi click vào khung avatar, kích hoạt input file
    avatarContainer.addEventListener("click", function () {
      avatarInput.click();
    });

    // Khi người dùng chọn file
    avatarInput.addEventListener("change", function () {
      const file = this.files[0];
      if (file) {
        const reader = new FileReader();

        reader.onload = function (e) {
          avatarPreview.src = e.target.result;
        };

        reader.readAsDataURL(file);
      }
    });
  }
});
