import os
import sys

def main():

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crop_mapping_backend.settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError() from exc
    
    if len(sys.argv) > 1 and sys.argv[1] == "runserver":
        import uvicorn
        print("Starting ASGI server with Uvicorn...")
        uvicorn.run("crop_mapping_backend.asgi:application", host="0.0.0.0", port=8000, reload=True)
    else:
        execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()