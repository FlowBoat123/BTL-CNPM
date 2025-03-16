from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import torch
import requests  # Thay vì axios, dùng requests để gọi API trong Python
import logging

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

@app.route('/webhook', methods=['POST'])
def webhook():
    # Nhận dữ liệu từ Dialogflow
    req = request.get_json(silent=True, force=True)
    intent = req.get('queryResult', {}).get('intent', {}).get('displayName', '')
    question = req.get('queryResult', {}).get('queryText', '')
    parameters = req.get('queryResult', {}).get('parameters', {})
    logging.info(f"Question received: {question}")
    # Xử lý intent
    if intent == "dental_info":  # Intent hỏi thông tin nha khoa
        answer = get_answer(question, context_list)
        response = {"fulfillmentText": answer}
    elif intent == "ask_weather":  # Intent hỏi thời tiết
        location = parameters.get('locate', '')  # Lấy tham số 'locate' từ Dialogflow
        weather_response = get_weather(location)
        response = {"fulfillmentText": weather_response}
    elif intent == "make_appointment":
        # Lấy thông tin từ entity
        parameters = req.get("queryResult", {}).get("parameters", {})
        date_time = parameters.get("date", "")
        service = parameters.get("service", "chung chung")
        logging.info(f"Date time: {date_time}, Service: {service}")
        # Xử lý lưu vào DB (giả lập)
        response = f"Bạn đã đặt lịch hẹn {service} vào {date_time}."
        
        return jsonify({
            "fulfillmentText": response
        })
    else:
        response = {"fulfillmentText": "Tôi không hiểu câu hỏi của bạn. Vui lòng thử lại!"}

    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)