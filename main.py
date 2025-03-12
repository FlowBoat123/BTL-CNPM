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
    "Viêm nướu là tình trạng nướu bị sưng đỏ do mảng bám tích tụ."
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
        # logging.info(f"Searching answer for: {inputs}")
        with torch.no_grad():
            outputs = model(**inputs)
            answer_start = torch.argmax(outputs.start_logits)
            answer_end = torch.argmax(outputs.end_logits) + 1
            if answer_start <= answer_end and answer_start >= 0 and answer_end <= len(inputs["input_ids"][0]):
                answer = tokenizer.decode(inputs["input_ids"][0][answer_start:answer_end], skip_special_tokens=True)
                score = outputs.start_logits[0][answer_start] + outputs.end_logits[0][answer_end - 1]
                if score > best_score:
                    best_score = score
                    best_answer = answer
    return best_answer if best_answer else "Không tìm được câu trả lời phù hợp."

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
    else:
        response = {"fulfillmentText": "Tôi không hiểu câu hỏi của bạn. Vui lòng thử lại!"}

    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)