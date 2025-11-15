// Background service worker for FocusForge extension
const API_URL = 'http://localhost:8765';

let currentDomain = null;
let startTime = null;
let isBlocked = false;

// Track active tab
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  handleTabChange(tab);
});

// Track URL changes
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.active) {
    handleTabChange(tab);
  }
});

// Handle tab change
async function handleTabChange(tab) {
  // Save previous activity
  if (currentDomain && startTime) {
    const now = new Date();
    const duration = Math.max(1, Math.floor((now - startTime) / 1000));
    await saveActivity(currentDomain, tab.url, tab.title, duration);
  }

  // Get new domain
  const url = new URL(tab.url || 'about:blank');
  const newDomain = url.hostname;

  // Check if blocked
  const blocked = await checkIfBlocked(newDomain);
  
  if (blocked) {
    // Redirect to blocked page
    chrome.tabs.update(tab.id, {
      url: chrome.runtime.getURL('blocked.html') + `?site=${encodeURIComponent(newDomain)}`
    });
  } else {
    currentDomain = newDomain;
    startTime = new Date();
  }
}

// Save activity to API
async function saveActivity(domain, url, title, durationSeconds) {
  try {
    const response = await fetch(`${API_URL}/website-activity`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        domain: domain,
        url: url,
        title: title,
        timestamp: new Date().toISOString(),
        duration: durationSeconds
      })
    });

    if (!response.ok) {
      console.error('Failed to save activity:', response.statusText);
    }
  } catch (error) {
    console.error('Error saving activity:', error);
  }
}

// Check if website is blocked
async function checkIfBlocked(domain) {
  try {
    const response = await fetch(`${API_URL}/website-activity/check-blocked/${encodeURIComponent(domain)}`);
    const data = await response.json();
    return data.blocked || false;
  } catch (error) {
    console.error('Error checking blocked status:', error);
    return false;
  }
}

// Periodic activity save (every 10 seconds)
chrome.alarms.create('saveActivity', { periodInMinutes: 1/6 }); // 10 seconds

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'saveActivity' && currentDomain && startTime) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        const now = new Date();
        const duration = Math.max(1, Math.floor((now - startTime) / 1000));
        saveActivity(currentDomain, tabs[0].url, tabs[0].title, duration);
        startTime = now; // Reset timer
      }
    });
  }
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'checkBlocked') {
    checkIfBlocked(request.domain).then(blocked => {
      sendResponse({ blocked });
    });
    return true; // Keep channel open for async response
  }
});

console.log('FocusForge extension loaded');
