# paychangu.py - UPDATED with correct endpoint and ngrok bypass

import requests
import json
import hmac
import hashlib
from datetime import datetime
import secrets
import re
from flask import current_app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PayChangu:
    def __init__(self, mode='sandbox'):
        self.mode = mode
        # The documentation shows api.paychangu.com for both sandbox and live
        # Sandbox uses sandbox keys, not a different URL
        self.base_url = "https://api.paychangu.com"
        logger.info(f"PayChangu initialized in {mode} mode with URL: {self.base_url}")

    def get_headers(self):
        """Get headers for API requests"""
        secret_key = current_app.config.get('PAYCHANGU_SECRET_KEY')
        if not secret_key:
            logger.error("PAYCHANGU_SECRET_KEY not found in config")
            raise ValueError("PayChangu secret key not configured")

        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json"
            # REMOVE ngrok-skip-browser-warning header
        }

    def initiate_mobile_money_payment(self, amount, phone_number, email, name, reference, callback_url=None):
        """
        Initiate a mobile money payment

        Args:
            amount: Payment amount (int)
            phone_number: Customer phone number (string)
            email: Customer email (string)
            name: Customer name (string)
            reference: Payment reference (string)
            callback_url: Optional custom webhook URL (string)

        Returns:
            dict: PayChangu API response
        """
        # Get operator ID
        operator_id = self.get_operator_id(phone_number)

        if not operator_id:
            logger.error(f"Could not determine operator for phone: {phone_number}")
            return {
                "status": "error",
                "message": "Unsupported mobile network. Please use Airtel or TNM."
            }

        # Format phone number - MUST be exactly 9 digits (no country code, no plus)
        mobile = re.sub(r'\D', '', str(phone_number))

        # Remove country code if present
        if mobile.startswith('265'):
            mobile = mobile[3:]
        # Remove leading zero if present
        if mobile.startswith('0'):
            mobile = mobile[1:]

        # Take last 9 digits
        mobile = mobile[-9:]

        # Ensure it's exactly 9 digits (pad with zeros if needed)
        mobile = mobile.zfill(9)

        # Ensure it's exactly 9 digits
        if len(mobile) != 9:
            logger.error(f"Mobile number must be 9 digits, got {len(mobile)}: {mobile}")
            return {
                "status": "error",
                "message": f"Mobile number must be 9 digits. Please enter your 9-digit number (e.g., 983142415)"
            }

        # Generate a charge_id (required field)
        charge_id = f"CHG-{reference}"

        # Use provided callback_url or default from config
        if not callback_url:
            callback_url = f"{current_app.config['SITE_URL']}/paychangu-webhook"

        # CORRECT PAYLOAD based on error message
        payload = {
            "amount": int(amount),  # Must be integer, not string
            "currency": "MWK",
            "mobile_money_operator_ref_id": operator_id,
            "mobile": mobile,  # Must be exactly 9 digits, no country code
            "name": name,
            "email": email,
            "reference": reference,
            "charge_id": charge_id,  # This field is required!
            "callback_url": callback_url,
            "return_url": f"{current_app.config['SITE_URL']}/payment-success",
            "description": f"myMSCE Subscription"
        }

        url = f"{self.base_url}/mobile-money/payments/initialize"
        logger.info(f"Initiating payment to: {url}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.get_headers(),  # Now includes ngrok bypass
                timeout=30
            )

            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text}")

            if response.status_code in [200, 201]:
                return response.json()
            elif response.status_code == 400:
                error_data = response.json()
                logger.error(f"Validation error: {error_data}")
                return {
                    "status": "error",
                    "message": "Payment validation failed",
                    "details": error_data
                }
            else:
                return {
                    "status": "error",
                    "message": f"Payment service error (HTTP {response.status_code})",
                    "details": response.text
                }

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Payment error: {str(e)}"
            }

    def generate_charge_id(self, reference):
        """Generate a unique charge ID for PayChangu"""
        import hashlib
        import time

        # Create a unique string using reference and timestamp
        unique_string = f"{reference}-{time.time()}"
        # Create a hash to ensure it's a valid format
        hash_object = hashlib.md5(unique_string.encode())
        charge_id = f"CHG-{hash_object.hexdigest()[:12].upper()}"
        return charge_id



    def get_operator_id(self, phone_number):
        """
        Determine mobile money operator from phone number
        """
        # Clean the phone number - remove all non-digits
        phone = re.sub(r'\D', '', str(phone_number))
        logger.info(f"Cleaned phone number: {phone}")

        # Handle country code
        if phone.startswith('265'):
            phone = phone[3:]

        # Handle leading zero
        if phone.startswith('0'):
            phone = phone[1:]

        # Take last 9 digits
        phone = phone[-9:]

        # Get prefix (first 2 digits of the 9-digit number)
        if len(phone) >= 2:
            prefix = phone[:2]
            logger.info(f"Network prefix: {prefix}")

            # Airtel Money prefixes (98, 99)
            if prefix in ['98', '99']:
                logger.info("Detected Airtel Money")
                return "20be6c20-adeb-4b5b-a7ba-0769820df4fb"

            # TNM Mpamba prefixes (88, 89)
            elif prefix in ['88', '89']:
                logger.info("Detected TNM Mpamba")
                return "27494cb5-ba9e-437f-a114-4e7a7686bcca"

        logger.warning(f"Could not determine operator for phone: {phone_number}")
        return None

    def verify_payment(self, charge_id):
        """Verify payment status instantly with PayChangu"""
        url = f"{self.base_url}/mobile-money/payments/{charge_id}/verify"
        
        try:
            response = requests.get(
                url,
                headers=self.get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Verification response: {data}")
                
                # Check if payment is successful
                if data.get('status') == 'success':
                    payment_data = data.get('data', {})
                    payment_status = payment_data.get('status')
                    
                    if payment_status == 'success' or payment_status == 'completed':
                        return {
                            'success': True,
                            'completed': True,
                            'data': payment_data
                        }
                    else:
                        return {
                            'success': True,
                            'completed': False,
                            'status': payment_status,
                            'data': payment_data
                        }
                else:
                    return {
                        'success': False,
                        'completed': False,
                        'message': data.get('message', 'Verification failed')
                    }
            else:
                return {
                    'success': False,
                    'completed': False,
                    'message': f"HTTP {response.status_code}"
                }
        except Exception as e:
            logger.error(f"Verification error: {str(e)}")
            return {
                'success': False,
                'completed': False,
                'message': str(e)
            }