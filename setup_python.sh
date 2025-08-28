#!/bin/bash

# Global variables
VIRTUAL_ENV_DIR="$(pwd)/venv"
MIN_SUPPORTED_MINOR=8
pythonPath=""
pythonVersion=""
error_occurred=false

# Step 0: Check for libpq-dev dependency (for psycopg2-binary)
echo "🔍 Checking for PostgreSQL development libraries (libpq-dev)..."
install_libpq_dev() {
    if command -v apt &> /dev/null; then
        echo "📦 Installing with apt..."
        sudo apt update && sudo apt install -y libpq-dev
    elif command -v dnf &> /dev/null; then
        echo "📦 Installing with dnf..."
        sudo dnf install -y postgresql-devel
    elif command -v yum &> /dev/null; then
        echo "📦 Installing with yum..."
        sudo yum install -y postgresql-devel
    elif command -v apk &> /dev/null; then
        echo "📦 Installing with apk..."
        sudo apk add postgresql-dev
    else
        echo "❌ Unsupported package manager. Please install libpq-dev manually."
        error_occurred=true
    fi
}

install_libpq_dev

# Step 1: Find all Python interpreters installed on the system
if [[ "$error_occurred" == false ]]; then
    echo "🔍 Searching for Python interpreters on the system..."
    python_interpreters=$(which -a python python3 2>/dev/null)
    unique_interpreters=$(echo "$python_interpreters" | tr ' ' '\n' | while read -r python_exec; do
        readlink -f "$python_exec"
    done | sort -u)

    for python_exec in $unique_interpreters; do
        if [[ "$python_exec" != *"$VIRTUAL_ENV_DIR"* ]]; then
            version_output=$("$python_exec" --version 2>/dev/null)
            if [[ $? -eq 0 ]]; then
                echo "✅ Found: $version_output at $python_exec"
                pythonPath="$python_exec"
            fi
        fi
    done

    if [[ -z "$pythonPath" ]]; then
        echo "❌ Error: No Python interpreter found on the system. Please install Python and try again."
        error_occurred=true
    fi
fi

# Step 2: Check Python version
if [[ "$error_occurred" == false ]]; then
    echo "🔢 Determining the version of the selected Python interpreter..."
    pythonVersion=$("$pythonPath" --version 2>/dev/null | awk '{print $2}')
    echo "🐍 Using Python at: $pythonPath (version $pythonVersion)"

    IFS='.' read -r major minor patch <<< "$pythonVersion"
    if [[ "$major" -le 3 && "$minor" -lt "$MIN_SUPPORTED_MINOR" ]]; then
        echo "❌ Error: Python version $pythonVersion is not supported. Upgrade to Python >= 3.$MIN_SUPPORTED_MINOR."
        error_occurred=true
    fi
fi

# Step 3: Install pip if missing
if [[ "$error_occurred" == false ]]; then
    echo "🔧 Checking if pip is installed..."
    if ! "$pythonPath" -m pip --version >/dev/null 2>&1; then
        echo "📥 pip not found. Installing..."
        curl -sS https://bootstrap.pypa.io/get-pip.py | "$pythonPath"
        if [[ $? -ne 0 ]]; then
            echo "❌ Error: Failed to install pip."
            error_occurred=true
        else
            echo "✅ pip installed successfully."
        fi
    fi
fi

# Step 4: Create and activate virtual environment
if [[ "$error_occurred" == false ]]; then
    echo "📦 Creating virtual environment in '$VIRTUAL_ENV_DIR'..."
    "$pythonPath" -m venv "$VIRTUAL_ENV_DIR"
    if [[ $? -ne 0 ]]; then
        echo "❌ Error: Failed to create virtual environment."
        error_occurred=true
    else
        echo "✅ Virtual environment created."
        echo "⚙️  Activating virtual environment..."
        source "$VIRTUAL_ENV_DIR/bin/activate"

        # Step 5: Upgrade pip inside venv
        echo "🔼 Upgrading pip inside virtual environment..."
        python -m pip install --upgrade pip
        if [[ $? -ne 0 ]]; then
            echo "❌ Error: Failed to upgrade pip inside venv."
            error_occurred=true
        fi

        # Step 6: Install requirements
        if [[ "$error_occurred" == false && -f requirements.txt ]]; then
            echo "📜 Installing packages from requirements.txt..."
            pip install --only-binary=:all: -r requirements.txt
            if [[ $? -ne 0 ]]; then
                echo "❌ Error: Failed to install some packages from requirements.txt."
                error_occurred=true
            else
                echo "✅ All packages installed successfully."
            fi
        elif [[ "$error_occurred" == false ]]; then
            echo "⚠️  No requirements.txt found. Skipping package installation."
        fi

        deactivate
        echo "🔚 Virtual environment deactivated."
    fi
fi

# Final output
if [[ "$error_occurred" == true ]]; then
    echo "❌ Setup failed due to errors."
else
    echo "✅ Setup completed successfully!"
fi
