import sys
from gui import SugangApp

def main():
    try:
        app = SugangApp()
        app.mainloop()
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
