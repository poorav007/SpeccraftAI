from fastapi import FastAPI

app = FastAPI()

def legacy_endpoint():
    return {"status": "legacy"}

app.add_api_route("/legacy", legacy_endpoint)

@app.get("/modern")
def modern_endpoint():
    return {"status": "modern"}

