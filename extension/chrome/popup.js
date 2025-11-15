// Popup script
const API_URL = 'http://localhost:8765';

// Load status on popup open
document.addEventListener('DOMContentLoaded', async () => {
  await loadFocusStatus();
  await loadStats();
  
  // Open app button
  document.getElementById('openApp').addEventListener('click', () => {
    // This would launch the desktop app
    alert('Open the FocusForge desktop app to start a focus session!');
  });
});

// Load focus session status
async function loadFocusStatus() {
  try {
    const response = await fetch(`${API_URL}/focus/status`);
    const data = await response.json();
    
    const statusContainer = document.getElementById('statusContainer');
    const statusText = document.getElementById('statusText');
    
    if (data.active) {
      statusContainer.classList.add('status-active');
      const minutes = Math.floor(data.session_duration / 60);
      statusText.innerHTML = `
        🎯 <strong>Focus Session Active</strong><br>
        ${minutes} minutes elapsed
      `;
    } else {
      statusText.textContent = '✅ No active focus session';
    }
  } catch (error) {
    document.getElementById('statusText').textContent = '⚠️ Cannot connect to app';
  }
}

// Load statistics
async function loadStats() {
  try {
    const response = await fetch(`${API_URL}/stats/daily`);
    const data = await response.json();
    
    // Count unique sites
    const siteCount = data.web_usage ? data.web_usage.length : 0;
    document.getElementById('siteCount').textContent = siteCount;
    
    // Calculate total time
    const totalSeconds = data.web_usage ? 
      data.web_usage.reduce((sum, item) => sum + item.seconds, 0) : 0;
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    document.getElementById('timeTracked').textContent = 
      hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
    
  } catch (error) {
    console.error('Error loading stats:', error);
  }
  
  // Load blocked attempts
  chrome.storage.local.get(['blockedAttempts'], (result) => {
    document.getElementById('blockedCount').textContent = result.blockedAttempts || 0;
  });
}
