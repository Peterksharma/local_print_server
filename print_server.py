from flask import Flask, request, jsonify
import cups
import zeroconf
import threading
import time
import tempfile
import os

app = Flask(__name__)

# Initialize CUPS connection
conn = cups.Connection()

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
        if info:
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
        """Handle service updates"""
        self.add_service(zc, type_, name)

# Initialize printer discovery
printer_discovery = PrinterDiscovery()
printer_discovery.start_discovery()

@app.route('/printers', methods=['GET'])
def get_printers():
    """Get both local and network printers"""
    try:
        # Get local CUPS printers
        local_printers = conn.getPrinters()
        
        # Get network printers
        network_printers = printer_discovery.printers
        
        return jsonify({
            'local': local_printers,
            'network': network_printers
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/printers/add', methods=['POST'])
def add_printer():
    """Add a network printer to CUPS"""
    try:
        data = request.get_json()
        printer_info = data['printer']
        
        # Construct printer URI
        uri = f"ipp://{printer_info['address']}:{printer_info['port']}/ipp/print"
        
        # Try to find a suitable PPD
        ppds = conn.getPPDs()
        suitable_ppd = None
        
        # Look for a matching PPD based on make/model
        if 'manufacturer' in printer_info.get('properties', {}):
            manufacturer = printer_info['properties']['manufacturer']
            for ppd_name, ppd_info in ppds.items():
                if manufacturer.lower() in ppd_info['make-and-model'].lower():
                    suitable_ppd = ppd_name
                    break
        
        # If no specific PPD found, use 'everywhere' PPD
        if not suitable_ppd:
            suitable_ppd = 'everywhere'
        
        # Add the printer
        conn.addPrinter(
            name=printer_info['name'],
            device=uri,
            ppd=suitable_ppd,
            info=printer_info.get('properties', {}).get('note', ''),
            location=printer_info.get('properties', {}).get('location', '')
        )
        
        # Enable the printer
        conn.enablePrinter(printer_info['name'])
        conn.acceptJobs(printer_info['name'])
        
        return jsonify({'message': 'Printer added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/print', methods=['POST'])
def print_file():
    """Handle print job"""
    try:
        printer_name = request.headers.get('Printer-Name')
        if not printer_name:
            return jsonify({'error': 'Printer name not specified'}), 400
            
        if not request.headers.get('Content-Type') == 'application/pdf':
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        # Create temporary file for the PDF content
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(request.get_data())
            tmp_path = tmp.name
        
        try:
            # Get printer options
            printer_options = {}
            if 'Print-Options' in request.headers:
                printer_options = request.json
            
            # Submit print job
            job_id = conn.printFile(
                printer_name,
                tmp_path,
                "Web Print Job",
                printer_options
            )
            
            return jsonify({
                'message': 'Print job submitted successfully',
                'job_id': job_id
            })
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
            
    except cups.IPPError as e:
        return jsonify({'error': f'CUPS error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/job/<int:job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get print job status"""
    try:
        jobs = conn.getJobs(which_jobs='all')
        if job_id in jobs:
            return jsonify({
                'status': jobs[job_id]['state'],
                'printer': jobs[job_id]['printer'],
                'job_id': job_id
            })
        return jsonify({'error': 'Job not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=3000)
    finally:
        printer_discovery.stop_discovery()