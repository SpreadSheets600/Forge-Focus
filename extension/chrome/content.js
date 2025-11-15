// Content script - runs on every page
(function() {
  'use strict';

  const currentDomain = window.location.hostname;

  // Check if current site is blocked
  chrome.runtime.sendMessage(
    { action: 'checkBlocked', domain: currentDomain },
    (response) => {
      if (response && response.blocked) {
        // Site is blocked, content will be replaced by background script redirect
        console.log('Site is blocked by FocusForge');
      }
    }
  );

  // Track time on page
  let pageStartTime = Date.now();

  // Send activity before leaving
  window.addEventListener('beforeunload', () => {
    const timeSpent = (Date.now() - pageStartTime) / 1000;
    
    // Use sendBeacon for reliability
    const data = {
      domain: currentDomain,
      url: window.location.href,
      title: document.title,
      timestamp: new Date().toISOString(),
      duration: timeSpent
    };

    navigator.sendBeacon(
      'http://localhost:8765/website-activity',
      JSON.stringify(data)
    );
  });
})();
