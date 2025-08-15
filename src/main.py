from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/webhook/whatsapp")
def receive_webhook(data: dict):
    print("Datos recibidos:")
    print(data)
    return {"status": "ok"}