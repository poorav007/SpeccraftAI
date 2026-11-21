user_id = 123
app = None

@app.get("/hello")
def hello():
    return {"message": "Hello"}


app.add_api_route(
    "/users",
    hello,
    methods=["GET"]
)


@app.get(f"/users/{user_id}")
def get_user(user_id: int):
    return {"id": user_id}


@app.get("/products")
def get_products(category):
    return {"category": category}


@app.get("/items")
def get_items(user: str = Depends(get_current_user)):
    return {"user": user}

@app.get("/test-model", response_model=MissingResponse)
def test_model():
    return {}