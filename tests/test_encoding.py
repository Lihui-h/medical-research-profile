import requests
import json

def test_encoding():
    url = "https://httpbin.org/post"
    data = {"name": "浦东妇保医院", "chars": "®©≥≤µ"}  # 包含特殊字符
    
    # 直接发送原始字节
    json_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
    
    response = requests.post(
        url,
        data=json_bytes,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    
    print("响应状态:", response.status_code)
    print("响应内容:", response.json())

if __name__ == "__main__":
    test_encoding()