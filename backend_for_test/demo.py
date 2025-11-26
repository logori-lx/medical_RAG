from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import time  # ✅ 用来模拟大模型耗时

class RequestHandler(BaseHTTPRequestHandler):
    # Parsing the JSON request body
    def _parse_json_body(self, length):
        try:
            body = self.rfile.read(length).decode('utf-8')
            return json.loads(body)
        except json.JSONDecodeError:
            return None

    # Send JSON response
    def _send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        # If the frontend is using fetch on localhost, you can also add a CORS line (optional).
        # self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    # Handling POST requests
    def do_POST(self):
        # Process only the specified path
        if self.path != '/api/user/ask':
            self._send_json_response(
                {'error': 'Path does not exist'},
                status_code=404
            )
            return

        # Check if Content-Type is JSON
        content_type = self.headers.get('Content-Type', '')
        if not re.search(r'application/json', content_type):
            self._send_json_response(
                {'error': 'Please use application/json format'},
                status_code=415
            )
            return

        # Read and parse the request body
        try:
            content_length = int(self.headers['Content-Length'])
        except (KeyError, ValueError):
            self._send_json_response(
                {'error': 'Missing Content-Length header'},
                status_code=400
            )
            return

        request_data = self._parse_json_body(content_length)
        if not request_data or 'question' not in request_data:
            self._send_json_response(
                {'error': 'The request body is missing the question field.'},
                status_code=400
            )
            return

        question = request_data.get("question", "")
        print(f"Received question：{question}")

        # Simulated large-scale model thinking time: 5-second pause
        time.sleep(5)

        # mock main answer
        mock_response = (
            "得了高血压平时需要注意以下几点："
            "1. 饮食方面，控制食盐摄入量，每天不超过 6 克，避免吃太油腻的食物，"
            "多吃新鲜绿色蔬菜水果和有机食物，还可以适量用党参泡水喝，因为党参有降血脂、降血压等作用；"
            "2. 适度增强体育锻炼，提高身体素质；"
            "3. 保持情绪平和，避免激动，减轻精神压力，不要过度紧张；"
            "4. 若通过生活方式调整后血压控制效果不佳，应在医生指导下配合降压药物治疗。"
        )

        # mock reference case
        mock_cases = [
            {
                "id": 1,
                "question": "我有高血压这两天女婿来的时候给我拿了些党参泡水喝，您好高血压可以吃党参吗?",
                "answer": (
                    "高血压病人可以口服党参的。党参有降血脂、降血压的作用，可以帮助改善心血管状况，"
                    "但仍需注意血压监测，遵医嘱服药。"
                ),
            },
            {
                "id": 2,
                "question": "我是一个中学教师，最近体检发现高血压，该怎么治疗、需要注意什么？",
                "answer": (
                    "高血压患者首先要注意控制食盐摄入量，每天不超过 6 克，注意避免油腻饮食，多吃蔬菜水果；"
                    "同时保持规律作息与适量运动，必要时在医生指导下使用降压药物。"
                ),
            },
        ]

        # return response：response + cases
        self._send_json_response({
            "response": mock_response,
            "cases": mock_cases,
        })

    # Handling other request methods
    def do_GET(self):
        self._send_json_response(
            {'message': 'Please use the POST method to access the /api/user/ask interface.'},
            status_code=405
        )

def run_server(host='0.0.0.0', port=886):
    server_address = (host, port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Server starts up and listens. {host}:{port} ...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nThe server is shutting down....")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
