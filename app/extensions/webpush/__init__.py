from flask import Flask, url_for
from pywebpush import webpush, WebPushException
from py_vapid import Vapid
import cryptography.hazmat.primitives.serialization as serialization
import json
import base64
from urllib.parse import urlparse
import time
import logging
logger = logging.getLogger("WebPush")


class WebPusher:
    def __init__(self, vapid_private_key: Vapid | None = None, vapid_claims: dict | None = None,
                 app: Flask | None = None,
                 icon_path: str | None = None):
        self._vapid_private_key = vapid_private_key
        self.vapid_claims = vapid_claims
        self.static_icon_path = icon_path
        if app is not None:
            self.init_app(app)
        
    def init_app(self, app: Flask):
        self.app = app
        if 'VAPID_PRIVATE_KEY' in app.config and self._vapid_private_key is None:
            self._vapid_private_key = app.config['VAPID_PRIVATE_KEY']
        if 'VAPID_EMAIL' in app.config and self.vapid_claims is None:
            self.vapid_claims = {"sub": f"mailto:{app.config['VAPID_EMAIL']}"}
        else:
            self.vapid_claims = {"sub": "mailto:your-email@example.com"}

    def send(self, subscription_info: dict, title: str, message: str, url: str, **params):
        try:
            logger.info(f"Sending push notification to {subscription_info['endpoint']}")
            endpoint = subscription_info['endpoint']
            parsed = urlparse(endpoint)
            audience = f"{parsed.scheme}://{parsed.netloc}"

            claims = self.vapid_claims.copy() if self.vapid_claims else {}
            claims['aud'] = audience
            claims['exp'] = int(time.time()) + 3600 * 9
            data = {
                'title': title,
                'body': message,
                'icon': self.static_icon_path,
                'url': url
            }
            data.update(params)
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(data),
                vapid_private_key=self.private_key(),
                vapid_claims=claims
            )
        except WebPushException as e:
            logger.error(f"WebPushException: {e}")
    
    def public_key(self):
        return base64.urlsafe_b64encode(self._vapid_private_key.public_key.public_bytes(encoding=serialization.Encoding.X962,
                                                                                format=serialization.PublicFormat.UncompressedPoint)).decode("utf-8").replace('=', '')
    
    def private_key(self): 
        return base64.urlsafe_b64encode(self._vapid_private_key.private_key.private_bytes(encoding=serialization.Encoding.DER,
                                                    format=serialization.PrivateFormat.PKCS8,
                                                    encryption_algorithm=serialization.NoEncryption())).decode('utf-8')