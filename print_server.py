from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import cups
import zeroconf
import threading
import time
import tempfile
import os
import logging
import hashlib
from functools import wraps
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
    static_url_path='/static',
    static_folder='static',
    template_folder='templates'
)

# Security configurations
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24).hex()),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    ALLOWED_EXTENSIONS={'pdf'},
    API_KEYS=set(os.environ.get('API_KEYS', 'test_key').split(','))  # Default test key for development
)

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per day", "10 per minute"]
)

# Initialize CUPS connection
conn = cups.Connection()

def require_api_key(f):
    """API key verification decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key not in app.config['API_KEYS']:
            return jsonify({'error': 'Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated

def validate_printer_name(printer_name: str) -> bool:
    """Validate printer name for security"""
    if not printer_name or len(printer_name) > 255:
        return False
    dangerous_chars = ['/', '\\', ';', '&', '|', '>', '<', '*', '$', '`', '"', "'"]
    return not any(char in printer_name for char in dangerous_chars)

class PrinterDiscovery:
    def __init__(self):
        self.zc = zeroconf.Zeroconf()
        self.browsers = []
        self.printers = {}
        
    def start_discovery(self):
        # Look for IPP printers
        service_type = "_ipp._tcp.local."
        listener = PrinterListener(self.printers)
        browser = zeroconf.ServiceBrowser(self.zc, service_type, listener)
        self.browsers.append(browser)
        
        # Look for AirPrint printers
        service_type = "_airprint._tcp.local."
        listener = PrinterListener(self.printers)
        browser = zeroconf.ServiceBrowser(self.zc, service_type, listener)
        self.browsers.append(browser)
    
    def stop_discovery(self):
        self.zc.close()

class PrinterListener:
    def __init__(self, printers_dict):
        self.printers = printers_dict

    def add_service(self, zc: zeroconf.Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info and info.parsed_addresses():
            self.printers[name] = {
                'name': name.replace('._ipp._tcp.local.', '').replace('._airprint._tcp.local.', ''),
                'address': str(info.parsed_addresses()[0]),
                'port': info.port,
                'properties': {k.decode(): v.decode() if isinstance(v, bytes) else str(v) 
                             for k, v in info.properties.items()}
            }

    def remove_service(self, zc: zeroconf.Zeroconf, type_: str, name: str) -> None:
        if name in self.printers:
            del self.printers[name]

    def update_service(self, zc: zeroconf.Zeroconf, type_: str, name: str) -> None:
        self.add_service(zc, type_, name)

# Initialize printer discovery
printer_discovery = PrinterDiscovery()
printer_discovery.start_discovery()

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/printers', methods=['GET'])
def get_printers():
    """Get both local and network printers"""
    try:
        # Get local CUPS printers
        local_printers = conn.getPrinters()
        
        # Get network printers
        network_printers = printer_discovery.printers
        
        # Format printers for the GUI
        formatted_printers = []
        
        # Add local printers
        for name, details in local_printers.items():
            formatted_printers.append({
                'name': name,
                'address': details.get('device-uri', 'Local Printer'),
                'type': 'local'
            })
            
        # Add network printers
        for name, details in network_printers.items():
            formatted_printers.append({
                'name': details['name'],
                'address': details['address'],
                'type': 'network'
            })
            
        return jsonify(formatted_printers)
    except Exception as e:
        logger.error(f"Error getting printers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/add_printer', methods=['POST'])
def add_printer():
    """Add a network printer to CUPS"""
    try:
        data = request.get_json()
        if not data or not all(key in data for key in ['name', 'address']):
            return jsonify({'error': 'Missing printer name or address'}), 400
            
        name = data['name']
        address = data['address']
        
        # Validate printer name
        if not validate_printer_name(name):
            return jsonify({'error': 'Invalid printer name'}), 400
        
        # Construct printer URI (assuming IPP protocol)
        uri = f"ipp://{address}/ipp/print"
        
        # Add printer to CUPS
        conn.addPrinter(name, device=uri)
        conn.enablePrinter(name)
        conn.acceptJobs(name)
        
        return jsonify({'message': 'Printer added successfully'})
    except Exception as e:
        logger.error(f"Error adding printer: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/print', methods=['POST'])
def print_file():
    """Handle print job"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
            
        printer_name = request.form.get('printer')
        if not printer_name or not validate_printer_name(printer_name):
            return jsonify({'error': 'Invalid or missing printer name'}), 400
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
            
            try:
                # Submit print job
                job_id = conn.printFile(
                    printer_name,
                    tmp_path,
                    f"Web Print Job {uuid.uuid4().hex[:8]}",
                    {}
                )
                
                logger.info(f"Print job {job_id} submitted to {printer_name}")
                return jsonify({
                    'message': 'Print job submitted successfully',
                    'job_id': job_id
                })
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                    
    except Exception as e:
        logger.error(f"Error processing print job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/job_status/<int:job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get print job status"""
    try:
        jobs = conn.getJobs(which_jobs='all')
        if job_id in jobs:
            status = jobs[job_id]['state']
            # Convert CUPS job state to human-readable status
            status_map = {
                3: 'pending',
                4: 'held',
                5: 'processing',
                6: 'stopped',
                7: 'canceled',
                8: 'aborted',
                9: 'completed'
            }
            return jsonify({
                'status': status_map.get(status, 'unknown'),
                'printer': jobs[job_id]['printer'],
                'job_id': job_id
            })
        return jsonify({'error': 'Job not found'}), 404
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        logger.info("Starting print server...")
        app.run(host='0.0.0.0', port=3000, debug=True)
    finally:
        printer_discovery.stop_discovery()