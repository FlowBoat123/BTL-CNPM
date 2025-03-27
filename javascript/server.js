const express = require("express");
const { WebhookClient } = require("dialogflow-fulfillment");
const axios = require("axios");

const app = express();
app.use(express.json());

const OPENWEATHER_API_KEY = "ab8f25f7e1b90d9a754a2d094887c5cb"; // Thay bằng API key thực

app.post("/webhook", async (req, res) => {
  const agent = new WebhookClient({ request: req, response: res });

  async function getWeather(agent) {
    // Kiểm tra log để debug lỗi
    console.log("Webhook triggered with request:", JSON.stringify(req.body, null, 2));

    const location = agent.parameters.locate; // Đảm bảo lấy đúng tham số từ Dialogflow
    if (!location) {
      agent.add("Bạn muốn biết thời tiết ở đâu?");
      return;
    }

    try {
      const weatherUrl = `https://api.openweathermap.org/data/2.5/weather?q=${location}&appid=${OPENWEATHER_API_KEY}&units=metric&lang=vi`;
      const weatherResponse = await axios.get(weatherUrl);
      const data = weatherResponse.data;

      const temp = data.main.temp;
      const description = data.weather[0].description;
      const city = data.name;

      agent.add(`Thời tiết ở ${city} hiện tại: ${temp}°C, ${description}.`);
    } catch (error) {
      agent.add(`Không thể lấy thông tin thời tiết cho ${location}. Vui lòng thử lại!`);
      console.error("Error fetching weather data:", error);
    }
  }

  const intentMap = new Map();
  intentMap.set("ask_weather", getWeather); // Đổi tên intent cho đúng với Dialogflow
  await agent.handleRequest(intentMap);
});

app.listen(3000, () => {
  console.log("Server is running on port 3000");
});
