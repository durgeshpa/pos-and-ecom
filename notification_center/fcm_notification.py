from pyfcm import FCMNotification

fcm_api_key = "AIzaSyBwgNHtPPmzowWBRZ_ny3HYypoYQ_P8eGE"
 
push_service = FCMNotification(api_key=fcm_api_key)
 
# OR initialize with proxies
 
proxy_dict = {
          "http"  : "http://127.0.0.1",
          "https" : "http://127.0.0.1",
        }
push_service = FCMNotification(api_key=fcm_api_key, proxy_dict=proxy_dict)
 
# Your api-key can be gotten from:  https://console.firebase.google.com/project/<project-name>/settings/cloudmessaging
 

def send_fcm_notification(registration_ids=[], message_title="", message_body=""):

	# Send to multiple devices by passing a list of ids.
	registration_ids = ["<device registration_id 1>", "<device registration_id 2>", ...]
	message_title = "test title"
	message_body = "test message"
	result = push_service.notify_multiple_devices(registration_ids=registration_ids, message_title=message_title, message_body=message_body)
	 
	print result