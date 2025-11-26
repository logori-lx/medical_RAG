import pytest
import json
from http.server import HTTPServer
from threading import Thread
import requests
from demo import RequestHandler, run_server

# Helper function for starting the test server
def start_test_server():
    server = Thread(target=run_server, args=('localhost', 8888), daemon=True)
    server.start()
    return server

@pytest.fixture(scope="module", autouse=True)
def server():
    # Start the test server
    server_thread = start_test_server()
    # Waiting for the server to start
    import time
    time.sleep(1)
    yield
    # No further action is required after the test; the daemon thread will exit along with the main process.

BASE_URL = "http://localhost:8888/api/user/ask"

def test_post_correct_request():
    """Test a correct POST request"""
    data = {"question": "高血压需要注意什么？"}
    response = requests.post(
        BASE_URL,
        json=data,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "response" in result
    assert "cases" in result
    assert isinstance(result["cases"], list)
    assert len(result["cases"]) > 0


def test_get_method():
    """Test using the GET method to access the interface"""
    response = requests.get(BASE_URL)
    assert response.status_code == 405
    assert "message" in response.json()

def test_missing_content_type():
    """The test is missing the Content-Type header."""
    data = {"question": "测试"}
    response = requests.post(
        BASE_URL,
        json=data,
        headers={"Content-Type": "text/plain"}
    )
    
    assert response.status_code == 415
    assert "error" in response.json()

def test_missing_content_length():
    """The test is missing the Content-Length header (simulated by not passing data)."""
    response = requests.post(
        BASE_URL,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 400
    assert "error" in response.json()

def test_invalid_json():
    """Test invalid JSON format"""
    response = requests.post(
        BASE_URL,
        data="{invalid json}",
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 400
    assert "error" in response.json()

def test_missing_question_field():
    """The test request body is missing the question field."""
    data = {"other_field": "value"}
    response = requests.post(
        BASE_URL,
        json=data,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 400
    assert "error" in response.json()