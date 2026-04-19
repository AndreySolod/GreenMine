self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  if (event.data) {
    try {
      const pushData = event.data.json();

      const notificationOptions = {
        body: pushData.body,
        icon: pushData.icon ,
        badge: pushData.icon, // For android, 72x72
        //image: pushData.image,
        tag: pushData.tag || 'default',
        data: { url: pushData.url },
        requireInteraction: pushData.requireInteraction || false,
        silent: pushData.silent || false,
        vibrate: pushData.vibrate || [200, 100, 200],
        timestamp: new Date(pushData.timestamp),
        actions: pushData.actions || []
      };
      
      self.registration.showNotification(pushData.title, notificationOptions);
    } catch (error) {
      console.error('Push notification error:', error);
    }
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
    event.waitUntil(
    clients.openWindow(event.notification.data.url)
    );
});