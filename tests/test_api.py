import os, tempfile
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp()
from fastapi.testclient import TestClient
from backend.main import app
client=TestClient(app)
CID='priya.sharma@gmail.com'
def email(i, subject, body, thread='th_1'):
 return {'email_id':f'em_{i}','thread_id':thread,'message_index':0,'from_name':'A','from_email':'a@b.com','to':'sales@company.com','cc':[],'subject':subject,'body':body,'received_at':'2026-08-01T09:14:22+05:30','attachments':[],'is_reply':False}
def test_bad_enum_shape():
 r=client.post('/tasks',json={'candidate_id':CID,'source_email_id':'x','thread_id':'t','title':'x','assignee_id':'Aarti','category':'triage','priority':'low','due_date':None,'deal_value_inr':None,'company_name':None,'confidence':.5})
 assert r.status_code==400 and r.json()['error']=='invalid_enum_value'
def test_ingest_idempotent_and_chat_zero():
 batch=[email(1,'RFP','RFP for platform budget Rs. 25 lakhs deadline 12 Aug 2026'),email(2,'Out of Office','I am out of office with limited access', 'th_2')]
 assert client.post('/ingest',json={'candidate_id':CID,'emails':batch}).json()['tasks_created']==1
 assert client.post('/ingest',json={'candidate_id':CID,'emails':batch}).json()['tasks_created']==0
 assert len(client.get('/tasks',params={'candidate_id':CID}).json())==1
 assert client.post('/api/chat',json={'candidate_id':CID,'query':'How many emails were about GST refunds?'}).json()['supporting_data']['gst_refund_count']==0


def test_thread_reply_does_not_clobber_existing_due_date_or_value():
 batch=[email(10,'RFP','RFP for platform budget Rs. 25 lakhs deadline 12 Aug 2026','th_keep')]
 assert client.post('/ingest',json={'candidate_id':CID,'emails':batch}).json()['tasks_created']==1
 reply=[email(11,'Re: RFP','Just checking in, any updates?','th_keep')]
 reply[0]['is_reply']=True
 assert client.post('/ingest',json={'candidate_id':CID,'emails':reply}).json()['tasks_updated']==1
 task=client.get('/tasks',params={'candidate_id':CID,'thread_id':'th_keep'}).json()[0]
 assert task['category']=='enterprise_rfp'
 assert task['assignee_id']=='u_aarti'
 assert task['deal_value_inr']==2500000
 assert task['due_date']=='2026-08-12'
