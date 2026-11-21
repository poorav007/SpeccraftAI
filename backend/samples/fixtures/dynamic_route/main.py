from fastapi import FastAPI

app = FastAPI()
dynamic_prefix = "/dynamic/path"

@app.get(dynamic_prefix)
def dynamic_endpoint():
    return {"msg": "hello"}

@app.get("/valid/path")
def valid_endpoint():
    return {"msg": "valid"}

