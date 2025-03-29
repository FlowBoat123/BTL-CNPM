from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import torch
import requests  # Thay vì axios, dùng requests để gọi API trong Python
from datetime import datetime
import logging
import re # Để xử lý regex cho session ID

# Cấu hình logging để ghi ra console
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Kiểm tra xem Flask có bị ghi log vào Werkzeug không
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Log thử xem có hiển thị không
logging.info("Flask logging setup completed!")


app = Flask(__name__)

# Tải mô hình và tokenizer cho QA
tokenizer = AutoTokenizer.from_pretrained("hogger32/xlmRoberta-for-VietnameseQA")
model = AutoModelForQuestionAnswering.from_pretrained("hogger32/xlmRoberta-for-VietnameseQA")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
# Danh sách ngữ cảnh nha khoa
context_list = [
    "Sâu răng là tình trạng mô cứng của răng bị phá hủy do vi khuẩn trong miệng tạo axit từ đường.",
    "Viêm nướu là tình trạng nướu bị sưng đỏ do mảng bám tích tụ.",
    "Viêm nha chu là bệnh lý nghiêm trọng của nướu, có thể dẫn đến mất răng nếu không điều trị kịp thời.",
    "Áp xe răng là tình trạng nhiễm trùng nặng do vi khuẩn tích tụ bên trong răng hoặc nướu.",
    "Mòn men răng xảy ra khi men răng bị bào mòn do axit hoặc thói quen nghiến răng.",
    "Răng nhạy cảm là tình trạng ê buốt khi ăn uống đồ nóng, lạnh, chua hoặc ngọt.",
    "Hôi miệng có thể do vệ sinh răng miệng kém, khô miệng hoặc bệnh lý nha chu.",
    "Lệch khớp cắn có thể gây khó khăn khi nhai và đau hàm.",
    "Răng khôn mọc lệch có thể gây đau, viêm và ảnh hưởng đến các răng kế cận.",
    "Mất răng có thể gây tiêu xương hàm và ảnh hưởng đến chức năng nhai.",
    "Viêm tủy răng là tình trạng tủy răng bị nhiễm trùng, có thể gây đau dữ dội.",
    "Nứt răng có thể gây đau nhức khi nhai hoặc tiếp xúc với nhiệt độ nóng, lạnh.",
    "Viêm lưỡi là tình trạng lưỡi bị sưng đau, có thể do nhiễm trùng hoặc thiếu vitamin.",
    "Viêm môi do kích ứng có thể do mỹ phẩm, thức ăn hoặc dị ứng.",
    "Loét miệng (nhiệt miệng) là các vết loét nhỏ gây đau rát khi ăn uống.",
    "Chảy máu chân răng có thể do viêm nướu hoặc bệnh lý nha chu.",
    "Răng bị mẻ có thể do chấn thương hoặc cắn phải vật cứng.",
    "Viêm quanh răng là tình trạng viêm nhiễm xung quanh chân răng.",
    "Răng bị lung lay có thể do viêm nha chu hoặc chấn thương.",
    "Viêm xoang hàm có thể gây đau nhức vùng hàm trên và răng.",
    "Răng bị đổi màu có thể do thực phẩm, thuốc lá hoặc nhiễm fluor.",
    "Viêm tuyến nước bọt có thể gây sưng đau và khó khăn khi nuốt.",
    "Răng bị thưa có thể do mất răng hoặc di truyền.",
    "Viêm lợi trùm là tình trạng lợi bao phủ một phần răng khôn gây viêm nhiễm."

    # Cách chữa trị và phòng ngừa sâu răng
    "Sâu răng được điều trị bằng cách hàn răng để loại bỏ phần mô bị hủy và phục hồi hình dạng răng.",
    "Phòng ngừa sâu răng bằng cách đánh răng hai lần mỗi ngày với kem đánh răng chứa fluor.",
    "Trám sealant là phương pháp phủ một lớp bảo vệ lên răng để ngăn ngừa sâu răng.",
    "Sâu răng nặng có thể cần điều trị tủy hoặc nhổ răng nếu không thể phục hồi.",

    # Cách chữa trị và phòng ngừa viêm nướu
    "Viêm nướu được điều trị bằng cách cạo vôi răng và làm sạch mảng bám tại nha sĩ.",
    "Súc miệng bằng nước muối ấm có thể giảm viêm nướu nhẹ.",
    "Phòng ngừa viêm nướu bằng cách dùng chỉ nha khoa để loại bỏ thức ăn thừa giữa các kẽ răng.",
    "Viêm nướu kéo dài không điều trị có thể tiến triển thành viêm nha chu.",

    # Cách chữa trị và phòng ngừa viêm nha chu
    "Viêm nha chu được điều trị bằng phẫu thuật nha chu hoặc cạo vôi răng dưới nướu.",
    "Sử dụng thuốc kháng sinh có thể hỗ trợ điều trị viêm nha chu nặng.",
    "Phòng ngừa viêm nha chu bằng cách duy trì vệ sinh răng miệng và khám nha sĩ định kỳ.",

    # Cách chữa trị áp xe răng
    "Áp xe răng được điều trị bằng cách dẫn lưu mủ và dùng kháng sinh để kiểm soát nhiễm trùng.",
    "Nhổ răng bị áp xe có thể cần thiết nếu răng không thể cứu được.",

    # Cách chữa trị và phòng ngừa mòn men răng
    "Mòn men răng được khắc phục bằng cách trám răng hoặc bọc sứ để bảo vệ răng.",
    "Tránh đồ uống có ga và thực phẩm chứa axit cao giúp phòng ngừa mòn men răng.",
    "Sử dụng ống hút khi uống nước chanh hoặc soda để giảm tiếp xúc axit với răng.",

    # Cách chữa trị răng nhạy cảm
    "Răng nhạy cảm được điều trị bằng kem đánh răng chứa kali nitrat để giảm ê buốt.",
    "Nha sĩ có thể phủ một lớp fluor lên răng nhạy cảm để bảo vệ ngà răng.",

    # Cách chữa trị và phòng ngừa hôi miệng
    "Hôi miệng được cải thiện bằng cách đánh lưỡi và uống đủ nước để tránh khô miệng.",
    "Điều trị bệnh lý nha chu hoặc sâu răng có thể loại bỏ nguyên nhân gây hôi miệng.",
    "Nhấm nháp trà xanh hoặc nhai kẹo gum không đường giúp giảm hôi miệng tạm thời.",

    # Cách chữa trị lệch khớp cắn
    "Lệch khớp cắn được chỉnh sửa bằng niềng răng hoặc phẫu thuật hàm trong trường hợp nặng.",
    "Tập luyện cơ hàm với bài tập do nha sĩ hướng dẫn có thể hỗ trợ điều trị lệch khớp cắn nhẹ.",

    # Cách chữa trị răng khôn mọc lệch
    "Răng khôn mọc lệch thường được nhổ bỏ để tránh viêm nhiễm và tổn thương răng bên cạnh.",
    "Súc miệng nước muối sau khi nhổ răng khôn giúp giảm nguy cơ nhiễm trùng.",

    # Cách xử lý mất răng
    "Mất răng được khắc phục bằng cách cấy ghép implant hoặc làm cầu răng sứ.",
    "Hàm giả tháo lắp là giải pháp tạm thời cho người mất nhiều răng.",

    # Cách chữa trị viêm tủy răng
    "Viêm tủy răng được điều trị bằng cách lấy tủy và hàn kín ống tủy.",
    "Đau do viêm tủy có thể giảm tạm thời bằng thuốc giảm đau trước khi đến nha sĩ.",

    # Cách chữa trị loét miệng (nhiệt miệng)
    "Loét miệng có thể được làm dịu bằng cách bôi gel chứa benzocaine hoặc súc miệng nước muối.",
    "Bổ sung vitamin B12 và sắt giúp phòng ngừa nhiệt miệng tái phát.",

    # Cách chữa trị chảy máu chân răng
    "Chảy máu chân răng được kiểm soát bằng cách cạo vôi răng và cải thiện vệ sinh miệng.",
    "Bổ sung vitamin C qua thực phẩm như cam, kiwi giúp tăng cường sức khỏe nướu.",

    # Cách chữa trị răng đổi màu
    "Răng đổi màu được làm trắng bằng cách tẩy trắng tại nha sĩ hoặc dùng bộ kit tại nhà.",
    "Tránh hút thuốc và cà phê giúp ngăn ngừa răng bị ố vàng.",

    # Cách chữa trị viêm lợi trùm
    "Viêm lợi trùm được điều trị bằng cách cắt bỏ phần lợi thừa hoặc nhổ răng khôn.",
    "Súc miệng bằng dung dịch sát khuẩn giúp giảm viêm lợi trùm trước khi phẫu thuật."
]
# Khóa API OpenWeatherMap
OPENWEATHER_API_KEY = "ab8f25f7e1b90d9a754a2d094887c5cb"  # Thay bằng API key thực của bạn

def normalize_question(question):
    if question:  
        return question.capitalize()  # Viết hoa chữ cái đầu
    return question

def get_answer(question, contexts):
    question = normalize_question(question)  # Chuẩn hóa câu hỏi trước khi xử lý
    best_answer = None
    best_score = float('-inf')
    
    for context in contexts:
        inputs = tokenizer(question, context, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**inputs)
            answer_start = torch.argmax(outputs.start_logits)
            answer_end = torch.argmax(outputs.end_logits) + 1
            
            if 0 <= answer_start < answer_end <= len(inputs["input_ids"][0]):
                answer = tokenizer.decode(inputs["input_ids"][0][answer_start:answer_end], skip_special_tokens=True)
                score = outputs.start_logits[0][answer_start] + outputs.end_logits[0][answer_end - 1]
                
                if score > best_score:
                    best_score = score
                    best_answer = answer

    return best_answer if best_answer else tokenizer.decode(inputs["input_ids"][0][answer_start:answer_end], skip_special_tokens=True)

def get_weather(location):
    if not location:
        return "Bạn muốn biết thời tiết ở đâu?"
    try:
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={OPENWEATHER_API_KEY}&units=metric&lang=vi"
        response = requests.get(weather_url)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        data = response.json()

        temp = data["main"]["temp"]
        description = data["weather"][0]["description"]
        city = data["name"]

        return f"Thời tiết ở {city} hiện tại: {temp}°C, {description}."
    except requests.RequestException as e:
        return f"Không thể lấy thông tin thời tiết cho {location}. Vui lòng thử lại! Error: {str(e)}"

def convert_day_to_vietnamese(english_day):
    days_mapping = {
        "Monday": "Thứ 2",
        "Tuesday": "Thứ 3",
        "Wednesday": "Thứ 4",
        "Thursday": "Thứ 5",
        "Friday": "Thứ 6",
        "Saturday": "Thứ 7",
        "Sunday": "Chủ nhật"
    }
    return days_mapping.get(english_day, english_day)  # Trả về ngày đã chuyển đổi hoặc giữ nguyên nếu không tìm thấy

# Lưu dữ liệu session
user_sessions = {}

def handle_make_appointment(req):
    parameters = req.get("queryResult", {}).get("parameters", {})
    session_id = get_session_id(req)  # Lấy session ID
    date_time = parameters.get("date", "")  # Ví dụ: "2025-07-15T12:00:00+07:00"
    hour_time = parameters.get("hour", "")  # Ví dụ: "2025-03-25T09:00:00+07:00"
    service = parameters.get("service", "")  # Ví dụ: "chung chung"

    logging.info(f"Date time: {date_time}, Hour: {hour_time}, Service: {service}")

    if not date_time or not hour_time:
        return {"fulfillmentText": "Vui lòng cung cấp đầy đủ ngày và giờ để đặt lịch hẹn."}
    if not service:
        return {"fulfillmentText": "Hiện nay phòng khám nha khoa chúng tôi cung cấp 3 dịch vụ chính là trồng răng sứ, nhổ răng và răng thẩm mỹ. Vui lòng chọn 1 trong 3 dịch vụ trên."}

    try:
        # Chuyển đổi định dạng ISO 8601 thành datetime
        date_obj = datetime.fromisoformat(date_time)
        hour_obj = datetime.fromisoformat(hour_time)

        # Lấy ngày và thứ trong tuần
        date_str = date_obj.strftime("%Y-%m-%d")  # "2025-07-15"
        hour_str = hour_obj.strftime("%H:%M")      # "09:00"
        day_of_week = convert_day_to_vietnamese(date_obj.strftime("%A"))      # "Tuesday" (Thứ trong tuần)

        # Kiểm tra giờ có nằm trong khoảng 9:00 - 17:00 không
        hour_minutes = hour_obj.hour * 60 + hour_obj.minute
        start_time = 9 * 60   # 9:00 sáng = 540 phút
        end_time = 17 * 60    # 17:00 chiều = 1020 phút

        if not (start_time <= hour_minutes <= end_time):
            return {"fulfillmentText": "Giờ đặt lịch phải từ 9:00 sáng đến 17:00 chiều. Vui lòng chọn lại giờ khác."}

        # Kiểm tra thời gian có trong tương lai không
        appointment_time_str = f"{date_str} {hour_str}"  # "2025-07-15 09:00"
        appointment_time = datetime.strptime(appointment_time_str, "%Y-%m-%d %H:%M")

        current_time = datetime.now()
        if appointment_time <= current_time:
            return {"fulfillmentText": "Ngày giờ bạn chọn đã qua hoặc không hợp lệ. Vui lòng chọn thời gian trong tương lai."}
    except ValueError as e:
        logging.error(f"Error parsing date/time: {e}")
        return {"fulfillmentText": "Định dạng ngày hoặc giờ không hợp lệ. Vui lòng thử lại."}

    # 🔥 **Kiểm tra xem khung giờ đó đã có ai đặt chưa**
    try:
        appointments_ref = db.collection("appointments")
        query = appointments_ref.where("date", "==", date_str).where("hour", "==", hour_str).get()

        if query:
            return {"fulfillmentText": f"⚠️ Giờ {hour_str} ngày {date_str} đã có người đặt lịch. Vui lòng chọn khung giờ khác."}
    except Exception as e:
        logging.error(f"❌ Lỗi khi kiểm tra lịch hẹn: {e}")
        return {"fulfillmentText": "Có lỗi xảy ra khi kiểm tra lịch hẹn. Vui lòng thử lại sau."}

    # Lưu thông tin vào session
    user_sessions[session_id] = {
        "date": date_str,
        "time": hour_str,
        "day": day_of_week,  # Thêm thông tin thứ trong tuần
        "service": service,
        "patientName": None,
        "sdt": None
    }

    logging.info(f"Session data updated: {user_sessions[session_id]}")

    response = (
        f"✅ Đã đặt lịch hẹn cho bạn vào lúc {hour_str} ngày {date_str} "
        f"({day_of_week}) với dịch vụ {service}. "
        f"Vui lòng cung cấp thêm thông tin (tên, số điện thoại) để xác nhận."
    )
    
    return {"fulfillmentText": response}


def get_session_id(req):
    """Trích xuất session ID từ request"""
    session_path = req.get("session", "")
    match = re.search(r'/sessions/(.+)', session_path)
    return match.group(1) if match else "default_session"

@app.route('/webhook', methods=['POST'])
def webhook():
    # Nhận dữ liệu từ Dialogflow
    req = request.get_json(silent=True, force=True)
    intent = req.get('queryResult', {}).get('intent', {}).get('displayName', '')
    question = req.get('queryResult', {}).get('queryText', '')
    parameters = req.get('queryResult', {}).get('parameters', {})
    session_id = get_session_id(req)  # Lấy session ID

    logger.info(f"Received intent: {intent}, Question: {question}")
    # Xử lý intent
    if intent == "dental_info":  # Intent hỏi thông tin nha khoa
        # Trả về follow-up event để kéo dài thời gian
        logging.info("Follow-up event: DentalInfoContinue")
        response = {
            "followupEventInput": {
                "name": "DentalInfoContinue",
                "languageCode": "vi",
                "parameters": {"question": question}
            }
        }
    elif intent == "DentalInfoContinue":  # Intent tiếp theo
        question = parameters.get('question', req.get('queryText', ''))
        answer = get_answer(question, context_list)
        response = {"fulfillmentText": answer}
    elif intent == "ask_weather":  # Intent hỏi thời tiết
        location = parameters.get('locate', '')  # Lấy tham số 'locate' từ Dialogflow
        weather_response = get_weather(location)
        response = {"fulfillmentText": weather_response}
    elif intent == "make_appointment":
        response = handle_make_appointment(req)
    else:
        response = handle_intent(intent, parameters, question, session_id)

    return jsonify(response)

def handle_intent(intent, parameters, user_message, session_id):
    """Xử lý intent và lưu trạng thái theo session_id"""
    
    # Khởi tạo session nếu chưa có
    # if session_id not in user_sessions:
    #     user_sessions[session_id] = {'patientName': None, 'sdt': None, 'note': []}

    user_data = user_sessions[session_id]
    logging.info(f"Current session data: {user_data}")

    if intent == "ask_personal_info":
        name_data = parameters.get('name', '')  
        sdt = parameters.get('sdt', '')

        # Kiểm tra nếu name là dictionary, lấy giá trị bên trong
        name = name_data.get('name', '') if isinstance(name_data, dict) else name_data  

        if not name:
            return {"fulfillmentText": "Bạn vui lòng cho tôi biết tên của bạn là gì?"}
        if not sdt:
            return {"fulfillmentText": "Bạn vui lòng cung cấp số điện thoại của bạn?"}

        # Kiểm tra xem session_id đã tồn tại trong user_sessions chưa
        if session_id not in user_sessions:
            return {"fulfillmentText": "Lỗi: Chưa có thông tin về ngày, giờ và dịch vụ!"}

        # Cập nhật thông tin người dùng vào session
        user_sessions[session_id]["patientName"] = name
        user_sessions[session_id]["sdt"] = sdt

        # Lấy toàn bộ thông tin đã có
        user_info = user_sessions[session_id]

        logging.info(f"✅ Dữ liệu đầy đủ, chuẩn bị lưu vào database: {user_info}")

        # Lưu vào database
        save_user_to_db(session_id, user_info)

        return {
            "fulfillmentText": "Cảm ơn bạn! Tất cả thông tin đã được lưu. Bạn sẽ nhận được xác nhận lịch hẹn sớm!"
        }

    return {"fulfillmentText": "Tôi không hiểu yêu cầu của bạn."}

import firebase_admin
from firebase_admin import credentials, firestore

# Kết nối Firebase với serviceAccount.json
cred = credentials.Certificate("serviceAccount.json")  # Đảm bảo file nằm trong thư mục dự án
firebase_admin.initialize_app(cred)

db = firestore.client()  # Kết nối Firestore

def save_user_to_db(session_id, user_data):
    """Lưu toàn bộ thông tin đặt lịch vào Firestore"""
    try:
        doc_ref = db.collection("appointments").document(session_id)
        doc_ref.set(user_data)  # Ghi đè dữ liệu nếu session_id đã tồn tại
        logging.info(f"✅ Dữ liệu đã được lưu vào Firestore: {user_data}")
    except Exception as e:
        logging.error(f"❌ Lỗi khi lưu dữ liệu vào Firestore: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)