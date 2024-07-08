from fastapi import FastAPI
from app.hooks import load_hooks

app = FastAPI()

# Load environment variables and configure logging here...

@app.get("/")
async def root():
    return {"message": "Hello World"}

# Load all hooks
load_hooks(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
