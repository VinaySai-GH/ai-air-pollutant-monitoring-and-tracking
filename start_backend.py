"""
Simple script to start the FastAPI backend.
Run this from the project root directory.
"""
import uvicorn

if __name__ == "__main__":
    print("="*60)
    print("Starting AI Air Pollution Monitoring Backend")
    print("="*60)
    print("\nBackend will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    print("\nPress CTRL+C to stop the server\n")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
