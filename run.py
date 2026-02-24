import sys
import threading
import time
import webbrowser
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from config import PORT


def open_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    print(f"\n🚀 XHS Link 启动中，访问 http://localhost:{PORT}\n")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="warning",
    )
