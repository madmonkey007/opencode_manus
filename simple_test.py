import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def home():
    return {'status': 'ok', 'message': 'Server is running!'}

print('Starting simple test server on http://127.0.0.1:8089')
print('Press Ctrl+C to stop')
print('=' * 60)

uvicorn.run(app, host='127.0.0.1', port=8089, log_level='info')
