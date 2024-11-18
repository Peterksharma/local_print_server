// API base URL
const API_URL = 'http://localhost:3000';

// Refresh printer list
async function refreshPrinters() {
    try {
        const response = await fetch(`${API_URL}/printers`);
        const printers = await response.json();
        const printerList = document.getElementById('printerList');
        const printerSelect = document.getElementById('selectedPrinter');
        
        // Clear existing lists
        printerList.innerHTML = '';
        printerSelect.innerHTML = '';
        
        // Add printers to both lists
        printers.forEach(printer => {
            // Add to printer list
            const listItem = document.createElement('div');
            listItem.className = 'list-group-item';
            listItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-0">${printer.name}</h6>
                        <small class="text-muted">${printer.address}</small>
                    </div>
                    <span class="badge bg-success">Online</span>
                </div>
            `;
            printerList.appendChild(listItem);
            
            // Add to printer select
            const option = document.createElement('option');
            option.value = printer.name;
            option.textContent = printer.name;
            printerSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error fetching printers:', error);
        alert('Failed to fetch printers. Please try again.');
    }
}

// Add network printer
document.getElementById('addPrinterForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const name = document.getElementById('printerName').value;
    const address = document.getElementById('printerAddress').value;
    
    try {
        const response = await fetch(`${API_URL}/add_printer`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, address }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to add printer');
        }
        
        alert('Printer added successfully!');
        refreshPrinters();
        document.getElementById('addPrinterForm').reset();
    } catch (error) {
        console.error('Error adding printer:', error);
        alert(error.message || 'Failed to add printer. Please try again.');
    }
});

// Handle file printing
document.getElementById('printForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const printer = document.getElementById('selectedPrinter').value;
    const file = document.getElementById('fileInput').files[0];
    
    if (!file) {
        alert('Please select a file to print');
        return;
    }
    
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert('Only PDF files are supported');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('printer', printer);
    
    try {
        const response = await fetch(`${API_URL}/print`, {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to print file');
        }
        
        const result = await response.json();
        alert(`Print job submitted! Job ID: ${result.job_id}`);
        document.getElementById('printForm').reset();
        updateJobStatus(result.job_id);
    } catch (error) {
        console.error('Error printing file:', error);
        alert(error.message || 'Failed to print file. Please try again.');
    }
});

// Update job status
async function updateJobStatus(jobId) {
    try {
        const response = await fetch(`${API_URL}/job_status/${jobId}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to get job status');
        }
        
        const status = await response.json();
        const jobList = document.getElementById('jobList');
        const jobItem = document.createElement('div');
        jobItem.className = 'list-group-item';
        jobItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-0">Job #${jobId}</h6>
                    <small class="text-muted">${status.printer}</small>
                </div>
                <span class="badge ${status.status === 'completed' ? 'bg-success' : 'bg-primary'}">${status.status}</span>
            </div>
        `;
        jobList.insertBefore(jobItem, jobList.firstChild);
        
        // If job is not in a final state, poll for updates
        if (!['completed', 'canceled', 'aborted'].includes(status.status)) {
            setTimeout(() => updateJobStatus(jobId), 5000);
        }
    } catch (error) {
        console.error('Error updating job status:', error);
    }
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    refreshPrinters();
});
