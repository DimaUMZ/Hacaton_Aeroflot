import requests
import base64

def test_detection():
    # Закодируйте тестовое изображение в base64
    with open("test_image.jpg", "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
    
    response = requests.post("http://localhost:8000/api/ml/detect", json={
        "image_base64": f"data:image/jpeg;base64,{image_base64}",
        "confidence_threshold": 0.5
    })
    
    print("Status Code:", response.status_code)
    print("Response:", response.json())

if __name__ == "__main__":
    test_detection()