from crypt import methods
import dateparser
import datetime
import time
from dateparser.search import search_dates
import json
import requests
from pension_maps import * 
from flask import Flask, request, jsonify
from re import sub
from decimal import Decimal

app = Flask(__name__)
base_url = "https://va-gdit.demo.hyperscience.com/"
endpoint = "api/v5/submissions"
endpoint_url = base_url + endpoint
auth_token = "85d17abd54e7ac1ce828fa2087ea645ca1a193dc"
headers = {'Authorization': 'Token ' + auth_token}

def hs_submit_document():
    folder = '/Users/niranjan/Library/CloudStorage/OneDrive-Personal/GDIT/01 2022 02 VICCS Pension Automation/demo/'
    files = [
            ('file', ('scenario1.pdf', open(folder+'Scenario 1- EP180 Veterans Pension Grant.pdf', 'rb'), 'application/pdf'))
        ]
    r = requests.post(endpoint_url, headers=headers, files=files)
    print(json.dumps(r.json(), indent=4, sort_keys=True))
    saved_submission_id = r.json()['submission_id']
    return saved_submission_id

def hs_check_status(saved_submission_id):
    endpoint = f"api/v5/submissions/{saved_submission_id}?flat=true"
    endpoint_url = base_url + endpoint
    r = requests.get(endpoint_url, headers=headers)
    print(json.dumps(r.json(), indent=4, sort_keys=True))
    hs_payload = r.json()
    hs_processing_state = hs_payload['state']
    return hs_processing_state

def hs_fetch_extracted_data(saved_submission_id):
    endpoint = f"api/v5/submissions/{saved_submission_id}?flat=false"
    endpoint_url = base_url + endpoint
    r = requests.get(endpoint_url, headers=headers)
    print(json.dumps(r.json(), indent=4, sort_keys=True))
    hs_payload = r.json()
    hs_processing_state = hs_payload['state']
    if hs_processing_state == 'complete':
        return hs_payload
    else:
        return {'error': 'Hyperscience process not complete'}

def build_response(hs_payload, f):
    response_payload = {}
    document_list =[]
    for document in hs_payload['documents']:
        document_list.append(document['layout_name'])
        if document['layout_name'] in map_of_maps.keys():
            mapped_data = {}
            document_map = map_of_maps[document['layout_name']]
            arrayconversion_list = array_conversion_list_map[document['layout_name']]
            field_concat_list = field_concat_map[document['layout_name']]
            mcc_list = multi_choice_conv_map[document['layout_name']]
            checkbox_conv_list = checkbox_conversion_map[document['layout_name']]
            for doc_field in document['document_fields']:
                hs_field = doc_field['name']
                try:
                    mapped_field = document_map[hs_field]
                    if not '.' in mapped_field:
                        mapped_data[mapped_field] = doc_field['transcription']['raw']
                    else:
                        mapped_field_split = mapped_field.split('.')
                        if len(mapped_field_split) == 2:
                            if mapped_field_split[0] in mapped_data.keys():
                                mapped_data[mapped_field_split[0]][mapped_field_split[1]] = doc_field['transcription']['raw']
                            else:
                                mapped_data[mapped_field_split[0]] = {}
                                mapped_data[mapped_field_split[0]][mapped_field_split[1]] = doc_field['transcription']['raw']
                        if len(mapped_field_split) == 3:
                            if mapped_field_split[0] in mapped_data.keys():
                                if mapped_field_split[1] in mapped_data[mapped_field_split[0]].keys():
                                    mapped_data[mapped_field_split[0]][mapped_field_split[1]][mapped_field_split[2]] = doc_field['transcription']['raw']
                                else:
                                    mapped_data[mapped_field_split[0]][mapped_field_split[1]] = {}
                                    mapped_data[mapped_field_split[0]][mapped_field_split[1]][mapped_field_split[2]] = doc_field['transcription']['raw']
                            else:
                                mapped_data[mapped_field_split[0]] = {}
                                mapped_data[mapped_field_split[0]][mapped_field_split[1]] = {}
                                mapped_data[mapped_field_split[0]][mapped_field_split[1]][mapped_field_split[2]] = doc_field['transcription']['raw']
                except KeyError as e:
                    #f.write(f"Key Not found in Map for {document['layout_name']} for: {hs_field}\n")
                    j=1

            #Convert individual keys to arrays in each document
            for arrayconversion_item in arrayconversion_list:
                if not '.' in arrayconversion_item:
                    mapped_data[arrayconversion_item] = []
                    for i in range(0,20):
                        if arrayconversion_item + str(i) in mapped_data.keys():
                            mapped_data[arrayconversion_item].append(mapped_data[arrayconversion_item + str(i)])
                            mapped_data.pop(arrayconversion_item + str(i))
                else:
                    conversion_item_list = arrayconversion_item.split('.')
                    mapped_data[conversion_item_list[0]][conversion_item_list[1]] = []
                    for i in range(0,15):
                        if conversion_item_list[1] + str(i) in mapped_data[conversion_item_list[0]].keys():
                            mapped_data[conversion_item_list[0]][conversion_item_list[1]].append(mapped_data[conversion_item_list[0]][conversion_item_list[1] + str(i)])
                            mapped_data[conversion_item_list[0]].pop(conversion_item_list[1] + str(i))

            #Concatenate fields as necessary
            for field_concat_item in field_concat_list:
                base_key = field_concat_item[0]
                for i in range(1, len(field_concat_item)):
                    mapped_data[base_key] = mapped_data[base_key] + ', ' + mapped_data[field_concat_item[i]]
                    mapped_data.pop(field_concat_item[i])

            #Multiple Choice conversion data
            for mcc_item in mcc_list:
                base_key = mcc_item[0]
                for i in range(1, len(mcc_item)):
                    if '.' not in base_key:
                        if mapped_data[base_key][mcc_item[i]] == 'True':
                            mapped_data[base_key] = mcc_item[i]
                            break
                    else:
                        #print(base_key)
                        mapped_data[base_key.split('.')[0]][base_key.split('.')[1]] = mcc_item[i]
                    #mapped_data[base_key].pop(mcc_item[i])

            #Checkbox conversion data
            for cc_item in checkbox_conv_list:
                if '.' not in cc_item:
                    if mapped_data[cc_item]['true'] == 'True':
                        mapped_data[cc_item] = True
                    else:
                        mapped_data[cc_item] = False 
                else:
                    #print(cc_item)
                    if mapped_data[cc_item.split('.')[0]][cc_item.split('.')[1]]['true'] == 'True':
                        mapped_data[cc_item.split('.')[0]][cc_item.split('.')[1]] = True
                    else:
                        mapped_data[cc_item.split('.')[0]][cc_item.split('.')[1]] = False 

            #Convert date formats as necessary - Search Dates
            for date_field in search_date_map[document['layout_name']]:
                extracted_date = search_dates(mapped_data[date_field], settings={'RELATIVE_BASE': datetime.datetime(datetime.datetime.now().year, 1, 1), 'PREFER_DATES_FROM': 'past'})
                if not extracted_date == None:
                    mapped_data[date_field] = extracted_date[0][1].strftime("%m/%d/%Y")
                #dateparser.parse('2021 Jan 2nd', settings={'RELATIVE_BASE': datetime.datetime(datetime.datetime.now().year, 1, 1), 'PREFER_DATES_FROM': 'past'}).strftime("%m/%d/%Y")

            #Convert date formats as necessary - Parse Dates
            for date_field in parse_date_map[document['layout_name']]:
                if not '.' in date_field:
                    extracted_date = dateparser.parse(mapped_data[date_field], settings={'RELATIVE_BASE': datetime.datetime(datetime.datetime.now().year, 1, 1), 'PREFER_DATES_FROM': 'past'})
                    if not extracted_date == None:
                        mapped_data[date_field] = extracted_date.strftime("%m/%d/%Y")
                else:
                    if not type(mapped_data[date_field.split('.')[0]]) == list:
                        extracted_date = dateparser.parse(mapped_data[date_field.split('.')[0]][date_field.split('.')[1]], settings={'RELATIVE_BASE': datetime.datetime(datetime.datetime.now().year, 1, 1), 'PREFER_DATES_FROM': 'past'})
                        if not extracted_date == None:
                            mapped_data[date_field.split('.')[0]][date_field.split('.')[1]] = extracted_date.strftime("%m/%d/%Y")
                    else:
                        for i in range(0,len(mapped_data[date_field.split('.')[0]])):
                            extracted_date = dateparser.parse(mapped_data[date_field.split('.')[0]][i][date_field.split('.')[1]], settings={'RELATIVE_BASE': datetime.datetime(datetime.datetime.now().year, 1, 1), 'PREFER_DATES_FROM': 'past'})
                            if not extracted_date == None:
                                mapped_data[date_field.split('.')[0]][i][date_field.split('.')[1]] = extracted_date.strftime("%m/%d/%Y")

            #Append resultant mapped payload of a document to response payload
            response_payload[response_paylod_key_map[document['layout_name']]] = mapped_data

    #Convert individual keys to arrays in Response Payload
    arrayconversion_list = array_conversion_list_map['response_payload']
    for arrayconversion_item in arrayconversion_list:
        response_payload[arrayconversion_item] = []
        for i in range(0,15):
            if arrayconversion_item + str(i) in response_payload.keys():
                response_payload[arrayconversion_item].append(response_payload[arrayconversion_item + str(i)])
                response_payload.pop(arrayconversion_item + str(i))

    #convert amounts and remove empty rows from SS Inquiry
    if 'SSN Inquiry Form' in document_list or 'SSN Inquiry Form V2' in document_list:
        for i in range(0,len(response_payload['ss_inquiry'])):
            if not response_payload['ss_inquiry'][i]['premium_amount'] == '':
                response_payload['ss_inquiry'][i]['premium_amount'] = float(Decimal(sub(r'[^\d.]', '', response_payload['ss_inquiry'][i]['premium_amount'])))
            for monthly_benefit_item in list(response_payload['ss_inquiry'][i]['monthly_benefit']):
                if monthly_benefit_item['amount'] == '':
                    response_payload['ss_inquiry'][i]['monthly_benefit'].remove(monthly_benefit_item)
            for j in range(0,len(response_payload['ss_inquiry'][i]['monthly_benefit'])):
                #if not response_payload['ss_inquiry'][i]['monthly_benefit'][j]['amount'] == '':
                response_payload['ss_inquiry'][i]['monthly_benefit'][j]['amount'] = float(Decimal(sub(r'[^\d.]', '', response_payload['ss_inquiry'][i]['monthly_benefit'][j]['amount'])))

    # Add "recepient" attribute to SS Inquiry payload
    if 'ss_inquiry' in response_payload.keys():
        if len(response_payload['ss_inquiry']) == 2:
            response_payload['ss_inquiry'][0]['recepient'] = 'Veteran'
            response_payload['ss_inquiry'][1]['recepient'] = 'Spouse'
        elif len(response_payload['ss_inquiry']) == 1:
            response_payload['ss_inquiry'][0]['recepient'] = 'Claimant'

    #Remove empty rows from 8416 and format amount paid
    if 'Medical Expense Report VA 21P-8416 Dec 2021' in document_list:
        for expense_item in list(response_payload['form8416data']['expenses']):
            if expense_item['amount_paid'] == '' and expense_item['date_paid'] == '':
                response_payload['form8416data']['expenses'].remove(expense_item)
        for i in range(0,len(response_payload['form8416data']['expenses'])):
            response_payload['form8416data']['expenses'][i]['amount_paid'] = float(Decimal(sub(r'[^\d.]', '', response_payload['form8416data']['expenses'][i]['amount_paid'])))

    #Response payload restructuring for Pega input compliance for Scenario 1 and 2    
    if 'VA 21P-527EZ' in document_list:
        for key in response_payload['form527data']:
            response_payload[key] = response_payload['form527data'][key]
        response_payload['entitlement_date'] = response_payload['form0966data']['entitlement_date']
        response_payload.pop('form0966data')
        response_payload.pop('form527data')
        response_payload['spouse_name'] = response_payload['veteran_marriages']['details'][0]['whom_married']
        response_payload['spouse'] = True
        response_payload['live_in_dependents'] = 0
        response_payload['not_live_in_dependents'] = 1
        response_payload['child_support'] = 0
        response_payload.pop('marital_status')
        response_payload.pop('spouse_veteran')
    elif 'Medical Expense Report VA 21P-8416 Dec 2021' in document_list:
        response_payload['award_data'] = award_data
        for key in response_payload['form8416data']:
            response_payload[key] = response_payload['form8416data'][key]
        response_payload.pop('form8416data')
        response_payload['claim_date'] = '1/10/2022'

    return (response_payload, document_list)

def submit_pega_case(f, response_payload, document_list):
    #Pega Case payload creation and Pega API call
    pega_endpoint_url = 'https://hc86e2e-va.pegatsdemo.com:443/prweb/api/v1/cases'
    headers = {'Authorization': 'Basic c2FyaXRoYTpydWxlcw==',
            'Content-Type': 'text/plain'}
    pega_request = {
        "caseTypeID": "",
        "processID": "pyStartCase",
        "parentCaseID": "",
        "content": {}
    }
    if 'VA 21P-527EZ' in document_list:
        pega_request['caseTypeID'] = 'VA-VBAPFS-Work-VeteransPensionGrant'
        pega_request['content']['Formdata527'] = response_payload
        pega_response = requests.post(pega_endpoint_url, headers=headers, data=str(pega_request))
    elif 'Medical Expense Report VA 21P-8416 Dec 2021' in document_list:
        pega_request['caseTypeID'] = 'VA-VBAPFS-Work-MedicalExpenseAdjustment'
        pega_request['content']['Formdata527'] = response_payload
        pega_response = requests.post(pega_endpoint_url, headers=headers, data=str(pega_request))
    f.write('Pega Response payload:\n')
    f.write(json.dumps(pega_response.json(), indent=4, sort_keys=False))
    return pega_response

@app.route('/hs-translate/<submission_id>')
def hs_translate(submission_id):
    f = open("logs/runlog"+datetime.datetime.now().strftime("%m%d%Y")+".txt", "a+")
    start_time = time.time()
    f.write(f"\n***hs-translate run for {submission_id} started at: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} *** \n")
    headers = request.headers
    auth = headers.get("X-Api-Key")
    response_payload = {}
    status_code = 0
    if auth == '85d17abd54e7ac1ce828fa2087ea645ca1a193dc':
        #submission_id = '38' #hs_submit_document()
        hs_status = hs_check_status(submission_id)
        if hs_status == 'complete':
            hs_payload = hs_fetch_extracted_data(submission_id)
            (response_payload, document_list) = build_response(hs_payload, f)
            f.write('Response Payload:\n')
            f.write(json.dumps(response_payload, indent=4))
            status_code = 200
        else:
            f.write('Response Payload:\n')
            response_payload = {"message": "ERROR: Submission id not complete."}
            status_code = 401    
    else:
        f.write('Response Payload:\n')
        response_payload = {"message": "ERROR: Unauthorized"}
        status_code = 401
    
    f.write(f"\n***Completed Execution for submission id: {submission_id}. Execution took  {time.time() - start_time} seconds***")
    return jsonify(response_payload), status_code

@app.route('/hs-submission', methods = ['POST'])
def hs_submission():
    f = open("logs/runlog"+datetime.datetime.now().strftime("%m%d%Y")+".txt", "a+")
    start_time = time.time()
    f.write(f"\n***hs-submission started at: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} *** \n")
    headers = request.headers
    auth = headers.get("X-Api-Key")
    response_payload = {}
    status_code = 0
    if auth == '85d17abd54e7ac1ce828fa2087ea645ca1a193dc':
        request_payload = request.form
        f.write('Request Payload:\n')
        f.write(json.dumps(request_payload, indent=4))
        submission_id = request_payload['submission-id']
        hs_status = hs_check_status(submission_id)
        #response_payload = request_payload
        response_payload['submission-id'] = request_payload['submission-id']
        response_payload['case-id'] = request_payload['case-id']
        response_payload['hs-status'] = hs_status
        status_code = 200
        f.write('Response Payload:\n')
        f.write(json.dumps(response_payload, indent=4))
    else:
        response_payload = {"message": "ERROR: Unauthorized"}
        status_code = 401
    f.write(f"\n***Completed Execution hs-submission. Execution took  {time.time() - start_time} seconds***\n")
    return jsonify(response_payload), status_code

@app.route('/pega-submission/<submission_id>')
def pega_submission(submission_id):
    f = open("logs/runlog"+datetime.datetime.now().strftime("%m%d%Y")+".txt", "a+")
    start_time = time.time()
    f.write(f"\n***pega-submission run for {submission_id} started at: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} *** \n")
    headers = request.headers
    auth = headers.get("X-Api-Key")
    response_payload = {}
    status_code = 0
    if auth == '85d17abd54e7ac1ce828fa2087ea645ca1a193dc':
        #submission_id = '38' #hs_submit_document()
        hs_status = hs_check_status(submission_id)
        if hs_status == 'complete':
            hs_payload = hs_fetch_extracted_data(submission_id)
            (translate_payload, document_list) = build_response(hs_payload, f)
            f.write('Translated Payload:\n')
            f.write(json.dumps(translate_payload, indent=4))
            response_payload = submit_pega_case(f, translate_payload, document_list)
            status_code = response_payload.status_code
            response_payload = json.loads(response_payload.text)
            f.write('Response Payload:\n')
            f.write(json.dumps(response_payload, indent=4))
            
        else:
            f.write('Response Payload:\n')
            response_payload = {"message": "ERROR: Submission id not complete."}
            status_code = 401    
    else:
        f.write('Response Payload:\n')
        response_payload = {"message": "ERROR: Unauthorized"}
        status_code = 401
    
    f.write(f"\n***Completed Execution for submission id: {submission_id}. Execution took  {time.time() - start_time} seconds***\n")
    return jsonify(response_payload), status_code


if __name__ == '__main__':
    #app.run(host='127.0.0.1', port=5000)
    app.run(host='0.0.0.0', port=5000)