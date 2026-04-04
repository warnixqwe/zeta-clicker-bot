from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def mini_app():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Zeta Clicker</title>
    </head>
    <body>
        <h1>🦆 Zeta Clicker</h1>
        <button id="testBtn" style="font-size: 40px; padding: 20px;">Кликни меня</button>
        <script>
            let clicks = 0;
            document.getElementById('testBtn').onclick = function() {
                clicks++;
                this.textContent = 'Кликов: ' + clicks;
            };
        </script>
    </body>
    </html>
    """)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)