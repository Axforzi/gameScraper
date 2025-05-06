import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.app import app

if __name__ == "__main__":
    app.run(debug=True)