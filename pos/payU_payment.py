import requests
import hashlib
import datetime

url = "https://info.payu.in/merchant/postservice?form=2"
headers = { "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded" }
def hash_gen(trxn_id, key, commond):
    """Create hash ........."""
    salt = 'g0nGFe03'
    hash_string = "{}|{}|{}|{}".format(key, commond, trxn_id, salt)
    return hashlib.sha512(hash_string.encode()).hexdigest().lower()


def send_request_payu_api(trxn_id):
    """Send post request for very thr tranjection......."""
    key = '3TnMpV'
    commond = 'verify_payment'
    hash_value = hash_gen(trxn_id, key, commond)
    payload = "key={}&command={}&var1={}&hash={}".format(key,commond ,trxn_id,hash_value)
    print(payload)
    return requests.request("POST", url, data=payload, headers=headers).json()


def send_request_refund(payment_id, amount):
    """send request for payment refund 
       on PAYU api .....
    """
    key = '3TnMpV'
    commond = 'cancel_refund_transaction'
    hash_value = hash_gen(payment_id, key, commond)
    uniq_id = str(datetime.datetime.now())
    payload="key={}&hash={}&command={}&var1={}&var2={}&var3={}".format(key,hash_value,commond,payment_id,uniq_id,amount)
    response = requests.request("POST", url, headers=headers, data=payload).json()
    return response


def track_status_refund(request_id):
    key = '3TnMpV'
    commond = "check_action_status"
    hash_value = hash_gen(request_id, key, commond)
    payload="key={}&hash={}&command={}&var1={}".format(key,hash_value,commond,request_id)
    response = requests.request("POST", url, headers=headers, data=payload).json()
    return response

def getAllRefundsFromTxnIds(trxn_id):
    key = '3TnMpV'
    commond = 'getAllRefundsFromTxnIds'
    hash_value = hash_gen(trxn_id, key, commond)
    payload = "key={}&command={}&var1={}&hash={}".format(key,commond ,trxn_id,hash_value)
    return requests.request("POST", url, data=payload, headers=headers).json()

#print(send_request_payu_api('210196'))
#print(getAllRefundsFromTxnIds('210187'))
# # print(track_status_refund("10175461651"))
# x = send_request_refund('14621425580',.6)
# if not x.get('status'):
#     print("jjj")
# else:
#     print("hhh")

# #print(x)
# x = {"status":1,"msg":"Refund Request Queued","request_id":"10180342669","bank_ref_num":None,"mihpayid":14621425580,"error_code":102}
