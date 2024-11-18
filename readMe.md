# CUPS Print Server

A lightweight print server that enables network printing through a REST API. This server discovers local and network printers using CUPS and Zero-configuration networking (Zeroconf), allowing for easy printer discovery and management.

## Features

- 🖨️ Automatic printer discovery (local CUPS and network printers)
- 🌐 RESTful API for print operations
- 🔒 Secure printing with API key authentication
- 📊 Print job status tracking
- ✨ Support for printer options and configurations
- 🧪 Built-in test script for printer verification

## Prerequisites

- Python 3.7 or higher
- CUPS (Common Unix Printing System)
- Virtual environment (venv)

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install libcups2-dev python3-venv
```

#### macOS
```bash
brew install cups
```

## Quick Start

1. Clone the repository:
```bash
git clone [your-repository-url]
cd cups-print-server
```

2. Run the setup script:
```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Check for Python installation
- Set up virtual environment
- Install required dependencies
- Optionally start the server

## Manual Setup

If you prefer manual setup:

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the server:
```bash
python app.py
```

## Testing

A test script is included to verify printer functionality:

```bash
python test_print.py
```

The test script provides:
- Interactive printer selection
- Test page generation
- Print job submission
- Job status monitoring

## API Endpoints

### Get Printers
```http
GET /printers
Header: X-API-Key: your_api_key
```

### Add Printer
```http
POST /printers/add
Header: X-API-Key: your_api_key
Content-Type: application/json

{
    "printer": {
        "name": "PrinterName",
        "address": "192.168.1.100",
        "port": 631,
        "properties": {
            "manufacturer": "HP",
            "note": "Office Printer"
        }
    }
}
```

### Print File
```http
POST /print
Headers:
  X-API-Key: your_api_key
  Content-Type: application/pdf
  Printer-Name: PrinterName
```

### Check Job Status
```http
GET /job/<job_id>
Header: X-API-Key: your_api_key
```

## Security Features

- API key authentication
- Request rate limiting
- Input validation
- Secure file handling
- CORS protection
- Maximum file size limits

## Configuration

The server can be configured through environment variables:

```bash
export PRINT_SERVER_API_KEY=your_api_key
export PRINT_SERVER_PORT=3000
```

## File Structure

```
cups-print-server/
├── app.py              # Main print server
├── test_print.py       # Test utility
├── setup.sh           # Setup script
├── requirements.txt    # Python dependencies
└── README.md          # Documentation
```

## Common Issues

### CUPS Connection Error
If you see CUPS connection errors, ensure the CUPS service is running:
```bash
# Ubuntu/Debian
sudo service cups start

# macOS
sudo cupsctl start
```

### Permission Issues
Ensure your user has the correct permissions:
```bash
# Add user to lpadmin group (Ubuntu/Debian)
sudo usermod -a -G lpadmin $USER
```


---

Made by Peter Sharma
