#!/usr/bin/env python3
"""
Options Strategy Testing - Complete Setup Script
Creates necessary directories and files for the project
"""

import os
import sys

def setup_project():
    """Setup project structure and files"""
    
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(base_dir, 'src')
    
    # Create src directory if it doesn't exist
    if not os.path.exists(src_dir):
        os.makedirs(src_dir)
        print(f"✓ Created {src_dir}")
    else:
        print(f"✓ {src_dir} already exists")
    
    # React files content
    files = {
        'src/main.jsx': '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
''',
        'src/index.css': '''* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
}

#root {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
}
''',
    }
    
    # Create files if they don't exist
    for filepath, content in files.items():
        full_path = os.path.join(base_dir, filepath)
        if not os.path.exists(full_path):
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
            print(f"✓ Created {filepath}")
        else:
            print(f"✓ {filepath} already exists")
    
    print("\n✓ Project setup complete!")
    print("\nNext steps:")
    print("1. pip install -r requirements.txt")
    print("2. npm install")
    print("3. Create .env with your POLYGON_API_KEY")
    print("4. python main.py (in one terminal)")
    print("5. npm run dev (in another terminal)")

if __name__ == '__main__':
    try:
        setup_project()
    except Exception as e:
        print(f"✗ Setup failed: {e}")
        sys.exit(1)
