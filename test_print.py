import requests
import json
import time
from reportlab.pdfgen import canvas
import logging
from pathlib import Path
import sys
from typing import Dict, Any, Optional

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

    def get_printers(self) -> bool:
        """Fetch and store available printers"""
        try:
            response = requests.get(f'{self.base_url}/printers')
            response.raise_for_status()
            data = response.json()
            
            # Store printers
            self.printers = {
                'local': data['local'],
                'network': data['network']
            }
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get printers: {e}")
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
            c.drawString(100, 680, f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            c.drawString(100, 660, "If you can read this, the test print was successful!")
            
            c.save()
            return filename
        except Exception as e:
            logger.error(f"Failed to create test print: {e}")
            return None

    def send_test_print(self) -> bool:
        """Send test print to selected printer"""
        if not self.selected_printer:
            logger.error("No printer selected")
            return False

        pdf_file = self.create_test_print()
        if not pdf_file:
            return False

        try:
            with open(pdf_file, 'rb') as f:
                response = requests.post(
                    f'{self.base_url}/print',
                    headers={
                        'Content-Type': 'application/pdf',
                        'Printer-Name': self.selected_printer
                    },
                    data=f
                )
                response.raise_for_status()
                
                result = response.json()
                job_id = result.get('job_id')
                if job_id:
                    logger.info(f"Print job submitted successfully. Job ID: {job_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to send test print: {e}")
            return False
        finally:
            pdf_file.unlink(missing_ok=True)

    def main_menu(self):
        """Display and handle main menu"""
        while True:
            print("\nMain Menu")
            print("-" * 50)
            print("1. Select Printer")
            print("2. Send Test Print")
            print("3. Exit")
            
            choice = input("\nEnter your choice (1-3): ")
            
            if choice == '1':
                self.select_printer()
            elif choice == '2':
                if not self.selected_printer:
                    print("\nPlease select a printer first.")
                    continue
                    
                confirm = input(f"\nSend test print to {self.selected_printer}? (y/n): ")
                if confirm.lower() == 'y':
                    if self.send_test_print():
                        print("Test print sent successfully!")
                    else:
                        print("Failed to send test print.")
            elif choice == '3':
                print("\nGoodbye!")
                break
            else:
                print("\nInvalid choice. Please try again.")

def main():
    tester = PrinterTester()
    
    # Check if we can connect to the print server
    try:
        if not tester.get_printers():
            logger.error("Failed to connect to print server. Is it running?")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error connecting to print server: {e}")
        sys.exit(1)

    # Start the interactive menu
    tester.main_menu()

if __name__ == '__main__':
    main()