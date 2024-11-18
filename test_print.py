import requests
import json
import time
from reportlab.pdfgen import canvas
import logging
from pathlib import Path
import sys
from typing import Dict, Any, Optional
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PrinterTester:
    def __init__(self, host='localhost', port=3000):
        self.host = host
        self.port = port
        self.base_url = f'http://{host}:{port}'
        self.printers: Dict[str, Any] = {}
        self.selected_printer: Optional[str] = None
        # Get API key from environment or use default test key
        self.api_key = os.environ.get('PRINT_SERVER_API_KEY', 'test_key')

    def get_printers(self):
        try:
            response = requests.get(f'{self.base_url}/printers')
            response.raise_for_status()  # Raises an HTTPError for bad responses
            data = response.json()
            
            # Debug print to see the actual structure
            print("Received data:", data)
            
            # Check if data exists and has the expected structure
            if not data:
                print("No printer data received")
            return False

            # Safely access the data with get() method
            printers = []
            for printer in data.get('printers', []):
                printer_info = {
                    'name': printer.get('name'),
                    'local': printer.get('local', False),  # Default to False if not present
                    'state': printer.get('state'),
                    'accepting': printer.get('accepting', False),  # Default to False if not present
                    'shared': printer.get('shared', False),  # Default to False if not present
                    'uri': printer.get('uri')
                }
                printers.append(printer_info)
                
            self.printers = printers
                    return True
        except requests.exceptions.RequestException as e:
            print(f"Error fetching printers: {e}")
            return False
        except KeyError as e:
            print(f"Error parsing printer data: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

    def display_printer_menu(self) -> list:
        """Display printer selection menu and return list of printer names"""
        print("\nAvailable Printers:")
        print("-" * 50)
        
        printer_list = []
        
        # Display local printers
        if self.printers['local']:
            print("\nLocal Printers:")
            for idx, (name, details) in enumerate(self.printers['local'].items(), 1):
                print(f"{idx}. {name}")
                print(f"   Status: {details.get('printer-state-message', 'No status message')}")
                print(f"   State: {details.get('printer-state', 'Unknown')}")
                print(f"   Location: {details.get('printer-location', 'No location set')}")
                printer_list.append(name)

        # Display network printers
        if self.printers['network']:
            print("\nNetwork Printers:")
            start_idx = len(printer_list) + 1
            for idx, (name, details) in enumerate(self.printers['network'].items(), start_idx):
                print(f"{idx}. {name}")
                print(f"   Address: {details['address']}:{details['port']}")
                if 'properties' in details:
                    if 'ty' in details['properties']:
                        print(f"   Model: {details['properties']['ty']}")
                    if 'note' in details['properties']:
                        print(f"   Note: {details['properties']['note']}")
                printer_list.append(name)

        return printer_list

    def select_printer(self) -> bool:
        """Interactive printer selection"""
        printer_list = self.display_printer_menu()
        
        if not printer_list:
            logger.error("No printers available")
            return False
        
        while True:
            try:
                choice = input("\nEnter the number of the printer to use (or 'q' to quit): ")
                if choice.lower() == 'q':
                    return False
                
                idx = int(choice) - 1
                if 0 <= idx < len(printer_list):
                    self.selected_printer = printer_list[idx]
                    print(f"\nSelected printer: {self.selected_printer}")
                    return True
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def create_test_print(self) -> Optional[Path]:
        """Create a test print PDF"""
        try:
            filename = Path('test_print.pdf')
            c = canvas.Canvas(str(filename))
            c.setFont("Helvetica-Bold", 24)
            c.drawString(100, 750, "Test Print")
            
            c.setFont("Helvetica", 14)
            c.drawString(100, 700, f"Printer: {self.selected_printer}")
            c.drawString(100, 680, f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            c.setFont("Helvetica", 12)
            c.drawString(100, 600, "This is a test print to verify printer connectivity.")
            c.drawString(100, 580, "If you can read this, the print job was successful!")
            
            c.save()
            return filename
        except Exception as e:
            logger.error(f"Failed to create test print PDF: {e}")
            return None

    def submit_print_job(self, pdf_file: Path) -> bool:
        """Submit a print job to the selected printer"""
        if not self.selected_printer:
            logger.error("No printer selected")
            return False

        try:
            with open(pdf_file, 'rb') as f:
                files = {'file': ('test_print.pdf', f, 'application/pdf')}
                data = {'printer': self.selected_printer}
                response = requests.post(
                    f'{self.base_url}/print',
                    files=files,
                    data=data,
                    headers={'X-API-Key': self.api_key}
                )
                response.raise_for_status()
                job_id = response.json().get('job_id')
                print(f"Print job submitted successfully. Job ID: {job_id}")
                return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to submit print job: {e}")
            return False

def main():
    tester = PrinterTester()
    
    # Get available printers
    if not tester.get_printers():
        sys.exit(1)
    
    # Select printer
    if not tester.select_printer():
        sys.exit(1)
    
    # Create test print
    pdf_file = tester.create_test_print()
    if not pdf_file:
        sys.exit(1)
    
    # Submit print job
    if not tester.submit_print_job(pdf_file):
        sys.exit(1)
    
    print("Test completed successfully!")

if __name__ == '__main__':
    main()