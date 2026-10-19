from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.auth.routes import router as auth_router
from src.github.routes import router as github_router
from src.github.repository_routes import router as repository_router
from src.analysis.routes import router as analysis_router
from src.issues.routes import router as issues_router


app = FastAPI(
    title="Autonomous DevSecOps",
    version="1.0.0",
    description=(
        "Autonomous software engineering and security platform "
        "for repository analysis, diagnosis, repair, and verification."
    ),
)


app.include_router(auth_router)
app.include_router(github_router)
app.include_router(repository_router)
app.include_router(analysis_router)
app.include_router(issues_router)


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Autonomous DevSecOps</title>

        <style>
            body {
                margin: 0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: Arial, sans-serif;
                background: #f4f7fb;
                color: #1f2937;
            }

            .container {
                width: 90%;
                max-width: 650px;
                padding: 40px;
                background: white;
                border-radius: 16px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
                text-align: center;
            }

            h1 {
                margin-bottom: 10px;
                font-size: 32px;
            }

            p {
                color: #6b7280;
                font-size: 16px;
                line-height: 1.6;
            }

            .status {
                display: inline-block;
                margin: 20px 0;
                padding: 8px 16px;
                border-radius: 20px;
                background: #e8f7ee;
                color: #18794e;
                font-weight: bold;
            }

            .buttons {
                margin-top: 25px;
            }

            a {
                display: inline-block;
                margin: 8px;
                padding: 12px 20px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
            }

            .docs {
                background: #2563eb;
                color: white;
            }

            .redoc {
                background: #eef2ff;
                color: #3730a3;
            }
        </style>
    </head>

    <body>
        <div class="container">
            <h1>Autonomous DevSecOps</h1>

            <p>
                Autonomous software engineering and security platform
                for repository analysis, diagnosis, repair, and verification.
            </p>

            <div class="status">
                ● API is running
            </div>

            <div class="buttons">
                <a class="docs" href="/docs">
                    Open API Docs
                </a>

                <a class="redoc" href="/redoc">
                    ReDoc
                </a>
            </div>
        </div>
    </body>
    </html>
    """