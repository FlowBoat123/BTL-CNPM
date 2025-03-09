document.getElementById("appointmentForm").addEventListener("submit", function(event) {
    event.preventDefault();
  
    let name = document.getElementById("name").value;
    let date = document.getElementById("date").value;
    let time = document.getElementById("time").value;
  
    if (name && date && time) {
        let appointmentList = document.getElementById("appointmentList");
        let listItem = document.createElement("li");
        listItem.textContent = `${name} - ${date} lúc ${time}`;
        appointmentList.appendChild(listItem);
  
        // Xóa input sau khi thêm
        document.getElementById("appointmentForm").reset();
    } else {
        alert("Vui lòng nhập đầy đủ thông tin!");
    }
  });
  